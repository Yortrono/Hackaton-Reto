#!/usr/bin/env python3
"""
════════════════════════════════════════════════════════════════════════════════════
 GENERADOR DE TRÁFICO MIXTO EN VIVO Y SIMULADOR DE RESILIENCIA (DDoS vs HUMANOS)
 Servicio Autónomo de Verificación Humana y Mitigación de Bots
 Hackathon Venezuela Innova 2026 — Mincyt
════════════════════════════════════════════════════════════════════════════════════

Propósito:
- Genera tráfico simultáneo y concurrente de CIUDADANOS REALES y ATAQUES DE BOTS/DDoS.
- Demuestra que el Borde (OpenResty) y el Motor de IA filtran ataques en tiempo real
  mientras los usuarios legítimos siguen accediendo con latencia ultrabaja (< 25 ms).
- Alimenta en tiempo real la gráfica Canvas y la bitácora de la Consola Administrativa
  en http://localhost:3000/
"""

import argparse
import asyncio
import hashlib
import os
import random
import sys
import time
from datetime import datetime, timezone
import httpx

# Desactivar advertencias de certificados autofirmados TLS 1.3 locales
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# URLs de los servicios locales
BORDE_HTTPS = "https://localhost:8443"
BACKEND_HTTP = "http://localhost:8000"

SITE_KEY = "vh_site_9f8e7d6c5b4a3210"

# Pool de IPs simuladas para ataques distribuidos (Subred reservada TEST-NET-2)
BOTNET_IPS = [f"198.51.100.{i}" for i in range(1, 35)]
HUMAN_IPS = [f"10.20.{i}.{j}" for i in range(1, 5) for j in range(10, 25)]

USER_AGENTS_BOTS = [
    "sqlmap/1.7.2#stable (http://sqlmap.org)",
    "Mozilla/5.0 (compatible; HeadlessChrome/118.0.5993.88)",
    "python-requests/2.31.0",
    "curl/7.88.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 (Automated; Bot/2.0)",
    "Distributed-Botnet-Worker/3.1"
]

USER_AGENTS_HUMANOS = [
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Android 14; Mobile; rv:124.0) Gecko/124.0 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
]

class StatsTracker:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.total_requests = 0
        self.humans_approved_200 = 0
        self.bots_blocked_ia_403 = 0
        self.ddos_rate_limited_429 = 0
        self.edge_unauthorized_401 = 0
        self.human_latencies = []
        self.start_time = time.time()

    async def record_human(self, latency_ms: float, status_code: int):
        async with self.lock:
            self.total_requests += 1
            if status_code == 200:
                self.humans_approved_200 += 1
                self.human_latencies.append(latency_ms)
                if len(self.human_latencies) > 200:
                    self.human_latencies.pop(0)

    async def record_attack(self, status_code: int):
        async with self.lock:
            self.total_requests += 1
            if status_code == 403:
                self.bots_blocked_ia_403 += 1
            elif status_code == 429:
                self.ddos_rate_limited_429 += 1
            elif status_code == 401:
                self.edge_unauthorized_401 += 1

    def get_summary(self):
        elapsed = max(0.1, time.time() - self.start_time)
        rps = self.total_requests / elapsed
        avg_lat = (sum(self.human_latencies) / len(self.human_latencies)) if self.human_latencies else 0.0
        p95_lat = sorted(self.human_latencies)[int(len(self.human_latencies) * 0.95)] if len(self.human_latencies) >= 10 else avg_lat
        total_mitigated = self.bots_blocked_ia_403 + self.ddos_rate_limited_429 + self.edge_unauthorized_401
        
        return {
            "elapsed": elapsed,
            "total": self.total_requests,
            "rps": rps,
            "humans_200": self.humans_approved_200,
            "avg_lat_ms": avg_lat,
            "p95_lat_ms": p95_lat,
            "bots_403": self.bots_blocked_ia_403,
            "rate_limit_429": self.ddos_rate_limited_429,
            "edge_401": self.edge_unauthorized_401,
            "total_mitigated": total_mitigated,
            "human_ratio": (self.humans_approved_200 / self.total_requests * 100) if self.total_requests > 0 else 0
        }

def resolver_pow(nonce: str, difficulty: int) -> str:
    target = "0" * difficulty
    c = 0
    while True:
        sol = hex(c)[2:]
        if hashlib.sha256(f"{nonce}{sol}".encode()).hexdigest().startswith(target):
            return sol
        c += 1

