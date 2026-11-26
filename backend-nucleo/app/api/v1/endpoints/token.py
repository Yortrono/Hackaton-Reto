from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.contracts import TokenValidateRequest, TokenValidateResponse
from app.core.jwt_service import jwt_service

router = APIRouter()

@router.post(
    "/token/validate",
    response_model=TokenValidateResponse,
    summary="Validar Token de Verificación Asimétrico",
    description="Valida la firma Ed25519 del token, vigencia y consume el identificador único (jti) para mitigar ataques de repetición."
)
def validate_token(
    req: TokenValidateRequest,
    db: Session = Depends(get_db)
):
    try:
        res = jwt_service.validate_human_token(
            token=req.jwt_token,
            site_key=req.site_key,
            consume_jti=req.consume_jti
        )
        return TokenValidateResponse(
            valid=res["valid"],
            jti=res["jti"],
            risk_score=res["risk_score"],
            consumed_at=res.get("consumed_at")
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": str(e)}
        )
