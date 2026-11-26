# Guía de Ejecución Acelerada con Antigravity (Desarrollador 2)

Para que **Antigravity** no pierda tiempo adivinando arquitectura ni modifique carpetas de tus compañeros (**Dev 1** y **Dev 3**), trabaja con dos mecanismos nativos del entorno:
1. **Contexto Persistente (`AGENTS.md`):** Guárdalo en la raíz del repositorio. Antigravity lo inyecta automáticamente en cada turno (`always_on`).
2. **Prompts Atómicos Auto-Verificables:** Ejecuta los 5 bloques en orden. Cada prompt incluye un **comando de verificación** para que el propio agente pruebe y corrija su código antes de entregártelo.

---

## Parte 1: Archivo `AGENTS.md` (Guardar en la raíz del repositorio)

Crea un archivo llamado `AGENTS.md` en la carpeta principal del proyecto y pega exactamente este contenido:

```markdown
# Reglas de Ingeniería — Módulo IA, Borde e Infraestructura (Dev 2)

## 1. Contexto y Objetivo
Construimos el **Servicio Autónomo de Verificación Humana y Mitigación de Bots** (Hackathon Venezuela Innova 2026). Debe operar 100 % *on-premise* / *air-gapped* sin conexión a internet ni servicios cloud externos.

## 2. Alcance Estricto de Archivos (No tocar código de Dev 1 ni Dev 3)
Solo puedes crear o modificar archivos dentro de:
- `docker-compose.yml` y `.env.example`
- `borde-proxy/` (Reverse Proxy / API Gateway)
- `ia-conductual/` (Entrenamiento e inferencia local)
- `demo-institucional/` (App web de prueba protegida)
- `scripts-ataque/` (Pruebas de estrés, bots y verificación offline)
- `docs/01-arquitectura-soberana.md`, `docs/03-ia-conductual-local.md`, `docs/07-despliegue-onpremise.md`

**PROHIBIDO** editar `backend-nucleo/`, `sdk-cliente/` o `consola-admin/`.

## 3. Invariantes Técnicas Obligatorias
- **Stack 100 % FOSS:** Solo librerías de código abierto auditables (OpenResty/Nginx + Lua, Python 3.11+, FastAPI, LightGBM, `onnxruntime`, `scikit-learn`).
- **Latencia de IA:** Toda inferencia en `ia-conductual/` debe ejecutarse localmente en **$< 50\text{ ms}$** (meta: $< 10\text{ ms}$).
- **Privacidad por Diseño:** Procesamiento 100 % efímero en memoria RAM. **NUNCA** guardar coordenadas crudas, pulsaciones de teclado ni IPs sin anonimizar en disco o logs.
- **Seguridad Perimetral:** Terminación $\text{TLS } 1.3$ obligatoria en el borde. Red Docker interna aislada (`internal: true`) sin acceso a internet.
- **Estilo de Código:** Python con *type hints* estrictos, manejo explícito de errores y comentarios/documentación técnica en **castellano**.

## 4. Contrato JSON de Entrada al Motor de IA
```json
{
  "challenge_id": "uuid-v4",
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
}
```
```

---

## Parte 2: Secuencia de Prompts Puntuales (Copy-Paste por Fase)

### Prompt 1 — Infraestructura Base, TLS 1.3 y App Demo (Hora 00:00)
*Pega esto en el chat de Antigravity para levantar la red y el entorno de pruebas en 15 minutos:*

