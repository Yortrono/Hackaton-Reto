---
name: soberania-verificacion-humana
description: Estándares obligatorios de soberanía tecnológica, contratos JSON compartidos, privacidad por diseño y reglas de coordinación para los 3 desarrolladores del Servicio Autónomo de Verificación Humana y Mitigación de Bots. Activar en cualquier tarea de arquitectura, código, pruebas o documentación del proyecto.
---

# Skill Global del Equipo — Hackathon Venezuela Innova 2026

Esta habilidad define las reglas transversales que **Dev 1 (Backend/Cripto)**, **Dev 2 (IA/Borde/Infra)** y **Dev 3 (SDK/Consola/SBOM)** deben cumplir sin excepción para garantizar que los cinco subsistemas integren a la primera y cumplan los 27 ítems de evaluación del jurado.

## 1. Principios Arquitectónicos No Negociables
1. **Soberanía Tecnológica Total (Zero External Dependencies):**
   - La plataforma debe operar 100 % *on-premise* o en nube nacional aislada (*air-gapped*).
   - **PROHIBIDO** realizar peticiones salientes hacia internet en tiempo de ejecución: cero llamadas a Cloudflare, reCAPTCHA, hCaptcha, Google Fonts, CDNs públicos (unpkg, jsdelivr, cdnjs) o servicios de telemetría externos.
   - El 100 % de las librerías y contenedores deben ser de código abierto (FOSS) auditables.
2. **Privacidad por Diseño (Zero Raw Biometrics / Zero Raw IPs):**
   - El análisis conductual es **estrictamente efímero en memoria RAM**.
   - **PROHIBIDO** guardar en disco, logs o base de datos coordenadas crudas de ratón/táctil, pulsaciones de teclado individuales o direcciones IP sin anonimizar.
   - Cualquier registro de eventos o métricas debe usar direcciones IP anonimizadas mediante *hash* criptográfico con sal rotativa.
3. **Rendimiento de Inteligencia Artificial Local:**
   - Toda inferencia del modelo conductual (`ONNX Runtime` / `LightGBM`) debe ejecutarse localmente en el servidor con una latencia estrictamente inferior a **$50\text{ ms}$**.

## 2. Fuente Única de Verdad para Integración Asíncrona
Antes de crear o modificar cualquier endpoint, payload o mock, consulta obligatoriamente `@docs/02-contratos-json.md`.

### Reglas de Serialización Compartidas:
- **Llaves JSON:** Siempre `snake_case` en inglés técnico (`challenge_id`, `risk_score`, `site_key`, `jwt_token`).
- **Tiempos:** ISO-8601 en UTC (`"2026-11-26T18:30:00Z"`) o Unix timestamp en segundos para claims JWT (`iat`, `exp`).
- **Errores HTTP (4xx / 5xx):** Todos los servicios (`borde-proxy` y `backend-nucleo`) deben devolver el envoltorio unificado:
  ```json
  {
    "error": {
      "code": "VERIFICATION_REQUIRED",
      "message": "Descripción clara en castellano",
      "details": {},
      "trace_id": "uuid-v4",
      "timestamp": "2026-11-26T18:30:00Z"
    }
  }
  ```

### Mapa de Puertos Internos (Red Docker `soberana_interna`):
- `borde-proxy`: `80` / `443` (único punto de entrada expuesto al exterior con $\text{TLS } 1.3$).
- `backend-nucleo`: `8000` (API REST `/api/v1/*`).
- `ia-conductual`: `8001` (Inferencia interna `/internal/*`).
- `consola-admin`: `3000` (Panel administrativo web).
- `demo-institucional`: `8080` (Aplicación institucional protegida de demostración).

## 3. Protocolo de Aislamiento de Archivos (Cero Conflictos Git)
Cada agente debe respetar estrictamente las fronteras de directorio de su desarrollador asignado:
- **Dev 1:** `backend-nucleo/`, `docs/02-contratos-api.yaml`, `docs/04-seguridad-criptografia.md`.
- **Dev 2:** `borde-proxy/`, `ia-conductual/`, `demo-institucional/`, `scripts-ataque/`, `docker-compose.yml`, `docs/01-arquitectura-soberana.md`, `docs/03-ia-conductual-local.md`, `docs/07-despliegue-onpremise.md`.
- **Dev 3:** `sdk-cliente/`, `consola-admin/`, `SBOM.json`, `LICENCIA.md`, `README.md`, `docs/05-guia-integracion-sdk.md`, `docs/06-manual-consola-admin.md`.

Si un cambio requiere modificar un contrato en otro subsistema, **no edites el código de tu compañero**: actualiza o propone el cambio en `@docs/02-contratos-json.md` y notifícalo en el punto de sincronización.

## 4. Lista de Verificación Antes de cada Punto de Control
Al finalizar cualquier bloque de trabajo, el agente debe verificar:
1. ¿El código compila/arranca sin conexión a internet?
2. ¿Los payloads de entrada y salida coinciden campo por campo con `@docs/02-contratos-json.md`?
3. ¿Se eliminaron logs de depuración que puedan exponer IPs reales, claves privadas o telemetría cruda?
4. ¿Toda la documentación y mensajes orientados al usuario están redactados en castellano técnico correcto?