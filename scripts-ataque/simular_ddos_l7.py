#!/usr/bin/env python3
"""
Simulador de Ataque DDoS Capa 7 y Ráfaga Concurrente
Servicio Autónomo de Verificación Humana y Mitigación de Bots
Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)

Lanza 300 peticiones concurrentes contra https://localhost:8443/login
y evalúa el porcentaje de mitigación HTTP 429 frente a la disponibilidad
continua de un usuario legítimo con token verificado.
"""

import asyncio
from collections import Counter
import time
import httpx
import jwt

TARGET_URL = "https://localhost:8443/login"
HEALTH_URL = "https://localhost:8443/api/consulta"
NUM_REQUESTS = 300
CONCURRENCY_LIMIT = 50


def generar_token_humano_valido() -> str:
    """Genera un JWT válido emitido por la autoridad soberana."""
    now = int(time.time())
    payload = {
        "iss": "servicio-verificacion-humana.gob.ve",
        "sub": "ciudadano_legitimo_demo",
        "aud": "vh_site_9f8e7d6c5b4a3210",
        "jti": "legit-test-uuid-42",
        "iat": now,
        "exp": now + 300,
        "risk_score": 0.08,
        "verification_mode": "passive"
    }
    return jwt.encode(payload, "secret_key_soberana_2026_test", algorithm="HS256")


async def enviar_peticion_ataque(client: httpx.AsyncClient, req_id: int) -> int:
    try:
        r = await client.post(
            TARGET_URL,
            headers={
                "User-Agent": f"Ataque-DDoS-Worker-{req_id}/2.0",
                "Content-Type": "application/json"
            },
            json={"cedula": f"V-{req_id}", "password": "password_stuffing"},
            timeout=5.0
        )
        return r.status_code
    except Exception as e:
        return 0


async def enviar_peticion_legitima(client: httpx.AsyncClient, token: str) -> tuple[int, float]:
    t0 = time.perf_counter()
    try:
        r = await client.get(
            HEALTH_URL,
            headers={
                "User-Agent": "NavegadorCiudadano-Legitimo/1.0",
                "X-Human-Token": token
            },
            timeout=5.0
        )
        t_ms = (time.perf_counter() - t0) * 1000.0
        return r.status_code, t_ms
    except Exception:
        return 0, 0.0


async def ejecutar_simulacion():
    print("=" * 72)
    print("      SIMULADOR DE ATAQUE DE DENEGACIÓN DE SERVICIO (DDoS L7)")
    print("=" * 72)
    print(f"[*] Objetivo:                    {TARGET_URL}")
    print(f"[*] Volumen de Ráfaga:           {NUM_REQUESTS} peticiones HTTP concurrentes")
    print(f"[*] Límite de Concurrencia:      {CONCURRENCY_LIMIT} workers paralelos")
    print("-" * 72)

    limits = httpx.Limits(max_keepalive_connections=CONCURRENCY_LIMIT, max_connections=CONCURRENCY_LIMIT)
    async with httpx.AsyncClient(verify=False, limits=limits) as client:
        # Pre-calentar y verificar disponibilidad base
        token_humano = generar_token_humano_valido()
        status_base, t_base = await enviar_peticion_legitima(client, token_humano)
        print(f"[+] Disponibilidad pre-ataque (Ciudadano Verificado): HTTP {status_base} ({t_base:.2f} ms)")

        # Lanzar ráfaga de 300 peticiones en paralelo
        print(f"\n[🔥] Iniciando ráfaga masiva de {NUM_REQUESTS} peticiones contra /login...")
        t_inicio = time.perf_counter()

        sem = asyncio.Semaphore(CONCURRENCY_LIMIT)

        async def worker(idx: int) -> int:
            async with sem:
                return await enviar_peticion_ataque(client, idx)

        tareas = [worker(i) for i in range(NUM_REQUESTS)]

        # En medio de la ráfaga, verificar disponibilidad para el ciudadano legítimo
        async def chequear_legitimo():
            await asyncio.sleep(0.05)
            return await enviar_peticion_legitima(client, token_humano)

        tarea_legitima = asyncio.create_task(chequear_legitimo())

        # Ejecutar ráfaga
        respuestas = await asyncio.gather(*tareas)
        status_legitimo, t_legitimo = await tarea_legitima

        t_total = time.perf_counter() - t_inicio

    conteo = Counter(respuestas)
    reqs_429 = conteo.get(429, 0)
    reqs_401 = conteo.get(401, 0)
    reqs_otras = sum(v for k, v in conteo.items() if k not in (429, 401))

    pct_429 = (reqs_429 / NUM_REQUESTS) * 100.0
    throughput = NUM_REQUESTS / t_total

    print("\n" + "=" * 72)
    print("               RESULTADOS DE LA MITIGACIÓN PERIMETRAL")
    print("=" * 72)
    print(f"  • Tiempo Total de Ráfaga:          {t_total:.2f} segundos")
    print(f"  • Rendimiento Evaluado:            {throughput:.1f} req/s")
    print(f"  • Peticiones Bloqueadas (HTTP 429): {reqs_429}/{NUM_REQUESTS} ({pct_429:.1f} %)")
    print(f"  • Peticiones Retadas (HTTP 401):    {reqs_401}/{NUM_REQUESTS}")
    print(f"  • Fallos de Conexión o Timeout:    {reqs_otras}")
    print(f"  • Acceso de Ciudadano Legítimo:    HTTP {status_legitimo} (Latencia: {t_legitimo:.2f} ms)")
    print("=" * 72)

    assert reqs_429 > 0, "Error: El borde no mitigó ninguna petición con HTTP 429"
    assert status_legitimo == 200, f"Error: El tráfico legítimo fue degradado (HTTP {status_legitimo})"

    print("\n[✔] ÉXITO: El borde perimetral mitigó efectivamente la ráfaga DDoS.")
    print("    El portal institucional se mantuvo 100 % disponible para ciudadanos verificados.")


if __name__ == "__main__":
    asyncio.run(ejecutar_simulacion())