```text
/plan
Objetivo: Crear la infraestructura base en Docker Compose, certificados TLS 1.3 locales y una aplicación web institucional de demostración.

Alcance y archivos a crear:
1. `docker-compose.yml`: Define dos redes (`perimetral` pública y `soberana_interna` con `internal: true`). Servicios: `borde-proxy` (único con puertos 80/443 expuestos), `ia-conductual` (puerto interno 8001), `demo-institucional` (puerto interno 8080), y placeholders preparados para `backend-nucleo` (8000) y `consola-admin` (3000).
2. `borde-proxy/certs/generar_certs.sh`: Script OpenSSL que genere una CA local y certificado autofirmado válido para `localhost` y `portal.gob.local`.
3. `borde-proxy/nginx.conf`: Configuración base con redirección HTTP->HTTPS, TLS 1.3 estricto (`TLSv1.3`), cabeceras de seguridad (HSTS, X-Frame-Options, X-Content-Type-Options) y proxy inverso hacia `demo-institucional`.
4. `demo-institucional/`: App ligera en FastAPI + HTML minimalista ("Portal Ciudadano de Trámites") con rutas `GET /`, `POST /login` y `GET /api/consulta`, incluyendo un `<div id="verificacion-humana-widget"></div>` listo para el SDK de Dev 3.

Restricciones:
- Cero dependencias de CDNs externos (Bootstrap, Google Fonts, etc.) en el HTML de `demo-institucional`. Todo CSS debe ser inline o local.
- No modificar carpetas fuera de `borde-proxy/`, `demo-institucional/` y `docker-compose.yml`.

Verificación:
Ejecuta `bash borde-proxy/certs/generar_certs.sh`, levanta `docker compose up -d --build borde-proxy demo-institucional` y verifica con `curl -vk https://localhost/api/consulta` que responda HTTP 200 sobre TLSv1.3.
```

---

### Prompt 2 — Dataset Sintético y Entrenamiento Modelo ONNX (Hora 02:00)
*Una vez verificado el Prompt 1, ejecuta `/compact` y lanza este prompt:*

```text
Objetivo: Construir el pipeline de generación de datos sintéticos conductuales, entrenar un clasificador LightGBM y exportarlo a ONNX Runtime.

Alcance y archivos a crear en `ia-conductual/training/`:
1. `generar_dataset.py`: Genera 20,000 muestras balanceadas (`0 = Humano`, `1 = Bot`) respetando exactamente las 13 variables numéricas/booleanas del contrato JSON en @AGENTS.md:
   - Humanos: alta entropía angular (`2.2` a `3.5`), bajo `straight_line_ratio` (`< 0.25`), varianza natural en aceleración y tiempos de teclado (`std_flight_ms > 15`), `webdriver_flag = false`.
   - Bots: trayectorias rectas (`straight_line_ratio > 0.75`), entropía baja (`< 1.0`), intervalos robóticos constantes (`std_flight_ms < 5`) o `webdriver_flag = true` / tiempo a primera interacción `< 120 ms`.
2. `train_model.py`: Entrena un `LGBMClassifier`, evalúa Precision, Recall, F1 y matriz de confusión, y exporta el modelo con `onnxmltools` / `skl2onnx` a `ia-conductual/models/modelo_conductual_v1.onnx` junto con `ia-conductual/models/metadata_v1.json` (versión, fecha, métricas, orden exacto de features).
3. `ia-conductual/requirements.txt`: Versiones exactas de `lightgbm`, `scikit-learn`, `onnxmltools`, `skl2onnx`, `onnxruntime`, `fastapi`, `uvicorn`, `pydantic`.

Restricciones:
- Todo el dataset debe generarse en memoria o guardarse temporalmente sin datos identificables.
- El archivo `.onnx` final debe pesar menos de 5 MB para carga instantánea en RAM.

Verificación:
Ejecuta `python ia-conductual/training/generar_dataset.py && python ia-conductual/training/train_model.py` y confirma que `modelo_conductual_v1.onnx` existe y logra F1-score > 0.96 en el set de prueba.
```

---

### Prompt 3 — Microservicio Local de Inferencia ONNX con Hot-Reload (Hora 05:00)
*Lanza este prompt para tener la API de IA lista para conectarse con Dev 1 y Dev 3:*

```text
Objetivo: Implementar el microservicio FastAPI de inferencia conductual en `ia-conductual/app/` con latencia < 15 ms, recarga en caliente de modelos y métricas en tiempo real.

