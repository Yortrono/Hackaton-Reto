# Servicio Autónomo de Verificación Humana y Mitigación de Bots

## Participantes
- Angela Rojas (Dev 3 - SDK Cliente Minimalista, Consola Administrativa y Observabilidad Web)
- José Peña (Dev 1 - Backend Núcleo, Bóveda Criptográfica Ed25519 y API REST)
- Yorbel Carrero (Dev 2 - IA Conductual Local en RAM, Borde / Reverse Proxy OpenResty e Infraestructura)

## Descripción del proyecto
Plataforma soberana, modular y autocontenida de defensa perimetral, verificación humana y mitigación de bots automatizados concebida para operar 100 % *on-premise* y en entornos desconectados (*air-gapped*), eliminando cualquier dependencia de proveedores extranjeros o servicios privativos en la nube (tales como Cloudflare, reCAPTCHA o hCaptcha).

La solución protege portales y servicios web institucionales del Estado venezolano mediante una arquitectura multicapa:
1. **Inspección en el Borde:** El Reverse Proxy OpenResty intercepta el tráfico entrante, aplica limitación de tasa (*rate limiting*) dinámica, filtra ataques de denegación de servicio (DDoS L7) y valida de forma descentralizada la firma asimétrica **Ed25519** de los tokens de verificación antes de permitir el acceso al backend de la aplicación.
2. **Evaluación de Telemetría Biomecánica:** Un SDK web ligero y autocontenido analiza de forma pasiva e invisible las señales de interacción del usuario (entropía angular y aceleración del puntero, dinámica de vuelo/presión de teclas y consistencia de entorno), resolviendo una prueba de trabajo criptográfica (PoW Web Crypto).
3. **Inferencia Local Ultrarrápida:** El microservicio de IA local ejecuta un modelo de clasificación probabilística en memoria RAM (ONNX Runtime / LightGBM) en $< 1\text{ ms}$ (meta oficial $< 50\text{ ms}$) bajo el principio de *Privacidad por Diseño* (cero almacenamiento de biometría cruda en disco o logs).
4. **Desafío Interactivo Accesible:** Si el puntaje de riesgo supera el umbral configurado, se activa un reto interactivo no frustrante de alineación espacial (`spatial_alignment`), 100 % accesible vía teclado o pantalla táctil.

## Alcance
- **Funcionalidades implementadas en el hackathon:**
  - **Capa de Borde / Reverse Proxy y API Gateway (OpenResty + LuaJIT):** Terminación TLS 1.3 perimetral, aplicación dinámica de políticas por ruta (`/login`, `/api/consulta`), rate limiting por IP/ruta con respuesta `HTTP 429`, mitigación anti-DDoS y validación local de tokens JWT Ed25519.
  - **Núcleo Backend de Verificación (FastAPI):** Cumplimiento estricto de los contratos de API oficiales (`POST /api/v1/challenge/init`, `POST /api/v1/challenge/verify`, `POST /api/v1/token/validate` y `GET /api/v1/policies/{site_id}`). Gestión de desafíos PoW SHA-256, prevención de ataques de repetición con consumo de identificador único de un solo uso (`jti`), y anonimización de direcciones IP mediante hash criptográfico SHA-256 unidireccional.
  - **Módulo de Inteligencia Artificial Conductual Local (ONNX Runtime):** Modelo supervisado ligero entrenado localmente para clasificar tráfico humano vs. bots sobre 14 variables normalizadas. Inferencia en memoria RAM con latencia media de $0.73\text{ ms}$ y recarga de pesos en caliente (*hot-reload thread-safe*).
  - **SDK / Widget Web Minimalista (Vanilla JS):** Componente frontend autocontenido (~25 KB) sin CDNs ni librerías externas. Modo dual pasivo/interactivo, inyección automática de cabeceras `X-Human-Token` y cookies seguras `vh_token`.
  - **Consola Administrativa y de Observabilidad Web (Node.js / Vanilla JS):** Control de acceso basado en roles (RBAC: `security_admin`, `operator`, `auditor`) con soporte de segundo factor MFA/TOTP (RFC 6238). Implementación completa de los 6 módulos funcionales:
    1. *Gestión de Sitios y Aplicaciones:* Registro de dominios, llaves públicas/privadas y rutas protegidas.
    2. *Motor de Reglas y Mitigación:* Modos (`monitor`, `challenge`, `block`), umbrales de IA y listas blancas/negras IP/CIDR.
    3. *Bóveda Criptográfica Local:* Gestión, visualización PEM y rotación de pares de claves asimétricas Ed25519 con custodia en reposo cifrada en AES-256-GCM.
    4. *Observabilidad en Tiempo Real:* Dashboards con KPIs (peticiones totales, ratio humano vs. bot, latencia de IA), gráfico Canvas continuo en vivo y bitácora con filtrado interactivo por tipo de acción (`Bloqueo`, `Rate Limit`, `Desafío`, `Pasivo`).
    5. *Gestión del Modelo de IA:* Ficha técnica, versión activa (`lgbm-conductual-v1.0.0`), precisión auditada (98.4%) y cargador seguro de nuevos modelos `.onnx`.
    6. *Auditoría Inmutable:* Registro histórico encadenado criptográficamente mediante SHA-256 (`prev_hash`) con verificación matemática de integridad al 100%.
  - **Demo Institucional Protegida:** Portal Ciudadano web simulando el ingreso a trámites oficiales del Mincyt.
  - **Auditoría de Dependencias (SBOM):** Catálogo de componentes de software (CycloneDX 1.5) garantizando el 100 % de librerías FOSS y 0 CVEs críticos.

