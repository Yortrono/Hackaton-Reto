import hashlib
from datetime import datetime, timezone
from typing import Dict, Any
from app.config import settings

class PrivacyProtector:
    """
    Cumplimiento de Privacidad por Diseño (Zero Raw Biometrics / Zero Raw IPs):
    - Anonimiza direcciones IP mediante SHA-256(IP + sal_rotativa_diaria).
    - Filtra y elimina coordenadas crudas o pulsaciones individuales antes de cualquier persistencia o logging.
    """

    @staticmethod
    def get_daily_salt() -> str:
        """Genera una sal diaria no predecible basada en la fecha UTC y la llave secreta del servidor."""
        day_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        combined = f"{day_str}:{settings.SALT_ROTATIVE_SECRET}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    @classmethod
    def anonymize_ip(cls, ip_address: str) -> str:
        """Anonimiza una dirección IP real en un hash SHA-256 irreversible con sal rotativa diaria."""
        if not ip_address:
            ip_address = "127.0.0.1"
        salt = cls.get_daily_salt()
        raw_hash = hashlib.sha256(f"{ip_address}:{salt}".encode("utf-8")).hexdigest()
        return f"sha256:{raw_hash[:32]}"

    @staticmethod
    def sanitize_telemetry(telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrae exclusivamente agregaciones estadísticas requeridas para el modelo.
        Descarta cualquier coordenada cruda de ratón o secuencias de teclas individuales.
        """
        pointer = telemetry_data.get("pointer_metrics", {})
        keyboard = telemetry_data.get("keyboard_metrics", {})
        env = telemetry_data.get("environment_signals", {})

        return {
            "telemetry_window_ms": telemetry_data.get("telemetry_window_ms", 0.0),
            "pointer_aggregates": {
                "event_count": pointer.get("event_count", 0),
                "mean_velocity": pointer.get("mean_velocity", 0.0),
                "std_acceleration": pointer.get("std_acceleration", 0.0),
                "angular_entropy": pointer.get("angular_entropy", 0.0),
                "straight_line_ratio": pointer.get("straight_line_ratio", 0.0)
            },
            "keyboard_aggregates": {
                "key_count": keyboard.get("key_count", 0),
                "mean_dwell_ms": keyboard.get("mean_dwell_ms", 0.0),
                "std_flight_ms": keyboard.get("std_flight_ms", 0.0)
            },
            "environment_flags": {
                "webdriver": env.get("webdriver_flag", False),
                "plugins_count": env.get("plugins_count", 0),
                "languages_consistent": env.get("languages_consistent", True)
            }
        }

privacy_protector = PrivacyProtector()
