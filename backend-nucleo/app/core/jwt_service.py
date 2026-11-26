import time
import uuid
import jwt
from typing import Dict, Any, Optional, Tuple
from app.config import settings
from app.core.crypto_vault import crypto_vault

class JWTService:
    """
    Servicio de Emisión y Validación de Tokens Asimétricos EdDSA / Ed25519:
    - Firma exclusivamente con la clave privada Ed25519 activa de la bóveda.
    - Cumplimiento estricto del contrato @docs/02-contratos-json.md.
    - Expiración corta (TTL <= 120s).
    - JTI único (UUID v4) de un solo uso con invalidación instantánea (mitigación de replay attacks).
    """

    def __init__(self):
        # Almacén de JTI consumidos en memoria con timestamp de expiración para limpieza
        self._consumed_jtis: Dict[str, float] = {}

    def issue_human_token(
        self,
        site_key: str,
        risk_score: float,
        session_id: Optional[str] = None,
        verification_mode: str = "passive",
        ttl_seconds: Optional[int] = None,
        kid: Optional[str] = None,
        private_key_pem_encrypted: Optional[str] = None
    ) -> Tuple[str, str, int]:
        """
        Emite un token JWT firmado asimétricamente con Ed25519.
        Retorna: (jwt_token, jti, ttl_seconds)
        """
        if ttl_seconds is None or ttl_seconds <= 0 or ttl_seconds > settings.JWT_MAX_TTL_SECONDS:
            ttl_seconds = settings.JWT_DEFAULT_TTL_SECONDS

        now = int(time.time())
        exp = now + ttl_seconds
        jti = str(uuid.uuid4())
        sub = session_id or f"anon_session_{uuid.uuid4().hex[:8]}"

        payload = {
            "iss": settings.JWT_ISSUER,
            "sub": sub,
            "aud": site_key,
            "jti": jti,
            "iat": now,
            "exp": exp,
            "risk_score": round(float(risk_score), 4),
            "verification_mode": verification_mode
        }

        # Obtener clave privada para firmar
        if private_key_pem_encrypted and kid:
            private_key = crypto_vault.load_private_key(private_key_pem_encrypted)
            headers = {"kid": kid, "typ": "JWT", "alg": "EdDSA"}
        else:
            from app.db.database import get_db_context
            from app.db.models import CryptoKeyModel
            with get_db_context() as db:
                active_key = db.query(CryptoKeyModel).filter(CryptoKeyModel.active == 1).first()
                if not active_key:
                    raise RuntimeError("No hay clave criptográfica activa configurada en la bóveda")
                private_key = crypto_vault.load_private_key(active_key.private_key_pem_encrypted)
                headers = {"kid": active_key.kid, "typ": "JWT", "alg": "EdDSA"}

        token = jwt.encode(payload, private_key, algorithm="EdDSA", headers=headers)
        return token, jti, ttl_seconds

    def validate_human_token(
        self,
        token: str,
        site_key: str,
        consume_jti: bool = True
    ) -> Dict[str, Any]:
        """
        Valida la firma asimétrica Ed25519 del token, aud, exp y jti no consumido.
        Si consume_jti=True, registra el JTI para prevenir ataques de repetición.
        """
        self._cleanup_expired_jtis()

        # Decodificar cabecera sin verificar para obtener 'kid'
        try:
            unverified_headers = jwt.get_unverified_header(token)
            kid = unverified_headers.get("kid")
        except Exception as e:
            raise ValueError(f"Cabecera JWT malformada: {str(e)}")

        from app.db.database import get_db_context
        from app.db.models import CryptoKeyModel, ConsumedJTIModel

        with get_db_context() as db:
            # Buscar clave pública correspondiente al kid o clave activa
            query = db.query(CryptoKeyModel)
            if kid:
                key_record = query.filter(CryptoKeyModel.kid == kid).first()
            else:
                key_record = query.filter(CryptoKeyModel.active == 1).first()

            if not key_record:
                raise ValueError("Clave pública no encontrada para el 'kid' especificado")

            public_key = crypto_vault.load_public_key(key_record.public_key_pem)

            # Verificar firma y claims estándar
            try:
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["EdDSA"],
                    audience=site_key,
                    issuer=settings.JWT_ISSUER
                )
            except jwt.ExpiredSignatureError:
                raise ValueError("Token expirado")
            except jwt.InvalidAudienceError:
                raise ValueError("Audiencia del token no coincide con el sitio")
            except jwt.InvalidIssuerError:
                raise ValueError("Emisor del token no autorizado")
            except Exception as e:
                raise ValueError(f"Firma criptográfica inválida: {str(e)}")

            jti = payload.get("jti")
            if not jti:
                raise ValueError("El token carece de identificador único (jti)")

            # Verificar si ya fue consumido en memoria o en base de datos
            if jti in self._consumed_jtis:
                raise ValueError("Ataque de repetición detectado: token ya consumido")

            db_consumed = db.query(ConsumedJTIModel).filter(ConsumedJTIModel.jti == jti).first()
            if db_consumed:
                raise ValueError("Ataque de repetición detectado: token ya consumido")

            # Si consume_jti es True, registrar revocación
            consumed_at_str = None
            if consume_jti:
                exp_ts = payload.get("exp", time.time() + 120)
                self._consumed_jtis[jti] = float(exp_ts)

                now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                consumed_at_str = now_iso
                new_jti = ConsumedJTIModel(
                    jti=jti,
                    site_key=site_key,
                    expires_at=float(exp_ts),
                    consumed_at=now_iso
                )
                db.add(new_jti)
                db.commit()

            return {
                "valid": True,
                "jti": jti,
                "risk_score": payload.get("risk_score", 0.0),
                "consumed_at": consumed_at_str,
                "payload": payload
            }

    def _cleanup_expired_jtis(self):
        """Limpia en memoria los JTIs cuyo 'exp' ya venció."""
        now = time.time()
        expired = [jti for jti, exp in self._consumed_jtis.items() if exp < now]
        for jti in expired:
            self._consumed_jtis.pop(jti, None)

jwt_service = JWTService()
