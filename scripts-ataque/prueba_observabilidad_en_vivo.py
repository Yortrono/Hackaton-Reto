#!/usr/bin/env python3
"""
Demostración de Observabilidad en Tiempo Real (Dev 2 / Scripts de Verificación)
Hackathon Venezuela Innova 2026 — Servicio Autónomo de Verificación Humana y Mitigación de Bots

Este script ejecuta un escenario dinámico que activa de forma visible y medible
todos los indicadores y curvas de la Consola Administrativa (http://localhost:3000):
  1. Fase 1: Ráfaga de Bots Automatizados (Pico Rojo en Gráfica y Eventos de Seguridad)
  2. Fase 2: Flujo de Ciudadanos Humanos Verificados (Subida de Curva Verde y KPIs)
  3. Fase 3: Concurrencia Mixta (Mitigación de Bots en Borde sin Afectar al Humano)
"""

import sys
import time
import json
import hashlib
import random
import concurrent.futures
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PORTAL_URL = "https://localhost:8443"
CONSOLE_URL = "http://localhost:3000"

def log(msg: str):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

def resolver_pow(nonce: str, difficulty: int) -> str:
    target_prefix = "0" * difficulty
    counter = 0
    while True:
        sol_hex = hex(counter)[2:]
        h = hashlib.sha256(f"{nonce}{sol_hex}".encode("utf-8")).hexdigest()
        if h.startswith(target_prefix):
            return sol_hex
        counter += 1

def simular_humano(ciudadano_id: int):
    """Ejecuta el ciclo completo de verificación humana legítima."""
    s = requests.Session()
    s.verify = False

    # 1. Challenge Init
    try:
        r_init = s.post(f"{PORTAL_URL}/api/v1/challenge/init", json={
            "site_key": "vh_site_9f8e7d6c5b4a3210",
            "target_route": "/login"
        }, timeout=3.0)
        if r_init.status_code != 200:
            return False, f"Init HTTP {r_init.status_code}"
        init_data = r_init.json()
        cid = init_data["challenge_id"]
        nonce = init_data["nonce"]
        diff = init_data.get("pow_difficulty", 3)

        # 2. Resolver PoW dinámico
        pow_sol = resolver_pow(nonce, diff)

        # 3. Telemetría humana con entropía y cadencia natural
        telemetry = {
            "challenge_id": cid,
            "telemetry_window_ms": random.randint(1800, 3200),
            "pointer_metrics": {
                "event_count": random.randint(45, 75),
                "mean_velocity": round(random.uniform(0.9, 1.6), 2),
                "std_acceleration": round(random.uniform(0.25, 0.45), 2),
                "angular_entropy": round(random.uniform(2.6, 3.1), 2),
                "straight_line_ratio": round(random.uniform(0.06, 0.16), 2)
            },
            "keyboard_metrics": {
                "key_count": random.randint(10, 16),
                "mean_dwell_ms": round(random.uniform(75.0, 98.0), 1),
                "std_flight_ms": round(random.uniform(26.0, 38.0), 1)
            },
            "environment_signals": {
                "webdriver_flag": False,
                "plugins_count": random.randint(4, 7),
                "languages_consistent": True,
                "viewport_ratio_valid": True,
                "time_to_first_interaction_ms": random.randint(480, 850)
            }
        }

        # 4. Verify
        r_ver = s.post(f"{PORTAL_URL}/api/v1/challenge/verify", json={
            "site_key": "vh_site_9f8e7d6c5b4a3210",
            "challenge_id": cid,
            "pow_solution": pow_sol,
            "telemetry": telemetry
        }, timeout=3.0)

        if r_ver.status_code != 200:
            return False, f"Verify HTTP {r_ver.status_code}"

        ver_data = r_ver.json()
        token = ver_data.get("jwt_token")
        if not token:
            return False, "Token no emitido"

        # 5. Acceder a ruta protegida con token
        headers = {
            "X-Human-Token": token,
            "X-Forwarded-For": f"10.20.{ciudadano_id // 200}.{(ciudadano_id % 200) + 1}",
            "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) CiudadanoVzla/{ciudadano_id}"
        }
        r_login = s.post(f"{PORTAL_URL}/login", json={
            "cedula": f"V-{20000000 + ciudadano_id}",
            "password": "PasswordSoberano2026*"
        }, headers=headers, timeout=3.0)

        r_consulta = s.get(f"{PORTAL_URL}/api/consulta", headers=headers, timeout=3.0)

        return (r_login.status_code == 200 and r_consulta.status_code == 200), f"Acceso Concedido Ciudadano #{ciudadano_id}"

    except Exception as e:
        return False, str(e)

def simular_peticion_bot(bot_id: int):
    """Petición maliciosa o no autenticada de botnet que impacta el borde."""
    s = requests.Session()
    s.verify = False
    spoofed_ip = f"198.51.100.{random.randint(1, 250)}"
    headers = {
        "X-Forwarded-For": spoofed_ip,
        "User-Agent": f"BotnetWorker/2.0 (Node-{bot_id})"
    }
    try:
        r = s.post(f"{PORTAL_URL}/login", json={"cedula": "BOT_ATTACK", "password": "brute"}, headers=headers, timeout=2.0)
        return r.status_code
    except Exception:
        return 0

