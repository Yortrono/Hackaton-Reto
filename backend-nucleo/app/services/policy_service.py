import json
import ipaddress
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from app.db.models import SiteModel, SitePolicyModel, CryptoKeyModel
from app.schemas.contracts import SitePoliciesResponse, SitePolicy, CryptoPublicKeyInfo
from app.services.audit_service import audit_service

class PolicyService:
    """
    Servicio de Gestión y Sincronización de Políticas hacia el Reverse Proxy de Borde (Dev 2):
    Permite consultar las reglas activas de un sitio y exponer las claves públicas vigentes.
    """

    @classmethod
    def get_site_policies_response(cls, db: Session, site_id: str) -> Optional[SitePoliciesResponse]:
        # Buscar sitio por site_id o site_key
        site = db.query(SiteModel).filter(
            (SiteModel.site_id == site_id) | (SiteModel.site_key == site_id)
        ).first()

        if not site:
            return None

        policy_record = db.query(SitePolicyModel).filter(SitePolicyModel.site_id == site.site_id).first()
        if not policy_record:
            policy_data = SitePolicy()
            updated_at = site.created_at
        else:
            raw_json = json.loads(policy_record.policy_json)
            policy_data = SitePolicy(**raw_json)
            updated_at = policy_record.updated_at

        # Obtener claves públicas activas
        active_keys = db.query(CryptoKeyModel).filter(CryptoKeyModel.active == 1).all()
        crypto_public_keys = [
            CryptoPublicKeyInfo(
                kid=k.kid,
                algorithm=k.algorithm,
                curve=k.curve,
                public_key_pem=k.public_key_pem,
                active=True
            )
            for k in active_keys
        ]

        return SitePoliciesResponse(
            site_id=site.site_id,
            site_key=site.site_key,
            updated_at=updated_at,
            policy=policy_data,
            crypto_public_keys=crypto_public_keys
        )

    @classmethod
    def update_site_policy(
        cls,
        db: Session,
        site_id: str,
        new_policy: SitePolicy,
        actor_username: str,
        actor_role: str
    ) -> Optional[SitePoliciesResponse]:
        site = db.query(SiteModel).filter(SiteModel.site_id == site_id).first()
        if not site:
            return None

        policy_record = db.query(SitePolicyModel).filter(SitePolicyModel.site_id == site_id).first()
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        policy_json = new_policy.model_dump_json()

        if not policy_record:
            policy_record = SitePolicyModel(
                site_id=site_id,
                mode=new_policy.mode,
                policy_json=policy_json,
                updated_at=now_iso
            )
            db.add(policy_record)
        else:
            policy_record.mode = new_policy.mode
            policy_record.policy_json = policy_json
            policy_record.updated_at = now_iso

        db.commit()

        # Registrar en auditoría inmutable
        audit_service.record_action(
            db=db,
            actor_username=actor_username,
            actor_role=actor_role,
            action="POLICY_UPDATED",
            resource=f"site_id:{site_id}",
            payload_details=new_policy.model_dump()
        )

        return cls.get_site_policies_response(db, site_id)

    @classmethod
    def is_ip_blacklisted(cls, policy: SitePolicy, client_ip: str) -> bool:
        """Verifica si una IP se encuentra en la lista negra (soporta notación CIDR)."""
        if not policy.ip_blacklist or not client_ip:
            return False
        try:
            client_addr = ipaddress.ip_address(client_ip)
            for item in policy.ip_blacklist:
                try:
                    if "/" in item:
                        if client_addr in ipaddress.ip_network(item, strict=False):
                            return True
                    else:
                        if client_addr == ipaddress.ip_address(item):
                            return True
                except ValueError:
                    continue
        except ValueError:
            return False
        return False

    @classmethod
    def is_ip_whitelisted(cls, policy: SitePolicy, client_ip: str) -> bool:
        """Verifica si una IP se encuentra en la lista blanca (soporta notación CIDR)."""
        if not policy.ip_whitelist or not client_ip:
            return False
        try:
            client_addr = ipaddress.ip_address(client_ip)
            for item in policy.ip_whitelist:
                try:
                    if "/" in item:
                        if client_addr in ipaddress.ip_network(item, strict=False):
                            return True
                    else:
                        if client_addr == ipaddress.ip_address(item):
                            return True
                except ValueError:
                    continue
        except ValueError:
            return False
        return False

policy_service = PolicyService()
