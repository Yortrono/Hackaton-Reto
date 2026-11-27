"""
Aplicación Web Demo Institucional — Portal Ciudadano de Trámites
Módulo Soberano de Prueba para Mitigación de Bots y Verificación Humana
Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)
"""

import os
import time
import json
import uuid
import base64
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel

app = FastAPI(
    title="Portal Ciudadano de Trámites",
    description="Aplicación institucional protegida por el Servicio Autónomo de Verificación Humana",
    version="1.0.0",
)

IA_INFERENCE_URL = os.getenv("IA_INFERENCE_URL", "http://ia-conductual:8001/internal/predict")
SDK_FILE_PATH = os.path.join(os.path.dirname(__file__), "static", "sdk", "sdk-verificacion.min.js")


BACKEND_URL = os.getenv("BACKEND_URL", "http://backend-nucleo:8000")


class LoginPayload(BaseModel):
    cedula: str
    password: str


HTML_PORTAL = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portal Ciudadano de Trámites — República Bolivariana de Venezuela</title>
    <style>
        :root {
            --primary: #002b49;
            --secondary: #cf102d;
            --accent: #f8c300;
            --bg: #f4f6f9;
            --card-bg: #ffffff;
            --text: #1a202c;
            --text-muted: #718096;
            --border: #e2e8f0;
            --success: #38a169;
            --danger: #e53e3e;
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        body {
            background-color: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            background-color: var(--primary);
            color: white;
            padding: 1rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header-title {
            font-size: 1.25rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .badge-soberania {
            background-color: #0b4f6c;
            color: #d1fae5;
            padding: 0.25rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        main {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 2rem 1rem;
        }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 2rem;
            max-width: 480px;
            width: 100%;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }
        .card h2 {
            font-size: 1.35rem;
            color: var(--primary);
            margin-bottom: 0.5rem;
        }
        .card p.subtitle {
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-bottom: 1.5rem;
        }
        .form-group {
            margin-bottom: 1.25rem;
        }
        label {
            display: block;
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: 0.35rem;
            color: #2d3748;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 0.65rem 0.85rem;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }
        input[type="text"]:focus, input[type="password"]:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(0, 43, 73, 0.15);
        }
        #verificacion-humana-widget {
            margin: 1.25rem 0;
            min-height: 48px;
            padding: 0.65rem 1rem;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            background-color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.85rem;
            color: #475569;
        }
        .vh-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 500;
        }
        .vh-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #eab308;
            display: inline-block;
        }
        .vh-dot.ready {
            background-color: #22c55e;
            box-shadow: 0 0 6px rgba(34, 197, 94, 0.6);
        }
        .btn-submit {
            width: 100%;
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 0.75rem 1rem;
            font-size: 1rem;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .btn-submit:hover {
            background-color: #001f35;
        }
        .btn-consulta {
            display: inline-block;
            margin-top: 1rem;
            width: 100%;
            text-align: center;
            background-color: #edf2f7;
            color: #4a5568;
            text-decoration: none;
            padding: 0.6rem;
            border-radius: 6px;
            font-size: 0.875rem;
            font-weight: 500;
            border: 1px solid var(--border);
            cursor: pointer;
        }
        .btn-consulta:hover {
            background-color: #e2e8f0;
        }
        #resultado {
            margin-top: 1rem;
            padding: 0.75rem;
            border-radius: 6px;
            font-size: 0.875rem;
            display: none;
            word-break: break-all;
        }
        .alert-success {
            background-color: #def7ec;
            color: #03543f;
            border: 1px solid #84e1bc;
        }
        .alert-error {
            background-color: #fde8e8;
            color: #9b1c1c;
            border: 1px solid #f8b4b4;
        }
        footer {
            text-align: center;
            padding: 1rem;
            font-size: 0.75rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border);
        }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <span>Portal Ciudadano de Trámites</span>
        </div>
        <div class="badge-soberania">Infraestructura Soberana TLS 1.3</div>
    </header>

    <main>
        <div class="card">
            <h2>Acceso al Sistema</h2>
            <p class="subtitle">Ingrese sus credenciales de identidad ciudadana.</p>

            <form id="loginForm">
                <div class="form-group">
                    <label for="cedula">Cédula de Identidad</label>
                    <input type="text" id="cedula" name="cedula" placeholder="V-12345678" value="V-28492019" required autocomplete="off">
                </div>

                <div class="form-group">
                    <label for="password">Contraseña</label>
                    <input type="password" id="password" name="password" placeholder="••••••••" value="demoPass2026*" required>
                </div>

                <!-- Contenedor Oficial para el Widget del SDK de Dev 3 -->
                <div id="verificacion-humana-widget">
                    <span class="vh-badge" id="vh-badge-status">
                        <span class="vh-dot" id="vh-dot"></span>
                        <span id="vh-status-text">Verificando entorno seguro...</span>
                    </span>
                    <span style="font-size: 11px; color: #94a3b8; font-family: monospace;">FOSS ONNX</span>
                </div>

                <button type="submit" class="btn-submit" id="btnIngresar">Ingresar al Trámite</button>
            </form>

            <button type="button" class="btn-consulta" id="btnConsultaLink">Probar Endpoint Protegido (/api/consulta)</button>

            <div id="resultado"></div>
        </div>
    </main>

    <footer>
        República Bolivariana de Venezuela &bull; Servicio Autónomo de Verificación Humana y Mitigación de Bots &bull; Red Soberana Air-Gapped
    </footer>

    <!-- SDK de Verificación Humana de Dev 3 con auto-inicio -->
    <script src="/sdk/sdk-verificacion.min.js" data-site-key="vh_site_9f8e7d6c5b4a3210"></script>

    <script>
        const form = document.getElementById('loginForm');
        const resDiv = document.getElementById('resultado');
        const btnConsulta = document.getElementById('btnConsultaLink');
        const badgeText = document.getElementById('vh-status-text');
        const badgeDot = document.getElementById('vh-dot');

        let activeToken = null;

        // Inicializar SDK explícitamente si aún no se instanció
        if (window.VerificacionHumana && typeof window.VerificacionHumana.init === 'function') {
            window.vhInstance = window.VerificacionHumana.init({
                siteKey: 'vh_site_9f8e7d6c5b4a3210',
                containerId: 'verificacion-humana-widget',
                autoInit: true,
                passiveDelayMs: 600,
                onVerified: function(data) {
                    activeToken = data.jwt_token;
                    if (badgeText) badgeText.textContent = 'Verificación Humana Confirmada';
                    if (badgeDot) {
                        badgeDot.className = 'vh-dot ready';
                    }
                }
            });
        }

        // Escuchar evento personalizado del SDK
        window.addEventListener('verificacion-humana:verified', function(ev) {
            if (ev.detail && ev.detail.token) {
                activeToken = ev.detail.token;
                if (badgeText) badgeText.textContent = 'Verificación Humana Confirmada';
                if (badgeDot) badgeDot.className = 'vh-dot ready';
            }
        });

        // Asegurar que si hay cookie vh_token se use de inmediato
        function getCookie(name) {
            const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
            return v ? decodeURIComponent(v[2]) : null;
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            resDiv.style.display = 'none';

            if (window.vhInstance && window.vhInstance.isBlocked) {
                resDiv.style.display = 'block';
                resDiv.className = 'alert-error';
                resDiv.innerHTML = '<strong>✕ Acceso Denegado:</strong> El sistema de seguridad ha bloqueado la sesión por comportamiento automatizado.';
                return;
            }

            const token = activeToken || getCookie('vh_token');
            if (!token) {
                resDiv.style.display = 'block';
                resDiv.className = 'alert-error';
                resDiv.innerHTML = '<strong>✕ Verificación Requerida:</strong> Verificación humana en proceso. Por favor espere un instante o complete el reto.';
                return;
            }

            const headers = { 'Content-Type': 'application/json', 'X-Human-Token': token };

            const payload = {
                cedula: document.getElementById('cedula').value,
                password: document.getElementById('password').value
            };

            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                resDiv.style.display = 'block';

                if (response.ok) {
                    resDiv.className = 'alert-success';
                    resDiv.innerHTML = '<strong>✓ Acceso Concedido:</strong> ' + (data.mensaje || 'Autenticación exitosa.') + '<br><small style="color: #047857;">Token validado en Borde por OpenResty TLS 1.3</small>';
                } else {
                    resDiv.className = 'alert-error';
                    resDiv.innerHTML = '<strong>✕ Acceso Denegado:</strong> ' + (data.error?.message || data.detail || 'Error en validación.') + (data.error?.code ? ' (Código: ' + data.error.code + ')' : '');
                }
            } catch (err) {
                resDiv.style.display = 'block';
                resDiv.className = 'alert-error';
                resDiv.textContent = 'Error de conexión con el servidor: ' + err.message;
            }
        });

        btnConsulta.addEventListener('click', async () => {
            resDiv.style.display = 'none';

            if (window.vhInstance && window.vhInstance.isBlocked) {
                resDiv.style.display = 'block';
                resDiv.className = 'alert-error';
                resDiv.innerHTML = '<strong>✕ Acceso Denegado:</strong> El sistema de seguridad ha bloqueado la sesión.';
                return;
            }

            const token = activeToken || getCookie('vh_token');
            if (!token) {
                resDiv.style.display = 'block';
                resDiv.className = 'alert-error';
                resDiv.innerHTML = '<strong>✕ Verificación Requerida:</strong> No se ha completado la verificación humana.';
                return;
            }

            const headers = { 'X-Human-Token': token };

            try {
                const response = await fetch('/api/consulta', { headers: headers });
                const data = await response.json();
                resDiv.style.display = 'block';
                if (response.ok) {
                    resDiv.className = 'alert-success';
                    resDiv.innerHTML = '<strong>✓ Consulta Exitosa:</strong> ' + data.mensaje;
                } else {
                    resDiv.className = 'alert-error';
                    resDiv.innerHTML = '<strong>✕ Verificación Requerida:</strong> ' + (data.error?.message || 'Acceso restringido por Borde.');
                }
            } catch (err) {
                resDiv.style.display = 'block';
                resDiv.className = 'alert-error';
                resDiv.textContent = 'Error al consultar endpoint: ' + err.message;
            }
        });
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def inicio() -> HTMLResponse:
    """Retorna la interfaz web institucional del Portal Ciudadano."""
    return HTMLResponse(content=HTML_PORTAL, status_code=200)


