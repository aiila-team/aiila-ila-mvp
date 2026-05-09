"""
ILA — FastAPI Endpoints
app/api/v1/entities.py + alerts.py combined into one reference file

These are the actual HTTP endpoints your React frontend will call.
Each endpoint queries PostgreSQL using SQLAlchemy and returns
the data you loaded with the mock data scripts.

Endpoints in this file:
  GET  /api/v1/alerts                  — Alert inbox (paginated, filtered)
  GET  /api/v1/alerts/{id}             — Single alert with entity detail
  PATCH /api/v1/alerts/{id}/status     — Update alert status
  GET  /api/v1/entities                — Entity list
  GET  /api/v1/entities/{id}           — Entity profile (with aliases + risk factors)
  GET  /api/v1/entities/{id}/timeline  — Events mentioning this entity
  GET  /api/v1/entities/{id}/explain   — Top-3 risk factors (explainability)
  GET  /api/v1/dashboard/stats         — KPI cards for dashboard home
"""

from uuid import UUID
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, and_, or_
from pydantic import BaseModel

from app.db.session import get_db
from app.models import (
    Entity, EntityAlias, RiskAlert, RawEvent, EntityEvent,
    Source, AlertStatus, RiskLevel, AlertType
)

alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])
entities_router = APIRouter(prefix="/entities", tags=["entities"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])
search_router = APIRouter(prefix="/search", tags=["search"])


# ─── Pydantic Schemas (Response Models) ───────────────────────────────────────

class AliasOut(BaseModel):
    id: UUID
    alias_type: str
    alias_value: str
    platform: Optional[str]
    confidence: float
    is_verified: bool

    class Config:
        from_attributes = True


class EntitySummary(BaseModel):
    id: str
    entity_type: str
    primary_identifier: str
    display_name: Optional[str]
    risk_score: float
    risk_level: str
    is_flagged: bool
    event_count: int
    last_seen: Optional[datetime]

    class Config:
        from_attributes = True


class EntityDetail(BaseModel):
    id: str
    entity_type: str
    primary_identifier: str
    display_name: Optional[str]
    risk_score: float
    risk_level: str
    influence_score: float
    anomaly_score: float
    sentiment_avg: float
    event_count: int
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
    is_flagged: bool
    investigation_notes: Optional[str]
    risk_factors: List[str]
    aliases: List[AliasOut]
    metadata_: Optional[dict]

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: str
    entity_id: str
    alert_type: str
    title: str
    description: Optional[str]
    risk_score: float
    risk_level: str
    status: str
    matched_pattern: Optional[str]
    risk_factors: List[str]
    evidence_data: Optional[dict]
    created_at: datetime
    entity: Optional[EntitySummary]

    class Config:
        from_attributes = True


class AlertStatusUpdate(BaseModel):
    status: AlertStatus
    analyst_note: Optional[str] = None


class EventOut(BaseModel):
    id: str
    content: str
    content_language: str
    platform: str
    author_handle: Optional[str]
    sentiment_score: Optional[float]
    published_at: Optional[datetime]
    url: Optional[str]
    extracted_entities: List[dict]

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_entities: int
    flagged_entities: int
    alerts_today: int
    critical_alerts: int
    high_alerts: int
    active_sources: int
    events_today: int
    top_risk_entities: List[EntitySummary]
    alerts_last_24h_by_hour: List[dict]


# ─── Alert Endpoints ──────────────────────────────────────────────────────────