Alcance y archivos a crear:
1. `ia-conductual/app/engine.py`: Clase `BehavioralInferenceEngine` que carga `modelo_conductual_v1.onnx` en `onnxruntime.InferenceSession` al iniciar, ejecuta predicción probabilística devolviendo `risk_score` ($R \in [0.0, 1.0]$), clasificación (`human` si $R < 0.35$, `challenge` si $0.35 \le R < 0.75$, `bot` si $R \ge 0.75$) y tiempo exacto de inferencia en milisegundos. Debe soportar un método thread-safe `reload_model(new_onnx_path, metadata)` para actualizar pesos sin reiniciar el contenedor.
2. `ia-conductual/app/main.py`: Endpoints internos:
   - `POST /internal/predict`: Recibe el JSON del contrato de @AGENTS.md y retorna `{ "challenge_id", "risk_score", "decision", "inference_time_ms", "model_version" }`.
   - `POST /internal/model/reload`: Recibe un archivo `.onnx` y `version` (invocado por el backend cuando el admin sube nuevos pesos en la consola), valida su esquema de entrada y reemplaza el modelo activo en caliente.
   - `GET /internal/metrics`: Devuelve versión activa, total de inferencias, latencia promedio/p99 en ms y distribución de decisiones (`human`, `challenge`, `bot`).
3. `ia-conductual/Dockerfile`: Imagen ligera (`python:3.11-slim`) que ejecute el servidor con `uvicorn`.

Restricciones:
- PROHIBIDO almacenar los payloads de entrada en logs o archivos. Solo registrar contadores agregados y latencias en memoria.
- Asegurar que el modelo se cargue una sola vez en el evento `startup` (nunca por cada petición).

Verificación:
Levanta el contenedor `ia-conductual` y ejecuta un script de prueba que envíe 100 peticiones secuenciales a `POST /internal/predict` (50 perfiles humanos y 50 perfiles bot), verificando que la latencia p99 sea < 50 ms y las decisiones coincidan con cada perfil.
```

---

### Prompt 4 — Capa de Borde Inteligente (Rate Limiting, DDoS L7, JWT y Políticas) (Hora 08:00)
*Este es el núcleo perimetral. Usa OpenResty (Nginx + LuaJIT) para máxima velocidad:*

```text
/plan
Objetivo: Actualizar `borde-proxy/` usando OpenResty (`openresty/openresty:alpine`) para implementar sincronización dinámica de políticas, rate limiting multicapa, mitigación DDoS L7 y validación de tokens JWT en borde.

Alcance y archivos a modificar/crear en `borde-proxy/`:
1. `borde-proxy/Dockerfile`: Basado en `openresty/openresty:alpine` con `lua-resty-jwt` y `lua-resty-http` instalados localmente (sin descargas en runtime).
2. `borde-proxy/lua/policy_sync.lua`: Worker en segundo plano (`ngx.timer.every` cada 5 segundos) que consulta `GET http://backend-nucleo:8000/api/v1/policies/default` (con fallback a un archivo local `borde-proxy/default_policy.json` si el backend aún no responde) y guarda en `lua_shared_dict policies_cache`:
   - Modo activo (`monitor`, `challenge`, `block`).
   - Rutas protegidas (ej. `/login`, `/api/consulta`).
   - Listas blancas/negras de IP/CIDR.
   - Umbrales de rate limiting y clave pública PEM para validar JWT.
3. `borde-proxy/lua/edge_guard.lua`: Se ejecuta en fase `access_by_lua_file`:
   - Bloquea IPs en lista negra (`HTTP 403`).
   - Aplica rate limiting en memoria compartida (`lua_shared_dict rate_limit_store`) por IP (anonimizada vía SHA-256 en memoria) y por ruta (`/login` máx. 10 req/min). Ante exceso devuelve `HTTP 429` con cabecera `Retry-After`.
   - Mitigación DDoS L7: rechaza peticiones sin `User-Agent`, con payloads > 1 MB o ráfagas anómalas.
   - Si la ruta está marcada como protegida y el modo no es `monitor`, exige cabecera `X-Human-Token` o cookie `vh_token`, verifica su firma criptográfica y expiración (`exp`) localmente en Lua; si falta o es inválido, devuelve `HTTP 401` con JSON `{ "error": "verification_required", "mode": "..." }`.