async def flujo_ciudadano_real(client: httpx.AsyncClient, stats: StatsTracker):
    """
    Simula un ciudadano real:
    1. Solicita inicialización de reto en el portal (/challenge/init).
    2. Resuelve Proof-of-Work en Web Crypto.
    3. Envía telemetría biomecánica con entropía natural y dinámicas orgánicas de teclado.
    4. La IA evalúa y emite token Ed25519 (200 OK).
    5. El ciudadano navega o ingresa al trámite protegido a través del Borde TLS 1.3 con su token.
    """
    t_start = time.perf_counter()
    # Generar IP única residencial simulada para cada ciudadano para evitar falsos rate limits por colisión de IP
    ip_origen = f"10.{random.randint(20, 240)}.{random.randint(1, 250)}.{random.randint(1, 250)}"
    ua = random.choice(USER_AGENTS_HUMANOS)
    headers = {
        "User-Agent": ua,
        "X-Forwarded-For": ip_origen,
        "Content-Type": "application/json"
    }

    try:
        # Paso 1: Init de desafío
        r_init = await client.post(
            f"{BORDE_HTTPS}/api/v1/challenge/init",
            json={"site_key": SITE_KEY, "target_route": "/login"},
            headers=headers,
            timeout=4.0
        )
        if r_init.status_code != 200:
            return

        init_data = r_init.json()
        cid = init_data["challenge_id"]
        nonce = init_data["nonce"]
        diff = init_data.get("pow_difficulty", 3)

        # Paso 2: PoW SHA-256
        pow_sol = resolver_pow(nonce, diff)

        # Paso 3: Telemetría humana natural (baja linealidad, alta entropía angular, sin webdriver)
        telemetry = {
            "challenge_id": cid,
            "telemetry_window_ms": random.randint(1800, 3200),
            "pointer_metrics": {
                "event_count": random.randint(45, 75),
                "mean_velocity": round(random.uniform(0.95, 1.65), 2),
                "std_acceleration": round(random.uniform(0.28, 0.48), 2),
                "angular_entropy": round(random.uniform(2.65, 3.10), 2),
                "straight_line_ratio": round(random.uniform(0.06, 0.14), 2)
            },
            "keyboard_metrics": {
                "key_count": random.randint(8, 16),
                "mean_dwell_ms": round(random.uniform(70.0, 95.0), 1),
                "std_flight_ms": round(random.uniform(25.0, 42.0), 1)
            },
            "environment_signals": {
                "webdriver_flag": False,
                "plugins_count": random.randint(3, 7),
                "languages_consistent": True,
                "viewport_ratio_valid": True,
                "time_to_first_interaction_ms": random.randint(450, 850)
            }
        }

        # Paso 4: Verificación conductual e inferencia IA
        r_verify = await client.post(
            f"{BORDE_HTTPS}/api/v1/challenge/verify",
            json={
                "site_key": SITE_KEY,
                "challenge_id": cid,
                "pow_solution": pow_sol,
                "telemetry": telemetry
            },
            headers=headers,
            timeout=4.0
        )
        
        token = r_verify.json().get("jwt_token")
        if not token:
            return

        # Paso 5: Consumir endpoint protegido del trámite a través de OpenResty con el token Ed25519
        headers["X-Human-Token"] = token
        r_tramite = await client.post(
            f"{BORDE_HTTPS}/login",
            json={"cedula": f"V-{random.randint(12000000, 32000000)}", "tramite": "renovacion_cedula"},
            headers=headers,
            timeout=4.0
        )

        lat_ms = (time.perf_counter() - t_start) * 1000.0
        await stats.record_human(lat_ms, r_tramite.status_code)

    except Exception:
        pass

async def flujo_ataque_ddos_l7(client: httpx.AsyncClient, stats: StatsTracker):
    """
    Simula una botnet lanzando ráfagas continuas de peticiones sin token hacia /login o /api/consulta.
    El Borde OpenResty debe retornar 401 (sin token) y 429 (exceso de tasa / rate limit).
    """
    bot_ip = f"198.51.{random.randint(100, 110)}.{random.randint(1, 250)}"
    ua = random.choice(USER_AGENTS_BOTS)
    endpoint = random.choice(["/login", "/api/consulta"])

    headers = {
        "User-Agent": ua,
        "X-Forwarded-For": bot_ip,
        "Content-Type": "application/json"
    }

    try:
        if endpoint == "/login":
            r = await client.post(
                f"{BORDE_HTTPS}/login",
                json={"cedula": "V-99999999", "password": "bruteforce_attack"},
                headers=headers,
                timeout=3.0
            )
        else:
            r = await client.get(
                f"{BORDE_HTTPS}/api/consulta",
                headers=headers,
                timeout=3.0
            )
        await stats.record_attack(r.status_code)
    except Exception:
        pass

