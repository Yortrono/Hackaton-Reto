#!/usr/bin/env python3
"""
Simulador de Ataques Automatizados y Bots Headless
Servicio Autónomo de Verificación Humana y Mitigación de Bots
Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)

Demuestra:
1. Detección inmediata de bots automatizados con puntaje de riesgo R >= 0.75.
2. Identificación de perfiles anómalos (trayectorias rectas, robótica de teclado, webdriver).
3. Interceptación perimetral en borde-proxy (HTTP 401 / 403).
"""

import json
import subprocess
import time
import uuid
import httpx

EDGE_URL = "https://localhost:8443"
IA_URL = "http://localhost:8001"

PERFILES_BOT = [
    {
        "nombre": "Bot Headless Chrome (Selenium / Puppeteer)",
        "descripcion": "Webdriver activo, interacción instantánea < 50ms, 0 plugins instalados.",
        "telemetry": {
            "challenge_id": str(uuid.uuid4()),
            "telemetry_window_ms": 650.0,
            "pointer_metrics": {
                "event_count": 8,
                "mean_velocity": 4.85,
                "std_acceleration": 0.02,
                "angular_entropy": 0.42,
                "straight_line_ratio": 0.88
            },
            "keyboard_metrics": {
                "key_count": 12,
                "mean_dwell_ms": 22.0,
                "std_flight_ms": 2.1
            },
            "environment_signals": {
                "webdriver_flag": True,
                "plugins_count": 0,
                "languages_consistent": False,
                "viewport_ratio_valid": False,
                "time_to_first_interaction_ms": 38.0
            }
        }
    },
    {
        "nombre": "Bot de Relleno de Credenciales (Credential Stuffing Macro)",
        "descripcion": "Intervalos mecánicos ultra-constantes (std_flight < 3ms), velocidad uniforme.",
        "telemetry": {
            "challenge_id": str(uuid.uuid4()),
            "telemetry_window_ms": 1100.0,
            "pointer_metrics": {
                "event_count": 14,
                "mean_velocity": 3.20,
                "std_acceleration": 0.05,
                "angular_entropy": 0.65,
                "straight_line_ratio": 0.94
            },
            "keyboard_metrics": {
                "key_count": 16,
                "mean_dwell_ms": 28.0,
                "std_flight_ms": 1.4
            },
            "environment_signals": {
                "webdriver_flag": False,
                "plugins_count": 1,
                "languages_consistent": True,
                "viewport_ratio_valid": True,
                "time_to_first_interaction_ms": 75.0
            }
        }
    },
    {
        "nombre": "Script de Raspado / Ataque L7 (Linear Mouse Interpolation)",
        "descripcion": "Trayectoria matemática recta perfecta (straight_line_ratio > 0.95), entropía mínima.",
        "telemetry": {
            "challenge_id": str(uuid.uuid4()),
            "telemetry_window_ms": 820.0,
            "pointer_metrics": {
                "event_count": 22,
                "mean_velocity": 5.40,
                "std_acceleration": 0.01,
                "angular_entropy": 0.18,
                "straight_line_ratio": 0.98
            },
            "keyboard_metrics": {
                "key_count": 0,
                "mean_dwell_ms": 0.0,
                "std_flight_ms": 0.0
            },
            "environment_signals": {
                "webdriver_flag": False,
                "plugins_count": 0,
                "languages_consistent": True,
                "viewport_ratio_valid": False,
                "time_to_first_interaction_ms": 42.0
            }
        }
    }
]


def probar_inferencia_ia():
    print("=" * 70)
    print("  FASE 1: EVALUACIÓN DE VECTORES DE ATAQUE CONTRA MOTOR IA LOCAL")
    print("=" * 70)

    for p in PERFILES_BOT:
        print(f"\n[+] Evaluando: {p['nombre']}")
        print(f"    Detalle: {p['descripcion']}")

        payload = p["telemetry"]
        data = None

        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.post(f"{IA_URL}/internal/predict", json=payload)
                if r.status_code == 200:
                    data = r.json()
        except Exception:
            pass

        if data is None:
            # Fallback seguro con podman exec usando stdin
            cmd = [
                "podman", "exec", "-i", "ia-conductual", "python", "-c",
                "import sys, urllib.request; req = urllib.request.Request('http://localhost:8001/internal/predict', data=sys.stdin.read().encode(), headers={'Content-Type': 'application/json'}); print(urllib.request.urlopen(req).read().decode())"
            ]
            res = subprocess.run(cmd, input=json.dumps(payload), capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)

        risk = data.get("risk_score", 0.0)
        decision = data.get("decision", "unknown")
        dt_ms = data.get("inference_time_ms", 0.0)
        version = data.get("model_version", "unknown")

        print(f"    • Puntaje de Riesgo (Risk Score): {risk:.4f}  (Meta: >= 0.7500)")
        print(f"    • Decisión Emitida:              '{decision.upper()}'")
        print(f"    • Tiempo de Inferencia:          {dt_ms:.3f} ms")
        print(f"    • Versión Activa del Modelo:     {version}")

        assert risk >= 0.75, f"Fallo: El riesgo {risk} es menor que 0.75"
        assert decision == "bot", f"Fallo: La decisión '{decision}' no es 'bot'"
        print("    [✔] RESULTADO: BLOQUEO INMEDIATO EXITOSO")


def probar_interceptacion_borde():
    print("\n" + "=" * 70)
    print("  FASE 2: INTERCEPTACIÓN EN CAPA DE BORDE (OPENRESTY)")
    print("=" * 70)

    with httpx.Client(verify=False, timeout=5.0) as client:
        # Petición maliciosa a /login sin token
        print("\n[*] Enviando petición automatizada de bot a POST /login sin token...")
        r = client.post(
            f"{EDGE_URL}/login",
            headers={"User-Agent": "Bot-Automated-Agent/1.0", "Content-Type": "application/json"},
            json={"cedula": "V-99999999", "password": "password_bruteforce"}
        )
        print(f"    • Código HTTP retornado: {r.status_code} (Esperado: 401)")
        try:
            err = r.json().get("error", {})
            print(f"    • Código de Error:       {err.get('code')}")
            print(f"    • Mensaje Soberano:      {err.get('message')}")
            print(f"    • Trace ID:              {err.get('trace_id')}")
        except Exception:
            print(f"    • Respuesta: {r.text[:120]}")

        assert r.status_code == 401, f"Fallo: Esperado 401, obtenido {r.status_code}"

        # Petición sin User-Agent (DDoS L7 Scraper)
        print("\n[*] Enviando petición DDoS L7 sin cabecera User-Agent...")
        r2 = client.get(f"{EDGE_URL}/", headers={"User-Agent": ""})
        print(f"    • Código HTTP retornado: {r2.status_code} (Esperado: 403)")
        try:
            err2 = r2.json().get("error", {})
            print(f"    • Código de Error:       {err2.get('code')}")
            print(f"    • Mensaje:               {err2.get('message')}")
        except Exception:
            print(f"    • Respuesta: {r2.text[:120]}")

        assert r2.status_code == 403, f"Fallo: Esperado 403, obtenido {r2.status_code}"

    print("\n[🎉] ¡Arsenal de Pruebas de Bot ejecutado con 100% de detecciones!")


if __name__ == "__main__":
    probar_inferencia_ia()
    probar_interceptacion_borde()
