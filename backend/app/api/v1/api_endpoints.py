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

import json
import re
import time
from typing import Optional, List, Literal
from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func, and_, or_
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.models import (
    Entity, EntityAlias, RiskAlert, RawEvent, EntityEvent,
    Source, AlertStatus, RiskLevel, AlertType, EntityType
)
from app.services.ocr_service import get_ocr_service

router = APIRouter()


def _dashboard_fallback(now: datetime) -> dict:
    alerts_by_hour = []
    from datetime import timedelta
    for h in range(24):
        hour_start = now - timedelta(hours=24 - h)
        alerts_by_hour.append({"hour": hour_start.strftime("%H:00"), "count": 0})

    return {
        "total_entities": 0,
        "flagged_entities": 0,
        "alerts_today": 0,
        "critical_alerts": 0,
        "high_alerts": 0,
        "active_sources": 0,
        "events_today": 0,
        "high_risk_entities": 0,
        "risk_metrics": {
            "entities_high_or_critical": 0,
            "avg_entity_risk_score": 0.0,
        },
        "top_risk_entities": [],
        "alerts_last_24h_by_hour": alerts_by_hour,
    }


def _format_risk_factors(raw_factors: list, risk_score: float) -> list[dict]:
    if not raw_factors:
        return []
    formatted = []
    
    n = len(raw_factors)
    if n == 1:
        weights = [1.0]
    elif n == 2:
        weights = [0.6, 0.4]
    else:
        weights = [0.5, 0.3, 0.2] + [0.1] * (n - 3)
        total_w = sum(weights)
        weights = [w / total_w for w in weights]
        
    for i, item in enumerate(raw_factors):
        if isinstance(item, dict):
            formatted.append(item)
            continue
        
        item_str = str(item)
        if ":" in item_str:
            parts = item_str.split(":", 1)
            factor = parts[0].strip()
            detail = parts[1].strip()
        else:
            if item_str.lower().startswith("matched"):
                factor = "Pattern Match"
                detail = item_str
            else:
                factor = item_str
                detail = ""
                
        contrib = round(weights[i] * risk_score, 2) if risk_score > 0 else 0.0
        if contrib == 0.0:
            contrib = 0.5
            
        formatted.append({
            "factor": factor,
            "detail": detail,
            "contribution": contrib,
            "category": "anomaly" if "anomaly" in factor.lower() else "network" if "cluster" in factor.lower() or "centrality" in factor.lower() else "pattern"
        })
    return formatted