@alerts_router.get("", response_model=dict)
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    sort_by: str = Query("risk_score"),      # risk_score | created_at
    sort_dir: str = Query("desc"),           # desc | asc
    db: Session = Depends(get_db),
):
    """
    Alert inbox — the main screen analysts see first.
    Supports pagination, filtering, and sorting.

    Example calls:
      GET /api/v1/alerts                              # all alerts, sorted by risk
      GET /api/v1/alerts?status=new                  # only new alerts
      GET /api/v1/alerts?risk_level=critical          # only critical
      GET /api/v1/alerts?sort_by=created_at&sort_dir=desc  # most recent first
    """
    query = db.query(RiskAlert).join(Entity, RiskAlert.entity_id == Entity.id)

    # Filtering
    if status:
        query = query.filter(RiskAlert.status == status)
    if risk_level:
        query = query.filter(RiskAlert.risk_level == risk_level)
    if alert_type:
        query = query.filter(RiskAlert.alert_type == alert_type)

    # Sorting
    sort_col = RiskAlert.risk_score if sort_by == "risk_score" else RiskAlert.created_at
    query = query.order_by(desc(sort_col) if sort_dir == "desc" else asc(sort_col))

    # Pagination
    total = query.count()
    alerts = query.offset((page - 1) * page_size).limit(page_size).all()

    # Build response manually to avoid lazy-load issues
    items = []
    for alert in alerts:
        entity = db.query(Entity).filter(Entity.id == alert.entity_id).first()
        items.append({
            "id": alert.id,
            "entity_id": alert.entity_id,
            "alert_type": alert.alert_type,
            "title": alert.title,
            "description": alert.description,
            "risk_score": alert.risk_score,
            "risk_level": alert.risk_level,
            "status": alert.status,
            "matched_pattern": alert.matched_pattern,
            "risk_factors": alert.risk_factors or [],
            "evidence_data": alert.evidence_data or {},
            "created_at": alert.created_at,
            "entity": {
                "id": entity.id,
                "entity_type": entity.entity_type,
                "primary_identifier": entity.primary_identifier,
                "display_name": entity.display_name,
                "risk_score": entity.risk_score,
                "risk_level": entity.risk_level,
                "is_flagged": entity.is_flagged,
                "event_count": entity.event_count,
                "last_seen": entity.last_seen,
            } if entity else None,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@alerts_router.get("/{alert_id}", response_model=dict)
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """Single alert with full entity detail."""
    alert = db.query(RiskAlert).filter(RiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    entity = db.query(Entity).filter(Entity.id == alert.entity_id).first()
    aliases = db.query(EntityAlias).filter(EntityAlias.entity_id == entity.id).all() if entity else []

    return {
        "alert": {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "title": alert.title,
            "description": alert.description,
            "risk_score": alert.risk_score,
            "risk_level": alert.risk_level,
            "status": alert.status,
            "matched_pattern": alert.matched_pattern,
            "risk_factors": alert.risk_factors or [],
            "evidence_data": alert.evidence_data or {},
            "analyst_note": alert.analyst_note,
            "created_at": alert.created_at,
            "reviewed_at": alert.reviewed_at,
        },
        "entity": {
            "id": entity.id,
            "entity_type": entity.entity_type,
            "primary_identifier": entity.primary_identifier,
            "display_name": entity.display_name,
            "risk_score": entity.risk_score,
            "risk_level": entity.risk_level,
            "is_flagged": entity.is_flagged,
            "event_count": entity.event_count,
            "first_seen": entity.first_seen,
            "last_seen": entity.last_seen,
            "risk_factors": entity.risk_factors or [],
            "aliases": [
                {
                    "id": a.id,
                    "alias_type": a.alias_type,
                    "alias_value": a.alias_value,
                    "platform": a.platform,
                    "confidence": a.confidence,
                    "is_verified": a.is_verified,
                }
                for a in aliases
            ],
        } if entity else None,
    }


@alerts_router.patch("/{alert_id}/status", response_model=dict)
def update_alert_status(
    alert_id: str,
    update: AlertStatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Update alert status in the analyst workflow:
      new → under_review → confirmed | dismissed

    Also records analyst note and timestamp.
    """
    alert = db.query(RiskAlert).filter(RiskAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = update.status
    if update.analyst_note:
        alert.analyst_note = update.analyst_note
    if update.status in [AlertStatus.CONFIRMED, AlertStatus.DISMISSED]:
        alert.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(alert)
    return {"id": alert.id, "status": alert.status, "updated_at": datetime.now(timezone.utc)}


# ─── Entity Endpoints ─────────────────────────────────────────────────────────

@entities_router.get("", response_model=dict)
def list_entities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    is_flagged: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("risk_score"),
    db: Session = Depends(get_db),
):
    """
    Entity list with filtering. Used by entity browser page.

    Example calls:
      GET /api/v1/entities?entity_type=person&is_flagged=true
      GET /api/v1/entities?search=+91987
      GET /api/v1/entities?risk_level=critical
    """
    query = db.query(Entity)

    if entity_type:
        query = query.filter(Entity.entity_type == entity_type)
    if risk_level:
        query = query.filter(Entity.risk_level == risk_level)
    if is_flagged is not None:
        query = query.filter(Entity.is_flagged == is_flagged)
    if search:
        query = query.filter(
            or_(
                Entity.primary_identifier.ilike(f"%{search}%"),
                Entity.display_name.ilike(f"%{search}%"),
            )
        )

    sort_col = {
        "risk_score": Entity.risk_score,
        "last_seen": Entity.last_seen,
        "event_count": Entity.event_count,
    }.get(sort_by, Entity.risk_score)
    query = query.order_by(desc(sort_col))

    total = query.count()
    entities = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [
            {
                "id": e.id,
                "entity_type": e.entity_type,
                "primary_identifier": e.primary_identifier,
                "display_name": e.display_name,
                "risk_score": e.risk_score,
                "risk_level": e.risk_level,
                "is_flagged": e.is_flagged,
                "event_count": e.event_count,
                "last_seen": e.last_seen,
            }
            for e in entities
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@entities_router.get("/{entity_id}", response_model=dict)
def get_entity_profile(entity_id: str, db: Session = Depends(get_db)):
    """
    Full entity profile — the detail page an analyst sees when investigating.
    Returns: entity + all aliases + risk factors + alert count.
    """
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    aliases = db.query(EntityAlias).filter(EntityAlias.entity_id == entity_id).all()
    alert_count = db.query(RiskAlert).filter(RiskAlert.entity_id == entity_id).count()

    return {
        "id": entity.id,
        "entity_type": entity.entity_type,
        "primary_identifier": entity.primary_identifier,
        "display_name": entity.display_name,
        "risk_score": entity.risk_score,
        "risk_level": entity.risk_level,
        "influence_score": entity.influence_score,
        "anomaly_score": entity.anomaly_score,
        "sentiment_avg": entity.sentiment_avg,
        "event_count": entity.event_count,
        "alert_count": alert_count,
        "first_seen": entity.first_seen,
        "last_seen": entity.last_seen,
        "is_flagged": entity.is_flagged,
        "investigation_notes": entity.investigation_notes,
        "risk_factors": entity.risk_factors or [],
        "metadata": entity.metadata_ or {},
        "aliases": [
            {
                "id": a.id,
                "alias_type": a.alias_type,
                "alias_value": a.alias_value,
                "platform": a.platform,
                "confidence": a.confidence,
                "resolution_method": a.resolution_method,
                "is_verified": a.is_verified,
                "first_seen": a.first_seen,
            }
            for a in aliases
        ],
    }


@entities_router.get("/{entity_id}/timeline", response_model=dict)
def get_entity_timeline(
    entity_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Chronological list of events mentioning this entity.
    Powers the "Source Timeline" panel on the entity profile page.
    """
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Join through entity_events → raw_events
    query = (
        db.query(RawEvent)
        .join(EntityEvent, EntityEvent.event_id == RawEvent.id)
        .filter(EntityEvent.entity_id == entity_id)
        .order_by(desc(RawEvent.published_at))
    )
    total = query.count()
    events = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "entity_id": entity_id,
        "items": [
            {
                "id": e.id,
                "content": e.content[:300] + "..." if len(e.content) > 300 else e.content,
                "platform": e.platform,
                "author_handle": e.author_handle,
                "content_language": e.content_language,
                "sentiment_score": e.sentiment_score,
                "published_at": e.published_at,
                "url": e.url,
                "extracted_entities": e.extracted_entities or [],
            }
            for e in events
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@entities_router.get("/{entity_id}/explain", response_model=dict)
def explain_entity_risk(entity_id: str, db: Session = Depends(get_db)):
    """
    ML Explainability endpoint — returns the top risk factors for an entity.
    This is the "why was this flagged?" panel in the UI.

    Returns structured breakdown of each contributing factor with score.
    """
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    # Build explainability breakdown
    factors = entity.risk_factors or []

    # Compute sub-scores for the breakdown gauge
    sub_scores = {
        "anomaly_detection": round(entity.anomaly_score * 10, 2),
        "pattern_match":     round((entity.risk_score / 10.0) * 2.5, 2),
        "network_centrality": round(entity.influence_score * 10, 2),
        "sentiment_signal":  round(abs(entity.sentiment_avg) * 10, 2),
        "activity_velocity": round(min(entity.event_count / 200.0, 1.0) * 10, 2),
    }

    return {
        "entity_id": entity_id,
        "overall_risk_score": entity.risk_score,
        "risk_level": entity.risk_level,
        "top_factors": factors,
        "score_breakdown": sub_scores,
        "formula": "risk = (anomaly×0.30 + pattern×0.25 + centrality×0.20 + velocity×0.15 + sentiment×0.10) × source_multiplier",
        "data_points": {
            "total_events_analyzed": entity.event_count,
            "first_seen": entity.first_seen,
            "last_seen": entity.last_seen,
            "avg_sentiment": entity.sentiment_avg,
            "anomaly_score": entity.anomaly_score,
        }
    }


# ─── Dashboard Endpoint ───────────────────────────────────────────────────────

@dashboard_router.get("/stats", response_model=dict)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Aggregate stats for the dashboard home page KPI cards.
    Called once on page load and refreshed every 30 seconds.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_entities  = db.query(Entity).count()
    flagged_entities = db.query(Entity).filter(Entity.is_flagged == True).count()
    alerts_today    = db.query(RiskAlert).filter(RiskAlert.created_at >= today_start).count()
    
    # ── FIXED: Using Enums instead of strings ──
    critical_alerts = db.query(RiskAlert).filter(
        RiskAlert.risk_level == RiskLevel.CRITICAL,
        RiskAlert.status == AlertStatus.NEW
    ).count()
    
    high_alerts = db.query(RiskAlert).filter(
        RiskAlert.risk_level == RiskLevel.HIGH,
        RiskAlert.status == AlertStatus.NEW
    ).count()
    
    active_sources  = db.query(Source).filter(Source.is_active == True).count()
    events_today    = db.query(RawEvent).filter(RawEvent.ingested_at >= today_start).count()

    # Top 5 highest-risk entities
    top_entities = (
        db.query(Entity)
        .filter(Entity.is_flagged == True)
        .order_by(desc(Entity.risk_score))
        .limit(5)
        .all()
    )

    # Alerts per hour for last 24h (for sparkline chart)
    # Simplified: just return mock hourly distribution
    # In production: use a proper time-bucket query
    alerts_by_hour = []
    from datetime import timedelta
    for h in range(24):
        hour_start = now - timedelta(hours=24 - h)
        hour_end = hour_start + timedelta(hours=1)
        count = db.query(RiskAlert).filter(
            RiskAlert.created_at >= hour_start,
            RiskAlert.created_at < hour_end
        ).count()
        alerts_by_hour.append({
            "hour": hour_start.strftime("%H:00"),
            "count": count,
        })

    return {
        "total_entities": total_entities,
        "flagged_entities": flagged_entities,
        "alerts_today": alerts_today,
        "critical_alerts": critical_alerts,
        "high_alerts": high_alerts,
        "active_sources": active_sources,
        "events_today": events_today,
        "top_risk_entities": [
            {
                "id": e.id,
                "entity_type": e.entity_type,
                "primary_identifier": e.primary_identifier,
                "display_name": e.display_name,
                "risk_score": e.risk_score,
                "risk_level": e.risk_level,
                "is_flagged": e.is_flagged,
                "event_count": e.event_count,
                "last_seen": e.last_seen,
            }
            for e in top_entities
        ],
        "alerts_last_24h_by_hour": alerts_by_hour,
    }


# ─── Search Endpoint ──────────────────────────────────────────────────────────

@search_router.get("", response_model=dict)
def global_search(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
):
    """
    Global search across entities and alerts.
    Matches on: entity identifier, display name, alias values, alert title.

    Example: GET /api/v1/search?q=+91987654
    """
    entities = (
        db.query(Entity)
        .join(EntityAlias, EntityAlias.entity_id == Entity.id, isouter=True)
        .filter(
            or_(
                Entity.primary_identifier.ilike(f"%{q}%"),
                Entity.display_name.ilike(f"%{q}%"),
                EntityAlias.alias_value.ilike(f"%{q}%"),
            )
        )
        .distinct()
        .limit(10)
        .all()
    )

    alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.title.ilike(f"%{q}%"))
        .limit(5)
        .all()
    )

    return {
        "query": q,
        "entities": [
            {
                "id": e.id,
                "entity_type": e.entity_type,
                "primary_identifier": e.primary_identifier,
                "risk_score": e.risk_score,
                "risk_level": e.risk_level,
            }
            for e in entities
        ],
        "alerts": [
            {
                "id": a.id,
                "title": a.title,
                "risk_score": a.risk_score,
                "status": a.status,
            }
            for a in alerts
        ],
        "total_results": len(entities) + len(alerts),
    }
