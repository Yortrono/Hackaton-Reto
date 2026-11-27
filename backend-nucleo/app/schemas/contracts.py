from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

# --- 1. Envoltorio Estándar de Errores ---

class ErrorDetail(BaseModel):
    code: str = Field(..., description="Código de error estandarizado del catálogo cerrado")
    message: str = Field(..., description="Mensaje explicativo en castellano")
    details: Dict[str, Any] = Field(default_factory=dict, description="Metadatos contextuales del error")
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Identificador de traza único")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))

class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- 2. Flujo de Verificación (Challenge Init / Verify / Predict) ---

class ClientContext(BaseModel):
    sdk_version: str = "1.0.0"
    user_agent_hash: Optional[str] = None
    timezone_offset: Optional[int] = None
    screen_resolution: Optional[str] = None
    language: Optional[str] = "es-VE"

class ChallengeInitRequest(BaseModel):
    site_key: str = Field(..., min_length=8, max_length=64, description="Clave pública del sitio institucional")
    target_route: str = Field(..., description="Ruta protegida solicitada por el cliente")
    client_context: Optional[ClientContext] = Field(default_factory=ClientContext)

class InteractiveChallengeInfo(BaseModel):
    required_immediately: bool = False
    type: str = "spatial_alignment"
    target_angle: Optional[int] = None
    tolerance: Optional[int] = None
    prompt: str = "Deslice el control hasta alinear el indicador"
    accessible_hint: str = "Use las flechas izquierda o derecha del teclado para centrar la marca"

class ChallengeInitResponse(BaseModel):
    challenge_id: str
    policy_mode: str
    pow_difficulty: int
    nonce: str
    expires_in_seconds: int
    interactive_challenge: Optional[InteractiveChallengeInfo] = None

class PointerMetrics(BaseModel):
    event_count: int = 0
    mean_velocity: float = 0.0
    std_acceleration: float = 0.0
    angular_entropy: float = 0.0
    straight_line_ratio: float = 0.0

class KeyboardMetrics(BaseModel):
    key_count: int = 0
    mean_dwell_ms: float = 0.0
    std_flight_ms: float = 0.0

class EnvironmentSignals(BaseModel):
    webdriver_flag: bool = False
    plugins_count: int = 0
    languages_consistent: bool = True
    viewport_ratio_valid: bool = True
    time_to_first_interaction_ms: float = 0.0

class TelemetryPayload(BaseModel):
    challenge_id: str
    telemetry_window_ms: float = 0.0
    pointer_metrics: Optional[PointerMetrics] = Field(default_factory=PointerMetrics)
    keyboard_metrics: Optional[KeyboardMetrics] = Field(default_factory=KeyboardMetrics)
    environment_signals: Optional[EnvironmentSignals] = Field(default_factory=EnvironmentSignals)

class InteractiveResponse(BaseModel):
    completed: bool = True
    interaction_duration_ms: Optional[float] = None
    precision_delta: Optional[float] = None

class ChallengeVerifyRequest(BaseModel):
    site_key: str
    challenge_id: str
    pow_solution: str
    telemetry: TelemetryPayload
    interactive_response: Optional[InteractiveResponse] = None

class ChallengeVerifyResponse(BaseModel):
    challenge_id: str
    status: str  # "verified", "challenge_required", "blocked"
    risk_score: float
    jwt_token: Optional[str] = None
    expires_in_seconds: Optional[int] = None
    interactive_challenge: Optional[InteractiveChallengeInfo] = None

class IAPredictResponse(BaseModel):
    challenge_id: str
    risk_score: float
    decision: str  # "human", "challenge", "bot"
    inference_time_ms: float
    model_version: str


# --- 3. Borde, Criptografía y Políticas ---

class AIThresholds(BaseModel):
    challenge_min: float = 0.35
    block_min: float = 0.75

class ProtectedRoute(BaseModel):
    path_prefix: str
    methods: List[str] = ["GET", "POST"]
    require_token: bool = True
    rate_limit_rpm: int = 60

class SitePolicy(BaseModel):
    mode: str = "challenge"  # "passive", "challenge", "strict"
    ai_thresholds: AIThresholds = Field(default_factory=AIThresholds)
    protected_routes: List[ProtectedRoute] = Field(default_factory=list)
    rate_limit_global_rpm: int = 120
    ip_whitelist: List[str] = Field(default_factory=list)
    ip_blacklist: List[str] = Field(default_factory=list)

class CryptoPublicKeyInfo(BaseModel):
    kid: str
    algorithm: str = "EdDSA"
    curve: str = "Ed25519"
    public_key_pem: str
    active: bool = True

class SitePoliciesResponse(BaseModel):
    site_id: str
    site_key: str
    updated_at: str
    policy: SitePolicy
    crypto_public_keys: List[CryptoPublicKeyInfo]

class TokenValidateRequest(BaseModel):
    jwt_token: str
    site_key: str
    consume_jti: bool = True

class TokenValidateResponse(BaseModel):
    valid: bool
    jti: str
    risk_score: float
    consumed_at: Optional[str] = None


# --- 4. Observabilidad y Auditoría ---

class TrafficStats(BaseModel):
    total_requests: int = 0
    verified_humans: int = 0
    interactive_challenges_solved: int = 0
    bots_blocked: int = 0
    ddos_rate_limited: int = 0
    human_percentage: float = 0.0

class AIPerformanceStats(BaseModel):
    active_model_version: str = "lgbm-conductual-v1.0.0"
    avg_inference_ms: float = 3.8
    p99_inference_ms: float = 11.2
    model_accuracy: float = 0.984

class SecurityEventItem(BaseModel):
    event_id: str
    timestamp: str
    ip_hash: str
    route: str
    action: str  # "verified", "challenged", "blocked", "rate_limited"
    reason: str
    risk_score: float

class ObservabilitySummaryResponse(BaseModel):
    window: str = "last_60_minutes"
    traffic_stats: TrafficStats
    ai_performance: AIPerformanceStats
    recent_security_events: List[SecurityEventItem]

class AuditLogItem(BaseModel):
    id: int
    timestamp: str
    actor_username: str
    actor_role: str
    action: str
    resource: str
    prev_hash: str
    entry_hash: str

class AuditLogsResponse(BaseModel):
    chain_integrity_valid: bool
    items: List[AuditLogItem]
