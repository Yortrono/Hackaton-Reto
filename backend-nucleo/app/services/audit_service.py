import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from app.db.models import AuditLogModel
from app.schemas.contracts import AuditLogItem

class AuditService:
    """
    Servicio de Auditoría Inmutable con Encadenamiento Criptográfico (Hash Chaining):
    Garantiza que toda acción administrativa quede registrada permanentemente.
    Fórmula:
      payload_hash = SHA256(json(payload))
      entry_hash = SHA256(prev_hash + payload_hash + timestamp + actor_username + action + resource)
    """

    GENESIS_HASH = "0" * 64

    @classmethod
    def record_action(
        cls,
        db: Session,
        actor_username: str,
        actor_role: str,
        action: str,
        resource: str,
        payload_details: Dict[str, Any]
    ) -> AuditLogModel:
        # 1. Obtener última entrada para enlazar el hash
        last_entry = db.query(AuditLogModel).order_by(AuditLogModel.id.desc()).first()
        prev_hash = last_entry.entry_hash if last_entry else cls.GENESIS_HASH

        # 2. Generar hash determinista del payload
        payload_str = json.dumps(payload_details, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        # 3. Timestamp UTC
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 4. Calcular entry_hash encadenado
        raw_chain_string = f"{prev_hash}|{payload_hash}|{timestamp}|{actor_username}|{actor_role}|{action}|{resource}"
        entry_hash = hashlib.sha256(raw_chain_string.encode("utf-8")).hexdigest()

        # 5. Persistir registro
        entry = AuditLogModel(
            timestamp=timestamp,
            actor_username=actor_username,
            actor_role=actor_role,
            action=action,
            resource=resource,
            payload_hash=payload_hash,
            prev_hash=prev_hash,
            entry_hash=entry_hash
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @classmethod
    def verify_chain_integrity(cls, db: Session) -> Tuple[bool, List[str]]:
        """
        Recorre todos los registros y verifica la validez matemática del encadenamiento criptográfico.
        Retorna: (is_valid, error_messages)
        """
        entries = db.query(AuditLogModel).order_by(AuditLogModel.id.asc()).all()
        if not entries:
            return True, []

        errors = []
        expected_prev_hash = cls.GENESIS_HASH

        for entry in entries:
            # Validar que prev_hash concuerde con el registro anterior
            if entry.prev_hash != expected_prev_hash:
                errors.append(
                    f"Ruptura de cadena en ID {entry.id}: prev_hash esperado {expected_prev_hash}, encontrado {entry.prev_hash}"
                )

            # Recomputar entry_hash
            raw_chain_string = f"{entry.prev_hash}|{entry.payload_hash}|{entry.timestamp}|{entry.actor_username}|{entry.actor_role}|{entry.action}|{entry.resource}"
            computed_hash = hashlib.sha256(raw_chain_string.encode("utf-8")).hexdigest()

            if computed_hash != entry.entry_hash:
                errors.append(
                    f"Manipulación detectada en ID {entry.id}: hash recalculado {computed_hash} no coincide con {entry.entry_hash}"
                )

            expected_prev_hash = entry.entry_hash

        is_valid = len(errors) == 0
        return is_valid, errors

    @classmethod
    def get_audit_logs(cls, db: Session, limit: int = 50) -> Tuple[bool, List[AuditLogItem]]:
        is_valid, _ = cls.verify_chain_integrity(db)
        entries = db.query(AuditLogModel).order_by(AuditLogModel.id.desc()).limit(limit).all()
        items = [
            AuditLogItem(
                id=e.id,
                timestamp=e.timestamp,
                actor_username=e.actor_username,
                actor_role=e.actor_role,
                action=e.action,
                resource=e.resource,
                prev_hash=e.prev_hash,
                entry_hash=e.entry_hash
            )
            for e in entries
        ]
        return is_valid, items

audit_service = AuditService()
