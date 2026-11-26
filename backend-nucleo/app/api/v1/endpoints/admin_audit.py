from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.contracts import AuditLogsResponse
from app.core.security import require_role
from app.services.audit_service import audit_service

router = APIRouter()

@router.get(
    "/admin/audit-logs",
    response_model=AuditLogsResponse,
    summary="Consultar Bitácora de Auditoría Criptográficamente Inmutable",
    description="Permite auditar el encadenamiento criptográfico (SHA-256 hash chaining) de todas las operaciones administrativas."
)
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    current_admin: dict = Depends(require_role(["security_admin", "operator", "auditor"])),
    db: Session = Depends(get_db)
):
    chain_valid, items = audit_service.get_audit_logs(db=db, limit=limit)
    return AuditLogsResponse(
        chain_integrity_valid=chain_valid,
        items=items
    )
