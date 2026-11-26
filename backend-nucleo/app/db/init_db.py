import json
import secrets
from datetime import datetime, timezone
from app.db.database import engine, Base, get_db_context
from app.db.models import (
    AdminUserModel,
    SiteModel,
    SitePolicyModel,
    CryptoKeyModel
)
from app.core.security import hash_password
from app.core.crypto_vault import crypto_vault
from app.services.audit_service import audit_service

def init_database():
    """Inicializa el esquema de base de datos y los datos maestros iniciales."""
    Base.metadata.create_all(bind=engine)

    with get_db_context() as db:
        # 1. Bóveda Criptográfica: Clave activa Ed25519 inicial
        active_key = db.query(CryptoKeyModel).filter(CryptoKeyModel.active == 1).first()
        if not active_key:
            kid = "key-2026-01"
            _, enc_priv, pub_pem = crypto_vault.generate_ed25519_keypair(kid=kid)
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            active_key = CryptoKeyModel(
                kid=kid,
                algorithm="EdDSA",
                curve="Ed25519",
                public_key_pem=pub_pem,
                private_key_pem_encrypted=enc_priv,
                active=1,
                created_at=now_iso
            )
            db.add(active_key)
            db.commit()

            # Registrar en auditoría
            audit_service.record_action(
                db=db,
                actor_username="system",
                actor_role="security_admin",
                action="CRYPTO_VAULT_INITIALIZED",
                resource=f"kid:{kid}",
                payload_details={"algorithm": "EdDSA", "curve": "Ed25519", "kid": kid}
            )

        # 2. Sitio por defecto (vh_site_9f8e7d6c5b4a3210 según contrato)
        default_site = db.query(SiteModel).filter(SiteModel.site_id == "default").first()
        if not default_site:
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            site_key = "vh_site_9f8e7d6c5b4a3210"
            raw_secret = secrets.token_hex(32)
            enc_secret = crypto_vault.encrypt_secret(raw_secret)

            default_site = SiteModel(
                site_id="default",
                name="Portal Institucional Soberano",
                domain="gobierno.gob.ve",
                site_key=site_key,
                secret_key_encrypted=enc_secret,
                active=True,
                created_at=now_iso
            )
            db.add(default_site)

            # Política asociada al sitio por defecto
            default_policy_dict = {
                "mode": "challenge",
                "ai_thresholds": {
                    "challenge_min": 0.35,
                    "block_min": 0.75
                },
                "protected_routes": [
                    {
                        "path_prefix": "/login",
                        "methods": ["POST"],
                        "require_token": True,
                        "rate_limit_rpm": 10
                    },
                    {
                        "path_prefix": "/api/consulta",
                        "methods": ["GET", "POST"],
                        "require_token": True,
                        "rate_limit_rpm": 30
                    }
                ],
                "rate_limit_global_rpm": 120,
                "ip_whitelist": ["127.0.0.1", "10.0.0.0/8"],
                "ip_blacklist": ["198.51.100.42"]
            }

            policy_record = SitePolicyModel(
                site_id="default",
                mode="challenge",
                policy_json=json.dumps(default_policy_dict),
                updated_at=now_iso
            )
            db.add(policy_record)
            db.commit()

            audit_service.record_action(
                db=db,
                actor_username="system",
                actor_role="security_admin",
                action="DEFAULT_SITE_CREATED",
                resource="site:default",
                payload_details={"site_id": "default", "site_key": site_key}
            )

        # 3. Usuarios administrativos para los tres roles obligatorios (RBAC)
        users = [
            ("admin_seguridad", "Soberania2026!Segura", "security_admin"),
            ("operador_politicas", "Operador2026!Vzla", "operator"),
            ("auditor_fiscal", "Auditor2026!Transparente", "auditor"),
        ]

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for username, password, role in users:
            existing_user = db.query(AdminUserModel).filter(AdminUserModel.username == username).first()
            if not existing_user:
                new_user = AdminUserModel(
                    username=username,
                    password_hash=hash_password(password),
                    role=role,
                    totp_secret=None,
                    totp_enabled=False,
                    is_active=True,
                    failed_login_attempts=0,
                    locked_until=0.0,
                    created_at=now_iso
                )
                db.add(new_user)
                db.commit()

                audit_service.record_action(
                    db=db,
                    actor_username="system",
                    actor_role="security_admin",
                    action="USER_CREATED",
                    resource=f"user:{username}",
                    payload_details={"username": username, "role": role}
                )

if __name__ == "__main__":
    init_database()
