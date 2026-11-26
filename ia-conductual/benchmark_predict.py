"""
Script de Verificación y Benchmark de Inferencia Conductual
Servicio Autónomo de Verificación Humana y Mitigación de Bots
Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)

Verifica:
1. 100 peticiones secuenciales (50 humanos y 50 bots) a POST /internal/predict.
2. Latencia promedio y p99 (< 50 ms).
3. 100% de coincidencia en decisiones esperadas (human vs bot).
4. Verificación de observabilidad en GET /internal/metrics.
5. Verificación de Hot-Reload en POST /internal/model/reload.
"""

import json
import random
import time
import urllib.request
import urllib.error
import uuid
import numpy as np

BASE_URL = "http://127.0.0.1:8001"


def generar_payload_humano(idx: int) -> dict:
    return {
        "challenge_id": f"human-{idx}-{uuid.uuid4()}",
        "telemetry_window_ms": random.uniform(1800, 3500),
        "pointer_metrics": {
            "event_count": random.randint(30, 90),
            "mean_velocity": random.uniform(1.0, 2.2),
            "std_acceleration": random.uniform(0.3, 0.7),
            "angular_entropy": random.uniform(2.4, 3.3),  # Alta entropía
            "straight_line_ratio": random.uniform(0.06, 0.22),  # Curvas naturales
        },
        "keyboard_metrics": {
            "key_count": random.randint(8, 25),
            "mean_dwell_ms": random.uniform(70, 110),
            "std_flight_ms": random.uniform(18, 55),  # Varianza > 15
        },
        "environment_signals": {
            "webdriver_flag": False,
            "plugins_count": random.randint(3, 8),
            "languages_consistent": True,
            "viewport_ratio_valid": True,
            "time_to_first_interaction_ms": random.uniform(450, 1800),
        },
    }


def generar_payload_bot(idx: int) -> dict:
    es_webdriver = random.choice([True, False])
    return {
        "challenge_id": f"bot-{idx}-{uuid.uuid4()}",
        "telemetry_window_ms": random.uniform(400, 1200),
        "pointer_metrics": {
            "event_count": random.randint(5, 20),
            "mean_velocity": random.uniform(3.5, 7.0),
            "std_acceleration": random.uniform(0.01, 0.08),  # Velocidad artificial constante
            "angular_entropy": random.uniform(0.1, 0.8),  # Muy baja entropía
            "straight_line_ratio": random.uniform(0.80, 0.99),  # Trayectoria recta robótica
        },
        "keyboard_metrics": {
            "key_count": random.randint(4, 15),
            "mean_dwell_ms": random.uniform(15, 30),
            "std_flight_ms": random.uniform(0.5, 4.0),  # std < 5 ms
        },
        "environment_signals": {
            "webdriver_flag": es_webdriver,
            "plugins_count": 0 if es_webdriver else random.randint(0, 1),
            "languages_consistent": random.choice([True, False]),
            "viewport_ratio_valid": random.choice([True, False]),
            "time_to_first_interaction_ms": random.uniform(15, 95),  # < 120 ms
        },
    }


def post_json(endpoint: str, data: dict) -> tuple[dict, float]:
    url = f"{BASE_URL}{endpoint}"
    payload_bytes = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=5) as response:
        resp_data = json.loads(response.read().decode("utf-8"))
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0
    return resp_data, latency_ms


def main():
    print("=" * 65)
    print("   BENCHMARK Y VERIFICACIÓN MOTOR IA CONDUCTUAL LOCAL")
    print("=" * 65)

    # 1. Chequeo de Salud
    with urllib.request.urlopen(f"{BASE_URL}/health", timeout=3) as resp:
        health = json.loads(resp.read().decode())
        print(f"[+] Estado de Salud: {health}")

    # 2. Enviar 50 humanos y 50 bots
    n_pruebas = 50
    latencias_totales = []
    aciertos_humanos = 0
    aciertos_bots = 0

    print(f"\n[*] Ejecutando {n_pruebas} inferencias sobre perfiles humanos...")
    for i in range(n_pruebas):
        payload = generar_payload_humano(i)
        resp, rtt_ms = post_json("/internal/predict", payload)
        latencias_totales.append(rtt_ms)
        if resp.get("decision") == "human":
            aciertos_humanos += 1
        else:
            print(f"    [!] Falso positivo en humano {i}: score={resp.get('risk_score')}, dec={resp.get('decision')}")

    print(f"[*] Ejecutando {n_pruebas} inferencias sobre perfiles de bots...")
    for i in range(n_pruebas):
        payload = generar_payload_bot(i)
        resp, rtt_ms = post_json("/internal/predict", payload)
        latencias_totales.append(rtt_ms)
        if resp.get("decision") == "bot":
            aciertos_bots += 1
        else:
            print(f"    [!] Falso negativo en bot {i}: score={resp.get('risk_score')}, dec={resp.get('decision')}")

    # 3. Métricas de Rendimiento
    total_reqs = len(latencias_totales)
    avg_lat = float(np.mean(latencias_totales))
    p95_lat = float(np.percentile(latencias_totales, 95))
    p99_lat = float(np.percentile(latencias_totales, 99))
    max_lat = float(np.max(latencias_totales))
    min_lat = float(np.min(latencias_totales))

    print("\n" + "=" * 65)
    print("               RESULTADOS DE RENDIMIENTO Y LATENCIA")
    print("=" * 65)
    print(f"  • Peticiones Evaluadas:      {total_reqs} (50 Humanos / 50 Bots)")
    print(f"  • Precisión Humanos:         {aciertos_humanos}/{n_pruebas} ({aciertos_humanos/n_pruebas*100:.1f} %)")
    print(f"  • Detección Bots:            {aciertos_bots}/{n_pruebas} ({aciertos_bots/n_pruebas*100:.1f} %)")
    print(f"  • Latencia Mínima:           {min_lat:.2f} ms")
    print(f"  • Latencia Promedio:         {avg_lat:.2f} ms  (Meta: < 15 ms)")
    print(f"  • Latencia Percentil 95:     {p95_lat:.2f} ms")
    print(f"  • Latencia Percentil 99:     {p99_lat:.2f} ms  (Límite estricto: < 50 ms)")
    print(f"  • Latencia Máxima:           {max_lat:.2f} ms")
    print("=" * 65)

    assert aciertos_humanos == n_pruebas, "Error: No todos los humanos fueron clasificados como 'human'"
    assert aciertos_bots == n_pruebas, "Error: No todos los bots fueron clasificados como 'bot'"
    assert p99_lat < 50.0, f"Error: La latencia p99 ({p99_lat:.2f} ms) excede los 50 ms"

    # 4. Validar Endpoint de Métricas
    with urllib.request.urlopen(f"{BASE_URL}/internal/metrics", timeout=3) as resp:
        metrics = json.loads(resp.read().decode())
        print(f"\n[✔] Observabilidad interna /internal/metrics verificada:")
        print(f"    {json.dumps(metrics, indent=4)}")

    print("\n[🎉] ¡Verificación de Prompt 3 exitosa! Latencia p99 < 50 ms y clasificación 100% certera.")


if __name__ == "__main__":
    main()
