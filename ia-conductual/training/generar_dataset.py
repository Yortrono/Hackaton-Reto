"""
Generador de Dataset Sintético Conductual
Servicio Autónomo de Verificación Humana y Mitigación de Bots
Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)

Genera 20,000 muestras balanceadas (10,000 humanos, 10,000 bots)
respetando estrictamente las variables y distribuciones del contrato JSON.
Privacidad por diseño: Datos 100% sintéticos y efímeros, sin datos personales.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

# Semilla fija para reproducibilidad científica
SEED = 2026
np.random.seed(SEED)

FEATURE_NAMES: List[str] = [
    "pointer_event_count",
    "pointer_mean_velocity",
    "pointer_std_acceleration",
    "pointer_angular_entropy",
    "pointer_straight_line_ratio",
    "keyboard_key_count",
    "keyboard_mean_dwell_ms",
    "keyboard_std_flight_ms",
    "env_webdriver_flag",
    "env_plugins_count",
    "env_languages_consistent",
    "env_viewport_ratio_valid",
    "env_time_to_first_interaction_ms",
    "telemetry_window_ms",
]


def extract_features_from_dict(telemetry: Dict) -> List[float]:
    """
    Extrae el vector plano de características numéricas en el orden exacto esperado por el modelo.
    """
    pm = telemetry.get("pointer_metrics", {})
    km = telemetry.get("keyboard_metrics", {})
    env = telemetry.get("environment_signals", {})

    return [
        float(pm.get("event_count", 0)),
        float(pm.get("mean_velocity", 0.0)),
        float(pm.get("std_acceleration", 0.0)),
        float(pm.get("angular_entropy", 0.0)),
        float(pm.get("straight_line_ratio", 0.0)),
        float(km.get("key_count", 0)),
        float(km.get("mean_dwell_ms", 0.0)),
        float(km.get("std_flight_ms", 0.0)),
        1.0 if env.get("webdriver_flag", False) else 0.0,
        float(env.get("plugins_count", 0)),
        1.0 if env.get("languages_consistent", True) else 0.0,
        1.0 if env.get("viewport_ratio_valid", True) else 0.0,
        float(env.get("time_to_first_interaction_ms", 0.0)),
        float(telemetry.get("telemetry_window_ms", 2000.0)),
    ]


def generar_muestras_humanas(n: int = 10000) -> np.ndarray:
    """
    Genera perfiles biométricos humanos legítimos:
    - Alta entropía angular (2.2 a 3.5)
    - Bajo straight_line_ratio (< 0.25)
    - Varianza natural en aceleración (0.25 a 0.85)
    - Variabilidad natural de intervalos de teclado (std_flight_ms > 15)
    - webdriver_flag = False (0.0)
    - plugins del navegador presentes (> 1)
    - Tiempo a primera interacción > 350 ms
    """
    pointer_event_count = np.random.randint(25, 120, size=n)
    pointer_mean_velocity = np.random.uniform(0.8, 2.5, size=n)
    pointer_std_acceleration = np.random.uniform(0.25, 0.85, size=n)
    pointer_angular_entropy = np.clip(np.random.normal(2.85, 0.35, size=n), 2.2, 3.5)
    pointer_straight_line_ratio = np.random.uniform(0.04, 0.24, size=n)

    keyboard_key_count = np.random.randint(5, 40, size=n)
    keyboard_mean_dwell_ms = np.random.normal(85.0, 15.0, size=n)
    keyboard_std_flight_ms = np.random.uniform(16.0, 65.0, size=n)  # > 15 ms

    env_webdriver_flag = np.zeros(n)  # Humano jamás tiene webdriver=True
    env_plugins_count = np.random.randint(2, 9, size=n)
    env_languages_consistent = np.random.choice([1.0, 0.0], size=n, p=[0.98, 0.02])
    env_viewport_ratio_valid = np.random.choice([1.0, 0.0], size=n, p=[0.99, 0.01])
    env_time_to_first_interaction_ms = np.random.uniform(380.0, 2400.0, size=n)

    telemetry_window_ms = np.random.uniform(1800.0, 4000.0, size=n)

    return np.column_stack([
        pointer_event_count,
        pointer_mean_velocity,
        pointer_std_acceleration,
        pointer_angular_entropy,
        pointer_straight_line_ratio,
        keyboard_key_count,
        keyboard_mean_dwell_ms,
        keyboard_std_flight_ms,
        env_webdriver_flag,
        env_plugins_count,
        env_languages_consistent,
        env_viewport_ratio_valid,
        env_time_to_first_interaction_ms,
        telemetry_window_ms,
    ])


def generar_muestras_bots(n: int = 10000) -> np.ndarray:
    """
    Genera perfiles automatizados y sintéticos de bots:
    - Subtipo 1 (Headless Browser / Selenium / Puppeteer): webdriver_flag = True, 0 plugins, t < 120ms
    - Subtipo 2 (Script directo / Bot HTTP / curl con spoofing): rectas perfectas, entropía baja (< 1.0)
    - Subtipo 3 (Replay / Macro automatizado): intervalos mecánicos idénticos (std_flight_ms < 5)
    """
    sub_n = n // 3
    resto = n - (sub_n * 2)

    # Subtipo 1: Headless / Webdriver automatizado
    n1 = sub_n
    p_events_1 = np.random.randint(5, 30, size=n1)
    p_vel_1 = np.random.uniform(2.5, 6.0, size=n1)
    p_std_acc_1 = np.random.uniform(0.01, 0.12, size=n1)
    p_ang_ent_1 = np.random.uniform(0.1, 0.95, size=n1)  # < 1.0
    p_straight_1 = np.random.uniform(0.76, 0.99, size=n1)  # > 0.75
    k_keys_1 = np.random.randint(2, 20, size=n1)
    k_dwell_1 = np.random.uniform(10.0, 40.0, size=n1)
    k_flight_1 = np.random.uniform(0.5, 4.8, size=n1)  # < 5 ms
    w_flag_1 = np.ones(n1)  # webdriver = True
    plugs_1 = np.zeros(n1)
    lang_1 = np.random.choice([1.0, 0.0], size=n1, p=[0.7, 0.3])
    vp_1 = np.random.choice([1.0, 0.0], size=n1, p=[0.8, 0.2])
    t_first_1 = np.random.uniform(10.0, 115.0, size=n1)  # < 120 ms
    w_time_1 = np.random.uniform(500.0, 1500.0, size=n1)

    mat_1 = np.column_stack([
        p_events_1, p_vel_1, p_std_acc_1, p_ang_ent_1, p_straight_1,
        k_keys_1, k_dwell_1, k_flight_1, w_flag_1, plugs_1,
        lang_1, vp_1, t_first_1, w_time_1
    ])

    # Subtipo 2: Script curl / scraping rápido con trayectoria recta
    n2 = sub_n
    p_events_2 = np.random.randint(0, 15, size=n2)
    p_vel_2 = np.random.uniform(3.0, 8.0, size=n2)
    p_std_acc_2 = np.random.uniform(0.00, 0.06, size=n2)
    p_ang_ent_2 = np.random.uniform(0.0, 0.70, size=n2)  # Muy baja entropía
    p_straight_2 = np.random.uniform(0.85, 1.0, size=n2)  # Línea recta
    k_keys_2 = np.random.randint(0, 10, size=n2)
    k_dwell_2 = np.random.uniform(5.0, 25.0, size=n2)
    k_flight_2 = np.random.uniform(0.1, 3.5, size=n2)  # Intervalos robóticos
    w_flag_2 = np.random.choice([1.0, 0.0], size=n2, p=[0.6, 0.4])
    plugs_2 = np.random.choice([0.0, 1.0], size=n2, p=[0.9, 0.1])
    lang_2 = np.random.choice([1.0, 0.0], size=n2, p=[0.5, 0.5])
    vp_2 = np.random.choice([1.0, 0.0], size=n2, p=[0.6, 0.4])
    t_first_2 = np.random.uniform(5.0, 95.0, size=n2)
    w_time_2 = np.random.uniform(200.0, 1200.0, size=n2)

    mat_2 = np.column_stack([
        p_events_2, p_vel_2, p_std_acc_2, p_ang_ent_2, p_straight_2,
        k_keys_2, k_dwell_2, k_flight_2, w_flag_2, plugs_2,
        lang_2, vp_2, t_first_2, w_time_2
    ])

    # Subtipo 3: Macro / Ataque de Relleno de Credenciales (Credential Stuffing)
    n3 = resto
    p_events_3 = np.random.randint(8, 25, size=n3)
    p_vel_3 = np.random.uniform(1.8, 5.0, size=n3)
    p_std_acc_3 = np.random.uniform(0.02, 0.14, size=n3)
    p_ang_ent_3 = np.random.uniform(0.2, 0.88, size=n3)
    p_straight_3 = np.random.uniform(0.78, 0.95, size=n3)
    k_keys_3 = np.random.randint(8, 30, size=n3)
    k_dwell_3 = np.random.normal(30.0, 2.0, size=n3)  # Dwell mecánico ultra preciso
    k_flight_3 = np.random.uniform(0.8, 4.5, size=n3)  # std < 5 ms
    w_flag_3 = np.random.choice([1.0, 0.0], size=n3, p=[0.5, 0.5])
    plugs_3 = np.random.choice([0.0, 1.0, 2.0], size=n3, p=[0.8, 0.15, 0.05])
    lang_3 = np.random.choice([1.0, 0.0], size=n3, p=[0.8, 0.2])
    vp_3 = np.random.choice([1.0, 0.0], size=n3, p=[0.85, 0.15])
    t_first_3 = np.random.uniform(25.0, 118.0, size=n3)
    w_time_3 = np.random.uniform(800.0, 2200.0, size=n3)

    mat_3 = np.column_stack([
        p_events_3, p_vel_3, p_std_acc_3, p_ang_ent_3, p_straight_3,
        k_keys_3, k_dwell_3, k_flight_3, w_flag_3, plugs_3,
        lang_3, vp_3, t_first_3, w_time_3
    ])

    return np.vstack([mat_1, mat_2, mat_3])


def generar_dataset(n_total: int = 20000) -> Tuple[np.ndarray, np.ndarray]:
    """
    Genera el dataset balanceado de entrenamiento y prueba.
    Retorna X (n_total, 14) en float32 y y (n_total,) en int64.
    """
    n_clase = n_total // 2
    print(f"[*] Generando {n_clase:,} muestras humanas y {n_clase:,} muestras de bots...")

    x_humanos = generar_muestras_humanas(n_clase)
    y_humanos = np.zeros(n_clase, dtype=np.int64)

    x_bots = generar_muestras_bots(n_clase)
    y_bots = np.ones(n_clase, dtype=np.int64)

    x_total = np.vstack([x_humanos, x_bots]).astype(np.float32)
    y_total = np.concatenate([y_humanos, y_bots])

    # Barajar el dataset manteniendo correspondencia de etiquetas
    indices = np.random.permutation(n_total)
    x_total = x_total[indices]
    y_total = y_total[indices]

    print(f"[+] Dataset sintético generado con éxito: X={x_total.shape}, y={y_total.shape}")
    print(f"    - Media straight_line_ratio (Humano): {x_humanos[:, 4].mean():.3f} | (Bot): {x_bots[:, 4].mean():.3f}")
    print(f"    - Media angular_entropy (Humano): {x_humanos[:, 3].mean():.3f} | (Bot): {x_bots[:, 3].mean():.3f}")
    print(f"    - Media std_flight_ms (Humano): {x_humanos[:, 7].mean():.3f} | (Bot): {x_bots[:, 7].mean():.3f}")

    return x_total, y_total


if __name__ == "__main__":
    X, y = generar_dataset(20000)
    out_dir = Path(__file__).parent
    out_file = out_dir / "dataset_conductual.npz"
    np.savez_compressed(out_file, X=X, y=y)
    print(f"[✔] Dataset serializado en memoria temporal sin PII: {out_file} ({out_file.stat().st_size / 1024:.1f} KB)")
