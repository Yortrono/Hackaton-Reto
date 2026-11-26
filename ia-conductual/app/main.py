"""
Microservicio de Inferencia Conductual Local
Servicio Autónomo de Verificación Humana y Mitigación de Bots
Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)

Endpoints internos:
- POST /internal/predict
- POST /internal/model/reload
- GET /internal/metrics
- GET /health
"""

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.engine import BehavioralInferenceEngine

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
MODEL_PATH = MODELS_DIR / "modelo_conductual_v1.onnx"
METADATA_PATH = MODELS_DIR / "metadata_v1.json"

engine: Optional[BehavioralInferenceEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    print("[*] Inicializando motor de inferencia conductual ONNX en memoria...")
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Modelo ONNX no encontrado en {MODEL_PATH}. Ejecute train_model.py primero.")
    engine = BehavioralInferenceEngine(str(MODEL_PATH), str(METADATA_PATH) if METADATA_PATH.exists() else None)
    print(f"[+] Motor listo en memoria RAM. Versión activa: {engine.model_version}")
    yield
    print("[-] Deteniendo microservicio de IA conductual.")


app = FastAPI(
    title="Microservicio de Inferencia Conductual Local",
    description="Inferencia probabilística sobre señales biomecánicas en red soberana interna",
    version="1.0.0",
    lifespan=lifespan,
)


# ==============================================================================
# Modelos Pydantic Estrictos (Contrato JSON de Entrada @AGENTS.md)
# ==============================================================================

class PointerMetrics(BaseModel):
    event_count: int = Field(default=0, ge=0)
    mean_velocity: float = Field(default=0.0, ge=0.0)
    std_acceleration: float = Field(default=0.0, ge=0.0)
    angular_entropy: float = Field(default=0.0, ge=0.0)
    straight_line_ratio: float = Field(default=0.0, ge=0.0, le=1.0)


class KeyboardMetrics(BaseModel):
    key_count: int = Field(default=0, ge=0)
    mean_dwell_ms: float = Field(default=0.0, ge=0.0)
    std_flight_ms: float = Field(default=0.0, ge=0.0)


class EnvironmentSignals(BaseModel):
    webdriver_flag: bool = Field(default=False)
    plugins_count: int = Field(default=0, ge=0)
    languages_consistent: bool = Field(default=True)
    viewport_ratio_valid: bool = Field(default=True)
    time_to_first_interaction_ms: float = Field(default=0.0, ge=0.0)


class TelemetryInput(BaseModel):
    challenge_id: str = Field(..., description="UUID v4 del reto o sesión anónima")
    telemetry_window_ms: float = Field(default=2000.0, ge=0.0)
    pointer_metrics: Optional[PointerMetrics] = None
    keyboard_metrics: Optional[KeyboardMetrics] = None
    environment_signals: Optional[EnvironmentSignals] = None


class PredictResponse(BaseModel):
    challenge_id: str
    risk_score: float
    decision: str
    inference_time_ms: float
    model_version: str


# ==============================================================================
# Endpoints Internos
# ==============================================================================

@app.post("/internal/predict", response_model=PredictResponse, status_code=status.HTTP_200_OK)
async def predict_internal(payload: TelemetryInput) -> Dict[str, Any]:
    """
    Recibe el objeto de telemetría y evalúa el puntaje de riesgo probabilístico.
    Invariante: Zero almacenamiento de datos biométricos o identificadores en logs/disco.
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Motor de inferencia no inicializado")

    data = payload.model_dump()
    result = engine.predict(data)
    return result


@app.post("/internal/model/reload", status_code=status.HTTP_200_OK)
async def reload_model_internal(
    file: UploadFile = File(..., description="Archivo de modelo .onnx"),
    version: str = Form(..., description="Identificador de la nueva versión"),
) -> Dict[str, Any]:
    """
    Permite al backend (Dev 1 / Dev 3) actualizar en caliente los pesos del modelo ONNX
    sin interrumpir el servicio ni reiniciar el contenedor.
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Motor de inferencia no inicializado")

    if not file.filename.endswith(".onnx"):
        raise HTTPException(status_code=400, detail="Solo se admiten archivos con extensión .onnx")

    try:
        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="El modelo excede el límite permitido de 5 MB")

        engine.reload_model(model_bytes=content, version=version)
        return {
            "status": "success",
            "message": f"Modelo actualizado a versión {version} en caliente",
            "active_model_version": version,
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Fallo al recargar modelo ONNX: {str(e)}")


@app.get("/internal/metrics", status_code=status.HTTP_200_OK)
async def metrics_internal() -> Dict[str, Any]:
    """
    Retorna versión activa, volumen total de inferencias, latencias p99/promedio
    y distribución de decisiones para la Consola Administrativa (Dev 3).
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Motor de inferencia no inicializado")

    return engine.get_metrics()


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """Chequeo de salud del servicio interno."""
    return {
        "status": "healthy",
        "service": "ia-conductual",
        "model_version": engine.model_version if engine else "uninitialized",
    }