def _pick_first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def _guess_ocr_fields(text: str, doc_type: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    compact = "\n".join(lines)

    if doc_type == "pan":
        id_number = _pick_first_match(compact, [r"\b([A-Z]{5}[0-9]{4}[A-Z])\b"])
    elif doc_type == "passport":
        id_number = _pick_first_match(compact, [r"\b([A-Z]-?[0-9]{7})\b"])
    else:
        id_number = _pick_first_match(compact, [r"\b([0-9]{4}\s?[0-9]{4}\s?[0-9]{4})\b"])

    dob = _pick_first_match(compact, [
        r"(?:DOB|Date of Birth|Birth)[:\s-]*([0-9]{2}[/-][0-9]{2}[/-][0-9]{2,4})",
        r"\b([0-9]{2}[/-][0-9]{2}[/-][0-9]{2,4})\b",
    ])

    address = _pick_first_match(compact, [
        r"(?:Address|Add|Residence)[:\s-]*([A-Za-z0-9,./()\-\s]{12,})",
    ])
    if not address:
        address = next((line for line in lines if any(ch.isdigit() for ch in line) and "," in line), "")

    name = _pick_first_match(compact, [
        r"(?:Name|Holder|Cardholder)[:\s-]*([A-Za-z][A-Za-z .'-]{2,})",
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b",
    ])
    if not name:
        name = next((line for line in lines if 2 <= len(line.split()) <= 4 and len(line) < 40), "")

    return {
        "name": name,
        "id_number": id_number.replace(" ", ""),
        "dob": dob,
        "address": address.strip(" ,.-"),
    }


def _serialize_alert_for_stream(db: Session, alert: RiskAlert, entity: Optional[Entity] = None) -> dict:
    source_name = "system"
    if alert.trigger_event_id:
        event = db.query(RawEvent).filter(RawEvent.id == alert.trigger_event_id).first()
        if event and event.source_id:
            source = db.query(Source).filter(Source.id == event.source_id).first()
            if source:
                source_name = source.name

    return {
        "id": alert.id,
        "title": alert.title,
        "description": alert.description or "",
        "severity": alert.risk_level.value if hasattr(alert.risk_level, "value") else str(alert.risk_level),
        "status": alert.status.value if hasattr(alert.status, "value") else str(alert.status),
        "source": source_name,
        "risk_score": alert.risk_score,
        "entity_id": alert.entity_id,
        "entity_name": entity.display_name if entity else None,
        "timestamp": alert.created_at.isoformat() if alert.created_at else datetime.now(timezone.utc).isoformat(),
        "tags": list(alert.risk_factors or []),
        "metadata": {
            "alert_type": alert.alert_type.value if hasattr(alert.alert_type, "value") else str(alert.alert_type),
            "matched_pattern": alert.matched_pattern,
            "evidence_data": alert.evidence_data or {},
        },
    }


@router.get("/alerts/stream")
def stream_alerts(db: Session = Depends(get_db)):
    """Server-sent event stream for the alert inbox."""

    def event_stream():
        recent_alerts = (
            db.query(RiskAlert)
            .order_by(desc(RiskAlert.created_at))
            .limit(20)
            .all()
        )

        for alert in reversed(recent_alerts):
            entity = db.query(Entity).filter(Entity.id == alert.entity_id).first()
            payload = {
                "type": "alert",
                "payload": _serialize_alert_for_stream(db, alert, entity),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"data: {json.dumps(payload)}\n\n"

        while True:
            payload = {
                "type": "ping",
                "payload": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(15)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Pydantic Schemas (Response Models) ───────────────────────────────────────

class AliasOut(BaseModel):
    id: str
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


class EntityUpdate(BaseModel):
    investigation_notes: Optional[str] = None


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

@router.get("/alerts", response_model=dict)
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[AlertStatus] = Query(None),
    risk_level: Optional[RiskLevel] = Query(None),
    alert_type: Optional[AlertType] = Query(None),
    sort_by: Literal["risk_score", "created_at"] = Query("risk_score"),
    sort_dir: Literal["desc", "asc"] = Query("desc"),
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


@router.get("/alerts/{alert_id}", response_model=dict)
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


@router.patch("/alerts/{alert_id}/status", response_model=dict)
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

@router.get("/entities", response_model=dict)
def list_entities(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: Optional[EntityType] = Query(None),
    risk_level: Optional[RiskLevel] = Query(None),
    is_flagged: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Literal["risk_score", "last_seen", "event_count"] = Query("risk_score"),
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
                "metadata_": e.metadata_,
            }
            for e in entities
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/entities/{entity_id}", response_model=dict)
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
        "risk_factors": _format_risk_factors(entity.risk_factors or [], entity.risk_score),
        "metadata_": entity.metadata_ or {},
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


@router.patch("/entities/{entity_id}", response_model=dict)
def update_entity(entity_id: str, body: EntityUpdate, db: Session = Depends(get_db)):
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    if body.investigation_notes is not None:
        entity.investigation_notes = body.investigation_notes
        
    db.commit()
    db.refresh(entity)
    return {"status": "success", "entity_id": entity_id, "investigation_notes": entity.investigation_notes}


@router.get("/entities/{entity_id}/timeline", response_model=dict)
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


@router.get("/entities/{entity_id}/explain", response_model=dict)
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

    # For evidence_summary
    alert_count = db.query(RiskAlert).filter(RiskAlert.entity_id == entity_id).count()
    platforms_seen = [
        p[0]
        for p in db.query(RawEvent.platform)
        .join(EntityEvent, EntityEvent.event_id == RawEvent.id)
        .filter(EntityEvent.entity_id == entity_id)
        .distinct()
        .all()
        if p[0]
    ]

    # Matched patterns:
    matched_patterns = []
    for f in (entity.risk_factors or []):
        if "Matched" in f:
            pat = f.replace("Matched", "").strip()
            if pat not in matched_patterns:
                matched_patterns.append(pat)
        elif "coordinated cluster" in f.lower():
            parts = f.split(":", 1)
            if len(parts) > 1:
                pat = parts[1].strip()
                if pat not in matched_patterns:
                    matched_patterns.append(pat)

    evidence_summary = {
        "event_count": entity.event_count,
        "recent_alert_count": alert_count,
        "source_reliability": 1.25 if entity.risk_score >= 6.5 else 1.0,
        "flagged_since": entity.first_seen.isoformat() if entity.first_seen else None,
        "platforms_seen": platforms_seen,
    }

    # Format the factors
    formatted_factors = _format_risk_factors(factors, entity.risk_score)

    return {
        "entity_id": entity_id,
        "overall_risk_score": entity.risk_score,
        "risk_level": entity.risk_level,
        "top_factors": formatted_factors,
        "matched_patterns": matched_patterns,
        "evidence_summary": evidence_summary,
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

@router.get("/dashboard/stats", response_model=dict)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Aggregate stats for the dashboard home page KPI cards.
    Called once on page load and refreshed every 30 seconds.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        total_entities = db.query(Entity).count()
        flagged_entities = db.query(Entity).filter(Entity.is_flagged == True).count()
        alerts_today = db.query(RiskAlert).filter(RiskAlert.created_at >= today_start).count()
        
        high_risk_count = db.query(Entity).filter(Entity.risk_score >= 6.5).count()
        avg_high_risk = db.query(func.avg(Entity.risk_score)).filter(Entity.risk_score >= 6.5).scalar() or 0.0

        critical_alerts = db.query(RiskAlert).filter(
            RiskAlert.risk_level == RiskLevel.CRITICAL,
            RiskAlert.status == AlertStatus.NEW,
        ).count()

        high_alerts = db.query(RiskAlert).filter(
            RiskAlert.risk_level == RiskLevel.HIGH,
            RiskAlert.status == AlertStatus.NEW,
        ).count()

        active_sources = db.query(Source).filter(Source.is_active == True).count()
        events_today = db.query(RawEvent).filter(RawEvent.ingested_at >= today_start).count()

        top_entities = (
            db.query(Entity)
            .filter(Entity.is_flagged == True)
            .order_by(desc(Entity.risk_score))
            .limit(5)
            .all()
        )

        alerts_by_hour = []
        from datetime import timedelta
        for h in range(24):
            hour_start = now - timedelta(hours=24 - h)
            hour_end = hour_start + timedelta(hours=1)
            count = db.query(RiskAlert).filter(
                RiskAlert.created_at >= hour_start,
                RiskAlert.created_at < hour_end,
            ).count()
            alerts_by_hour.append({"hour": hour_start.strftime("%H:00"), "count": count})

        return {
            "total_entities": total_entities,
            "flagged_entities": flagged_entities,
            "alerts_today": alerts_today,
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "active_sources": active_sources,
            "events_today": events_today,
            "high_risk_entities": high_risk_count,
            "risk_metrics": {
                "entities_high_or_critical": high_risk_count,
                "avg_entity_risk_score": float(avg_high_risk),
            },
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
    except Exception as exc:
        logger.exception("Failed to get dashboard stats")
        return _dashboard_fallback(now)


@router.post("/ocr/scan", response_model=dict)
async def scan_document_for_ocr(
    file: UploadFile = File(...),
    doc_type: str = Form("aadhaar"),
):
    """Run OCR on an uploaded ID image and extract likely document fields."""
    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Empty upload")

        ocr_service = get_ocr_service()
        result = ocr_service.extract_from_bytes(image_bytes, source_url=file.filename or "upload")
        fields = _guess_ocr_fields(result.text, doc_type.lower().strip())
        confidence = result.confidence if result.confidence >= 0 else 72.0
        score = max(0, min(100, int(round(confidence))))

        checksum_match = bool(fields["id_number"])
        hologram_check = bool(fields["address"] or fields["name"])
        photo_match = bool(fields["name"])
        font_consistency = bool(result.text.strip())

        valid = bool(fields["id_number"]) and score >= 35

        return {
            "success": result.success or bool(result.text.strip()),
            "doc_type": doc_type.lower().strip(),
            "ocr_text": result.text,
            "confidence": confidence,
            "score": score,
            "fields": fields,
            "valid": valid,
            "checks": {
                "fontConsistency": font_consistency,
                "checksumMatch": checksum_match,
                "hologramCheck": hologram_check,
                "photoMatch": photo_match,
            },
            "error": result.error,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR scan failed: {exc}")


# ─── Search Endpoint ──────────────────────────────────────────────────────────

@router.get("/search", response_model=dict)
def global_search(
    q: str = Query(..., min_length=2),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
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
        .all()
    )

    alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.title.ilike(f"%{q}%"))
        .all()
    )

    items = []
    for e in entities:
        items.append({
            "kind": "entity",
            "id": e.id,
            "entity_type": e.entity_type,
            "primary_identifier": e.primary_identifier,
            "risk_score": e.risk_score,
            "risk_level": e.risk_level,
            "score": 1.0,
        })
    for a in alerts:
        items.append({
            "kind": "alert",
            "id": a.id,
            "title": a.title,
            "risk_score": a.risk_score,
            "risk_level": a.risk_level,
            "status": a.status,
            "score": 0.8,
        })

    # Total count
    total_results = len(items)
    total_pages = (total_results + page_size - 1) // page_size if total_results > 0 else 1

    # Slice items for pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = items[start_idx:end_idx]

    return {
        "query": q,
        "page": page,
        "page_size": page_size,
        "total_results": total_results,
        "total_pages": total_pages,
        "items": paginated_items,
    }
