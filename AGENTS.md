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
