import pytest
from app.db.database import get_db_context
from app.db.models import AuditLogModel
from app.services.audit_service import audit_service
from app.db.init_db import init_database

@pytest.fixture(autouse=True)
def setup_db():
    init_database()

def test_audit_log_hash_chaining_validity():
    with get_db_context() as db:
        # Registrar tres acciones
        e1 = audit_service.record_action(
            db=db,
            actor_username="admin_seguridad",
            actor_role="security_admin",
            action="TEST_ACTION_1",
            resource="test:resource_1",
            payload_details={"val": 1}
        )

        e2 = audit_service.record_action(
            db=db,
            actor_username="operador_politicas",
            actor_role="operator",
            action="TEST_ACTION_2",
            resource="test:resource_2",
            payload_details={"val": 2}
        )

        assert e2.prev_hash == e1.entry_hash

        # Validar integridad matemática de toda la cadena
        is_valid, errors = audit_service.verify_chain_integrity(db)
        assert is_valid is True
        assert len(errors) == 0

def test_audit_chain_tamper_detection():
    with get_db_context() as db:
        # Manipular una entrada existente en la base de datos
        entry = db.query(AuditLogModel).order_by(AuditLogModel.id.desc()).first()
        assert entry is not None
        original_resource = entry.resource
        entry.resource = "manipulacion_maliciosa"
        db.commit()

        # Al verificar la integridad de la cadena, DEBE detectar la ruptura
        is_valid, errors = audit_service.verify_chain_integrity(db)
        assert is_valid is False
        assert len(errors) > 0
        assert any("Manipulación detectada" in err for err in errors)

        # Restaurar para no afectar otras pruebas
        entry.resource = original_resource
        db.commit()
