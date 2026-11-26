from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.contracts import (
    ChallengeInitRequest,
    ChallengeInitResponse,
    ChallengeVerifyRequest,
    ChallengeVerifyResponse
)
from app.services.verification_service import verification_service
from app.api.deps import get_client_ip

router = APIRouter()

@router.post(
    "/challenge/init",
    response_model=ChallengeInitResponse,
    summary="Inicializar Sesión de Verificación",
    description="Inicia el flujo de verificación para un cliente SDK, retornando el reto PoW y los parámetros de política."
)
def init_challenge(
    req: ChallengeInitRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    client_ip = get_client_ip(request)
    try:
        return verification_service.init_challenge(db, req, client_ip)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PAYLOAD", "message": str(e)}
        )

@router.post(
    "/challenge/verify",
    response_model=ChallengeVerifyResponse,
    summary="Verificar Señales Conductuales y Emitir Token",
    description="Recibe la solución PoW y telemetría conductual. Si es humano emite token EdDSA (200), si requiere reto devuelve spatial_alignment (200), o bloquea bots (403)."
)
async def verify_challenge(
    req: ChallengeVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    client_ip = get_client_ip(request)
    try:
        http_code, result = await verification_service.verify_challenge(db, req, client_ip)
        response.status_code = http_code
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PAYLOAD", "message": str(e)}
        )
