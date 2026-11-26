# Contratos JSON Estándar — Arquitectura Desacoplada

**Proyecto:** Servicio Autónomo de Verificación Humana y Mitigación de Bots (Hackathon Venezuela Innova 2026)  
**Propósito:** Fuente única de verdad (*Single Source of Truth*) para que **Dev 1 (Backend/Cripto)**, **Dev 2 (IA/Borde)** y **Dev 3 (SDK/Consola)** desarrollen en paralelo usando *mocks* idénticos a producción.

---

## 1. Convenciones Globales Obligatorias

Para evitar errores de serialización durante la integración en la Fase 2, los tres desarrolladores deben respetar estas 5 reglas:

1. **Nomenclatura de llaves:** Siempre `snake_case` en inglés técnico (`challenge_id`, `risk_score`, `site_key`).
2. **Fechas y marcas de tiempo:** Formato ISO-8601 en UTC (`"2026-11-26T18:30:00Z"`) o Unix Timestamp en segundos (`1795717800`) para claims estándar de JWT.
3. **Identificadores únicos:** UUID v4 (`"550e8400-e29b-41d4-a716-446655440000"`).
4. **Cabeceras de transporte:** Todas las peticiones y respuestas llevan `Content-Type: application/json; charset=utf-8`.
5. **Envoltorio Estándar de Errores (HTTP 4xx / 5xx):** Cualquier rechazo emitido por el **Borde (Dev 2)** o el **Backend (Dev 1)** debe usar exactamente esta estructura para que el **SDK y la Consola (Dev 3)** lo interpreten sin excepciones:

```json
{
  "error": {
    "code": "VERIFICATION_REQUIRED",
    "message": "Se requiere token de verificación humana válido para acceder a esta ruta.",
    "details": {
      "policy_mode": "challenge",
      "protected_route": "/login"
    },
    "trace_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "timestamp": "2026-11-26T18:30:00Z"
  }
}
```

**Catálogo cerrado de `error.code`:**
* `VERIFICATION_REQUIRED` (HTTP 401): Falta token JWT o expiró.
* `INVALID_TOKEN` (HTTP 401): Firma criptográfica inválida o `jti` ya consumido (*replay attack*).
* `BOT_BLOCKED` (HTTP 403): Puntaje de riesgo excede umbral de bloqueo o IP en lista negra.
* `RATE_LIMIT_EXCEEDED` (HTTP 429): Exceso de peticiones por IP/ruta.
* `INVALID_PAYLOAD` (HTTP 422): Esquema JSON malformado.
* `UNAUTHORIZED_ROLE` (HTTP 403): Usuario de consola sin permisos RBAC suficientes.

---

## 2. Contratos del Flujo de Verificación (SDK $\leftrightarrow$ Backend $\leftrightarrow$ IA)

### 2.1 Inicializar Sesión de Verificación
* **Endpoint:** `POST /api/v1/challenge/init`
* **Flujo:** `SDK Cliente (Dev 3)` $\rightarrow$ `Backend Núcleo (Dev 1)`

**Request:**
```json
{
  "site_key": "vh_site_9f8e7d6c5b4a3210",
  "target_route": "/login",
  "client_context": {
    "sdk_version": "1.0.0",
    "user_agent_hash": "a3f5c8d9e1b2...",
    "timezone_offset": -240,
    "screen_resolution": "1920x1080",
    "language": "es-VE"
  }
}
```

**Response (HTTP 200):**
```json
{
  "challenge_id": "550e8400-e29b-41d4-a716-446655440000",
  "policy_mode": "challenge",
  "pow_difficulty": 3,
  "nonce": "8f14e45fceea167a5a36dedd4bea2543",
  "expires_in_seconds": 120,
  "interactive_challenge": {
    "required_immediately": false,
    "type": "spatial_alignment",
    "prompt": "Deslice el control hasta alinear el indicador",
    "accessible_hint": "Use las flechas izquierda o derecha del teclado para centrar la marca"
  }
}
```

---

### 2.2 Verificar Señales Conductuales y Emitir Token
* **Endpoint:** `POST /api/v1/challenge/verify`
* **Flujo:** `SDK Cliente (Dev 3)` $\rightarrow$ `Backend Núcleo (Dev 1)`
* **Nota:** El bloque `telemetry` es **100 % idéntico** al definido en `AGENTS.md` para que Dev 1 lo reenvíe directamente al motor de IA de Dev 2 sin transformaciones costosas.

