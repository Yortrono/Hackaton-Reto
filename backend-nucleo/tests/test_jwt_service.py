import pytest
from app.core.jwt_service import jwt_service
from app.db.init_db import init_database

@pytest.fixture(autouse=True)
def setup_db():
    init_database()

def test_issue_and_validate_human_token():
    site_key = "vh_site_9f8e7d6c5b4a3210"
    token, jti, ttl = jwt_service.issue_human_token(
        site_key=site_key,
        risk_score=0.14,
        verification_mode="passive"
    )
    assert token is not None
    assert len(token.split(".")) == 3
    assert jti is not None
    assert ttl <= 120

    # Validar token
    res = jwt_service.validate_human_token(token, site_key=site_key, consume_jti=True)
    assert res["valid"] is True
    assert res["jti"] == jti
    assert res["risk_score"] == 0.14
    assert res["consumed_at"] is not None

def test_anti_replay_attack_jti_consumed():
    site_key = "vh_site_9f8e7d6c5b4a3210"
    token, jti, ttl = jwt_service.issue_human_token(
        site_key=site_key,
        risk_score=0.08
    )

    # Primer consumo: exitoso
    res = jwt_service.validate_human_token(token, site_key=site_key, consume_jti=True)
    assert res["valid"] is True

    # Segundo consumo (intento de repetición / replay attack): DEBE fallar
    with pytest.raises(ValueError, match="Ataque de repetición detectado"):
        jwt_service.validate_human_token(token, site_key=site_key, consume_jti=True)

def test_invalid_audience_rejected():
    site_key = "vh_site_9f8e7d6c5b4a3210"
    wrong_site = "vh_site_ataque_ilegitimo"
    token, jti, ttl = jwt_service.issue_human_token(
        site_key=site_key,
        risk_score=0.1
    )

    with pytest.raises(ValueError, match="Audiencia"):
        jwt_service.validate_human_token(token, site_key=wrong_site, consume_jti=False)
