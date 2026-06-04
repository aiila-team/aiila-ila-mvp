from __future__ import annotations

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
    source_type: str = Field(default="mock", max_length=64)
    url: str | None = None
    description: str | None = None
    tier: int = Field(default=2, ge=1, le=4)


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


def _normalize_tier(tier: int | str | None) -> int:
    if tier is None:
        return 2
    if isinstance(tier, int):
        return max(1, min(tier, 4))
    text = str(tier).strip().lower()
    if text in {"tier_1", "tier1", "1"}:
        return 1
    if text in {"tier_2", "tier2", "2"}:
        return 2
    if text in {"tier_3", "tier3", "3"}:
        return 3
    return 4


def _badge_for_tier(tier: int | str | None) -> str:
    value = _normalize_tier(tier)
    return {
        1: "Tier 1 — high reliability",
        2: "Tier 2 — standard",
        3: "Tier 3 — corroborate",
        4: "Tier 4 — low trust",
    }[value]


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    rows = db.query(Source).order_by(Source.name).all()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    for s in rows:
        events_today = (
            db.query(func.count(RawEvent.id))
            .filter(RawEvent.source_id == s.id, RawEvent.ingested_at >= today_start)
            .scalar()
            or 0
        )
        out.append(
            SourceOut(
                id=s.id,
                name=s.name,
                source_type=str(s.source_type),
                status="active" if s.is_active else "error",
                last_crawl_time=s.last_crawled_at,
                events_today=int(events_today),
                tier=_normalize_tier(s.tier),
                reliability_badge=_badge_for_tier(s.tier),
                url=s.url,
                is_active=bool(s.is_active),
                error_message=s.error_message,
            )
        )
    return out


@router.post("", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
def create_source(body: SourceCreate, db: Session = Depends(get_db), user_id: UUID = Depends(get_current_user_id)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user or str(user.role).lower() != "admin":
        raise HTTPException(status_code=403, detail="Only administrators can add sources")

    if db.query(Source).filter(Source.name == body.name).first():
        raise HTTPException(status_code=400, detail="Source name already exists")

    src = Source(
        name=body.name,
        source_type=body.source_type,
        url=body.url,
        description=body.description,
        tier=f"TIER_{_normalize_tier(body.tier)}",
        is_active=True,
        last_crawled_at=None,
        event_count_today=0,
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return SourceOut(
        id=src.id,
        name=src.name,
        source_type=str(src.source_type),
        status="active",
        last_crawl_time=src.last_crawled_at,
        events_today=0,
        tier=_normalize_tier(src.tier),
        reliability_badge=_badge_for_tier(src.tier),
        url=src.url,
        is_active=bool(src.is_active),
        error_message=src.error_message,
    )
