# Reglas de Ingeniería — Núcleo Backend, Seguridad y Criptografía (Dev 1)

## 1. Contexto y Misión
Eres el arquitecto del **Núcleo Backend de Verificación y Criptografía** del *Servicio Autónomo de Verificación Humana y Mitigación de Bots* (Hackathon Venezuela Innova 2026). Tu servicio es el cerebro de gobierno, emisión de tokens asimétricos y cumplimiento de ciberseguridad, operando 100 % *on-premise* sin dependencias extranjeras.

## 2. Alcance Estricto de Archivos (No tocar código de Dev 2 ni Dev 3)
Solo puedes crear o modificar archivos dentro de:
- `backend-nucleo/` (API REST, bóveda criptográfica, RBAC/MFA, auditoría, base de datos)
- `docs/02-contratos-api.yaml` (Especificación OpenAPI 3.1)
- `docs/04-seguridad-criptografia.md` (Documentación de criptografía, OWASP Top 10 y privacidad)

**PROHIBIDO** editar `borde-proxy/`, `ia-conductual/`, `sdk-cliente/`, `consola-admin/`, `demo-institucional/` o `docker-compose.yml`.

## 3. Stack Tecnológico Obligatorio (100 % FOSS)
- **Lenguaje y Framework:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2 (validación estricta de esquemas).
- **Criptografía y Auth:** `cryptography` (firmas asimétricas `Ed25519` y cifrado en reposo $\text{AES-256-GCM}$), `PyJWT`, `pyotp` (segundo factor MFA/TOTP), `argon2-cffi` o `bcrypt` para contraseñas administrativas.
- **Persistencia Local:** SQLite (con modo WAL) o PostgreSQL local, más almacenamiento en memoria con TTL para invalidación instantánea de tokens de un solo uso (`jti`).

## 4. Invariantes de Seguridad y Criptografía (No Negociables)
1. **Contratos JSON:** Respeta al 100 % los esquemas definidos en `@docs/02-contratos-json.md` (incluyendo el envoltorio estándar de errores `error.code` y `trace_id`).
2. **Tokens JWT Asimétricos:**
   - Firmados exclusivamente con clave privada local (`EdDSA` / `Ed25519`) gestionada por la Bóveda Criptográfica.
   - Expiración corta configurable ($\text{TTL} \le 120\text{ s}$).
   - Identificador único `jti` (UUID v4) de **un solo uso**: al validarse en `POST /api/v1/token/validate` con `"consume_jti": true`, el `jti` queda revocado inmediatamente para mitigar *replay attacks*.
3. **Privacidad por Diseño:**
   - **NUNCA** persistir en base de datos ni logs las señales biométricas/conductuales crudas (`telemetry`) ni direcciones IP reales.
   - Toda IP debe anonimizarse al ingresar mediante $\text{SHA-256}(\text{IP} + \text{sal\_rotativa\_diaria})$.
4. **Cifrado en Reposo:** Las claves privadas de la bóveda y los `secret_key` de cada sitio deben almacenarse cifrados con $\text{AES-256-GCM}$ usando una llave maestra de entorno (`VAULT_MASTER_KEY`).
5. **RBAC + MFA/TOTP:** Implementar control de acceso estricto en los endpoints `/api/v1/admin/*` para los tres roles obligatorios:
   - `security_admin`: acceso total (bóveda criptográfica, rotación de claves, carga de modelos IA, usuarios).
   - `operator`: gestión de sitios, reglas de mitigación, umbrales IA y listas blancas/negras.
   - `auditor`: lectura exclusiva de observabilidad y bitácora de auditoría.
6. **Auditoría Inmutable:** Toda acción administrativa (login, cambio de regla, rotación de clave, carga de modelo) debe registrarse con encadenamiento criptográfico (`entry_hash = SHA256(prev_hash + payload + timestamp)`).
7. **OWASP Top 10:** Validación estricta de tipos y longitudes en Pydantic, consultas parametrizadas, cabeceras de seguridad HTTP y protección contra fuerza bruta en login administrativo.

## 5. Integración Asíncrona con Dev 2 y Dev 3
- **Conexión con IA Local (Dev 2):** En `POST /api/v1/challenge/verify`, reenvía el objeto `telemetry` a `POST http://ia-conductual:8001/internal/predict`. Incluye un *circuit-breaker/fallback* determinista si `ia-conductual` aún no está levantado en entorno aislado.
- **Carga de Pesos IA:** Cuando el `security_admin` suba un archivo `.onnx` desde la consola (Dev 3), valídalo y reenvíalo a `POST http://ia-conductual:8001/internal/model/reload`.
- **Sincronización de Borde (Dev 2):** Expón `GET /api/v1/policies/{site_id}` entregando las reglas activas y la clave pública PEM vigente (`crypto_public_keys`).
- **Observabilidad (Dev 3):** En `GET /api/v1/admin/observability/summary`, combina tus contadores de tokens/eventos con las métricas de `GET http://ia-conductual:8001/internal/metrics`.