# Documento de Seguridad, Criptografía y Privacidad Soberana

**Proyecto:** Servicio Autónomo de Verificación Humana y Mitigación de Bots  
**Edición:** Hackathon Venezuela Innova 2026  
**Subsistema:** Núcleo Backend de Verificación y Criptografía (`backend-nucleo`)  
**Responsable:** Arquitecto de Backend, Criptografía y Seguridad (Dev 1)

---

## 1. Principios de Soberanía Tecnológica y Privacidad por Diseño

El sistema ha sido concebido desde sus cimientos para operar bajo un entorno estrictamente soberano (*air-gapped* o red nacional aislada), garantizando:
- **Cero dependencias extranjeras en tiempo de ejecución:** Sin llamadas externas a CDNs, reCAPTCHA, Cloudflare o APIs foráneas. El 100 % de las dependencias criptográficas y de tiempo de ejecución son de Código Abierto (FOSS) auditables (`cryptography`, `PyJWT`, `argon2-cffi`, `pyotp`, `FastAPI`).
- **Tratamiento efímero de telemetría (Zero Raw Biometrics):** El análisis de señales conductuales se procesa exclusivamente en memoria RAM. Está terminantemente prohibido almacenar en base de datos o bitácoras las coordenadas brutas de puntero, trayectorias continuas o eventos de teclado individuales.
- **Anonimización criptográfica de direcciones IP (Zero Raw IPs):** Toda dirección IP de cliente es transformada al ingresar mediante una función hash unidireccional con sal rotativa diaria:
  $$\text{IP\_Hash} = \text{SHA-256}(\text{IP\_Real} \parallel \text{Sal\_Rotativa\_Diaria})$$
  La sal rotativa se deriva diariamente de un secreto criptográfico local (`SALT_ROTATIVE_SECRET`) y de la fecha UTC, imposibilitando ataques de diccionario cruzados entre días distintos.

---

## 2. Bóveda Criptográfica y Gestión de Llaves Asimétricas

### 2.1 Criptografía Asimétrica de Curva Elíptica (Ed25519 / EdDSA)
Para la firma y emisión de los tokens de verificación humana se utiliza exclusivamente el algoritmo de firma digital de curvas de Edwards **Ed25519** (RFC 8032), que ofrece:
- Longitud de clave compacta (256 bits) con un nivel de seguridad equivalente a RSA-3072.
- Resistencia inmunológica a ataques de canal lateral por temporización (tiempo de ejecución constante en firma y verificación).
- Velocidad extrema de firma y validación ($\ll 1\text{ ms}$ por operación), óptima para inspección masiva en el Reverse Proxy de Borde (`borde-proxy` en OpenResty/Lua).

### 2.2 Cifrado en Reposo de Claves Privadas y Secretos ($\text{AES-256-GCM}$)
Las claves privadas Ed25519 y los secretos de cada sitio cliente (`secret_key`) nunca se persisten en texto plano en la base de datos SQLite. Se almacenan cifrados con $\text{AES-256-GCM}$ (Galois/Counter Mode) usando una llave maestra (`VAULT_MASTER_KEY`):
- Se utiliza un vector de inicialización/nonce criptográfico único de 96 bits ($\text{IV}$) generado por `os.urandom(12)` en cada cifrado.
- La etiqueta de autenticación (Auth Tag de 128 bits) previene cualquier intento de manipulación o bit-flipping de las claves almacenadas.
- La clave maestra de entorno se deriva internamente mediante $\text{SHA-256}$ asegurando exactamente 32 bytes (256 bits).

### 2.3 Ciclo de Vida y Rotación Soberana de Claves
El endpoint `POST /api/v1/admin/vault/rotate` permite al rol `security_admin` rotar la clave activa sin interrumpir el servicio:
1. Se genera un nuevo par de claves Ed25519 identificado con un `kid` timestamped (`key-YYYY-MM-DD-HHMMSS`).
2. Se cifra la nueva clave privada con $\text{AES-256-GCM}$ y se marca como activa (`active = 1`).
3. La clave anterior pasa a estado inactivo (`active = 0`), permitiendo verificar tokens en vuelo emitidos previamente hasta su expiración ($\le 120\text{ s}$).
4. El cambio se propaga de inmediato al Reverse Proxy mediante `GET /api/v1/policies/{site_id}`.

