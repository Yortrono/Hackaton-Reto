#!/usr/bin/env python3
"""
Simulador de Ataque DDoS L7 Distribuido (Multi-IP Botnet)
Servicio Autónomo de Verificación Humana y Mitigación de Bots
Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)

Lanza 300 peticiones concurrentes simulando múltiples IPs y bots
para observar en tiempo real la mitigación perimetral y el impacto
en la consola de observabilidad.
"""

import asyncio
from collections import Counter
import random
import time
import httpx

TARGET_URL = "https://localhost:8443/login"
HEALTH_URL = "https://localhost:8443/api/consulta"
NUM_REQUESTS = 300
CONCURRENCY_LIMIT = 40

# Generar 25 IPs simuladas para el ataque distribuido
IPS_BOTNET = [f"198.51.100.{i}" for i in range(1, 26)]


async def enviar_peticion_bot(client: httpx.AsyncClient, req_id: int) -> int:
    simulated_ip = random.choice(IPS_BOTNET)
    headers = {
        "User-Agent": f"Botnet-Worker-{req_id % 10}/1.0",
        "X-Forwarded-For": simulated_ip,
        "Content-Type": "application/json"
    }
    try:
        r = await client.post(
            TARGET_URL,
            headers=headers,
            json={"cedula": f"V-{req_id}", "password": "pass_bruteforce"},
            timeout=5.0
        )
        return r.status_code
    except Exception:
        return 0


async def enviar_peticion_ciudadano(client: httpx.AsyncClient, token: str) -> tuple[int, float]:
    t0 = time.perf_counter()
    headers = {
        "User-Agent": "NavegadorCiudadano-Legitimo/1.0",
        "X-Human-Token": token,
        "X-Forwarded-For": "10.10.1.45"  # IP legítima del ciudadano
    }
    try:
        r = await client.get(HEALTH_URL, headers=headers, timeout=5.0)
        t_ms = (time.perf_counter() - t0) * 1000.0
        return r.status_code, t_ms
    except Exception:
        return 0, 0.0


async def obtener_token_ciudadano(client: httpx.AsyncClient) -> str:
    """Realiza el ciclo legítimo de init y verify para obtener token Ed25519."""
    import hashlib
    r_init = await client.post("https://localhost:8443/api/v1/challenge/init", json={
        "site_key": "vh_site_9f8e7d6c5b4a3210",
        "target_route": "/login",
        "client_context": {
            "sdk_version": "1.0.0",
            "user_agent_hash": "legit-agent",
            "timezone_offset": 240,
            "screen_resolution": "1920x1080",
            "language": "es-VE"
        }
    })
    init_data = r_init.json()
    cid = init_data["challenge_id"]
    nonce = init_data["nonce"]
    diff = init_data["pow_difficulty"]

    counter = 0
    prefix = "0" * diff
    while True:
        hex_c = hex(counter)[2:]
        if hashlib.sha256((nonce + hex_c).encode()).hexdigest().startswith(prefix):
            solution = hex_c
            break
        counter += 1

    r_verify = await client.post("https://localhost:8443/api/v1/challenge/verify", json={
        "site_key": "vh_site_9f8e7d6c5b4a3210",
        "challenge_id": cid,
        "pow_solution": solution,
        "telemetry": {
            "challenge_id": cid,
            "telemetry_window_ms": 2000,
            "pointer_metrics": {"event_count": 50, "mean_velocity": 1.25, "std_acceleration": 0.4, "angular_entropy": 2.8, "straight_line_ratio": 0.12},
            "keyboard_metrics": {"key_count": 10, "mean_dwell_ms": 85.0, "std_flight_ms": 32.0},
            "environment_signals": {"webdriver_flag": False, "plugins_count": 5, "languages_consistent": True, "viewport_ratio_valid": True, "time_to_first_interaction_ms": 600}
        }
    })
    return r_verify.json().get("jwt_token", "")


async def main():
    print("=" * 72)
    print("   SIMULADOR DE ATAQUE DDoS L7 DISTRIBUIDO (MULTI-IP BOTNET)")
    print("=" * 72)
    print(f"[*] Objetivo:                    {TARGET_URL}")
    print(f"[*] Volumen de Ráfaga:           {NUM_REQUESTS} peticiones HTTP concurrentes")
    print(f"[*] IPs de Origen Simuladas:     {len(IPS_BOTNET)} nodos botnet distintos")
    print(f"[*] Concurrencia Simultánea:     {CONCURRENCY_LIMIT} workers paralelos")
    print("-" * 72)

    limits = httpx.Limits(max_keepalive_connections=CONCURRENCY_LIMIT, max_connections=CONCURRENCY_LIMIT)
    async with httpx.AsyncClient(verify=False, limits=limits) as client:
        print("[*] Obteniendo token Ed25519 firmado para ciudadano legítimo...")
        token_ciudadano = await obtener_token_ciudadano(client)
        status_base, t_base = await enviar_peticion_ciudadano(client, token_ciudadano)
        print(f"[+] Disponibilidad pre-ataque ciudadano: HTTP {status_base} ({t_base:.2f} ms)")

        print(f"\n[🔥] ¡DISPARANDO RÁFAGA DISTRIBUIDA DE {NUM_REQUESTS} PETICIONES!")
        t0 = time.perf_counter()

        sem = asyncio.Semaphore(CONCURRENCY_LIMIT)

        async def worker(i: int):
            async with sem:
                return await enviar_peticion_bot(client, i)

        tareas = [worker(i) for i in range(NUM_REQUESTS)]

        # Mientras el ataque ocurre, verificar disponibilidad ciudadana
        async def chequear_ciudadano():
            await asyncio.sleep(0.1)
            return await enviar_peticion_ciudadano(client, token_ciudadano)

        tarea_ciudadano = asyncio.create_task(chequear_ciudadano())

        respuestas = await asyncio.gather(*tareas)
        status_ciudadano, t_ciudadano = await tarea_ciudadano
        t_total = time.perf_counter() - t0

    conteo = Counter(respuestas)
    reqs_429 = conteo.get(429, 0)
    reqs_401 = conteo.get(401, 0)
    reqs_403 = conteo.get(403, 0)
    throughput = NUM_REQUESTS / t_total

    print("\n" + "=" * 72)
    print("            RESULTADOS DE LA MITIGACIÓN EN EL BORDE")
    print("=" * 72)
    print(f"  • Tiempo de Ráfaga:               {t_total:.2f} s")
    print(f"  • Rendimiento Evaluado:           {throughput:.1f} req/s")
    print(f"  • Bloqueadas por Rate-Limit (429): {reqs_429}/{NUM_REQUESTS}")
    print(f"  • Retadas por Falta de Token (401):{reqs_401}/{NUM_REQUESTS}")
    print(f"  • Bloqueadas por Lista Negra (403):{reqs_403}/{NUM_REQUESTS}")
    print(f"  • Ciudadano Legítimo Protegido:    HTTP {status_ciudadano} ({t_ciudadano:.2f} ms)")
    print("=" * 72)
    print("[✔] Prueba finalizada. Los eventos han sido reportados a la consola de observabilidad.")


if __name__ == "__main__":
    asyncio.run(main())
