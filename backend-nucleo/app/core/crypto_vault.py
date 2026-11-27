import os
import hashlib
import json
import base64
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import settings

class CryptoVault:
    """
    Bóveda Criptográfica Soberana:
    - Generación y custodia de pares de claves asimétricas Ed25519 (EdDSA).
    - Cifrado en reposo AES-256-GCM para llaves privadas y secretos de sitios usando VAULT_MASTER_KEY.
    - Soporte de rotación de claves y serialización a formato PEM estándar.
    """
    def __init__(self, master_key_hex: Optional[str] = None):
        raw_key = (master_key_hex or settings.VAULT_MASTER_KEY).encode("utf-8")
        # Asegurar exactamente 32 bytes (256 bits) para AES-256-GCM
        self._derived_master_key = hashlib.sha256(raw_key).digest()
        self._aesgcm = AESGCM(self._derived_master_key)

    def encrypt_secret(self, plaintext: str) -> str:
        """Cifra un secreto en reposo con AES-256-GCM retornando formato nonce:ciphertext:tag en base64."""
        nonce = os.urandom(12)  # 96 bits nonce estándar para GCM
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("ascii")

    def decrypt_secret(self, encrypted_b64: str) -> str:
        """Descifra un secreto cifrado con AES-256-GCM."""
        combined = base64.b64decode(encrypted_b64.encode("ascii"))
        nonce = combined[:12]
        ciphertext = combined[12:]
        decrypted = self._aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode("utf-8")

    def generate_ed25519_keypair(self, kid: Optional[str] = None) -> Tuple[str, str, str]:
        """
        Genera un nuevo par Ed25519.
        Retorna: (kid, private_key_pem_encrypted, public_key_pem)
        """
        if not kid:
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
            kid = f"key-{now_str}"

        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        encrypted_private_pem = self.encrypt_secret(private_pem)
        return kid, encrypted_private_pem, public_pem

    def load_private_key(self, encrypted_private_pem: str) -> ed25519.Ed25519PrivateKey:
        """Descifra y carga la clave privada Ed25519 en memoria."""
        decrypted_pem = self.decrypt_secret(encrypted_private_pem)
        return serialization.load_pem_private_key(
            decrypted_pem.encode("utf-8"),
            password=None
        )

    def load_public_key(self, public_pem: str) -> ed25519.Ed25519PublicKey:
        """Carga la clave pública Ed25519 desde PEM."""
        return serialization.load_pem_public_key(public_pem.encode("utf-8"))

crypto_vault = CryptoVault()
