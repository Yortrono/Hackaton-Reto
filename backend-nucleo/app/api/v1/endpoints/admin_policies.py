import secrets
import json
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import SiteModel, SitePolicyModel
from app.schemas.contracts import SitePolicy, SitePoliciesResponse
from app.schemas.admin import SiteCreateRequest, SiteResponse
from app.core.security import require_role
from app.core.crypto_vault import crypto_vault
from app.services.policy_service import policy_service
from app.services.audit_service import audit_service

router = APIRouter()

@router.get(
    "/admin/sites",
    response_model=List[SiteResponse],
    summary="Listar Sitios Institucionales Protegidos"
)
def list_sites(
    current_admin: dict = Depends(require_role(["security_admin", "operator", "auditor"])),
    db: Session = Depends(get_db)
):
    sites = db.query(SiteModel).all()
    return [
        SiteResponse(
            site_id=s.site_id,
            site_key=s.site_key,
            name=s.name,
            domain=s.domain,
            created_at=s.created_at,
            active=s.active
        )
        for s in sites
    ]

@router.post(
    "/admin/sites",
    response_model=SiteResponse,
    summary="Registrar Nuevo Sitio Institucional Protegido"
)
def create_site(
    req: SiteCreateRequest,
    current_admin: dict = Depends(require_role(["security_admin", "operator"])),
    db: Session = Depends(get_db)
):
    existing = db.query(SiteModel).filter(SiteModel.site_id == req.site_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PAYLOAD", "message": f"El sitio '{req.site_id}' ya existe"}
        )

    site_key = f"vh_site_{secrets.token_hex(8)}"
    raw_secret = secrets.token_hex(32)
    enc_secret = crypto_vault.encrypt_secret(raw_secret)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    site = SiteModel(
        site_id=req.site_id,
        name=req.name,
        domain=req.domain,
        site_key=site_key,
        secret_key_encrypted=enc_secret,
        active=True,
        created_at=now_iso
    )
    db.add(site)

    # Política inicial por defecto
    default_policy = SitePolicy()
    policy_record = SitePolicyModel(
        site_id=req.site_id,
        mode=default_policy.mode,
        policy_json=default_policy.model_dump_json(),
        updated_at=now_iso
    )
    db.add(policy_record)
    db.commit()

    audit_service.record_action(
        db=db,
        actor_username=current_admin["sub"],
        actor_role=current_admin["role"],
        action="SITE_CREATED",
        resource=f"site:{req.site_id}",
        payload_details={"site_id": req.site_id, "name": req.name, "site_key": site_key}
    )

    return SiteResponse(
        site_id=site.site_id,
        site_key=site.site_key,
        name=site.name,
        domain=site.domain,
        created_at=site.created_at,
        active=site.active
    )

@router.put(
    "/admin/policies/{site_id}",
    response_model=SitePoliciesResponse,
    summary="Actualizar Políticas de Mitigación de un Sitio"
)
def update_policy(
    site_id: str,
    policy: SitePolicy,
    current_admin: dict = Depends(require_role(["security_admin", "operator"])),
    db: Session = Depends(get_db)
):
    updated = policy_service.update_site_policy(
        db=db,
        site_id=site_id,
        new_policy=policy,
        actor_username=current_admin["sub"],
        actor_role=current_admin["role"]
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVALID_PAYLOAD", "message": f"Sitio '{site_id}' no encontrado"}
        )
    return updated
