from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import CryptoKeyModel
from app.schemas.contracts import CryptoPublicKeyInfo
from app.schemas.admin import RotateKeyResponse
from app.core.security import require_role
from app.core.crypto_vault import crypto_vault
from app.services.audit_service import audit_service

router = APIRouter()

@router.get(
    "/admin/vault/keys",
    response_model=List[CryptoPublicKeyInfo],
    summary="Listar Claves Criptográficas de la Bóveda",
    description="Exclusivo para el rol 'security_admin'. Retorna las claves públicas registradas en la bóveda."
)
def list_keys(
    current_admin: dict = Depends(require_role(["security_admin"])),
    db: Session = Depends(get_db)
):
    keys = db.query(CryptoKeyModel).all()
    return [
        CryptoPublicKeyInfo(
            kid=k.kid,
            algorithm=k.algorithm,
            curve=k.curve,
            public_key_pem=k.public_key_pem,
            active=bool(k.active)
        )
        for k in keys
    ]

@router.post(
    "/admin/vault/rotate",
    response_model=RotateKeyResponse,
    summary="Rotación Soberana de Claves Asimétricas Ed25519",
    description="Exclusivo para 'security_admin'. Genera un nuevo par Ed25519, cifra la privada con AES-256-GCM y activa la nueva clave."
)
def rotate_key(
    current_admin: dict = Depends(require_role(["security_admin"])),
    db: Session = Depends(get_db)
):
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    kid = f"key-{now_dt.strftime('%Y-%m-%d-%H%M%S')}"

    # Generar nuevo par Ed25519 y cifrar clave privada con AES-256-GCM
    _, enc_priv, pub_pem = crypto_vault.generate_ed25519_keypair(kid=kid)

    # Desactivar clave anterior
    db.query(CryptoKeyModel).filter(CryptoKeyModel.active == 1).update({"active": 0})

    # Guardar nueva clave activa
    new_key = CryptoKeyModel(
        kid=kid,
        algorithm="EdDSA",
        curve="Ed25519",
        public_key_pem=pub_pem,
        private_key_pem_encrypted=enc_priv,
        active=1,
        created_at=now_iso
    )
    db.add(new_key)
    db.commit()

    # Registrar en auditoría inmutable
    audit_service.record_action(
        db=db,
        actor_username=current_admin["sub"],
        actor_role=current_admin["role"],
        action="CRYPTO_KEY_ROTATED",
        resource=f"kid:{kid}",
        payload_details={"kid": kid, "algorithm": "EdDSA", "curve": "Ed25519"}
    )

    return RotateKeyResponse(
        kid=kid,
        algorithm="EdDSA",
        curve="Ed25519",
        created_at=now_iso,
        message="Clave asimétrica rotada y activada exitosamente"
    )
