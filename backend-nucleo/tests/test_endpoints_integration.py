import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.pow import pow_service
from app.db.init_db import init_database

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    init_database()

def test_health_check_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "backend-nucleo"

def test_challenge_init_and_verification_human_flow():
    site_key = "vh_site_9f8e7d6c5b4a3210"

    # 1. Init Challenge
    init_res = client.post("/api/v1/challenge/init", json={
        "site_key": site_key,
        "target_route": "/login",
        "client_context": {
            "sdk_version": "1.0.0",
            "language": "es-VE"
        }
    })
    assert init_res.status_code == 200
    init_data = init_res.json()
    challenge_id = init_data["challenge_id"]
    nonce = init_data["nonce"]
    difficulty = init_data["pow_difficulty"]
    assert init_data["policy_mode"] == "challenge"

    # 2. Resolver PoW
    solution = pow_service.solve_for_test(nonce, difficulty=difficulty)

    # 3. Verify Challenge (Humano verificado)
    verify_res = client.post("/api/v1/challenge/verify", json={
        "site_key": site_key,
        "challenge_id": challenge_id,
        "pow_solution": solution,
        "telemetry": {
            "challenge_id": challenge_id,
            "telemetry_window_ms": 2500,
            "pointer_metrics": {
                "event_count": 45,
                "mean_velocity": 1.4,
                "std_acceleration": 0.4,
                "angular_entropy": 2.5,
                "straight_line_ratio": 0.15
            },
            "keyboard_metrics": {
                "key_count": 10,
                "mean_dwell_ms": 80,
                "std_flight_ms": 30
            },
            "environment_signals": {
                "webdriver_flag": False,
                "plugins_count": 5,
                "languages_consistent": True
            }
        }
    })

    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["status"] == "verified"
    assert verify_data["jwt_token"] is not None
    jwt_token = verify_data["jwt_token"]

    # 4. Validar Token en /api/v1/token/validate
    val_res = client.post("/api/v1/token/validate", json={
        "jwt_token": jwt_token,
        "site_key": site_key,
        "consume_jti": True
    })
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["valid"] is True

    # 5. Intentar revalidar el mismo token consumido (anti-replay)
    replay_res = client.post("/api/v1/token/validate", json={
        "jwt_token": jwt_token,
        "site_key": site_key,
        "consume_jti": True
    })
    assert replay_res.status_code == 401
    assert replay_res.json()["error"]["code"] == "INVALID_TOKEN"

def test_challenge_verify_bot_blocked_http_403():
    site_key = "vh_site_9f8e7d6c5b4a3210"

    init_res = client.post("/api/v1/challenge/init", json={
        "site_key": site_key,
        "target_route": "/login"
    })
    init_data = init_res.json()
    challenge_id = init_data["challenge_id"]
    solution = pow_service.solve_for_test(init_data["nonce"], difficulty=init_data["pow_difficulty"])

    # Enviar telemetría con webdriver_flag=True (Selenium/Puppeteer)
    verify_res = client.post("/api/v1/challenge/verify", json={
        "site_key": site_key,
        "challenge_id": challenge_id,
        "pow_solution": solution,
        "telemetry": {
            "challenge_id": challenge_id,
            "telemetry_window_ms": 100,
            "environment_signals": {
                "webdriver_flag": True
            }
        }
    })

    assert verify_res.status_code == 403
    bot_data = verify_res.json()
    assert bot_data["status"] == "blocked"
    assert bot_data["jwt_token"] is None
    assert bot_data["risk_score"] >= 0.75

def test_admin_login_rbac_and_audit():
    # 1. Login como security_admin
    login_res = client.post("/api/v1/admin/auth/login", json={
        "username": "admin_seguridad",
        "password": "Soberania2026!Segura"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Consultar logs de auditoría
    audit_res = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["chain_integrity_valid"] is True
    assert len(audit_data["items"]) > 0

    # 3. Rotar clave criptográfica
    rotate_res = client.post("/api/v1/admin/vault/rotate", headers=headers)
    assert rotate_res.status_code == 200
    rotate_data = rotate_res.json()
    assert rotate_data["kid"].startswith("key-")
    assert rotate_data["algorithm"] == "EdDSA"

    # 4. Observabilidad
    obs_res = client.get("/api/v1/admin/observability/summary", headers=headers)
    assert obs_res.status_code == 200
    obs_data = obs_res.json()
    assert "traffic_stats" in obs_data
    assert "ai_performance" in obs_data
