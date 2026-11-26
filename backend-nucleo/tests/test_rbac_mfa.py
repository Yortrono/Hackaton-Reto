import pytest
from app.core.security import (
    hash_password,
    verify_password,
    generate_totp_secret,
    verify_totp,
    create_admin_access_token,
    decode_admin_access_token
)
import pyotp

def test_argon2id_password_hashing():
    pwd = "ContrasenaSoberana2026!"
    hashed = hash_password(pwd)
    assert hashed.startswith("$argon2")
    assert verify_password(pwd, hashed) is True
    assert verify_password("ContrasenaIncorrecta", hashed) is False

def test_totp_mfa_workflow():
    secret = generate_totp_secret()
    assert len(secret) == 32

    # Generar código TOTP actual
    totp = pyotp.TOTP(secret)
    current_code = totp.now()

    # Verificar código válido
    assert verify_totp(secret, current_code) is True

    # Código inválido rechazado
    assert verify_totp(secret, "000000") is False

def test_admin_jwt_claims_and_decoding():
    token = create_admin_access_token(username="admin_seguridad", role="security_admin")
    payload = decode_admin_access_token(token)
    assert payload["sub"] == "admin_seguridad"
    assert payload["role"] == "security_admin"
    assert payload["iss"] == "servicio-verificacion-humana.gob.ve/admin"
