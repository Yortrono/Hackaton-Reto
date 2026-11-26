import hashlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.admin import ModelUploadResponse
from app.core.security import require_role
from app.services.ia_client import ia_client
from app.services.audit_service import audit_service

router = APIRouter()

@router.post(
    "/admin/ai/model/upload",
    response_model=ModelUploadResponse,
    summary="Cargar y Recargar Modelo Conductual ONNX",
    description="Exclusivo para 'security_admin'. Valida el archivo ONNX, calcula checksum SHA-256 y lo reenvía a ia-conductual."
)
async def upload_model(
    file: UploadFile = File(...),
    current_admin: dict = Depends(require_role(["security_admin"])),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith((".onnx", ".bin")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PAYLOAD", "message": "El modelo debe ser un archivo binario .onnx válido"}
        )

    content = await file.read()
    if len(content) < 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_PAYLOAD", "message": "El archivo proporcionado está vacío o corrupto"}
        )

    checksum = hashlib.sha256(content).hexdigest()
    model_version = f"model-{file.filename}-{checksum[:8]}"

    # Reenviar a ia-conductual
    reloaded = await ia_client.reload_model(content, file.filename)

    # Registrar en auditoría inmutable
    audit_service.record_action(
        db=db,
        actor_username=current_admin["sub"],
        actor_role=current_admin["role"],
        action="AI_MODEL_RELOADED",
        resource=f"model:{model_version}",
        payload_details={
            "filename": file.filename,
            "checksum_sha256": checksum,
            "size_bytes": len(content),
            "reloaded_in_ia": reloaded
        }
    )

    return ModelUploadResponse(
        model_version=model_version,
        checksum_sha256=checksum,
        message="Modelo validado y registrado en la bitácora inmutable",
        reloaded_in_ia=reloaded
    )
