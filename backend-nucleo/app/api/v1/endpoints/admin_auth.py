import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import AdminUserModel
from app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    TOTPSetupResponse,
    TOTPVerifyRequest
)
from app.core.security import (
    verify_password,
    create_admin_access_token,
    generate_totp_secret,
    verify_totp,
    get_totp_uri,
    get_current_admin
)
from app.services.audit_service import audit_service

router = APIRouter()

@router.post(
    "/admin/auth/login",
    response_model=AdminLoginResponse,
    summary="Autenticación de Administradores con RBAC y MFA",
    description="Valida credenciales con Argon2id. Si el usuario tiene TOTP configurado, exige el segundo factor."
)
def admin_login(
    req: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(AdminUserModel).filter(AdminUserModel.username == req.username).first()
    now = time.time()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Credenciales inválidas"}
        )

    # Protección contra fuerza bruta
    if user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED", "message": "Cuenta temporalmente bloqueada por exceso de intentos fallidos. Intente más tarde."}
        )

    if not verify_password(req.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = now + 900  # Bloqueo de 15 minutos
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Credenciales inválidas"}
        )

    # Si tiene TOTP habilitado, validar código
    if user.totp_enabled:
        if not req.totp_code:
            # Retorna requerimiento de MFA
            temp_token = create_admin_access_token(user.username, "pending_mfa", expires_minutes=5)
            return AdminLoginResponse(
                mfa_required=True,
                temp_token=temp_token,
                role=user.role,
                username=user.username
            )
        if not verify_totp(user.totp_secret, req.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Código MFA/TOTP inválido"}
            )

    # Login exitoso: reiniciar intentos
    user.failed_login_attempts = 0
    user.locked_until = 0.0
    db.commit()

    token = create_admin_access_token(user.username, user.role)

    audit_service.record_action(
        db=db,
        actor_username=user.username,
        actor_role=user.role,
        action="ADMIN_LOGIN_SUCCESS",
        resource="auth:session",
        payload_details={"username": user.username, "role": user.role}
    )

    return AdminLoginResponse(
        access_token=token,
        mfa_required=False,
        role=user.role,
        username=user.username
    )

@router.post(
    "/admin/auth/setup-totp",
    response_model=TOTPSetupResponse,
    summary="Configurar Segundo Factor TOTP",
    description="Genera la semilla TOTP para configurar MFA en el usuario actual."
)
def setup_totp(
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    username = current_admin["sub"]
    user = db.query(AdminUserModel).filter(AdminUserModel.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail={"code": "INVALID_PAYLOAD", "message": "Usuario no encontrado"})

    secret = generate_totp_secret()
    user.totp_secret = secret
    db.commit()

    uri = get_totp_uri(secret, username)
    return TOTPSetupResponse(
        secret=secret,
        provisioning_uri=uri
    )

@router.post(
    "/admin/auth/verify-totp",
    summary="Confirmar y Habilitar MFA/TOTP",
    description="Verifica el código inicial y activa permanentemente el MFA en la cuenta."
)
def verify_totp_endpoint(
    req: TOTPVerifyRequest,
    current_admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    username = current_admin["sub"]
    user = db.query(AdminUserModel).filter(AdminUserModel.username == username).first()
    if not user or not user.totp_secret:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PAYLOAD", "message": "TOTP no iniciado"})

    if not verify_totp(user.totp_secret, req.totp_code):
        raise HTTPException(status_code=400, detail={"code": "INVALID_TOKEN", "message": "Código TOTP inválido"})

    user.totp_enabled = True
    db.commit()

    audit_service.record_action(
        db=db,
        actor_username=username,
        actor_role=user.role,
        action="TOTP_MFA_ENABLED",
        resource=f"user:{username}",
        payload_details={"username": username}
    )

    return {"message": "MFA/TOTP activado exitosamente"}
