from fastapi import Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import get_current_admin, require_role

def get_client_ip(request: Request) -> str:
    """Extrae la IP real del cliente respetando cabeceras de proxy de confianza (X-Forwarded-For)."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"