---

## 3. Tokens JWT Asimétricos y Mitigación de Replay Attacks

### 3.1 Estructura del Token de Verificación Humana
El token emitido por el backend contiene los siguientes claims estandarizados:

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

### 3.2 Invariantes de Seguridad del Token
1. **Firma Asimétrica Obligatoria:** Firmado con la clave privada Ed25519 de la bóveda. El reverse proxy de borde y los servicios protegidos solo requieren la clave pública PEM para validar la autenticidad sin compartir secretos simétricos.
2. **Expiración Corta:** $\text{TTL} = 90\text{ s}$ por defecto ($\text{TTL} \le 120\text{ s}$ máximo no configurable por cliente), minimizando la ventana de exposición en caso de intercepción en el cliente.
3. **Consumo de `jti` Único (Anti-Replay Attack):** Cada token posee un identificador universalmente único `jti` (UUID v4). Al ser validado por la aplicación protegida en `POST /api/v1/token/validate` con `"consume_jti": true`, el `jti` se almacena con su timestamp de expiración. Cualquier intento posterior de reutilizar el mismo token es inmediatamente rechazado con HTTP 401 (`INVALID_TOKEN`).

---

## 4. Prueba de Trabajo (Proof of Work - PoW)

Para proteger los endpoints de inicialización y verificación frente a ataques de denegación de servicio distribuido (DDoS) y saturación de IA, el sistema implementa una prueba de trabajo soberana basada en $\text{SHA-256}$:
- En `POST /api/v1/challenge/init`, el backend genera un `nonce` criptográfico aleatorio y asigna un nivel de dificultad $D$ (por defecto $D = 3$).
- El cliente debe encontrar una cadena hexadecimal `pow_solution` tal que:
  $$\text{SHA-256}(\text{nonce} \parallel \text{pow\_solution}) \text{ comience con } D \text{ ceros (ej. } \texttt{000...})$$
- La verificación en el backend toma $\mathcal{O}(1)$ tiempo constante ($\ll 0.01\text{ ms}$), mientras que para un atacante bot que envíe miles de peticiones automatizadas el coste en CPU se vuelve prohibitivo.

---

## 5. Control de Acceso Basado en Roles (RBAC) y Doble Factor (MFA/TOTP)

### 5.1 Catálogo de Roles
El panel administrativo `/api/v1/admin/*` implementa separación estricta de responsabilidades (*Principle of Least Privilege*):

| Rol | Privilegios Asignados |
| :--- | :--- |
| **`security_admin`** | Control total de la Bóveda Criptográfica, rotación de claves, carga de pesos de modelos ONNX y gestión de usuarios administradores. |
| **`operator`** | Gestión de sitios institucionales, modificación de políticas de protección (rutas, rate limits, listas blancas/negras) y umbrales de riesgo IA. |
| **`auditor`** | Acceso de solo lectura a la bitácora inmutable de auditoría y al cuadro de mando de observabilidad en tiempo real. |

### 5.2 Hashing de Contraseñas de Última Generación (Argon2id)
Las credenciales de los administradores se procesan con **Argon2id**, el ganador de la *Password Hashing Competition* (PHC). Ofrece resistencia probada frente a ataques basados en GPUs y ASICs mediante memoria configurable e iteraciones temporales.

### 5.3 Segundo Factor Obligatorio (TOTP / RFC 6238)
Los usuarios pueden enrolar aplicaciones autenticadoras soberanas (FreeOTP, Google Authenticator) mediante semillas base32 y códigos móviles basados en tiempo (intervalos de 30 segundos, algoritmo HMAC-SHA1 estándar).

