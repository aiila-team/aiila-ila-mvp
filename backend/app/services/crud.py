"""
ILA — CRUD Services
Reusable DB operations for entities, alerts, and sources.
Generated with Claude assistance — reviewed by Likhitha
"""

from uuid import UUID
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_

from app.models import Entity, EntityAlias, RiskAlert, Source, AlertStatus, RiskLevel


# ─────────────────────────────────────────
# ENTITY CRUD
# ─────────────────────────────────────────

def get_entity(db: Session, entity_id: UUID) -> Optional[Entity]:
    return db.query(Entity).filter(Entity.id == entity_id).first()


def get_entities(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    entity_type: Optional[str] = None,
    min_risk_score: Optional[float] = None,
    is_flagged: Optional[bool] = None,
) -> list[Entity]:
    query = db.query(Entity)
    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)
    if min_risk_score is not None:
        query = query.filter(Entity.risk_score >= min_risk_score)
    if is_flagged is not None:
        query = query.filter(Entity.is_flagged == is_flagged)
    return query.order_by(desc(Entity.risk_score)).offset(skip).limit(limit).all()


def get_entity_by_identifier(db: Session, identifier: str) -> Optional[Entity]:
    """Find entity by primary identifier or any alias."""
    entity = db.query(Entity).filter(
        Entity.primary_identifier == identifier
    ).first()
    if not entity:
        alias = db.query(EntityAlias).filter(
            EntityAlias.alias_value == identifier
        ).first()
        if alias:
            entity = alias.entity
    return entity


def create_entity(db: Session, data: dict) -> Entity:
    entity = Entity(**data)
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def update_entity_risk_score(db: Session, entity_id: UUID, risk_score: float) -> Optional[Entity]:
    entity = get_entity(db, entity_id)
    if entity:
        entity.risk_score = risk_score
        entity.last_seen_at = datetime.utcnow()
        if risk_score >= 6.5:
            entity.is_flagged = True
        db.commit()
        db.refresh(entity)
    return entity


def add_entity_alias(db: Session, entity_id: UUID, alias_type: str, alias_value: str, confidence: float = 1.0) -> EntityAlias:
    alias = EntityAlias(
        entity_id=entity_id,
        alias_type=alias_type,
        alias_value=alias_value,
        confidence=confidence,
    )
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return alias


def get_entity_aliases(db: Session, entity_id: UUID) -> list[EntityAlias]:
    return db.query(EntityAlias).filter(EntityAlias.entity_id == entity_id).all()


# ─────────────────────────────────────────
# ALERT CRUD
# ─────────────────────────────────────────

def get_alert(db: Session, alert_id: UUID) -> Optional[RiskAlert]:
    return db.query(RiskAlert).filter(RiskAlert.id == alert_id).first()


def get_alerts(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    min_risk_score: Optional[float] = None,
    sort_by: str = "risk_score",
    sort_order: str = "desc",
) -> list[RiskAlert]:
    query = db.query(RiskAlert)

    if status:
        query = query.filter(RiskAlert.status == status)
    if severity:
        query = query.filter(RiskAlert.severity == severity)
    if min_risk_score is not None:
        query = query.filter(RiskAlert.risk_score >= min_risk_score)

    sort_col = getattr(RiskAlert, sort_by, RiskAlert.risk_score)
    query = query.order_by(desc(sort_col) if sort_order == "desc" else asc(sort_col))

    return query.offset(skip).limit(limit).all()


def create_alert(db: Session, data: dict) -> RiskAlert:
    alert = RiskAlert(**data)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def update_alert_status(
    db: Session,
    alert_id: UUID,
    new_status: AlertStatus,
    reviewed_by: Optional[UUID] = None,
) -> Optional[RiskAlert]:
    alert = get_alert(db, alert_id)
    if alert:
        alert.status = new_status
        if reviewed_by:
            alert.reviewed_by = reviewed_by
            alert.reviewed_at = datetime.utcnow()
        db.commit()
        db.refresh(alert)
    return alert


def get_alerts_for_entity(db: Session, entity_id: UUID) -> list[RiskAlert]:
    return (
        db.query(RiskAlert)
        .filter(RiskAlert.entity_id == entity_id)
        .order_by(desc(RiskAlert.created_at))
        .all()
    )


# ─────────────────────────────────────────
# SOURCE CRUD
# ─────────────────────────────────────────

def get_source(db: Session, source_id: UUID) -> Optional[Source]:
    return db.query(Source).filter(Source.id == source_id).first()


def get_sources(db: Session, active_only: bool = False) -> list[Source]:
    query = db.query(Source)
    if active_only:
        query = query.filter(Source.is_active == True)
    return query.all()


def create_source(db: Session, data: dict) -> Source:
    source = Source(**data)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def update_source_crawl_status(
    db: Session,
    source_id: UUID,
    error_message: Optional[str] = None,
    events_count: int = 0,
) -> Optional[Source]:
    source = get_source(db, source_id)
    if source:
        source.last_crawled_at = datetime.utcnow()
        source.events_today = (source.events_today or 0) + events_count
        source.error_message = error_message
        db.commit()
        db.refresh(source)
    return source