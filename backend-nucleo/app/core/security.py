import time
import jwt
import pyotp
from typing import Optional, List, Dict, Any
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

ph = PasswordHasher()
security_bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Hashea una contraseña usando Argon2id."""
    return ph.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña con Argon2id."""
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False

def generate_totp_secret() -> str:
    """Genera un nuevo secreto base32 para TOTP/MFA."""
    return pyotp.random_base32()

def verify_totp(secret: str, code: str) -> bool:
    """Verifica un código TOTP de 6 dígitos con ventana de tolerancia."""
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)

def get_totp_uri(secret: str, username: str) -> str:
    """Genera URI para enrolamiento en aplicaciones de autenticación (ej. Google Authenticator, FreeOTP)."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name="Soberania-Verificacion-Humana")

def create_admin_access_token(
    username: str,
    role: str,
    expires_minutes: int = settings.ADMIN_JWT_EXPIRATION_MINUTES
) -> str:
    """Crea un token JWT de sesión administrativa."""
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + (expires_minutes * 60),
        "iss": "servicio-verificacion-humana.gob.ve/admin"
    }
    return jwt.encode(payload, settings.ADMIN_JWT_SECRET, algorithm="HS256")

def decode_admin_access_token(token: str) -> Dict[str, Any]:
    """Decodifica y valida un token JWT administrativo."""
    try:
        return jwt.decode(
            token,
            settings.ADMIN_JWT_SECRET,
            algorithms=["HS256"],
            issuer="servicio-verificacion-humana.gob.ve/admin"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": f"Token de administración inválido o expirado: {str(e)}"}
        )

def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)
) -> Dict[str, Any]:
    """Obtiene el payload del usuario autenticado en la consola administrativa."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "VERIFICATION_REQUIRED", "message": "Se requiere cabecera de autenticación Authorization: Bearer <token>"}
        )
    return decode_admin_access_token(credentials.credentials)

def require_role(allowed_roles: List[str]):
    """Dependencia de FastAPI para control de acceso RBAC estricto."""
    def role_checker(admin_user: Dict[str, Any] = Depends(get_current_admin)) -> Dict[str, Any]:
        user_role = admin_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "UNAUTHORIZED_ROLE",
                    "message": f"Acceso denegado: el rol '{user_role}' no tiene permisos suficientes para este recurso.",
                    "details": {"required_roles": allowed_roles, "current_role": user_role}
                }
            )
        return admin_user
    return role_checker
