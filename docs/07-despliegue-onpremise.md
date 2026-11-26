# Guía de Despliegue On-Premise y Air-Gapped

**Servicio Autónomo de Verificación Humana y Mitigación de Bots**  
**Hackathon Venezuela Innova 2026 — Dev 2 (IA, Borde e Infraestructura)**

---

## 1. Requisitos de Infraestructura Local

Este procedimiento permite desplegar la plataforma en servidores gubernamentales o centros de datos nacionales sin ningún tipo de conexión a internet (*air-gapped*).

### Especificaciones Mínimas:
- **CPU:** 2 núcleos x86_64 o ARM64.
- **Memoria RAM:** 2 GB libres (toda la plataforma consume $< 400\text{ MB}$ en ejecución).
- **Almacenamiento:** 5 GB de espacio en disco.
- **Sistema Operativo:** Canaima GNU/Linux, Debian 12+, Ubuntu 22.04+ o Alpine Linux.
- **Contenedores:** Docker 24+ con Docker Compose v2, o Podman 4.5+ con `podman-compose`.

---

## 2. Preparación Previa al Entorno Air-Gapped (Paso 0)

En un equipo con conexión o repositorio de artefactos soberano:

```bash
# 1. Clonar el repositorio del proyecto
git clone <url-repositorio-nacional> /opt/verificacion-humana
cd /opt/verificacion-humana

# 2. Si se exportan imágenes en formato tar para servidores aislados:
podman save -o imagenes_soberanas.tar \
    borde-proxy:latest \
    ia-conductual:latest \
    demo-institucional:latest
```

---

## 3. Despliegue Paso a Paso en el Servidor Aislado

### Paso 1: Configurar Variables de Entorno
Copiar la plantilla de configuración soberana:
```bash
cp .env.example .env
```
Verificar los puertos en `.env`:
- En servidores con permisos de puertos privilegiados (modo root/producción):
  `PROXY_HTTP_PORT=80` y `PROXY_HTTPS_PORT=443`.
- En entornos locales o sin privilegios rootless:
  `PROXY_HTTP_PORT=8088` y `PROXY_HTTPS_PORT=8443`.

### Paso 2: Generar Certificados Criptográficos TLS 1.3
Ejecutar el generador local de la Autoridad Certificadora Soberana:
```bash
bash borde-proxy/certs/generar_certs.sh
```
Esto creará de forma autónoma:
- `ca.key` y `ca.crt` (CA Raíz Soberana válida por 10 años).
- `server.key` y `server.crt` con nombres alternativos (`localhost`, `portal.gob.local`, `127.0.0.1`).

### Paso 3: Levantar la Infraestructura Soberana
Levantar los contenedores del servicio:
```bash
docker compose up -d --build
```
Los servicios quedarán distribuidos en las redes aisladas:
- `borde-proxy`: Puertos 80/443 expuestos.
- `demo-institucional`: Puerto interno 8080 (red aislada).
- `ia-conductual`: Puerto interno 8001 (red aislada).
- `backend-nucleo`: Puerto interno 8000 (red aislada).
- `consola-admin`: Puerto interno 3000 (red aislada).

---

## 4. Verificación y Auditoría Post-Despliegue

Ejecutar la suite automatizada de validación air-gapped:
```bash
bash scripts-ataque/verificar_airgapped.sh
```

El script audita:
1. Que la red `soberana_interna` tenga el atributo `internal: true`.
2. Que los contenedores internos no puedan emitir tráfico saliente hacia internet.
3. Que la latencia promedio del endpoint de IA sea $< 50\text{ ms}$.
4. Genera el inventario de dependencias para el SBOM en `docs/sbom_ia_borde.json`.

---

## 5. Simulación de Pruebas de Estrés y Demostración

Para demostrar la mitigación perimetral ante el jurado evaluador:

```bash
# 1. Probar detección y clasificación de bots automatizados:
python scripts-ataque/simular_bot.py

# 2. Probar mitigación de ataque DDoS L7 (300 peticiones concurrentes):
python scripts-ataque/simular_ddos_l7.py
```

---

## 6. Procedimiento de Recarga de Pesos de IA en Caliente (Hot-Reload)

Cuando un nuevo modelo `.onnx` es aprobado por la administración de seguridad:
```bash
curl -X POST http://ia-conductual:8001/internal/model/reload \
  -F "version=lgbm-v2.0.0" \
  -F "file=@nuevos_pesos.onnx"
```
El motor reemplaza los pesos atómicamente en memoria RAM sin interrumpir peticiones en curso ni requerir reinicio del contenedor.