- **Limitaciones o módulos fuera de alcance:**
  - Operación deliberadamente *air-gapped*: no se integran servicios de reputación de IP o geolocalización basados en nubes o APIs de terceros.
  - No se almacenan en disco ni en bases de datos coordenadas crudas $(x,y)$ de puntero ni secuencias de teclas pulsadas, en cumplimiento de los estándares éticos y legales de privacidad.

## Requerimientos del sistema
- **Lenguaje / Runtime y versiones:**
  - Python 3.11+ (para `backend-nucleo` y el motor de inferencia en `ia-conductual`)
  - Node.js 20+ LTS (para el servidor de la `consola-admin`)
  - OpenResty 1.25+ / Nginx con soporte LuaJIT y OpenSSL 3 (para `borde-proxy`)
- **Base de datos, contenedores o dependencias externas:**
  - **Contenedores:** Docker Engine 24+ con Docker Compose v2.20+ (o Podman 4.9+ con Podman Compose)
  - **Base de datos:** SQLite 3 integrado con modo WAL (Write-Ahead Logging) de alta concurrencia
  - **Criptografía:** Librerías nativas `cryptography` (hazmat Ed25519 / AES-256-GCM) y `pyotp` (MFA/TOTP)
  - **Dependencias externas:** Cero (0) servicios externos, APIs remotas o CDNs. El 100 % de los paquetes se ejecutan de manera local y desconectada.

## Paso a paso de instalación / despliegue
1. **Clonar el repositorio:**
   ```bash
   git clone https://gitlab.nube.gob.ve/grupo/lara/lara_grupo6/captcha.git
   cd captcha
   ```

2. **Configurar variables de entorno (.env):**
   ```bash
   cp .env.example .env
   ```

3. **Construir los contenedores locales (Instalación de dependencias autocontenidas):**
   ```bash
   docker compose build
   # O si utiliza Podman:
   podman compose build
   ```

4. **Ejecutar la aplicación:**
   ```bash
   docker compose up -d
   # O si utiliza Podman:
   podman compose up -d
   ```

### Enlaces de Acceso Local
- **Portal Ciudadano Protegido (Borde TLS 1.3):** [https://localhost:8443/](https://localhost:8443/) (o HTTP en [http://localhost:8088/](http://localhost:8088/))
- **Consola Administrativa y de Observabilidad:** [http://localhost:3000/](http://localhost:3000/)
- **Documentación OpenAPI del Backend Núcleo:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Microservicio de IA Conductual:** [http://localhost:8001/docs](http://localhost:8001/docs)
