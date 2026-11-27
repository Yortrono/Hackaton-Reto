#!/usr/bin/env python3
"""
Generador de Tráfico Continuo para Demostración en Vivo
Hackathon Venezuela Innova 2026 — Servicio Autónomo de Verificación Humana y Mitigación de Bots

Genera tráfico periódico (humanos verificados + ráfagas esporádicas de bots)
para mantener activo el flujo en la Consola Administrativa (http://localhost:3000).
"""

import time
import random
import hashlib
import requests
import urllib3
import concurrent.futures

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PORTAL_URL = "https://localhost:8443"

def resolver_pow(nonce: str, difficulty: int) -> str:
    target_prefix = "0" * difficulty
    counter = 0
    while True:
        sol_hex = hex(counter)[2:]
        h = hashlib.sha256(f"{nonce}{sol_hex}".encode("utf-8")).hexdigest()
        if h.startswith(target_prefix):
            return sol_hex
        counter += 1

def enviar_ciudadano(i):
    s = requests.Session()
    s.verify = False
    try:
        r_init = s.post(f"{PORTAL_URL}/api/v1/challenge/init", json={
            "site_key": "vh_site_9f8e7d6c5b4a3210",
            "target_route": "/login"
        }, timeout=4.0)
        if r_init.status_code != 200:
            return
        data = r_init.json()
        cid = data["challenge_id"]
        pow_sol = resolver_pow(data["nonce"], data.get("pow_difficulty", 3))

        telemetry = {
            "challenge_id": cid,
            "telemetry_window_ms": random.randint(1800, 3000),
            "pointer_metrics": {
                "event_count": random.randint(45, 70),
                "mean_velocity": round(random.uniform(0.9, 1.5), 2),
                "std_acceleration": round(random.uniform(0.25, 0.40), 2),
                "angular_entropy": round(random.uniform(2.7, 3.0), 2),
                "straight_line_ratio": round(random.uniform(0.08, 0.15), 2)
            },
            "keyboard_metrics": {
                "key_count": random.randint(8, 14),
                "mean_dwell_ms": round(random.uniform(75.0, 95.0), 1),
                "std_flight_ms": round(random.uniform(28.0, 36.0), 1)
            },
            "environment_signals": {
                "webdriver_flag": False,
                "plugins_count": 5,
                "languages_consistent": True,
                "viewport_ratio_valid": True,
                "time_to_first_interaction_ms": random.randint(500, 800)
            }
        }

        r_ver = s.post(f"{PORTAL_URL}/api/v1/challenge/verify", json={
            "site_key": "vh_site_9f8e7d6c5b4a3210",
            "challenge_id": cid,
            "pow_solution": pow_sol,
            "telemetry": telemetry
        }, timeout=4.0)

        token = r_ver.json().get("jwt_token")
        if token:
            headers = {
                "X-Human-Token": token,
                "X-Forwarded-For": f"10.50.{random.randint(1, 20)}.{random.randint(1, 250)}",
                "User-Agent": f"CiudadanoBrowser/2026 (Sesion-{i})"
            }
            s.post(f"{PORTAL_URL}/login", json={"cedula": f"V-{25000000 + i}", "password": "Secret2026*"}, headers=headers, timeout=4.0)
            s.get(f"{PORTAL_URL}/api/consulta", headers=headers, timeout=4.0)
    except Exception:
        pass

def enviar_rafaga_bots(cantidad=15):
    def bot_hit(b_id):
        s = requests.Session()
        s.verify = False
        headers = {
            "X-Forwarded-For": f"198.51.100.{random.randint(1, 254)}",
            "User-Agent": f"BotNetProbe/1.0 (Node-{b_id})"
        }
        try:
            s.post(f"{PORTAL_URL}/login", json={"cedula": "BOT", "password": "brute"}, headers=headers, timeout=2.0)
        except Exception:
            pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        list(ex.map(bot_hit, range(cantidad)))

def main():
    print("[*] Generador continuo de tráfico activo. Presiona Ctrl+C para detener.")
    ciclo = 0
    while ciclo < 30: # 30 ciclos (~1 minuto)
        ciclo += 1
        # 1 o 2 ciudadanos por ciclo
        for c in range(random.randint(1, 2)):
            enviar_ciudadano(ciclo * 10 + c)

        # Cada 4 ciclos, enviar ráfaga de bots
        if ciclo % 4 == 0:
            enviar_rafaga_bots(random.randint(12, 20))
            print(f"[{time.strftime('%H:%M:%S')}] Ciclo #{ciclo}: Ráfaga de bots disparada")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Ciclo #{ciclo}: Interacción humana procesada")

        time.sleep(1.8)

if __name__ == "__main__":
    main()