def obtener_metricas_consola():
    try:
        r = requests.get(f"{CONSOLE_URL}/api/v1/admin/observability/summary", timeout=2.0)
        if r.status_code == 200:
            data = r.json()
            stats = data.get("traffic_stats", {})
            return {
                "total": stats.get("total_requests", 0),
                "humanos": stats.get("verified_humans", 0),
                "pct_humano": stats.get("human_percentage", 0),
                "bots": stats.get("bots_blocked", 0) + stats.get("ddos_rate_limited", 0)
            }
    except Exception:
        pass
    return None

def main():
    print("=" * 72)
    print("DEMOSTRACIÓN DE OBSERVABILIDAD EN TIEMPO REAL")
    print("Servicio Autónomo de Verificación Humana y Mitigación de Bots")
    print("=" * 72)
    print(f"[*] Consola Administrativa: {CONSOLE_URL}")
    print(f"[*] Portal Protegido:      {PORTAL_URL}")
    print("[*] Abre http://localhost:3000 en tu navegador para ver los gráficos en vivo.\n")

    m_ini = obtener_metricas_consola()
    if m_ini:
        log(f"Métricas Iniciales -> Total: {m_ini['total']} | Humanos: {m_ini['humanos']} ({m_ini['pct_humano']}%) | Bots: {m_ini['bots']}")

    # -------------------------------------------------------------------------
    # FASE 1: RÁFAGA DE BOTS AUTOMATIZADOS (Activa la Curva Roja)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 72)
    log(">>> INICIANDO FASE 1: Ráfaga de Bots Automatizados (DDoS L7 / Fuerza Bruta)")
    log(">>> Observa en la consola administrativa: La CURVA ROJA se elevará inmediatamente.")
    print("-" * 72)

    num_bots = 80
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(simular_peticion_bot, i) for i in range(num_bots)]
        statuses = [f.result() for f in concurrent.futures.as_completed(futures)]

    bloqueados_401 = statuses.count(401)
    rate_limited_429 = statuses.count(429)
    log(f"Fase 1 completada: {num_bots} peticiones disparadas.")
    log(f"Resultados en Borde: {bloqueados_401} bloqueadas por falta de token (401), {rate_limited_429} mitigadas por Rate Limit (429).")

    time.sleep(3)
    m1 = obtener_metricas_consola()
    if m1:
        log(f"Consola tras Fase 1 -> Total: {m1['total']} | Bots Mitigados: {m1['bots']} | % Humano: {m1['pct_humano']}%")

    # -------------------------------------------------------------------------
    # FASE 2: FLUJO DE CIUDADANOS HUMANOS (Activa la Curva Verde)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 72)
    log(">>> INICIANDO FASE 2: Flujo Legítimo de Ciudadanos Humanos")
    log(">>> Observa en la consola administrativa: La CURVA VERDE subirá marcando tráfico legítimo.")
    print("-" * 72)

    num_humanos = 12
    humanos_exitosos = 0
    for i in range(num_humanos):
        ok, detalle = simular_humano(i + 1)
        if ok:
            humanos_exitosos += 1
            print(f"  [✓] Ciudadano #{i+1:02d}: Verificación conductual aprobada -> Token Ed25519 -> Acceso 200 OK")
        else:
            print(f"  [!] Ciudadano #{i+1:02d}: {detalle}")
        time.sleep(0.4)

    time.sleep(2)
    m2 = obtener_metricas_consola()
    if m2:
        log(f"Consola tras Fase 2 -> Total: {m2['total']} | Humanos Verificados: {m2['humanos']} | % Humano: {m2['pct_humano']}%")

    # -------------------------------------------------------------------------
    # FASE 3: TRÁFICO MIXTO SIMULTÁNEO (Bots mitigados + Humanos atendidos)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 72)
    log(">>> INICIANDO FASE 3: Tráfico Concurrente Mixto (Ataque activo vs. Humanos navegando)")
    log(">>> Ambas curvas se moverán simultáneamente reflejando la mitigación perimetral en vivo.")
    print("-" * 72)

    def worker_mixto(id_w):
        if id_w % 3 == 0:
            return simular_humano(100 + id_w)
        else:
            return False, f"Bot Status: {simular_peticion_bot(500 + id_w)}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futs = [executor.submit(worker_mixto, w) for w in range(30)]
        results = [f.result() for f in concurrent.futures.as_completed(futs)]

    time.sleep(3)
    m3 = obtener_metricas_consola()
    if m3:
        print("\n" + "=" * 72)
        log("RESUMEN FINAL DE OBSERVABILIDAD EN VIVO:")
        log(f"  • Peticiones Totales Procesadas: {m3['total']}")
        log(f"  • Ciudadanos Humanos Atendidos:  {m3['humanos']}")
        log(f"  • Intentos de Bots Bloqueados:   {m3['bots']}")
        log(f"  • Porcentaje de Tráfico Seguro:  {m3['pct_humano']}%")
        print("=" * 72)

if __name__ == "__main__":
    main()