@app.get("/sdk/sdk-verificacion.min.js")
async def servir_sdk():
    """Sirve el archivo minificado del SDK de verificación humana."""
    if os.path.exists(SDK_FILE_PATH):
        return FileResponse(SDK_FILE_PATH, media_type="application/javascript")
    return JSONResponse(status_code=404, content={"error": "SDK file not found"})


# =====================================================================
# Endpoints de Desafío y Verificación (Backend Bridge hacia IA)
# =====================================================================

@app.post("/api/v1/challenge/init")
async def challenge_init(request: Request) -> JSONResponse:
    """Reenvía la inicialización del desafío al Backend Núcleo oficial."""
    try:
        body = await request.body()
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/v1/challenge/init",
                content=body,
                headers={"Content-Type": "application/json"}
            )
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": f"Fallo al contactar Backend Núcleo: {str(e)}"})


@app.post("/api/v1/challenge/verify")
async def challenge_verify(request: Request) -> JSONResponse:
    """
    Reenvía la verificación de telemetría y PoW al Backend Núcleo oficial (Ed25519 + IA en RAM).
    """
    try:
        body = await request.body()
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/v1/challenge/verify",
                content=body,
                headers={"Content-Type": "application/json"}
            )
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        return JSONResponse(status_code=502, content={"error": f"Fallo al verificar con Backend Núcleo: {str(e)}"})


@app.post("/login")
async def login(request: Request) -> JSONResponse:
    """
    Ruta protegida para inicio de sesión en trámites.
    Procesa credenciales y valida estado de verificación.
    """
    try:
        data = await request.json()
    except Exception:
        data = {}

    cedula = data.get("cedula", "")
    if not cedula:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "mensaje": "La cédula de identidad es obligatoria.",
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "mensaje": f"Sesión autorizada para cédula {cedula}.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/api/consulta")
async def consulta_ciudadana() -> Dict[str, Any]:
    """
    Ruta protegida para consulta de trámites ciudadanos.
    """
    return {
        "status": "ok",
        "servicio": "Portal Ciudadano de Trámites",
        "version": "1.0.0",
        "infraestructura": "soberana-onpremise",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mensaje": "Consulta ciudadana procesada correctamente sobre canal seguro TLS 1.3.",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Endpoint de salud del microservicio demo."""
    return {"status": "healthy", "service": "demo-institucional"}
