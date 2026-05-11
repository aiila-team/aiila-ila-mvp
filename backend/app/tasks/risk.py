"""
tasks/risk.py
──────────────────────────────────────────────────────────────────────────────
Risk scoring task for the ILA Celery pipeline.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Entity, RiskAlert, AlertType, AlertStatus, RiskLevel
from app.services.risk_scorer import RiskScorer

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.score_risk_task")
def score_risk_task(entity_id: str) -> Dict[str, Any]:
    """Calculate and persist entity risk score, then create an alert if needed."""
    logger.info(f"[score_risk] Starting risk scoring for entity {entity_id}")
    db = SessionLocal()
    try:
        scorer = RiskScorer()
        result = scorer.calculate_risk_score(entity_id)

        entity = db.query(Entity).filter(Entity.id == UUID(entity_id)).first()
        if entity is None:
            raise ValueError(f"Entity {entity_id} not found in database")

        entity.risk_score = result["risk_score"]
        entity.risk_level = result["risk_level"]
        entity.risk_factors = {
            "signals": result["signals"],
            "explanation": result["explanation"],
        }
        entity.updated_at = datetime.now(timezone.utc)
        db.add(entity)

        alert_id: Optional[str] = None
        if result["risk_score"] >= settings.RISK_ALERT_THRESHOLD:
            alert = _create_or_update_risk_alert(db, entity, result)
            alert_id = str(alert.id) if alert else None

        db.commit()

        logger.info(
            f"[score_risk] Completed risk scoring for entity {entity_id} | "
            f"score={result['risk_score']:.2f} | level={result['risk_level']}"
        )

        return {
            "entity_id": entity_id,
            "risk_score": result["risk_score"],
            "risk_level": result["risk_level"],
            "alert_id": alert_id,
            "signals": result["signals"],
            "explanation": result["explanation"],
        }

    except Exception as exc:
        db.rollback()
        logger.error(f"[score_risk] Failed to score risk for entity {entity_id}: {exc}")
        raise
    finally:
        db.close()


def _create_or_update_risk_alert(db: SessionLocal, entity: Entity, result: Dict[str, Any]) -> RiskAlert:
    existing = (
        db.query(RiskAlert)
        .filter(
            RiskAlert.entity_id == entity.id,
            RiskAlert.alert_type == AlertType.ANOMALY_DETECTED,
            RiskAlert.status.in_([AlertStatus.NEW, AlertStatus.UNDER_REVIEW]),
        )
        .first()
    )

    title = (
        f"High risk entity detected: {entity.display_name or entity.primary_identifier} "
        f"({result['risk_score']:.1f}/10)"
    )
    description = (
        f"Entity {entity.primary_identifier} has a calculated risk score of "
        f"{result['risk_score']:.2f}/10. Explanation: {' '.join(result['explanation'])}"
    )

    if existing:
        if abs((existing.risk_score or 0.0) - result["risk_score"]) > 0.1:
            existing.risk_score = result["risk_score"]
            existing.risk_level = result["risk_level"]
            existing.severity = RiskLevel(result["risk_level"])
            existing.title = title
            existing.description = description
            existing.risk_factors = result["signals"]
            existing.evidence_data = {"explanation": result["explanation"]}
            existing.updated_at = datetime.now(timezone.utc)
            db.add(existing)
            logger.info(
                f"[score_risk] Updated existing risk alert for entity {entity.id} "
                f"with score {result['risk_score']:.2f}"
            )
        return existing

    alert = RiskAlert(
        entity_id=entity.id,
        alert_type=AlertType.ANOMALY_DETECTED,
        status=AlertStatus.NEW,
        severity=RiskLevel(result["risk_level"]),
        title=title,
        description=description,
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        risk_factors=result["signals"],
        evidence_data={"explanation": result["explanation"]},
    )
    db.add(alert)
    db.flush()
    logger.info(
        f"[score_risk] Created risk alert {alert.id} for entity {entity.id} "
        f"(score={result['risk_score']:.2f}, level={result['risk_level']})"
    )
    return alert
