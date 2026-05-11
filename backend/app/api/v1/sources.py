"""
Source monitoring — configured collectors and health.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models import RawEvent, Source, User

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: str = Field(default="other", max_length=64)
    url: str | None = None
    description: str | None = None
    tier: int = Field(default=2, ge=1, le=3, description="Reliability tier 1–3 (badge).")

    model_config = {"json_schema_extra": {"examples": [{"name": "Telegram OSINT mirror", "source_type": "telegram_public", "tier": 2}]}}


class SourceOut(BaseModel):
    id: UUID
    name: str
    source_type: str
    status: str
    last_crawl_time: datetime | None
    events_today: int
    tier: int
    reliability_badge: str
    url: str | None
    is_active: bool
    error_message: str | None

    model_config = {"from_attributes": True}


def _badge_for_tier(tier: int | None) -> str:
    t = tier or 2
    if t <= 1:
        return "Tier 1 — high reliability"
    if t == 2:
        return "Tier 2 — standard"
    return "Tier 3 — corroborate"


def _status(src: Source) -> str:
    if not src.is_active:
        return "error"
    if src.error_message:
        return "error"
    return "active"


@router.get("", response_model=list[SourceOut], summary="List configured data sources")
def list_sources(db: Session = Depends(get_db)):
    rows = db.query(Source).order_by(Source.name).all()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    out: list[SourceOut] = []
    for s in rows:
        events_today = (
            db.query(func.count(RawEvent.id))
            .filter(RawEvent.source_id == s.id, RawEvent.created_at >= today_start)
            .scalar()
            or 0
        )
        out.append(
            SourceOut(
                id=s.id,
                name=s.name,
                source_type=s.source_type,
                status=_status(s),
                last_crawl_time=s.last_crawled_at,
                events_today=int(events_today),
                tier=s.tier or 2,
                reliability_badge=_badge_for_tier(s.tier),
                url=s.url,
                is_active=bool(s.is_active),
                error_message=s.error_message,
            )
        )
    return out


@router.post("", response_model=SourceOut, status_code=status.HTTP_201_CREATED, summary="Register a data source")
def create_source(
    body: SourceCreate,
    db: Session = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or str(user.role).lower() != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can add sources")

    dup = db.query(Source).filter(Source.name == body.name).first()
    if dup:
        raise HTTPException(status_code=400, detail="Source name already exists")

    src = Source(
        name=body.name,
        source_type=body.source_type,
        url=body.url,
        description=body.description,
        tier=body.tier,
        is_active=True,
        last_crawled_at=None,
        events_today=0,
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return SourceOut(
        id=src.id,
        name=src.name,
        source_type=src.source_type,
        status=_status(src),
        last_crawl_time=src.last_crawled_at,
        events_today=0,
        tier=src.tier or 2,
        reliability_badge=_badge_for_tier(src.tier),
        url=src.url,
        is_active=bool(src.is_active),
        error_message=src.error_message,
    )