### 5.4 Mitigación de Ataques de Fuerza Bruta
El endpoint de autenticación `/api/v1/admin/auth/login` rastrea los intentos fallidos consecutivos por usuario. Tras 5 intentos fallidos, la cuenta se bloquea automáticamente durante 15 minutos, respondiendo con HTTP 429 (`RATE_LIMIT_EXCEEDED`).

---

## 6. Bitácora de Auditoría Criptográficamente Inmutable (Hash Chaining)

Toda acción administrativa que altere el estado del sistema (inicio de sesión, rotación de clave, modificación de política, registro de sitio, carga de modelo IA) se registra en una cadena inmutable inspirada en estructuras de registro Merkelizado:

$$\text{entry\_hash}_i = \text{SHA-256}(\text{prev\_hash}_{i-1} \parallel \text{payload\_hash}_i \parallel \text{timestamp}_i \parallel \text{actor}_i \parallel \text{action}_i \parallel \text{resource}_i)$$

- Para el primer registro del sistema (bloque génesis), $\text{prev\_hash}_0 = 0^{64}$.
- **Verificación de Integridad en Tiempo Real:** En `GET /api/v1/admin/audit-logs`, el método `verify_chain_integrity()` recalcula secuencialmente toda la cadena de hashes desde el origen. Si un atacante con acceso directo a la base de datos modifica el texto de un registro, añade una fila o elimina un evento pasado, la verificación matemática falla instantáneamente reportando `chain_integrity_valid: false`.

---

## 7. Mapeo y Mitigación contra OWASP Top 10 (API Security)

| Riesgo OWASP API | Vector Potencial | Mitigación Implementada en `backend-nucleo` |
| :--- | :--- | :--- |
| **API1: Broken Object Level Authorization (BOLA)** | Intento de alterar políticas de otro sitio manipulando `site_id` | Validación de pertenencia del sitio en base de datos y aislamiento de permisos por rol administrativo. |
| **API2: Broken Authentication** | Reutilización de credenciales o tokens caducados | JWT asimétricos con TTL $\le 120\text{ s}$, revocación obligatoria de `jti`, Argon2id y MFA/TOTP. |
| **API3: Broken Object Property Level Authorization** | Inyección de parámetros no autorizados en políticas | Esquemas estrictos de Pydantic v2 con validación de tipos, rangos y descarte de campos extra. |
| **API4: Unrestricted Resource Consumption** | Ataques DDoS o inundación de peticiones de validación | Prueba de trabajo (PoW) en `challenge/init`, SQLite en modo WAL de alto rendimiento y circuit breaker en llamadas a IA. |
| **API5: Broken Function Level Authorization** | Un operador intentando rotar claves criptográficas | Dependencia de FastAPI `require_role(["security_admin"])` que bloquea peticiones no privilegiadas con HTTP 403 `UNAUTHORIZED_ROLE`. |
| **API6: Unrestricted Access to Sensitive Business Flows** | Bots ejecutando peticiones automatizadas de compra o consulta | Verificación conductual de telemetría con IA local ($< 50\text{ ms}$) y escalado dinámico a retos espaciales interactivos. |
| **API7: Server Side Request Forgery (SSRF)** | Envío de URLs arbitrarias al backend | El backend no realiza llamadas HTTP salientes a internet ni a URLs suministradas por el usuario; solo se comunica internamente con `ia-conductual:8001` en red Docker aislada. |
| **API8: Security Misconfiguration** | Cabeceras HTTP inseguras o exposición de trazas de error | Middleware que inyecta HSTS, CSP, X-Frame-Options, X-Content-Type-Options y envoltorio unificado de errores que nunca expone stack traces internas. |
| **API9: Improper Inventory Management** | Endpoints no documentados o versiones obsoletas activas | Especificación OpenAPI 3.1 rigurosa generada en `docs/02-contratos-api.yaml` como única fuente de verdad. |
| **API10: Unsafe Consumption of APIs** | Dependencia no controlada de la IA conductual | Circuit-breaker determinista en `ia_client.py`: si `ia-conductual` falla, se ejecuta fallback heurístico local sin exponer el servicio ni colgar la petición. |
