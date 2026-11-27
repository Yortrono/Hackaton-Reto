import time
import uuid
import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.config import settings
from app.db.models import SiteModel, SitePolicyModel, ChallengeSessionModel, SecurityEventModel
from app.schemas.contracts import (
    ChallengeInitRequest,
    ChallengeInitResponse,
    InteractiveChallengeInfo,
    ChallengeVerifyRequest,
    ChallengeVerifyResponse,
    SitePolicy
)
from app.core.pow import pow_service
from app.core.privacy import privacy_protector
from app.core.jwt_service import jwt_service
from app.services.ia_client import ia_client
from app.services.policy_service import policy_service

class VerificationService:
    """
    Servicio Central de Verificación y Emisión de Credenciales Soberanas:
    Orquesta la sesión de verificación, validación de prueba de trabajo,
    consulta a inferencia de IA local y emisión asimétrica de tokens JWT EdDSA.
    """

    @classmethod
    def init_challenge(
        cls,
        db: Session,
        req: ChallengeInitRequest,
        client_ip: str
    ) -> ChallengeInitResponse:
        # 1. Validar existencia del sitio
        site = db.query(SiteModel).filter(
            SiteModel.site_key == req.site_key,
            SiteModel.active == True
        ).first()

        if not site:
            raise ValueError("El site_key proporcionado no existe o se encuentra inactivo")

        # 2. Consultar política del sitio
        policy_record = db.query(SitePolicyModel).filter(SitePolicyModel.site_id == site.site_id).first()
        policy = SitePolicy.model_validate_json(policy_record.policy_json) if policy_record else SitePolicy()

        # 3. Generar sesión y nonce para PoW
        challenge_id = str(uuid.uuid4())
        nonce, difficulty = pow_service.generate_challenge(settings.POW_DIFFICULTY)
        now = time.time()
        expires_at = now + settings.CHALLENGE_TTL_SECONDS
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Configuración de reto interactivo (preparado por si escala)
        target_angle = 135
        interactive_info = InteractiveChallengeInfo(
            required_immediately=False,
            type="spatial_alignment",
            prompt="Deslice el control hasta alinear el indicador",
            accessible_hint="Use las flechas izquierda o derecha del teclado para centrar la marca"
        )

        # 4. Guardar sesión
        session_record = ChallengeSessionModel(
            challenge_id=challenge_id,
            site_key=req.site_key,
            target_route=req.target_route,
            nonce=nonce,
            difficulty=difficulty,
            expires_at=expires_at,
            resolved=False,
            client_ip_hash=privacy_protector.anonymize_ip(client_ip),
            interactive_type="spatial_alignment",
            target_angle=target_angle,
            created_at=now_iso
        )
        db.add(session_record)
        db.commit()

        return ChallengeInitResponse(
            challenge_id=challenge_id,
            policy_mode=policy.mode,
            pow_difficulty=difficulty,
            nonce=nonce,
            expires_in_seconds=settings.CHALLENGE_TTL_SECONDS,
            interactive_challenge=interactive_info
        )

    @classmethod
    async def verify_challenge(
        cls,
        db: Session,
        req: ChallengeVerifyRequest,
        client_ip: str
    ) -> Tuple[int, ChallengeVerifyResponse]:
        """
        Verifica el reto, llama a la IA local y toma una decisión determinista.
        Retorna: (http_status_code, ChallengeVerifyResponse)
        """
        ip_hash = privacy_protector.anonymize_ip(client_ip)
        now = time.time()
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. Recuperar sesión
        session = db.query(ChallengeSessionModel).filter(
            ChallengeSessionModel.challenge_id == req.challenge_id,
            ChallengeSessionModel.site_key == req.site_key
        ).first()

        if not session:
            raise ValueError("Sesión de verificación inválida o no encontrada")

        if session.resolved:
            raise ValueError("La sesión de verificación ya fue utilizada previamente")

        if now > session.expires_at:
            raise ValueError("La sesión de verificación ha expirado")

        # 2. Validar PoW (Proof of Work)
        is_pow_valid = pow_service.verify_solution(session.nonce, req.pow_solution, session.difficulty)
        if not is_pow_valid:
            # Fallo de PoW -> bloquear inmediatamente
            cls._record_security_event(
                db, ip_hash, session.target_route, "blocked", "pow_verification_failed", 0.99
            )
            return 403, ChallengeVerifyResponse(
                challenge_id=req.challenge_id,
                status="blocked",
                risk_score=0.99,
                jwt_token=None
            )

        # 3. Consultar política del sitio
        site = db.query(SiteModel).filter(SiteModel.site_key == req.site_key).first()
        policy_record = db.query(SitePolicyModel).filter(SitePolicyModel.site_id == site.site_id).first() if site else None
        policy = SitePolicy.model_validate_json(policy_record.policy_json) if policy_record else SitePolicy()

        # 4. Chequear lista negra / blanca
        if policy_service.is_ip_blacklisted(policy, client_ip):
            cls._record_security_event(
                db, ip_hash, session.target_route, "blocked", "ip_blacklisted", 1.0
            )
            return 403, ChallengeVerifyResponse(
                challenge_id=req.challenge_id,
                status="blocked",
                risk_score=1.0,
                jwt_token=None
            )

        if policy_service.is_ip_whitelisted(policy, client_ip):
            # IP en lista blanca -> verificación automática
            token, jti, ttl = jwt_service.issue_human_token(
                site_key=req.site_key,
                risk_score=0.0,
                verification_mode="whitelisted"
            )
            session.resolved = True
            db.commit()
            cls._record_security_event(
                db, ip_hash, session.target_route, "verified", "ip_whitelisted", 0.0
            )
            return 200, ChallengeVerifyResponse(
                challenge_id=req.challenge_id,
                status="verified",
                risk_score=0.0,
                jwt_token=token,
                expires_in_seconds=ttl
            )

        # 5. Inferencia con IA local (Dev 2)
        ia_result = await ia_client.predict_telemetry(req.telemetry)
        risk_score = round(ia_result.risk_score, 2)

        challenge_min = policy.ai_thresholds.challenge_min
        block_min = policy.ai_thresholds.block_min

        # 6. Evaluación de decisión
        if risk_score >= block_min:
            # Caso C: Bot Detectado (HTTP 403)
            cls._record_security_event(
                db, ip_hash, session.target_route, "blocked", "high_bot_risk_score", risk_score
            )
            return 403, ChallengeVerifyResponse(
                challenge_id=req.challenge_id,
                status="blocked",
                risk_score=risk_score,
                jwt_token=None
            )

        elif risk_score >= challenge_min:
            # Caso B: Riesgo Medio -> Comprobar si resolvió el desafío interactivo
            if req.interactive_response and req.interactive_response.completed:
                # Reto interactivo resuelto con éxito -> emitir token
                session.resolved = True
                db.commit()
                token, jti, ttl = jwt_service.issue_human_token(
                    site_key=req.site_key,
                    risk_score=risk_score,
                    verification_mode="interactive_challenge"
                )
                cls._record_security_event(
                    db, ip_hash, session.target_route, "verified", "interactive_challenge_solved", risk_score
                )
                return 200, ChallengeVerifyResponse(
                    challenge_id=req.challenge_id,
                    status="verified",
                    risk_score=risk_score,
                    jwt_token=token,
                    expires_in_seconds=ttl
                )
            else:
                # Requiere completar reto interactivo
                interactive_challenge = InteractiveChallengeInfo(
                    required_immediately=True,
                    type="spatial_alignment",
                    target_angle=session.target_angle,
                    tolerance=8,
                    prompt="Gire el anillo hasta que la marca apunte a las 4 en punto",
                    accessible_hint="Presione Enter para avanzar en pasos de 15 grados"
                )
                cls._record_security_event(
                    db, ip_hash, session.target_route, "challenged", "medium_risk_score", risk_score
                )
                return 200, ChallengeVerifyResponse(
                    challenge_id=req.challenge_id,
                    status="challenge_required",
                    risk_score=risk_score,
                    jwt_token=None,
                    interactive_challenge=interactive_challenge
                )

        else:
            # Caso A: Humano Verificado (HTTP 200)
            session.resolved = True
            db.commit()
            token, jti, ttl = jwt_service.issue_human_token(
                site_key=req.site_key,
                risk_score=risk_score,
                verification_mode="passive"
            )
            cls._record_security_event(
                db, ip_hash, session.target_route, "verified", "human_telemetry_verified", risk_score
            )
            return 200, ChallengeVerifyResponse(
                challenge_id=req.challenge_id,
                status="verified",
                risk_score=risk_score,
                jwt_token=token,
                expires_in_seconds=ttl
            )

    @classmethod
    def _record_security_event(
        cls,
        db: Session,
        ip_hash: str,
        route: str,
        action: str,
        reason: str,
        risk_score: float
    ):
        event = SecurityEventModel(
            event_id=f"evt_{secrets.token_hex(6)}",
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ip_hash=ip_hash,
            route=route,
            action=action,
            reason=reason,
            risk_score=risk_score
        )
        db.add(event)
        db.commit()

verification_service = VerificationService()
