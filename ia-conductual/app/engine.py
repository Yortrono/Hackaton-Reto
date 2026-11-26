"""
Motor de Inferencia Conductual Local (Thread-Safe con Recarga en Caliente)
Servicio Autónomo de Verificación Humana y Mitigación de Bots
Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)

Invariantes Técnicas:
- Procesamiento 100% efímero en memoria RAM (Zero Raw Biometrics Persistence).
- Latencia objetivo: < 15 ms promedio, < 50 ms p99.
- Carga de modelo única al iniciar y soporte de hot-reload thread-safe.
"""

from collections import deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import onnxruntime as ort

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


class BehavioralInferenceEngine:
    """
    Motor local de inferencia conductual basado en ONNX Runtime.
    Soporta inferencia ultra rápida (< 15 ms) y hot-reload de modelos en tiempo de ejecución.
    """

    def __init__(self, model_path: str, metadata_path: Optional[str] = None) -> None:
        self.lock = threading.RLock()
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path) if metadata_path else None

        # Métricas de observabilidad en memoria (Zero PII)
        self.total_inferences: int = 0
        self.decision_counts: Dict[str, int] = {"human": 0, "challenge": 0, "bot": 0}
        self.latencies_ms: deque = deque(maxlen=2000)

        # Cargar modelo inicial
        self._load_session(self.model_path, self.metadata_path)

    def _load_session(self, model_path: Path, metadata_path: Optional[Path]) -> None:
        """Carga o recarga la sesión ONNX y metadatos asociados."""
        if not model_path.exists():
            raise FileNotFoundError(f"Archivo de modelo no encontrado: {model_path}")

        # Configurar opciones de ONNX Runtime para latencia mínima local
        so = ort.SessionOptions()
        so.intra_op_num_threads = 2
        so.inter_op_num_threads = 1
        so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        new_session = ort.InferenceSession(str(model_path), sess_options=so)
        input_name = new_session.get_inputs()[0].name

        # Cargar metadatos
        model_version = "lgbm-conductual-v1.0.0"
        thresholds = {"human_max": 0.35, "challenge_max": 0.75, "bot_min": 0.75}

        if metadata_path and metadata_path.exists():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    model_version = meta.get("model_version", model_version)
                    thresholds = meta.get("decision_thresholds", thresholds)
            except Exception as e:
                print(f"[!] Advertencia al leer metadata: {e}")

        # Reemplazo atómico con lock
        with self.lock:
            self.session = new_session
            self.input_name = input_name
            self.model_version = model_version
            self.thresholds = thresholds
            print(f"[✔] Modelo ONNX cargado exitosamente: versión={self.model_version}")

    def extract_features(self, telemetry: Dict[str, Any]) -> np.ndarray:
        """
        Extrae y normaliza las 14 features del contrato JSON en un array float32 (1, 14).
        """
        pm = telemetry.get("pointer_metrics") or {}
        km = telemetry.get("keyboard_metrics") or {}
        env = telemetry.get("environment_signals") or {}

        features = [
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
        return np.array([features], dtype=np.float32)

    def predict(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta la inferencia probabilística sobre las señales de telemetría.
        Retorna riesgo, decisión y tiempo exacto en ms sin persistir datos biométricos.
        """
        t0 = time.perf_counter()
        challenge_id = telemetry.get("challenge_id", "anon-challenge")

        x_input = self.extract_features(telemetry)

        with self.lock:
            outputs = self.session.run(None, {self.input_name: x_input})
            version = self.model_version
            t_human = self.thresholds["human_max"]
            t_challenge = self.thresholds["challenge_max"]

        # Parsear salida de ONNX Runtime (dict de probabilidades o array)
        raw_prob = outputs[1]
        if isinstance(raw_prob, list) and len(raw_prob) > 0:
            if isinstance(raw_prob[0], dict):
                risk_score = float(raw_prob[0].get(1, 0.0))
            else:
                risk_score = float(raw_prob[0][1])
        elif isinstance(raw_prob, np.ndarray):
            risk_score = float(raw_prob[0][1])
        else:
            risk_score = 0.5

        risk_score = max(0.0, min(1.0, risk_score))

        # Clasificación según umbrales de seguridad soberana
        if risk_score < t_human:
            decision = "human"
        elif risk_score < t_challenge:
            decision = "challenge"
        else:
            decision = "bot"

        dt_ms = (time.perf_counter() - t0) * 1000.0

        # Actualizar métricas agregadas en memoria (Thread-Safe)
        with self.lock:
            self.total_inferences += 1
            self.decision_counts[decision] += 1
            self.latencies_ms.append(dt_ms)

        return {
            "challenge_id": challenge_id,
            "risk_score": round(risk_score, 4),
            "decision": decision,
            "inference_time_ms": round(dt_ms, 3),
            "model_version": version,
        }

    def reload_model(self, model_bytes: bytes, version: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Valida e instala en caliente un nuevo modelo ONNX recibido en memoria (Hot-Reload).
        """
        temp_path = self.model_path.parent / f"temp_{int(time.time())}.onnx"
        try:
            with open(temp_path, "wb") as f:
                f.write(model_bytes)

            so = ort.SessionOptions()
            so.intra_op_num_threads = 2
            test_session = ort.InferenceSession(str(temp_path), sess_options=so)

            # Validar con entrada de prueba (1, 14)
            test_input = np.zeros((1, 14), dtype=np.float32)
            input_name = test_session.get_inputs()[0].name
            test_session.run(None, {input_name: test_input})

            # Sobrescribir modelo activo
            final_target = self.model_path.parent / f"modelo_conductual_{version}.onnx"
            temp_path.rename(final_target)

            with self.lock:
                self.session = test_session
                self.input_name = input_name
                self.model_version = version
                if metadata and "decision_thresholds" in metadata:
                    self.thresholds = metadata["decision_thresholds"]

            print(f"[✔] Hot-reload exitoso: Nuevo modelo activo versión={version}")
            return True
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            print(f"[✘] Error durante hot-reload de modelo: {e}")
            raise ValueError(f"Fallo en validación o carga del modelo ONNX: {str(e)}")

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna las métricas de rendimiento y estadísticas de clasificación."""
        with self.lock:
            lats = list(self.latencies_ms)
            total = self.total_inferences
            version = self.model_version
            counts = dict(self.decision_counts)

        if lats:
            avg_ms = float(np.mean(lats))
            p99_ms = float(np.percentile(lats, 99))
        else:
            avg_ms = 0.0
            p99_ms = 0.0

        return {
            "active_model_version": version,
            "total_inferences": total,
            "avg_inference_ms": round(avg_ms, 3),
            "p99_inference_ms": round(p99_ms, 3),
            "decisions": counts,
        }
