import pytest
from app.core.crypto_vault import crypto_vault

def test_aes_gcm_encryption_decryption():
    secret = "ClaveSecretaSoberana2026_Vzla"
    encrypted = crypto_vault.encrypt_secret(secret)
    assert encrypted != secret
    assert len(encrypted) > 20

    decrypted = crypto_vault.decrypt_secret(encrypted)
    assert decrypted == secret

def test_aes_gcm_tamper_detection():
    secret = "MensajeConfidencial"
    encrypted = crypto_vault.encrypt_secret(secret)
    # Manipular el texto cifrado
    tampered_bytes = bytearray(encrypted.encode("ascii"))
    tampered_bytes[15] = (tampered_bytes[15] + 1) % 256
    tampered_str = tampered_bytes.decode("ascii", errors="ignore")

    with pytest.raises(Exception):
        crypto_vault.decrypt_secret(tampered_str)

def test_ed25519_keypair_generation_and_loading():
    kid, enc_priv, pub_pem = crypto_vault.generate_ed25519_keypair(kid="test-key-01")
    assert kid == "test-key-01"
    assert "BEGIN PUBLIC KEY" in pub_pem
    assert "END PUBLIC KEY" in pub_pem

    # Cargar clave privada descifrándola de la bóveda
    priv_key = crypto_vault.load_private_key(enc_priv)
    assert priv_key is not None

    # Cargar clave pública
    pub_key = crypto_vault.load_public_key(pub_pem)
    assert pub_key is not None

    # Probar firma y verificación directa con cryptography
    data = b"Datos de prueba para firma soberana"
    signature = priv_key.sign(data)
    # No debe levantar excepción al verificar
    pub_key.verify(signature, data)