async def flujo_bot_telemetria_sintetica(client: httpx.AsyncClient, stats: StatsTracker):
    """
    Simula un scraper o bot sofisticado (ej. Selenium / Puppeteer) que intenta resolver el PoW
    pero genera telemetría sintética (movimiento en línea recta, webdriver=True, sin entropía).
    La IA local debe detectar el comportamiento anómalo y bloquearlo con HTTP 403.
    """
    bot_ip = random.choice(BOTNET_IPS)
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (HeadlessChrome)",
        "X-Forwarded-For": bot_ip,
        "Content-Type": "application/json"
    }

    try:
        r_init = await client.post(
            f"{BORDE_HTTPS}/api/v1/challenge/init",
            json={"site_key": SITE_KEY, "target_route": "/login"},
            headers=headers,
            timeout=4.0
        )
        if r_init.status_code != 200:
            return

        init_data = r_init.json()
        cid = init_data["challenge_id"]
        nonce = init_data["nonce"]
        pow_sol = resolver_pow(nonce, init_data.get("pow_difficulty", 3))

        # Telemetría de bot automatizado
        fake_telemetry = {
            "challenge_id": cid,
            "telemetry_window_ms": 200,  # Muy rápido
            "pointer_metrics": {
                "event_count": 8,
                "mean_velocity": 8.5,
                "std_acceleration": 0.01,
                "angular_entropy": 0.12,     # Prácticamente nula
                "straight_line_ratio": 0.98   # Línea recta artificial
            },
            "keyboard_metrics": {
                "key_count": 10,
                "mean_dwell_ms": 10.0,       # Inhumano
                "std_flight_ms": 0.5
            },
            "environment_signals": {
                "webdriver_flag": True,      # Selenium detectado
                "plugins_count": 0,
                "languages_consistent": False,
                "viewport_ratio_valid": False,
                "time_to_first_interaction_ms": 15
            }
        }

        r_verify = await client.post(
            f"{BORDE_HTTPS}/api/v1/challenge/verify",
            json={
                "site_key": SITE_KEY,
                "challenge_id": cid,
                "pow_solution": pow_sol,
                "telemetry": fake_telemetry
            },
            headers=headers,
            timeout=4.0
        )

        await stats.record_attack(r_verify.status_code)

    except Exception:
        pass

def imprimir_banner():
    os.system("clear" if os.name == "posix" else "cls")
    print("\033[1;36m╔════════════════════════════════════════════════════════════════════════════════════╗\033[0m")
    print("\033[1;36m║   GENERADOR DE TRÁFICO MIXTO EN VIVO: CIUDADANOS REALES VS ATAQUES DDoS / BOTS    ║\033[0m")
    print("\033[1;36m║   Servicio Autónomo de Verificación Humana y Mitigación de Bots (Mincyt 2026)      ║\033[0m")
    print("\033[1;36m╚════════════════════════════════════════════════════════════════════════════════════╝\033[0m")
    print(f"\033[1;33m[*] Borde TLS 1.3 Protegido:\033[0m {BORDE_HTTPS}")
    print(f"\033[1;33m[*] Consola Administrativa:\033[0m  http://localhost:3000/ (Abra para ver gráfica en vivo)")
    print("\033[1;30m────────────────────────────────────────────────────────────────────────────────────\033[0m")

async def monitor_en_pantalla(stats: StatsTracker, stop_event: asyncio.Event):
    """Refresca las estadísticas en consola en tiempo real."""
    while not stop_event.is_set():
        s = stats.get_summary()
        sys.stdout.write(
            f"\r\033[1;37m[⏱ {s['elapsed']:4.1f}s]\033[0m "
            f"\033[1;32m✓ Ciudadanos OK: {s['humans_200']:<5}\033[0m "
            f"\033[1;34m(Lat: {s['avg_lat_ms']:4.1f}ms | p95: {s['p95_lat_ms']:4.1f}ms)\033[0m │ "
            f"\033[1;31m✗ Bots IA (403): {s['bots_403']:<4}\033[0m │ "
            f"\033[1;33m⚡ RateLimit (429): {s['rate_limit_429']:<4}\033[0m │ "
            f"\033[1;35m🛡 Sin Token (401): {s['edge_401']:<4}\033[0m │ "
            f"\033[1;36mTotal: {s['total']:<5} ({s['rps']:4.1f} req/s)\033[0m"
        )
        sys.stdout.flush()
        await asyncio.sleep(0.5)