**Request (Modo Pasivo o con Resolución de Reto):**
```json
{
  "site_key": "vh_site_9f8e7d6c5b4a3210",
  "challenge_id": "550e8400-e29b-41d4-a716-446655440000",
  "pow_solution": "000a8f9c21",
  "telemetry": {
    "challenge_id": "550e8400-e29b-41d4-a716-446655440000",
    "telemetry_window_ms": 2450,
    "pointer_metrics": {
      "event_count": 48,
      "mean_velocity": 1.34,
      "std_acceleration": 0.42,
      "angular_entropy": 2.81,
      "straight_line_ratio": 0.12
    },
    "keyboard_metrics": {
      "key_count": 12,
      "mean_dwell_ms": 84.5,
      "std_flight_ms": 31.2
    },
    "environment_signals": {
      "webdriver_flag": false,
      "plugins_count": 5,
      "languages_consistent": true,
      "viewport_ratio_valid": true,
      "time_to_first_interaction_ms": 620
    }
  },
  "interactive_response": null
}
```
*(Si el usuario resolvió un desafío interactivo, `interactive_response` envía `{"completed": true, "interaction_duration_ms": 1150, "precision_delta": 0.04}`).*

**Response — Caso A: Humano Verificado (HTTP 200):**
```json
{
  "challenge_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "verified",
  "risk_score": 0.14,
  "jwt_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCIsImtpZCI6ImtleS0yMDI2LTAxIn0...",
  "expires_in_seconds": 90
}
```

**Response — Caso B: Riesgo Medio / Escalar a Reto Interactivo (HTTP 200):**
```json
{
  "challenge_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "challenge_required",
  "risk_score": 0.58,
  "jwt_token": null,
  "interactive_challenge": {
    "type": "spatial_alignment",
    "target_angle": 135,
    "tolerance": 8,
    "prompt": "Gire el anillo hasta que la marca apunte a las 4 en punto",
    "accessible_hint": "Presione Enter para avanzar en pasos de 15 grados"
  }
}
```

**Response — Caso C: Bot Detectado (HTTP 403):**
```json
{
  "challenge_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "blocked",
  "risk_score": 0.94,
  "jwt_token": null
}
```

---

### 2.3 Inferencia Conductual Local (Contrato Interno Dev 1 $\leftrightarrow$ Dev 2)
* **Endpoint:** `POST http://ia-conductual:8001/internal/predict`
* **Flujo:** `Backend Núcleo (Dev 1)` $\rightarrow$ `Módulo IA Local (Dev 2)`

**Request:**
Exactamente el objeto `telemetry` del punto 2.2.

**Response (HTTP 200 — Meta $< 50\text{ ms}$):**
```json
{
  "challenge_id": "550e8400-e29b-41d4-a716-446655440000",
  "risk_score": 0.14,
  "decision": "human",
  "inference_time_ms": 3.42,
  "model_version": "lgbm-conductual-v1.0.0"
}
```
*(Valores posibles de `decision`: `"human"`, `"challenge"`, `"bot"`).*

---

## 3. Contratos de Borde, Criptografía y Políticas (Dev 1 $\leftrightarrow$ Dev 2)

### 3.1 Sincronización Dinámica de Políticas hacia el Reverse Proxy
* **Endpoint:** `GET /api/v1/policies/{site_id}`
* **Flujo:** `Capa de Borde OpenResty (Dev 2)` $\rightarrow$ `Backend Núcleo (Dev 1)` (cada 5 segundos).

**Response (HTTP 200):**
```json
{
  "site_id": "default",
  "site_key": "vh_site_9f8e7d6c5b4a3210",
  "updated_at": "2026-11-26T18:30:00Z",
  "policy": {
    "mode": "challenge",
    "ai_thresholds": {
      "challenge_min": 0.35,
      "block_min": 0.75
    },
    "protected_routes": [
      {
        "path_prefix": "/login",
        "methods": ["POST"],
        "require_token": true,
        "rate_limit_rpm": 10
      },
      {
        "path_prefix": "/api/consulta",
        "methods": ["GET", "POST"],
        "require_token": true,
        "rate_limit_rpm": 30
      }
    ],
    "rate_limit_global_rpm": 120,
    "ip_whitelist": ["127.0.0.1", "10.0.0.0/8"],
    "ip_blacklist": ["198.51.100.42"]
  },
  "crypto_public_keys": [
    {
      "kid": "key-2026-01",
      "algorithm": "EdDSA",
      "curve": "Ed25519",
      "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEA...\n-----END PUBLIC KEY-----",
      "active": true
    }
  ]
}
```

