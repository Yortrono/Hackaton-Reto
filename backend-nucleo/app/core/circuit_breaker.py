from typing import Dict, Any
from app.schemas.contracts import TelemetryPayload, IAPredictResponse

class DeterministicCircuitBreaker:
    """
    Circuit Breaker y Fallback Heurístico Determinista:
    Si el contenedor de inferencia 'ia-conductual' (Dev 2) está offline, experimenta timeout
    o aún no ha iniciado, este módulo aplica reglas heurísticas de soberanía para tomar
    una decisión segura sin interrumpir la operación del sistema ni permitir accesos indebidos.
    """

    @staticmethod
    def evaluate_fallback(telemetry: TelemetryPayload) -> IAPredictResponse:
        env = telemetry.environment_signals or None
        pointer = telemetry.pointer_metrics or None
        keyboard = telemetry.keyboard_metrics or None

        # 1. Bandera directa de WebDriver (automatización Selenium, Puppeteer, Playwright)
        if env and env.webdriver_flag:
            return IAPredictResponse(
                challenge_id=telemetry.challenge_id,
                risk_score=0.98,
                decision="bot",
                inference_time_ms=0.5,
                model_version="heuristic-fallback-v1"
            )

        # 2. Ausencia total de interacción en una ventana de telemetría sospechosa
        event_count = pointer.event_count if pointer else 0
        key_count = keyboard.key_count if keyboard else 0
        plugins_count = env.plugins_count if env else 0

        if event_count == 0 and key_count == 0:
            # Petición sintética sin ningún movimiento
            return IAPredictResponse(
                challenge_id=telemetry.challenge_id,
                risk_score=0.88,
                decision="bot",
                inference_time_ms=0.4,
                model_version="heuristic-fallback-v1"
            )

        # 3. Movimiento lineal perfecto o entropía angular cero (patrón bot típico)
        if pointer and pointer.straight_line_ratio > 0.85 and pointer.angular_entropy < 0.2:
            return IAPredictResponse(
                challenge_id=telemetry.challenge_id,
                risk_score=0.78,
                decision="challenge",
                inference_time_ms=0.4,
                model_version="heuristic-fallback-v1"
            )

        # 4. Tráfico de riesgo medio / incertidumbre -> Desafío interactivo
        if plugins_count == 0 or (pointer and pointer.angular_entropy < 1.0):
            return IAPredictResponse(
                challenge_id=telemetry.challenge_id,
                risk_score=0.52,
                decision="challenge",
                inference_time_ms=0.3,
                model_version="heuristic-fallback-v1"
            )

        # 5. Interacción orgánica plausible -> Humano verificado
        return IAPredictResponse(
            challenge_id=telemetry.challenge_id,
            risk_score=0.12,
            decision="human",
            inference_time_ms=0.3,
            model_version="heuristic-fallback-v1"
        )

circuit_breaker = DeterministicCircuitBreaker()
