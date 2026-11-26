# Manual de Usuario y Operación — Consola Administrativa Soberana (Dev 3)

**Proyecto:** Servicio Autónomo de Verificación Humana y Mitigación de Bots  
**Hackathon Venezuela Innova 2026**

---

## 1. Visión General de la Consola

La **Consola Administrativa y de Observabilidad Web** (`consola-admin/`) es la interfaz de gobierno centralizada del sistema de mitigación de bots y verificación humana. Se ejecuta en el **puerto 3000** y ha sido construida bajo la premisa de **Cero Recursos Remotos**:
- Estilos locales puros sin llamadas a Google Fonts.
- Iconos vectoriales SVG embebidos de manera directa.
- Gráficos estadísticos trazados en memoria sobre elementos nativos HTML5 Canvas.
- Operación 100 % garantizada en entornos sin salida a internet (*air-gapped*).

---

## 2. Autenticación y Control de Acceso Basado en Roles (RBAC)

Para garantizar la integridad y soberanía en la toma de decisiones, la consola incorpora autenticación obligatoria de dos factores (**MFA/TOTP**) y tres perfiles de usuario:

### Matriz de Permisos por Rol:
| Módulo / Acción | `security_admin` | `operator` | `auditor` |
| :--- | :---: | :---: | :---: |
| **Módulo 1:** Gestión de Sitios y Rutas | Total | Total | Solo Lectura |
| **Módulo 2:** Umbrales IA y Mitigación | Total | Total | Solo Lectura |
| **Módulo 3:** Bóveda Cripto y Rotación de Claves | Total | Solo Lectura | Solo Lectura |
| **Módulo 4:** Observabilidad en Tiempo Real | Total | Total | Total (Lectura) |
| **Módulo 5:** Carga e Intercambio de Pesos IA | Total | Denegado | Solo Lectura |
| **Módulo 6:** Bitácora de Auditoría Inmutable | Total | Total | Total (Lectura) |

### Procedimiento de Ingreso:
1. Acceda en su navegador web a `http://localhost:3000` (o `http://<IP_SERVIDOR>:3000`).
2. Seleccione su usuario correspondiente (`admin`, `operador` o `auditor`).
3. Introduzca su contraseña local.
4. Introduzca el código temporal de 6 dígitos generado por su aplicación TOTP (Código predeterminado de prueba: `123456`).
5. Presione **"Autenticar con Segundo Factor"**.

---

## 3. Guía de los 6 Módulos Operativos

### Módulo 1 — Gestión de Sitios y Aplicaciones
- **Alta de Dominios:** Permite registrar nuevos dominios institucionales autorizados (ej. `tramites.gob.ve`, `citas.saime.gob.ve`).
- **Gestión de Credenciales:** Muestra de forma segura la `site_key` (clave pública consumida por el SDK en los navegadores) y la `secret_key` (clave privada para validación en el servidor de la aplicación).
- **Rutas Protegidas:** Configuración de prefijos de ruta (ej. `/login`, `/api/consulta`), métodos HTTP permitidos y límites específicos de peticiones por minuto (RPM).

### Módulo 2 — Motor de Reglas y Mitigación
- **Selector de Modo Perimetral:**
  - `challenge`: Flujo híbrido normal (verificación pasiva con escalado a reto espacial si se detecta riesgo).
  - `monitor`: Modo pasivo de registro y auditoría sin bloqueo activo de tráfico.
  - `block`: Modo defensivo reforzado ante sospecha de ciberataque activo.
- **Deslizadores de Umbrales de IA:**
  - `challenge_min` (Rango 0.05 a 0.95, default `0.35`): Puntuaciones superiores escalan al reto interactivo accesible.
  - `block_min` (Rango 0.50 a 0.99, default `0.75`): Puntuaciones superiores provocan el bloqueo inmediato del bot con HTTP 403 (`BOT_BLOCKED`).
- **Control de Listas de Acceso:** Gestión de listas blancas (IPs exentas de inspección) y listas negras (bloqueo automático) con soporte de formato CIDR.

### Módulo 3 — Bóveda Criptográfica Local
- **Claves Asimétricas Ed25519:** Estado del par de claves activas y su identificador (`kid`, ej. `key-2026-01`).
- **Visualizador PEM:** Muestra la clave pública activa en formato estándar para su distribución al proxy de borde OpenResty y validadores externos.
- **Rotación Criptográfica con un Clic:** El botón **"Rotar Clave Asimétrica Ahora"** genera un nuevo par de claves `Ed25519` en memoria, actualiza el `kid` vigente y registra criptográficamente la acción en la bitácora inmutable.

### Módulo 4 — Observabilidad en Tiempo Real
- **Métricas de Tráfico:** Contadores en tiempo real de peticiones totales, humanos verificados, retos resueltos y bots bloqueados.
- **Gráfico de Dona Nativo:** Muestra la distribución porcentual de tráfico legítimo vs. hostil.
- **Gráfico de Rendimiento IA:** Curva temporal de latencia de inferencia en milisegundos con indicador visual del límite estricto de **$50\text{ ms}$**.
- **Eventos de Seguridad Anonimizados:** Registro continuo de amenazas mitigadas donde las direcciones IP están estrictamente anonimizadas mediante `SHA-256(IP + sal_rotativa)` en cumplimiento con la privacidad por diseño.

### Módulo 5 — Gestión del Modelo de IA Local
- **Estado del Modelo Activo:** Versión en producción (`lgbm-conductual-v1.0.0`), precisión actual (98.4%) y latencia en RAM ($< 5\text{ ms}$).
- **Carga de Nuevos Pesos (.onnx):** Zona interactiva de arrastrar y soltar para subir nuevos modelos entrenados localmente. Al presionar **"Cargar e Intercambiar Pesos"**, el modelo se transfiere de forma segura y se recarga en caliente (*thread-safe*) sin reiniciar los contenedores.

### Módulo 6 — Auditoría Inmutable
- **Encadenamiento Criptográfico:** Cada acción administrativa (inicios de sesión, cambios de políticas, rotaciones de claves y recargas de modelos) se registra con su hash previo (`prev_hash`) y su hash de entrada:
  $$\text{entry\_hash} = \text{SHA-256}(\text{prev\_hash} + \text{id} + \text{timestamp} + \text{usuario} + \text{rol} + \text{acción} + \text{recurso})$$
- **Indicador de Integridad:** Un banner visual destacado confirma si la cadena es 100 % válida (`chain_integrity_valid: true`).
- **Botón "Recalcular Integridad":** Permite al auditor recomputar en el cliente todo el historial para comprobar matemáticamente la ausencia de alteraciones retrospectivas.