---

### 3.2 Estructura del Token JWT Asimétrico y Validación
* **Transporte en HTTP:** Cabecera `X-Human-Token: <jwt>` o cookie `vh_token=<jwt>`.
* **Validación en Borde (Dev 2):** Verifica firma con `public_key_pem` y expiración `exp` en memoria Lua.
* **Validación en Backend / App Institucional (Dev 1):** `POST /api/v1/token/validate` verifica firma + invalida `jti` en almacenamiento local (un solo uso).

**Payload Decodificado del JWT (Emitido por Dev 1):**
```json
{
  "iss": "servicio-verificacion-humana.gob.ve",
  "sub": "anon_session_7c9e6679",
  "aud": "vh_site_9f8e7d6c5b4a3210",
  "jti": "123e4567-e89b-12d3-a456-426614174000",
  "iat": 1795717800,
  "exp": 1795717890,
  "risk_score": 0.14,
  "verification_mode": "passive"
}
```

**Endpoint `POST /api/v1/token/validate` — Request:**
```json
{
  "jwt_token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCIsImtpZCI6ImtleS0yMDI2LTAxIn0...",
  "site_key": "vh_site_9f8e7d6c5b4a3210",
  "consume_jti": true
}
```

**Response (HTTP 200):**
```json
{
  "valid": true,
  "jti": "123e4567-e89b-12d3-a456-426614174000",
  "risk_score": 0.14,
  "consumed_at": "2026-11-26T18:30:12Z"
}
```

---

## 4. Contratos de la Consola Administrativa (Dev 1 $\leftrightarrow$ Dev 3)

### 4.1 Observabilidad en Tiempo Real
* **Endpoint:** `GET /api/v1/admin/observability/summary`
* **Flujo:** `Consola Admin (Dev 3)` $\rightarrow$ `Backend Núcleo (Dev 1)` (el Backend agrega sus contadores + los de `GET http://ia-conductual:8001/internal/metrics` de Dev 2).

**Response (HTTP 200):**
```json
{
  "window": "last_60_minutes",
  "traffic_stats": {
    "total_requests": 14820,
    "verified_humans": 11210,
    "interactive_challenges_solved": 980,
    "bots_blocked": 2410,
    "ddos_rate_limited": 220,
    "human_percentage": 82.25
  },
  "ai_performance": {
    "active_model_version": "lgbm-conductual-v1.0.0",
    "avg_inference_ms": 3.8,
    "p99_inference_ms": 11.2,
    "model_accuracy": 0.984
  },
  "recent_security_events": [
    {
      "event_id": "evt_001",
      "timestamp": "2026-11-26T18:29:45Z",
      "ip_hash": "sha256:9f86d081884c7d65...",
      "route": "/login",
      "action": "blocked",
      "reason": "high_bot_risk_score",
      "risk_score": 0.96
    }
  ]
}
```

---

### 4.2 Bóveda Criptográfica y Auditoría Inmutable
* **Endpoint Auditoría:** `GET /api/v1/admin/audit-logs?limit=20`

**Response (HTTP 200):**
```json
{
  "chain_integrity_valid": true,
  "items": [
    {
      "id": 42,
      "timestamp": "2026-11-26T18:15:00Z",
      "actor_username": "admin_seguridad",
      "actor_role": "security_admin",
      "action": "CRYPTO_KEY_ROTATED",
      "resource": "kid:key-2026-01",
      "prev_hash": "0000a4f1b9c3...",
      "entry_hash": "0000e8d2c1a7..."
    }
  ]
}
```

---

## 5. Instrucción Rápida para Trabajar en Paralelo Ahora Mismo

1. **Guarda este archivo** en `docs/02-contratos-json.md` dentro del repositorio compartido.
2. **Para Dev 1 (Backend):** Crea los esquemas Pydantic/Structs copiando exactamente estos JSON. Mientras Dev 2 termina el contenedor de IA, devuelve la respuesta simulada del punto `2.3` cuando `webdriver_flag == false`.
3. **Para Dev 2 (Tú — IA/Borde):** Coloca el JSON del punto `3.1` como tu archivo estático `borde-proxy/default_policy.json` para que tu proxy funcione de inmediato aunque Dev 1 no haya levantado el backend.
4. **Para Dev 3 (SDK/Consola):** Construye el colector del SDK generando exactamente la estructura `telemetry` del punto `2.2` y maqueta los gráficos de la consola consumiendo el JSON del punto `4.1`.