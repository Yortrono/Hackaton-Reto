from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import SecurityEventModel
from app.schemas.contracts import (
    ObservabilitySummaryResponse,
    TrafficStats,
    SecurityEventItem
)
from app.core.security import require_role
from app.services.ia_client import ia_client

router = APIRouter()

@router.get(
    "/admin/observability/summary",
    response_model=ObservabilitySummaryResponse,
    summary="Resumen de Observabilidad en Tiempo Real",
    description="Agrega contadores locales de eventos de seguridad con métricas de inferencia del módulo IA conductual (Dev 2)."
)
async def get_observability_summary(
    current_admin: dict = Depends(require_role(["security_admin", "operator", "auditor"])),
    db: Session = Depends(get_db)
):
    # Obtener eventos recientes
    recent_db_events = db.query(SecurityEventModel).order_by(SecurityEventModel.id.desc()).limit(20).all()

    # Calcular contadores
    total_events = db.query(SecurityEventModel).count()
    verified_count = db.query(SecurityEventModel).filter(SecurityEventModel.action == "verified").count()
    challenged_count = db.query(SecurityEventModel).filter(SecurityEventModel.action == "challenged").count()
    blocked_count = db.query(SecurityEventModel).filter(SecurityEventModel.action == "blocked").count()
    rate_limited_count = db.query(SecurityEventModel).filter(SecurityEventModel.action == "rate_limited").count()

    human_pct = round((verified_count / total_events * 100), 2) if total_events > 0 else 100.0

    traffic_stats = TrafficStats(
        total_requests=total_events,
        verified_humans=verified_count,
        interactive_challenges_solved=challenged_count,
        bots_blocked=blocked_count,
        ddos_rate_limited=rate_limited_count,
        human_percentage=human_pct
    )

    # Métricas de IA
    ai_perf = await ia_client.get_ia_metrics()

    # Eventos de seguridad para visualización
    event_items = [
        SecurityEventItem(
            event_id=e.event_id,
            timestamp=e.timestamp,
            ip_hash=e.ip_hash,
            route=e.route,
            action=e.action,
            reason=e.reason,
            risk_score=e.risk_score
        )
        for e in recent_db_events
    ]

    return ObservabilitySummaryResponse(
        window="last_60_minutes",
        traffic_stats=traffic_stats,
        ai_performance=ai_perf,
        recent_security_events=event_items
    )
