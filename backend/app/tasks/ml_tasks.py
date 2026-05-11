# Generated with Claude assistance — reviewed by Mythresh
"""
tasks/ml_tasks.py
──────────────────────────────────────────────────────────────────────────────
Celery ML Task Wrappers — ILA Day 3

This file wraps every ML service call in a Celery task so:
  - Inference runs asynchronously, off the main enrich pipeline thread
  - CPU-heavy work (IndicBERT, Isolation Forest) runs on dedicated ML workers
  - Results are written back to PostgreSQL after inference

Tasks defined here:
  sentiment_task(event_id)         → update raw_events.sentiment_score
  anomaly_task(entity_id)          → update entities.anomaly_score
  score_risk_task(entity_id)       → full composite risk score + alert creation
  backfill_sentiment_task(limit)   → bulk backfill missing sentiment scores
  backfill_risk_scores_task()      → bulk re-score all entities (e.g. after model update)

Worker routing:
  These tasks are CPU/memory heavy. In production (Week 2), route them to a
  separate 'ml' Celery queue on a larger instance:

  celery_app.config_from_object with:
    task_routes = {
        "tasks.ml_tasks.*": {"queue": "ml"},
    }

  For MVP, all tasks run on the default queue — fine for t3.medium.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import (
    RawEvent,
    Entity,
    EntityAlias,
    EntityType,
    RiskAlert,
    AlertType,
    AlertStatus,
    RiskLevel,
    gen_uuid,
)
from app.services.sentiment import analyze_sentiment, analyze_sentiment_batch
from app.services.anomaly_detector import detect_anomaly
from app.services.pattern_matcher import score_entity, RiskScoreResult

logger = get_task_logger(__name__)

# Risk alert creation threshold — mirrors enrich.py
RISK_ALERT_THRESHOLD = 6.5


# ═════════════════════════════════════════════════════════════════════════════
# SENTIMENT TASK
# ═════════════════════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    name="tasks.ml_tasks.sentiment_task",
    max_retries=2,
    default_retry_delay=20,
    acks_late=True,
    time_limit=120,
    soft_time_limit=90,
)
def sentiment_task(self, event_id: str) -> dict:
    """
    Async sentiment analysis for a single raw event.

    Reads:  raw_events.content
    Writes: raw_events.sentiment_score  (Float -1.0 to +1.0)

    Triggered by:
      - enrich.py (inline, synchronous path) — only dispatches this task
        when event is from a slow/large source and latency is acceptable.
      - backfill_sentiment_task (bulk path)

    Returns:
        {"event_id": ..., "sentiment_score": ..., "success": bool}
    """
    logger.info(f"[sentiment_task] START event_id={event_id}")

    db: Session = SessionLocal()
    try:
        event: Optional[RawEvent] = db.get(RawEvent, event_id)
        if event is None:
            logger.warning(f"[sentiment_task] Event {event_id} not found.")
            return {"event_id": event_id, "success": False, "error": "not_found"}

        if not event.content:
            return {"event_id": event_id, "success": False, "error": "empty_content"}

        # Run inference
        score: float = analyze_sentiment(event.content)
        event.sentiment_score = score
        db.commit()

        logger.info(f"[sentiment_task] DONE event_id={event_id} | score={score}")
        return {"event_id": event_id, "sentiment_score": score, "success": True}

    except Exception as exc:
        logger.error(f"[sentiment_task] FAILED event_id={event_id}: {exc}")
        raise self.retry(exc=exc, countdown=20)
    finally:
        db.close()


# ═════════════════════════════════════════════════════════════════════════════
# ANOMALY TASK
# ═════════════════════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    name="tasks.ml_tasks.anomaly_task",
    max_retries=2,
    default_retry_delay=15,
    acks_late=True,
    time_limit=60,
)
def anomaly_task(self, entity_id: str) -> dict:
    """
    Compute and persist the anomaly score for an entity.

    Builds the feature dict from the entity's recent event statistics,
    runs Isolation Forest, and writes the result back.

    Reads:  entities + entity_events + raw_events (for feature extraction)
    Writes: entities.anomaly_score

    Returns:
        {"entity_id": ..., "anomaly_score": ..., "success": bool}
    """
    logger.info(f"[anomaly_task] START entity_id={entity_id}")

    db: Session = SessionLocal()
    try:
        entity: Optional[Entity] = db.get(Entity, entity_id)
        if entity is None:
            return {"entity_id": entity_id, "success": False, "error": "not_found"}

        # Build feature dict from entity's recent activity
        features = _build_entity_features(db, entity)

        score: float = detect_anomaly(features)
        entity.anomaly_score = score
        db.commit()

        logger.info(
            f"[anomaly_task] DONE entity_id={entity_id} | "
            f"anomaly_score={score} | features={features}"
        )
        return {"entity_id": entity_id, "anomaly_score": score, "success": True}

    except Exception as exc:
        logger.error(f"[anomaly_task] FAILED entity_id={entity_id}: {exc}")
        raise self.retry(exc=exc, countdown=15)
    finally:
        db.close()


# ═════════════════════════════════════════════════════════════════════════════
# COMPOSITE RISK SCORE TASK
# ═════════════════════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    name="tasks.ml_tasks.score_risk_task",
    max_retries=3,
    default_retry_delay=20,
    acks_late=True,
    time_limit=180,
    soft_time_limit=150,
)
def score_risk_task(self, entity_id: str) -> dict:
    """
    Compute the full composite risk score for an entity and:
      1. Update entities.risk_score, risk_level, risk_factors
      2. Create a RiskAlert if score >= RISK_ALERT_THRESHOLD

    This is the Day 3 central scoring task.
    Called by enrich.py after entity resolution + anomaly_task completes.

    Pipeline position:
      enrich_event_task
        → resolve_entity_task
          → anomaly_task  (parallel)
          → sentiment_task (parallel)
            → score_risk_task  ← THIS TASK

    Returns:
        Full risk score result dict.
    """
    logger.info(f"[score_risk_task] START entity_id={entity_id}")

    db: Session = SessionLocal()
    try:
        entity: Optional[Entity] = db.get(Entity, entity_id)
        if entity is None:
            return {"entity_id": entity_id, "success": False, "error": "not_found"}

        # Gather all inputs for the composite scorer
        features = _build_entity_features(db, entity)

        # Get the source reliability multiplier from the entity's most recent event
        source_reliability = _get_source_reliability(db, entity)

        # Check entity aliases for type-based pattern flags
        aliases = list(entity.aliases or [])
        has_crypto = any(
            a.alias_type in (EntityType.CRYPTO_WALLET,) for a in aliases
        )
        has_upi = any(
            a.alias_type in (EntityType.UPI_ACCOUNT,) for a in aliases
        )

        # Run composite scorer
        result: RiskScoreResult = score_entity(
            anomaly_score=float(entity.anomaly_score or 0.0),
            sentiment_score=float(entity.sentiment_avg or 0.0),
            network_centrality=float(entity.influence_score or 0.0),
            source_reliability=source_reliability,
            features=features,
            entity_type=entity.entity_type,
            has_crypto_alias=has_crypto,
            has_upi_alias=has_upi,
        )

        # ── Write back to entity ──────────────────────────────────────────────
        entity.risk_score   = result.final_score
        entity.risk_level   = result.risk_level
        entity.risk_factors = result.top_factors

        # Flag entity if high/critical
        if result.final_score >= RISK_ALERT_THRESHOLD:
            entity.is_flagged = True

        # ── Create risk alert if threshold exceeded ───────────────────────────
        alert_id = None
        if result.final_score >= RISK_ALERT_THRESHOLD:
            alert_id = _create_or_update_risk_alert(db, entity, result)

        db.commit()

        logger.info(
            f"[score_risk_task] DONE entity_id={entity_id} | "
            f"score={result.final_score} | level={result.risk_level} | "
            f"matched_patterns={[t['id'] for t in result.matched_templates]} | "
            f"alert_created={alert_id is not None}"
        )

        return {
            "entity_id":        entity_id,
            "risk_score":       result.final_score,
            "risk_level":       result.risk_level,
            "component_scores": result.component_scores,
            "matched_templates":[t["id"] for t in result.matched_templates],
            "alert_id":         alert_id,
            "success":          True,
        }

    except Exception as exc:
        logger.error(f"[score_risk_task] FAILED entity_id={entity_id}: {exc}")
        raise self.retry(exc=exc, countdown=20)
    finally:
        db.close()


# ═════════════════════════════════════════════════════════════════════════════
# BULK BACKFILL TASKS
# ═════════════════════════════════════════════════════════════════════════════

@celery_app.task(
    name="tasks.ml_tasks.backfill_sentiment_task",
    acks_late=True,
    time_limit=600,
)
def backfill_sentiment_task(limit: int = 200) -> dict:
    """
    Backfill sentiment scores for events that are processed but have no score yet.
    Uses batch inference for efficiency.

    Triggered by: Celery Beat every 30 minutes (beat_schedule.py)
      "backfill-sentiment": {
          "task": "tasks.ml_tasks.backfill_sentiment_task",
          "schedule": crontab(minute="*/30"),
      }
    """
    db: Session = SessionLocal()
    try:
        # Find events with no sentiment score yet
        events = (
            db.query(RawEvent)
            .filter(
                RawEvent.is_processed == True,
                RawEvent.is_duplicate == False,
                RawEvent.sentiment_score.is_(None),
                RawEvent.content.isnot(None),
            )
            .limit(limit)
            .all()
        )

        if not events:
            logger.debug("[backfill_sentiment] No events to backfill.")
            return {"processed": 0}

        texts = [e.content for e in events]
        scores = analyze_sentiment_batch(texts)

        for event, score in zip(events, scores):
            event.sentiment_score = score

        db.commit()
        logger.info(f"[backfill_sentiment] Backfilled {len(events)} sentiment scores.")
        return {"processed": len(events)}

    except Exception as exc:
        logger.error(f"[backfill_sentiment] Error: {exc}")
        return {"processed": 0, "error": str(exc)}
    finally:
        db.close()


@celery_app.task(
    name="tasks.ml_tasks.backfill_risk_scores_task",
    acks_late=True,
    time_limit=3600,
)
def backfill_risk_scores_task(limit: int = 500) -> dict:
    """
    Re-score all entities. Run after a model update or threshold change.
    Dispatches individual score_risk_task per entity for parallel processing.
    """
    from celery import group

    db: Session = SessionLocal()
    try:
        entity_ids = [
            str(row.id)
            for row in db.query(Entity.id).limit(limit).all()
        ]
    finally:
        db.close()

    if not entity_ids:
        return {"dispatched": 0}

    job = group(score_risk_task.s(eid) for eid in entity_ids)
    job.apply_async()

    logger.info(f"[backfill_risk_scores] Dispatched {len(entity_ids)} score tasks.")
    return {"dispatched": len(entity_ids)}


# ═════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _build_entity_features(db: Session, entity: Entity) -> dict:
    """
    Build the feature dict for anomaly detection and risk scoring
    from the entity's recent raw_events activity.

    For MVP we query the last 1 hour of entity_events → raw_events.
    Phase 2: use a pre-computed feature store (Redis).
    """
    from datetime import timedelta
    from sqlalchemy import func as sqlfunc
    from app.models import EntityEvent

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    # Count events in last 1 hour
    recent_event_count = (
        db.query(sqlfunc.count(EntityEvent.id))
        .join(RawEvent, RawEvent.id == EntityEvent.event_id)
        .filter(
            EntityEvent.entity_id == str(entity.id),
            RawEvent.ingested_at >= one_hour_ago,
        )
        .scalar()
        or 0
    )

    # Average sentiment across all events for this entity
    from sqlalchemy import select
    avg_sentiment = (
        db.query(sqlfunc.avg(RawEvent.sentiment_score))
        .join(EntityEvent, EntityEvent.event_id == RawEvent.id)
        .filter(EntityEvent.entity_id == str(entity.id))
        .scalar()
        or 0.0
    )

    # Update entity sentiment average (side effect — fine here)
    entity.sentiment_avg = round(float(avg_sentiment), 4)

    # Feature dict
    # For MVP: transaction_count_1h ≈ recent_event_count for financial entities
    # post_frequency_1h ≈ recent_event_count for social entities
    is_financial = entity.entity_type in (
        EntityType.UPI_ACCOUNT, EntityType.PHONE, EntityType.CRYPTO_WALLET
    )
    is_social = entity.entity_type in (
        EntityType.SOCIAL_HANDLE, EntityType.TELEGRAM
    )

    features: dict = {
        "transaction_count_1h": recent_event_count if is_financial else 0,
        "post_frequency_1h":    recent_event_count if is_social    else 0,
        "unique_recipients_1h": 0,   # Phase 2: compute from transaction graph
        "avg_amount_deviation": 0.0, # Phase 2: compute from transaction amounts
        "unique_platforms_1h":  1,   # Phase 2: count distinct platforms
        "keyword_hit_rate":     0.0, # Phase 2: fraction of events with keyword hits
        "reply_ratio":          0.0, # Phase 2: from social platform metadata
    }

    return features


def _get_source_reliability(db: Session, entity: Entity) -> float:
    """
    Get the source reliability multiplier for an entity's most recent event.
    Falls back to 1.0 (tier-2 default) if no source found.
    """
    from app.models import EntityEvent, Source

    latest_link = (
        db.query(EntityEvent)
        .join(RawEvent, RawEvent.id == EntityEvent.event_id)
        .filter(EntityEvent.entity_id == str(entity.id))
        .order_by(RawEvent.ingested_at.desc())
        .first()
    )

    if latest_link is None:
        return 1.0

    latest_event = db.get(RawEvent, latest_link.event_id)
    if latest_event is None:
        return 1.0

    source = db.get(Source, latest_event.source_id)
    if source is None:
        return 1.0

    return float(source.reliability_multiplier or 1.0)


def _create_or_update_risk_alert(
    db: Session,
    entity: Entity,
    result: RiskScoreResult,
) -> Optional[str]:
    """
    Create a new RiskAlert or update an existing open one.
    Returns the alert UUID string, or None on failure.
    """
    # Check for existing open alert
    existing = (
        db.query(RiskAlert)
        .filter(
            RiskAlert.entity_id == str(entity.id),
            RiskAlert.status.in_([AlertStatus.NEW, AlertStatus.UNDER_REVIEW]),
            RiskAlert.alert_type == AlertType.ANOMALY_DETECTED,
        )
        .first()
    )

    if existing:
        existing.risk_score  = result.final_score
        existing.risk_level  = result.risk_level
        existing.risk_factors = result.top_factors
        existing.updated_at  = datetime.now(timezone.utc)
        db.flush()
        return str(existing.id)

    # Determine alert type — prefer the matched pattern's alert_type if any
    alert_type_str = (
        result.matched_templates[0]["alert_type"]
        if result.matched_templates
        else "anomaly_detected"
    )
    try:
        alert_type = AlertType(alert_type_str)
    except ValueError:
        alert_type = AlertType.ANOMALY_DETECTED

    matched_names = ", ".join(
        t["name"] for t in result.matched_templates[:2]
    ) if result.matched_templates else "composite score threshold"

    alert = RiskAlert(
        id=gen_uuid(),
        entity_id=str(entity.id),
        alert_type=alert_type,
        title=(
            f"Risk score {result.final_score:.1f}/10 — "
            f"{entity.display_name or entity.primary_identifier} "
            f"({entity.entity_type})"
        ),
        description=(
            f"Composite risk score {result.final_score:.2f} exceeds threshold "
            f"{RISK_ALERT_THRESHOLD}. Triggered by: {matched_names}."
        ),
        risk_score=result.final_score,
        risk_level=result.risk_level,
        status=AlertStatus.NEW,
        matched_pattern=matched_names,
        risk_factors=result.top_factors,
        evidence_data={
            "component_scores":  result.component_scores,
            "matched_templates": [t["id"] for t in result.matched_templates],
        },
    )

    try:
        db.add(alert)
        db.flush()
        return str(alert.id)
    except Exception as exc:
        logger.warning(f"Failed to create risk alert for entity {entity.id}: {exc}")
        return None
