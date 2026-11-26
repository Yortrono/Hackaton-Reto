"""
Aplicación Web Demo Institucional — Portal Ciudadano de Trámites
Módulo Soberano de Prueba para Mitigación de Bots y Verificación Humana
Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)
"""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="Portal Ciudadano de Trámites",
    description="Aplicación institucional protegida por el Servicio Autónomo de Verificación Humana",
    version="1.0.0",
)


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
            max-width: 460px;
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
        /* Contenedor oficial para el Widget del SDK de Dev 3 */
        #verificacion-humana-widget {
            margin: 1.25rem 0;
            min-height: 52px;
            padding: 0.75rem;
            border: 1px dashed #cbd5e1;
            border-radius: 6px;
            background-color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.85rem;
            color: #64748b;
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
                    <input type="text" id="cedula" name="cedula" placeholder="V-12345678" required autocomplete="off">
                </div>

                <div class="form-group">
                    <label for="password">Contraseña</label>
                    <input type="password" id="password" name="password" placeholder="••••••••" required>
                </div>

                <!-- Punto de Integración para el SDK de Dev 3 -->
                <div id="verificacion-humana-widget" data-site-key="vh_site_9f8e7d6c5b4a3210">
                    <span id="widget-placeholder-text">🛡️ Verificación Humana Activa (Protección Perimetral)</span>
                </div>

                <button type="submit" class="btn-submit" id="btnIngresar">Ingresar al Trámite</button>
            </form>

            <a href="/api/consulta" class="btn-consulta" id="btnConsultaLink">Probar Endpoint de Consulta (/api/consulta)</a>

            <div id="resultado"></div>
        </div>
    </main>

    <footer>
        República Bolivariana de Venezuela &bull; Servicio Autónomo de Verificación Humana y Mitigación de Bots &bull; Red Soberana Air-Gapped
    </footer>

    <!-- Placeholder preparado para el SDK de Dev 3 -->
    <script src="/sdk/sdk-verificacion.min.js" defer onerror="console.info('SDK en desarrollo local por Dev 3.')"></script>

    <script>
        const form = document.getElementById('loginForm');
        const resDiv = document.getElementById('resultado');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            resDiv.style.display = 'none';

            const payload = {
                cedula: document.getElementById('cedula').value,
                password: document.getElementById('password').value
            };

            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                resDiv.style.display = 'block';

                if (response.ok) {
                    resDiv.className = 'alert-success';
                    resDiv.textContent = 'Acceso concedido: ' + (data.mensaje || 'Autenticación exitosa.');
                } else {
                    resDiv.className = 'alert-error';
                    resDiv.textContent = 'Aviso: ' + (data.error?.message || data.detail || 'Error en validación.');
                }
            } catch (err) {
                resDiv.style.display = 'block';
                resDiv.className = 'alert-error';
                resDiv.textContent = 'Error de conexión con el servidor.';
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