4. `borde-proxy/nginx.conf`: Integrar `init_worker_by_lua_file` y `access_by_lua_file`, manteniendo TLS 1.3 y enrutamiento transparente hacia `demo-institucional` y `/api/v1/*` hacia `backend-nucleo`.

Restricciones:
- Si `backend-nucleo` no está levantado aún, el proxy NO debe fallar al arrancar; debe operar usando `default_policy.json` (fail-safe).
- Zero peticiones externas hacia internet.

Verificación:
Reconstruye `borde-proxy` con Docker Compose, verifica que una petición normal a `GET https://localhost/` pase (200), una petición sin token a `POST https://localhost/login` sea interceptada (401) y una ráfaga de 25 peticiones rápidas dispare `HTTP 429`.
```

---

### Prompt 5 — Arsenal de Pruebas (Bot Headless, DDoS, Offline) y Documentación (Hora 18:00)
*Para asegurar los puntos de Funcionalidad, Seguridad y Presentación ante el jurado:*

```text
Objetivo: Crear la suite de pruebas de ataque para la demostración en vivo, validar el arranque 100 % offline (air-gapped) y redactar la documentación técnica de mis subsistemas en castellano.

Alcance y archivos a crear:
1. `scripts-ataque/simular_bot.py`: Script en Python que envía peticiones automatizadas con trayectorias lineales y `webdriver_flag=true` contra `ia-conductual` y el flujo de login, demostrando la detección inmediata ($R > 0.75$).
2. `scripts-ataque/simular_ddos_l7.py`: Script asíncrono (`asyncio` + `httpx`) que lanza 300 peticiones concurrentes contra `https://localhost/login` y reporta el porcentaje de bloqueos `HTTP 429` del borde frente a la disponibilidad de una petición legítima con token válido.
3. `scripts-ataque/verificar_airgapped.sh`: Script Bash que inspecciona los contenedores activos, verifica que las redes internas tienen `Internal: true`, mide la latencia promedio del endpoint `/internal/predict` (< 50 ms) y exporta el inventario de paquetes de mis imágenes Docker para el SBOM.
4. Redactar de forma clara, técnica y en castellano los tres documentos asignados a Dev 2:
   - `docs/01-arquitectura-soberana.md` (con diagrama Mermaid de flujo de red y aislamiento).
   - `docs/03-ia-conductual-local.md` (explicando variables heurísticas, privacidad efímera y benchmarks < 50 ms).
   - `docs/07-despliegue-onpremise.md` (guía paso a paso para levantar la plataforma en servidores nacionales sin internet).

Restricciones:
- Los scripts de prueba no deben dejar basura ni modificar configuraciones de producción.

Verificación:
Ejecuta `bash scripts-ataque/verificar_airgapped.sh` y `python scripts-ataque/simular_ddos_l7.py`, confirmando latencia < 50 ms y bloqueo efectivo de la ráfaga DDoS.
```

---

## Parte 3: Atajos Clave de Antigravity para Ahorrar Tiempo

* **Usa `@` para referenciar archivos exactos:** Si ocurre un error en un contenedor, escribe `@borde-proxy/nginx.conf falla al recargar con este error: [pegar log]`. Antigravity leerá solo ese archivo sin gastar tokens escaneando todo el proyecto.
* **Usa `/compact` al terminar cada Prompt:** Al cerrar el Prompt 1, 2, 3 y 4, ejecuta `/compact` en el chat. Esto limpia el historial largo manteniendo las decisiones clave y evita que el agente se vuelva lento o confunda versiones viejas de archivos.
* **Corta desviaciones al instante con `Esc`:** Si ves que Antigravity intenta instalar una librería pesada o editar archivos de Dev 1, presiona `Esc` de inmediato y corrige el rumbo.