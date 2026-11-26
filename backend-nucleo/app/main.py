import uuid
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from app.config import settings
from app.db.init_db import init_database
from app.api.v1.router import api_router
from app.schemas.contracts import ErrorResponse, ErrorDetail

STATIC_DIR = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar base de datos SQLite WAL, bóveda y datos maestros al arrancar
    init_database()
    yield

app = FastAPI(
    title="Servicio Autónomo de Verificación Humana y Mitigación de Bots — Núcleo Backend",
    version="1.0.0",
    description="Núcleo soberano de verificación humana, bóveda criptográfica Ed25519/AES-256-GCM y auditoría inmutable (Hackathon Venezuela Innova 2026)",
    lifespan=lifespan,
    docs_url=None,  # Desactivado por defecto para usar recursos estáticos soberanos 100% locales
    redoc_url=None,
    openapi_url="/api/v1/openapi.json"
)

# Montar recursos estáticos FOSS locales (cero dependencias externas de CDN)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- Middlewares de Seguridad Soberana y OWASP ---

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
        request.state.trace_id = trace_id

        response = await call_next(request)

        # Inyectar Trace-ID
        response.headers["X-Trace-ID"] = trace_id

        # Cabeceras de seguridad estrictas (OWASP Top 10)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # CSP adaptativo: estricto para APIs, compatible con assets locales para documentación UI
        path = request.url.path
        if path.startswith(("/docs", "/redoc")):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "worker-src 'self' blob:; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https://cdn.redoc.ly; "
                "font-src 'self' data:;"
            )
        else:
            response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response

app.add_middleware(SecurityHeadersMiddleware)

# CORS seguro para integración de SDK y Consola
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Trace-ID", "X-Human-Token"]
)

# --- Endpoints de Documentación Soberana Offline ---

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.png",
    )

@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
        redoc_favicon_url="/static/favicon.png",
        with_google_fonts=False,  # Cero llamadas a Google Fonts (100% Soberano)
    )

# --- Manejo Estandarizado de Errores (@docs/02-contratos-json.md) ---

def build_error_json(
    code: str,
    message: str,
    details: dict,
    trace_id: str,
    status_code: int
) -> JSONResponse:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "trace_id": trace_id,
            "timestamp": timestamp
        }
    }
    return JSONResponse(status_code=status_code, content=payload)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    code = "INTERNAL_SERVER_ERROR"
    message = str(exc.detail)
    details = {}

    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "ERROR")
        message = exc.detail.get("message", message)
        details = exc.detail.get("details", {})
    else:
        if exc.status_code == 401:
            code = "VERIFICATION_REQUIRED"
        elif exc.status_code == 403:
            code = "BOT_BLOCKED"
        elif exc.status_code == 404:
            code = "INVALID_PAYLOAD"
        elif exc.status_code == 422:
            code = "INVALID_PAYLOAD"
        elif exc.status_code == 429:
            code = "RATE_LIMIT_EXCEEDED"

    return build_error_json(code, message, details, trace_id, exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    details = {"errors": exc.errors()}
    return build_error_json(
        code="INVALID_PAYLOAD",
        message="Esquema JSON o parámetros de petición malformados",
        details=details,
        trace_id=trace_id,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    return build_error_json(
        code="INTERNAL_SERVER_ERROR",
        message="Ocurrió un error inesperado en el servidor",
        details={"error_class": exc.__class__.__name__},
        trace_id=trace_id,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )

# --- Registrar Router de API v1 ---
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Salud"])
def health_check():
    return {
        "status": "healthy",
        "service": "backend-nucleo",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
