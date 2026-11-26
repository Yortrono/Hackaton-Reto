from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.contracts import SitePoliciesResponse
from app.services.policy_service import policy_service

router = APIRouter()

@router.get(
    "/policies/{site_id}",
    response_model=SitePoliciesResponse,
    summary="Sincronización Dinámica de Políticas hacia Borde",
    description="Expone las políticas de protección y las claves públicas Ed25519 activas para el Reverse Proxy OpenResty."
)
def get_site_policies(
    site_id: str,
    db: Session = Depends(get_db)
):
    response_data = policy_service.get_site_policies_response(db, site_id)
    if not response_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVALID_PAYLOAD", "message": f"Sitio con identificador '{site_id}' no encontrado"}
        )
    return response_data
