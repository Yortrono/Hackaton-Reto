from fastapi import APIRouter
from app.api.v1.endpoints import (
    challenge,
    token,
    policies,
    admin_auth,
    admin_vault,
    admin_policies,
    admin_audit,
    admin_observability,
    admin_ai
)

api_router = APIRouter()

# Flujo de verificación de retos (SDK <-> Backend <-> IA)
api_router.include_router(challenge.router, tags=["Verificación de Retos"])

# Validación de tokens asimétricos y anti-replay
api_router.include_router(token.router, tags=["Validación Criptográfica de Tokens"])

# Políticas y Borde (Borde OpenResty <-> Backend)
api_router.include_router(policies.router, tags=["Sincronización de Políticas y Claves"])

# Administración y RBAC/MFA
api_router.include_router(admin_auth.router, tags=["Administración - Autenticación y MFA"])
api_router.include_router(admin_vault.router, tags=["Administración - Bóveda Criptográfica"])
api_router.include_router(admin_policies.router, tags=["Administración - Sitios y Políticas"])
api_router.include_router(admin_audit.router, tags=["Administración - Bitácora Inmutable"])
api_router.include_router(admin_observability.router, tags=["Administración - Observabilidad"])
api_router.include_router(admin_ai.router, tags=["Administración - Modelos IA"])
