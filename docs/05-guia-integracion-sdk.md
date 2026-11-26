# Guía de Integración Técnica del SDK Cliente (Dev 3)

**Proyecto:** Servicio Autónomo de Verificación Humana y Mitigación de Bots  
**Hackathon Venezuela Innova 2026**

---

## 1. Introducción y Arquitectura del SDK

El **SDK Cliente** (`sdk-verificacion.min.js`) es una biblioteca web ligera (~25 KB) desarrollada en **Vanilla JavaScript puro**, diseñada bajo los principios de soberanía tecnológica:
- **Cero Dependencias Externas:** No realiza llamadas a CDNs, librerías de terceros ni servicios foráneos.
- **Privacidad Local Absoluta:** Calcula todas las señales biométricas agregadas directamente en la memoria RAM del navegador web. NUNCA transmite coordenadas crudas de ratón `(x, y)` ni pulsaciones de teclado individuales.
- **Modo de Operación Dual:** Verificación pasiva invisible para usuarios legítimos con escalado automático a reto interactivo accesible si el puntaje de riesgo de IA así lo determina.

---

## 2. Inclusión en Aplicaciones Web Institucionales

### Opción A: Inclusión Automática mediante Atributos HTML
Incluya el script local en las páginas donde desee proteger formularios (por ejemplo, en `/login` o `/tramites`):

```html
<!-- Enlace al archivo local on-premise -->
<script 
  src="/sdk/sdk-verificacion.min.js"
  data-site-key="vh_site_9f8e7d6c5b4a3210"
  data-api-base="http://borde-proxy:80"
  async>
</script>
```

### Opción B: Inicialización Programática en JavaScript
Si su aplicación utiliza frameworks SPA (React, Vue, Angular o Vanilla JS):

```javascript
import '/sdk/sdk-verificacion.min.js';

const verificador = window.VerificacionHumana.init({
  siteKey: 'vh_site_9f8e7d6c5b4a3210',
  apiBase: 'http://borde-proxy:80',
  targetRoute: '/api/v1/tramite/enviar',
  containerId: 'verificacion-humana-widget',
  passiveDelayMs: 1200,
  onVerified: function(resultado) {
    console.log('Humano verificado con éxito:', resultado.jwt_token);
  },
  onChallengeRequired: function(desafio) {
    console.log('Reto interactivo requerido:', desafio.prompt);
  },
  onError: function(error) {
    console.error('Acceso bloqueado o error:', error);
  }
});
```

---

## 3. Funcionamiento de los Modos de Operación

### 3.1 Modo Pasivo (Invisible)
1. Al cargar la página, el SDK invoca `POST /api/v1/challenge/init` enviando el contexto del navegador (resolución, zona horaria, hash de user agent).
2. El servidor responde con `challenge_id`, `nonce` y `pow_difficulty`.
3. El SDK recolecta de forma transparente en memoria:
   - **Métricas de Puntero:** Conteo de movimientos, velocidad media, desviación estándar de aceleración, entropía angular en 8 octantes y relación de línea recta.
   - **Métricas de Teclado:** Cadencia agregada de pulsación (`mean_dwell_ms`) y tiempo de vuelo entre teclas (`std_flight_ms`).
   - **Señales de Entorno:** Bandera de automatización `navigator.webdriver`, consistencia de idiomas y viewport.
4. Resuelve el ligero desafío criptográfico Proof-of-Work con la API estándar `crypto.subtle` (SHA-256).
5. Envía las señales agregadas a `POST /api/v1/challenge/verify`.

### 3.2 Modo Desafío Interactivo Accesible (`spatial_alignment`)
Si el modelo de IA local determina que el tráfico se encuentra en una zona de riesgo medio (`challenge_min <= score < block_min`):
1. El backend responde `"status": "challenge_required"`.
2. El SDK renderiza dinámicamente el componente visual de alineación espacial dentro de `<div id="verificacion-humana-widget"></div>`.
3. **Accesibilidad Universal (WCAG 2.1 AA):**
   - El dial u objetivo puede manipularse con el ratón, mediante pantalla táctil o **100 % mediante el teclado** (Flechas Izquierda/Derecha o Arriba/Abajo para rotar, tecla `Enter` o `Espacio` para confirmar).
   - Incluye atributos ARIA nativos (`role="slider"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext`).
4. Al alinearse dentro de la tolerancia angular especificada, se envía `interactive_response` para la emisión del token definitivo.

---

## 4. Inyección Transparente de Token JWT

Una vez obtenida la verificación humana (`"status": "verified"`):
1. **Cookie de Sesión:** El SDK almacena automáticamente el token en `document.cookie`:
   ```
   vh_token=<jwt_token>; path=/; SameSite=Lax
   ```
2. **Cabecera HTTP:** Se interceptan de forma transparente las llamadas globales `window.fetch` y `XMLHttpRequest`, inyectando la cabecera:
   ```http
   X-Human-Token: <jwt_token>
   ```
3. **Formularios HTML:** El SDK busca formularios en el DOM e inyecta un campo oculto:
   ```html
   <input type="hidden" name="vh_token" value="<jwt_token>">
   ```
4. **Evento de Sistema:** Emite el evento personalizado `verificacion-humana:verified` para que cualquier script de la página pueda reaccionar:
   ```javascript
   window.addEventListener('verificacion-humana:verified', function(e) {
     console.log('Token recibido:', e.detail.token);
   });
   ```

---

## 5. Validación en el Servidor Institucional

El servidor de la aplicación puede validar el token de dos formas:
1. **Validación en Borde (Recomendado):** El proxy OpenResty valida la firma criptográfica asimétrica `Ed25519` con la clave pública activa antes de que la petición llegue a la aplicación.
2. **Validación en Backend con Consumo Único:** Realizar una llamada interna al núcleo backend:
   ```http
   POST /api/v1/token/validate
   Content-Type: application/json

   {
     "jwt_token": "<jwt_token>",
     "site_key": "vh_site_9f8e7d6c5b4a3210",
     "consume_jti": true
   }
   ```
   Con `"consume_jti": true`, el identificador de token queda invalidado de inmediato, evitando cualquier ataque de repetición (*replay attack*).