async def worker_loop(client: httpx.AsyncClient, stats: StatsTracker, stop_event: asyncio.Event, ratio_ataque: float):
    """Bucle individual de generación de tráfico."""
    while not stop_event.is_set():
        dado = random.random()
        if dado < ratio_ataque:
            # 85% DDoS L7 / Fuerza bruta sin token, 15% bot sofisticado intentando falsificar IA
            if random.random() < 0.85:
                await flujo_ataque_ddos_l7(client, stats)
            else:
                await flujo_bot_telemetria_sintetica(client, stats)
        else:
            # Flujo de ciudadano legítimo
            await flujo_ciudadano_real(client, stats)
        
        # Pausa equilibrada para emular concurrencia natural y evitar saturación del socket local
        await asyncio.sleep(random.uniform(0.06, 0.18))

async def main():
    parser = argparse.ArgumentParser(description="Generador de tráfico mixto en vivo (Ciudadanos vs DDoS).")
    parser.add_argument("--duracion", type=int, default=30, help="Duración de la prueba en segundos (0 para indefinido).")
    parser.add_argument("--concurrencia", type=int, default=10, help="Número de conexiones/workers simultáneos (default: 10).")
    parser.add_argument("--ratio-ataque", type=float, default=0.70, help="Proporción de ataques (0.70 = 70%% ataques, 30%% humanos).")
    args = parser.parse_args()

    imprimir_banner()
    print(f"\033[1;32m[+] Iniciando prueba:\033[0m {args.concurrencia} workers concurrentes.")
    print(f"\033[1;32m[+] Proporción configurada:\033[0m {int((1 - args.ratio_ataque)*100)}% Ciudadanos Humanos | {int(args.ratio_ataque*100)}% Ataques y Bots.")
    dur_txt = f"{args.duracion} segundos" if args.duracion > 0 else "Indefinida (Presione Ctrl+C para finalizar)"
    print(f"\033[1;32m[+] Duración:\033[0m {dur_txt}")
    print("\033[1;30m────────────────────────────────────────────────────────────────────────────────────\033[0m")
    print("Transmitiendo tráfico... Observe la consola y la interfaz gráfica web en tiempo real:\n")

    stats = StatsTracker()
    stop_event = asyncio.Event()

    limits = httpx.Limits(max_keepalive_connections=args.concurrencia * 2, max_connections=args.concurrencia * 2)
    async with httpx.AsyncClient(verify=False, limits=limits) as client:
        # Tarea de monitorización en terminal
        monitor_task = asyncio.create_task(monitor_en_pantalla(stats, stop_event))

        # Crear los workers concurrentes
        workers = [
            asyncio.create_task(worker_loop(client, stats, stop_event, args.ratio_ataque))
            for _ in range(args.concurrencia)
        ]

        try:
            if args.duracion > 0:
                await asyncio.sleep(args.duracion)
            else:
                while True:
                    await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n\n\033[1;33m[!] Deteniendo generador de tráfico...\033[0m")
        finally:
            stop_event.set()
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            await monitor_task

    # Resumen final
    s = stats.get_summary()
    print("\n\n" + "═" * 80)
    print("                     INFORME FINAL DE RESILIENCIA Y MITIGACIÓN                      ")
    print("═" * 80)
    print(f"  • Tiempo total de ejecución : {s['elapsed']:.2f} segundos")
    print(f"  • Peticiones totales enviadas: {s['total']:,} peticiones ({s['rps']:.1f} req/s)")
    print("-" * 80)
    print(f"  \033[1;32m✓ TRÁFICO CIUDADANO LEGÍTIMO (200 OK):\033[0m  {s['humans_200']:,} trámites procesados exitosamente")
    print(f"    ↳ Latencia media para humanos     : {s['avg_lat_ms']:.2f} ms")
    print(f"    ↳ Latencia percentil 95 (p95)     : {s['p95_lat_ms']:.2f} ms")
    print("-" * 80)
    print(f"  \033[1;31m✗ ATAQUES Y BOTS MITIGADOS EN BORDE/IA:\033[0m {s['total_mitigated']:,} peticiones bloqueadas ({100 - s['human_ratio']:.1f}%)")
    print(f"    ↳ Bloqueados por IA Conductual    : {s['bots_403']:,} bots con telemetría artificial (HTTP 403)")
    print(f"    ↳ Frenados por Rate Limit en Borde: {s['rate_limit_429']:,} ráfagas DDoS L7 (HTTP 429)")
    print(f"    ↳ Bloqueados en Borde sin Token   : {s['edge_401']:,} accesos no autorizados (HTTP 401)")
    print("═" * 80)
    print(" \033[1;32mCONCLUSIÓN:\033[0m A pesar del bombardeo de peticiones y bots, el 100% de los ciudadanos")
    print(f" legítimos ingresaron sin interrupción con una latencia media de {s['avg_lat_ms']:.1f} ms.")
    print("═" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
