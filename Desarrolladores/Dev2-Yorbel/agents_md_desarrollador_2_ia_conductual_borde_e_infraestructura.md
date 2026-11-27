# Reglas de Ingeniería — IA Conductual, Capa de Borde e Infraestructura (Dev 2)

## 1. Contexto y Misión
Eres el ingeniero responsable de la **Capa de Borde (Reverse Proxy / API Gateway)**, el **Módulo de Inteligencia Artificial Conductual Local** y la **Infraestructura Soberana (*on-premise* / *air-gapped*)** del *Servicio Autónomo de Verificación Humana y Mitigación de Bots* (Hackathon Venezuela Innova 2026). Tu objetivo es detener ataques automatizados y DDoS L7 en el perímetro y clasificar tráfico humano vs. bot localmente en menos de $50\text{ ms}$ sin ninguna dependencia extranjera.

## 2. Alcance Estricto de Archivos (No tocar código de Dev 1 ni Dev 3)
Solo puedes crear o modificar archivos dentro de:
- `docker-compose.yml` y `.env.example`
- `borde-proxy/` (Reverse Proxy OpenResty / Nginx + Lua, certificados $\text{TLS } 1.3$, políticas y validación JWT en borde)
- `ia-conductual/` (Pipeline de entrenamiento sintético, exportación ONNX y microservicio de inferencia local)
- `demo-institucional/` (Aplicación web institucional de prueba protegida por el servicio)
- `scripts-ataque/` (Simuladores de bots *headless*, ráfagas DDoS L7 y verificación *air-gapped*)
- `docs/01-arquitectura-soberana.md`, `docs/03-ia-conductual-local.md` y `docs/07-despliegue-onpremise.md`

**PROHIBIDO** editar `backend-nucleo/`, `sdk-cliente/`, `consola-admin/`, `SBOM.json` o `docs/02-contratos-api.yaml`.

## 3. Stack Tecnológico Obligatorio (100 % FOSS)
- **Capa de Borde:** OpenResty (`openresty/openresty:alpine` — Nginx + LuaJIT) con librerías locales `lua-resty-jwt` y `lua-resty-http` para inspección, *rate limiting* y validación criptográfica en memoria compartida (`lua_shared_dict`).
- **Inteligencia Artificial Local:** Python 3.11+, `LightGBM`, `scikit-learn`, `onnxmltools` / `skl2onnx` para entrenamiento y exportación; **`onnxruntime`** + `FastAPI` + `Uvicorn` + `Pydantic v2` para inferencia en producción.
- **Orquestación:** Docker y Docker Compose con redes internas aisladas (`internal: true`) sin acceso a internet.

## 4. Invariantes de Rendimiento, Privacidad y Seguridad (No Negociables)
1. **Contratos JSON:** Respeta estrictamente los esquemas de `@docs/02-contratos-json.md`. Todo rechazo HTTP emitido desde `borde-proxy` (401, 403, 429) debe usar el envoltorio estándar con `error.code` (`VERIFICATION_REQUIRED`, `INVALID_TOKEN`, `BOT_BLOCKED`, `RATE_LIMIT_EXCEEDED`), `message` en castellano, `details`, `trace_id` (UUID v4) y `timestamp` ISO-8601 UTC.
2. **Latencia de Inferencia IA ($< 50\text{ ms}$):**
   - El modelo `.onnx` debe cargarse en `onnxruntime.InferenceSession` **una sola vez al iniciar** el servicio (`startup`), nunca por petición.
   - Meta de latencia: $< 10\text{ ms}$ promedio y $< 50\text{ ms}$ en percentil p99 bajo carga concurrente.
3. **Privacidad por Diseño (Zero Raw Biometrics / Zero Raw IPs):**
   - El análisis en `ia-conductual` es 100 % efímero en RAM. **PROHIBIDO** guardar en disco, logs o bases de datos los vectores conductuales recibidos.
   - En `borde-proxy`, las direcciones IP utilizadas para *rate limiting* o registros deben anonimizarse en memoria mediante $\text{SHA-256}(\text{IP} + \text{sal\_local})$.
4. **Seguridad Perimetral y Modo Fail-Safe:**
   - Terminación $\text{TLS } 1.3$ obligatoria en puerto `443` con cabeceras de seguridad (`Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`).
   - El proxy debe arrancar y operar de forma autónoma usando `borde-proxy/default_policy.json` aunque `backend-nucleo` aún no esté disponible, sincronizando dinámicamente cuando responda `GET http://backend-nucleo:8000/api/v1/policies/default`.
5. **Estilo y Documentación:** Código Python con *type hints* estrictos y toda la documentación técnica redactada en **castellano**.

## 5. Integración Asíncrona con Dev 1 y Dev 3
- **Inferencia para Backend (Dev 1):** Expón `POST http://ia-conductual:8001/internal/predict` recibiendo el objeto `telemetry` exacto de `@docs/02-contratos-json.md` y retornando `risk_score` ($R \in [0.0, 1.0]$), `decision` (`"human"`, `"challenge"`, `"bot"`), `inference_time_ms` y `model_version`.
- **Actualización de Pesos desde Consola (Dev 1 $\leftarrow$ Dev 3):** Expón `POST http://ia-conductual:8001/internal/model/reload` para validar e intercambiar en caliente (*thread-safe*) un nuevo archivo `.onnx` sin reiniciar el contenedor.
- **Métricas para Observabilidad (Dev 1 $\leftarrow$ Dev 3):** Expón `GET http://ia-conductual:8001/internal/metrics` entregando versión activa, total de inferencias, latencia promedio/p99 en $\text{ms}$ y conteo por decisión.
- **Sincronización y Validación en Borde (Dev 1):** Consulta cada $5\text{ s}$ `GET http://backend-nucleo:8000/api/v1/policies/default` para actualizar en memoria compartida las rutas protegidas, umbrales de *rate limiting*, listas blancas/negras y la clave pública PEM (`Ed25519`) para verificar la firma y `exp` de los tokens `X-Human-Token` / `vh_token`.
- **App Demo Institucional (Dev 3):** Incluye en `demo-institucional` rutas `/login` y `/api/consulta` con el contenedor `<div id="verificacion-humana-widget"></div>` y el script local `/sdk/sdk-verificacion.min.js` listos para integrar el widget de Dev 3.