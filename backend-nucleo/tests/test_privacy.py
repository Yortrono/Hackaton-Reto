from app.core.privacy import privacy_protector

def test_ip_anonymization_format_and_consistency():
    ip = "190.202.45.10"
    ip_hash_1 = privacy_protector.anonymize_ip(ip)
    ip_hash_2 = privacy_protector.anonymize_ip(ip)

    assert ip_hash_1.startswith("sha256:")
    assert len(ip_hash_1) == 7 + 32
    # La misma IP en el mismo día debe producir el mismo hash
    assert ip_hash_1 == ip_hash_2

    # Distintas IPs producen distintos hashes
    other_ip_hash = privacy_protector.anonymize_ip("200.74.192.5")
    assert other_ip_hash != ip_hash_1

def test_sanitize_telemetry_strips_raw_coordinates():
    raw_telemetry = {
        "telemetry_window_ms": 1500,
        "pointer_metrics": {
            "event_count": 25,
            "mean_velocity": 1.2,
            "std_acceleration": 0.3,
            "angular_entropy": 2.1,
            "straight_line_ratio": 0.15,
            "raw_coordinates_unsafe": [(100, 200), (105, 202)]  # Dato crudo no permitido
        },
        "keyboard_metrics": {
            "key_count": 5,
            "mean_dwell_ms": 70,
            "std_flight_ms": 25,
            "raw_keycodes_unsafe": ["KeyA", "KeyB"]  # Dato crudo no permitido
        },
        "environment_signals": {
            "webdriver_flag": False,
            "plugins_count": 3,
            "languages_consistent": True
        }
    }

    sanitized = privacy_protector.sanitize_telemetry(raw_telemetry)
    assert "raw_coordinates_unsafe" not in sanitized["pointer_aggregates"]
    assert "raw_keycodes_unsafe" not in sanitized["keyboard_aggregates"]
    assert sanitized["pointer_aggregates"]["event_count"] == 25
