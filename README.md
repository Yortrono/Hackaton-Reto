# Servicio Autónomo de Verificación Humana y Mitigación de Bots

**Hackathon Venezuela Innova 2026 — Plataforma Tecnológica Soberana**

Este repositorio contiene la arquitectura completa del servicio nacional de verificación de humanidad y defensa contra ataques automatizados (bots, scraping malicioso, credential stuffing y ataques DDoS L7), diseñado para operar **100 % *on-premise*** en infraestructura institucional nacional sin dependencias externas ni transferencia de datos al exterior.

---

## 1. Principios Arquitectónicos No Negociables

1. **Soberanía Tecnológica Total (Zero External Dependencies):**
   - El sistema opera de manera autónoma o en redes desconectadas (*air-gapped*).
   - Prohibido el uso de servicios extranjeros en tiempo de ejecución (Cloudflare, reCAPTCHA, Google Fonts, CDNs como cdnjs/unpkg).
   - 100 % de bibliotecas y contenedores de código abierto (FOSS) auditables.
2. **Privacidad por Diseño (Zero Raw Biometrics / Zero Raw IPs):**
   - Análisis conductual efímero en memoria RAM.
   - No se almacenan coordenadas de ratón crudas, pulsaciones de teclado ni texto del usuario.
   - Anonimización inmediata de direcciones IP mediante $\text{SHA-256}(\text{IP} + \text{sal\_rotativa})$.
3. **Inferencia Local de Alta Velocidad:**
   - Modelos conductuales basados en LightGBM y ONNX Runtime ejecutados en servidor local con latencia estrictamente inferior a $50\text{ ms}$ (promedio $< 5\text{ ms}$).

---

## 2. Estructura del Repositorio y Roles de Ingeniería

El proyecto se encuentra organizado bajo una separación modular estricta entre 3 desarrolladores:

| Subsistema / Módulo | Desarrollador | Tecnologías | Responsabilidad Principal |
| :--- | :--- | :--- | :--- |
| **`backend-nucleo/`** | **Dev 1** | Python 3.11+, FastAPI, Ed25519, SQLite WAL | API REST, Bóveda criptográfica, RBAC/MFA, emisión y consumo único de JWT (`jti`). |
| **`borde-proxy/`**, **`ia-conductual/`** | **Dev 2** | OpenResty (Nginx+Lua), LightGBM, ONNX Runtime | Inspección perimetral L7, mitigación de bots, inferencia local $< 50\text{ ms}$, Docker Compose. |
| **`sdk-cliente/`**, **`consola-admin/`** | **Dev 3** | Vanilla JS, Node.js (FOSS), Canvas nativo, SVG | Widget web autocontenido, consola de observabilidad de 6 módulos, SBOM y documentación. |

---

## 3. Subsistemas Desarrollados por Dev 3 (Angela)

### 3.1 SDK Cliente Minimalista (`sdk-cliente/`)
- **Autocontenido y Ligero:** Vanilla JS empaquetado en `sdk-verificacion.min.js` (~25 KB). Cero llamadas a CDNs o librerías de terceros.
- **Doble Modo Operativo:**
  - *Modo Pasivo (Invisible):* Recolección en RAM de entropía angular de puntero, cadencia de teclado y señales de navegador, resolución de Proof-of-Work (PoW) Web Crypto y verificación sin fricción para el usuario legítimo.
  - *Modo Desafío Accesible:* Reto interactivo de alineación espacial (`spatial_alignment`) responsive, operable al 100 % mediante teclado (flechas y Enter) con atributos ARIA completos.
- **Inyección Transparente de Token:** Guarda el JWT en cookie segura `vh_token`, inyecta la cabecera `X-Human-Token` en llamadas `fetch` y `XMLHttpRequest`, y añade campos ocultos en formularios automáticamente.
- **Página de Prueba:** Disponible en `sdk-cliente/index.html`.

### 3.2 Consola Administrativa y de Observabilidad (`consola-admin/`)
Panel de gestión y telemetría en tiempo real accesible en el **puerto 3000** con cero recursos remotos (todos los estilos, iconos SVG y gráficos en Canvas se sirven localmente):
- **Seguridad y RBAC:** Autenticación con soporte de segundo factor **MFA/TOTP** y roles estrictos:
  - `security_admin`: control total, rotación de claves criptográficas y carga de pesos IA.
  - `operator`: configuración de sitios, umbrales y listas blancas/negras.
  - `auditor`: solo lectura de observabilidad y bitácora de auditoría.
- **Los 6 Módulos Implementados:**
  1. *Gestión de Sitios y Aplicaciones:* Dominios, Site Key, Secret Key y rutas protegidas.
  2. *Motor de Reglas y Mitigación:* Selector de modo (`monitor`, `challenge`, `block`), deslizadores para umbrales de IA (`challenge_min`, `block_min`), rate limiting y listas IP/CIDR.
  3. *Bóveda Criptográfica Local:* Estado de claves asimétricas `Ed25519`, visualizador PEM y rotación periódica.
  4. *Observabilidad en Tiempo Real:* Dashboard con gráficos nativos en Canvas, contadores de tráfico humano vs. bots, latencia IA ($< 50\text{ ms}$) y eventos anonimizados.
  5. *Gestión del Modelo de IA:* Estado y métricas del modelo, y carga/recarga en caliente de archivos `.onnx`.
  6. *Auditoría Inmutable:* Bitácora cronológica con encadenamiento criptográfico SHA-256 e indicador de integridad de cadena (`chain_integrity_valid: true`).

### 3.3 Auditoría de Seguridad y Licencia
- **`SBOM.json`:** Software Bill of Materials consolidado en formato CycloneDX 1.5, validando que el 100 % de dependencias son FOSS y con 0 CVEs críticos.
- **`LICENCIA.md`:** Licencia Apache 2.0 con compromiso de soberanía tecnológica.

---

## 4. Guía de Ejecución y Pruebas Rápidas

### Probar el SDK Cliente:
```bash
cd sdk-cliente
npm test         # Ejecuta la suite de pruebas unitarias y validación de contratos
npm run build    # Compila y minimiza sdk-verificacion.min.js
```
Para ver la demostración interactiva en el navegador, abra directamente `sdk-cliente/index.html` o levante un servidor estático local.

### Levantar la Consola Administrativa:
```bash
cd consola-admin
npm test         # Ejecuta las pruebas de endpoints y verificación de contratos API
npm start        # Inicia el servidor web en http://localhost:3000
```
- Ingrese a `http://localhost:3000`
- Credenciales de prueba: Usuario `admin` (o `operador` / `auditor`), código TOTP: `123456`.

---

## 5. Documentación Técnica de Referencia

- [Contratos JSON Estándar](file:///home/participante/Hackathon-reto/Hackaton-Reto/docs/02-contratos-json.md)
- [Guía de Integración del SDK Web](file:///home/participante/Hackathon-reto/Hackaton-Reto/docs/05-guia-integracion-sdk.md)
- [Manual de la Consola Administrativa](file:///home/participante/Hackathon-reto/Hackaton-Reto/docs/06-manual-consola-admin.md)
- [Auditoría SBOM CycloneDX](file:///home/participante/Hackathon-reto/Hackaton-Reto/SBOM.json)
- [Licencia de Código Abierto](file:///home/participante/Hackathon-reto/Hackaton-Reto/LICENCIA.md)
