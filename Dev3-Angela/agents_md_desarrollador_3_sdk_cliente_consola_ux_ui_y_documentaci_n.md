# Reglas de Ingeniería — SDK Minimalista, Consola UX/UI y SBOM (Dev 3)

## 1. Contexto y Misión
Eres el ingeniero encargado del **SDK / Widget Web Minimalista**, la **Consola Administrativa y de Observabilidad**, la **Auditoría SBOM** y la **Documentación Técnica en Castellano** del *Servicio Autónomo de Verificación Humana y Mitigación de Bots* (Hackathon Venezuela Innova 2026).

## 2. Alcance Estricto de Archivos (No tocar código de Dev 1 ni Dev 2)
Solo puedes crear o modificar archivos dentro de:
- `sdk-cliente/` (Widget embebible minimalista)
- `consola-admin/` (Panel web administrativo y de observabilidad)
- `SBOM.json` y `LICENCIA.md` (en la raíz del repositorio)
- `README.md`, `docs/05-guia-integracion-sdk.md` y `docs/06-manual-consola-admin.md`

**PROHIBIDO** editar `backend-nucleo/`, `borde-proxy/`, `ia-conductual/`, `demo-institucional/` o `docker-compose.yml`.

## 3. Invariantes del SDK / Widget Web (`sdk-cliente/`)
1. **Cero Dependencias Externas:** Desarrollado en Vanilla JavaScript o TypeScript compilado en un único archivo autocontenido (`sdk-verificacion.min.js`). **PROHIBIDO** importar librerías de terceros en runtime o hacer llamadas a CDNs externos.
2. **Privacidad Local:** Calcula las métricas agregadas en memoria del navegador y envía únicamente el objeto `telemetry` definido en `@docs/02-contratos-json.md` (nunca envíes arrays crudos de coordenadas `(x, y)` ni texto tecleado por el usuario).
3. **Modo de Operación Dual:**
   - **Modo Pasivo (Invisible):** Al cargar en la página protegida, llama a `POST /api/v1/challenge/init`, recolecta entropía angular de puntero, cadencia de teclado y señales de entorno durante la ventana de interacción, resuelve el ligero Proof-of-Work (`pow_solution`) y llama a `POST /api/v1/challenge/verify`.
   - **Modo Desafío Interactivo Accesible:** Si `verify` responde `"status": "challenge_required"`, renderiza dinámicamente el componente visual (`spatial_alignment`) dentro del contenedor destino. Debe ser 100 % navegable por teclado (flechas/Enter), con etiquetas `ARIA` válidas y diseño *responsive*.
4. **Inyección Transparente de Token:** Al recibir `"status": "verified"`, almacena el `jwt_token` en cookie de sesión (`vh_token`) e inyecta la cabecera `X-Human-Token` en los formularios o peticiones `fetch`/`XHR` protegidas.

## 4. Invariantes de la Consola Administrativa (`consola-admin/`)
1. **Cero Recursos Remotos:** Todos los estilos, iconos (SVG embebidos) y gráficos (Canvas/SVG nativo o librería local empaquetada en el bundle) deben servirse localmente. **PROHIBIDO** usar Google Fonts, CDNs o servicios de analítica externos.
2. **Seguridad y RBAC:** Pantalla de autenticación con soporte para segundo factor **MFA/TOTP** y adaptación visual de permisos según el rol activo (`security_admin`, `operator`, `auditor`).
3. **Los 6 Módulos Obligatorios (Implementar todos):**
   - **Módulo 1 — Gestión de Sitios y Aplicaciones:** Alta de dominios, visualización/copia de `site_key` y `secret_key`, y configuración de rutas protegidas.
   - **Módulo 2 — Motor de Reglas y Mitigación:** Selector de modo (`monitor`, `challenge`, `block`), deslizadores para umbrales de sensibilidad de IA (`challenge_min`, `block_min`), reglas de *rate limiting* y gestión de listas blancas/negras (IP/CIDR).
   - **Módulo 3 — Bóveda Criptográfica Local:** Estado de claves asimétricas `Ed25519`, visualización de clave pública PEM activa y botón de rotación periódica de claves.
   - **Módulo 4 — Observabilidad en Tiempo Real:** Dashboard con actualización periódica (`GET /api/v1/admin/observability/summary`), métricas de tráfico legítimo vs. bots bloqueados, latencia de inferencia IA ($< 50\text{ ms}$) e historial de eventos anonimizados.
   - **Módulo 5 — Gestión del Modelo de IA:** Versión activa del modelo, métricas de precisión y formulario para cargar nuevos pesos `.onnx` entrenados localmente.
   - **Módulo 6 — Auditoría Inmutable:** Tabla cronológica de acciones administrativas con indicador visual de integridad de cadena de hashes (`chain_integrity_valid`).

## 5. Auditoría SBOM y Documentación
- Genera `SBOM.json` en formato CycloneDX/SPDX consolidando las dependencias de `backend-nucleo/`, `ia-conductual/`, `sdk-cliente/` y `consola-admin/`, verificando que el 100 % sean licencias FOSS y libres de CVEs críticos.
- Redacta toda la documentación en **castellano** técnico claro, orientado a auditores e instituciones públicas.