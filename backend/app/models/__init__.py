"""
ILA — Intelligence Layer for Analytics
SQLAlchemy ORM Models (PostgreSQL)

These are the exact tables that the mock data generator will populate.
Every table here maps 1:1 to what the FastAPI endpoints serve.

Table Hierarchy:
  sources → raw_events → entities → entity_aliases
                      ↘ risk_alerts
  keywords (standalone, used by keyword matcher)
  evidence_packages (generated on demand)
  users (auth)
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime,
    ForeignKey, Text, Enum, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


# ─── Enums ────────────────────────────────────────────────────────────────────

class EntityType(str, enum.Enum):
    PERSON        = "person"
    PHONE         = "phone"
    EMAIL         = "email"
    UPI_ACCOUNT   = "upi_account"
    SOCIAL_HANDLE = "social_handle"
    TELEGRAM      = "telegram"
    WEBSITE       = "website"
    IMEI          = "imei"
    CRYPTO_WALLET = "crypto_wallet"

class AlertStatus(str, enum.Enum):
    NEW           = "new"
    UNDER_REVIEW  = "under_review"
    CONFIRMED     = "confirmed"
    DISMISSED     = "dismissed"
    ESCALATED     = "escalated"

class AlertType(str, enum.Enum):
    FINANCIAL_FRAUD         = "financial_fraud"
    COORDINATED_INAUTHENTIC = "coordinated_inauthentic"
    KEYWORD_MATCH           = "keyword_match"
    ANOMALY_DETECTED        = "anomaly_detected"
    NETWORK_CLUSTER         = "network_cluster"
    PROPAGANDA              = "propaganda"
    MILITARY_EVENT          = "military_event"
    PHISHING                = "phishing"
    SIM_SWAP                = "sim_swap"

class SourceType(str, enum.Enum):
    TELEGRAM_PUBLIC  = "telegram_public"
    TWITTER_X        = "twitter_x"
    RSS_NEWS         = "rss_news"
    DARK_WEB         = "dark_web"
    UPI_TRANSACTION  = "upi_transaction"
    SOCIAL_MEDIA     = "social_media"
    FORUM            = "forum"
    MOCK             = "mock"

class SourceTier(str, enum.Enum):
    TIER_1 = "tier_1"   # verified govt / news — multiplier 1.5
    TIER_2 = "tier_2"   # mainstream media   — multiplier 1.0
    TIER_3 = "tier_3"   # unverified social  — multiplier 0.7
    TIER_4 = "tier_4"   # dark web / anon    — multiplier 0.3

class RiskLevel(str, enum.Enum):
    LOW      = "low"       # 0–4
    MEDIUM   = "medium"    # 4–6.5
    HIGH     = "high"      # 6.5–8.5
    CRITICAL = "critical"  # 8.5–10

class Language(str, enum.Enum):
    ENGLISH  = "en"
    HINDI    = "hi"
    URDU     = "ur"
    BENGALI  = "bn"
    TAMIL    = "ta"
    TELUGU   = "te"
    MARATHI  = "mr"
    PUNJABI  = "pa"
    UNKNOWN  = "unknown"


# ─── Helper ───────────────────────────────────────────────────────────────────

def gen_uuid():
    return str(uuid.uuid4())


# ─── Tables ───────────────────────────────────────────────────────────────────

class User(Base):
    """Analyst / operator who logs in to ILA."""
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    username      = Column(String(64), unique=True, nullable=False, index=True)
    email         = Column(String(128), unique=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    full_name     = Column(String(128))
    role          = Column(String(32), default="analyst")  # analyst | specialist | commander
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    last_login    = Column(DateTime(timezone=True))

    alerts_reviewed = relationship("RiskAlert", back_populates="reviewed_by_user",
                                   foreign_keys="RiskAlert.reviewed_by")


class Source(Base):
    """
    A configured data source — RSS feed, Telegram channel, mock feed, etc.
    One source produces many raw_events.
    """
    __tablename__ = "sources"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name            = Column(String(128), nullable=False)
    source_type     = Column(Enum(SourceType), nullable=False)
    tier            = Column(Enum(SourceTier), default=SourceTier.TIER_3)
    url             = Column(String(512))
    description     = Column(Text)
    is_active       = Column(Boolean, default=True)
    reliability_multiplier = Column(Float, default=1.0)
    crawl_interval_minutes = Column(Integer, default=15)
    last_crawled_at = Column(DateTime(timezone=True))
    event_count_today = Column(Integer, default=0)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    events = relationship("RawEvent", back_populates="source")


class Keyword(Base):
    """
    Analyst-defined keywords that trigger alerts when matched in events.
    Groups of keywords map to threat categories.
    """
    __tablename__ = "keywords"

    id           = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    word         = Column(String(256), nullable=False)
    category     = Column(String(64))       # e.g. "financial_fraud", "propaganda"
    language     = Column(Enum(Language), default=Language.ENGLISH)
    is_active    = Column(Boolean, default=True)
    match_count  = Column(Integer, default=0)
    created_by   = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("word", "category", name="uq_keyword_category"),
    )


class RawEvent(Base):
    """
    A single piece of raw ingested content — one post, one transaction, one article.
    This is the rawest form of data in the system before enrichment.
    """
    __tablename__ = "raw_events"

    id                  = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    source_id           = Column(UUID(as_uuid=False), ForeignKey("sources.id"), nullable=False, index=True)
    external_id         = Column(String(256))       # original ID from source platform
    content             = Column(Text, nullable=False)
    content_language    = Column(Enum(Language), default=Language.UNKNOWN)
    translated_content  = Column(Text)              # English translation if not English
    url                 = Column(String(1024))
    author_handle       = Column(String(256))       # @username or phone or "unknown"
    platform            = Column(String(64))        # "telegram", "twitter", "rss", etc.
    published_at        = Column(DateTime(timezone=True))
    ingested_at         = Column(DateTime(timezone=True), server_default=func.now())

    # Enrichment results (populated by Celery pipeline)
    is_processed        = Column(Boolean, default=False)
    is_duplicate        = Column(Boolean, default=False)
    duplicate_of        = Column(UUID(as_uuid=False), ForeignKey("raw_events.id"))
    extracted_entities  = Column(JSONB, default=list)   # [{type, value, confidence}]
    sentiment_score     = Column(Float)                 # -1.0 to +1.0
    anomaly_score       = Column(Float)                 # 0.0 to 1.0
    matched_keywords    = Column(JSONB, default=list)   # [keyword_id, ...]
    minhash_signature   = Column(JSONB)                 # for dedup
    metadata_           = Column("metadata", JSONB, default=dict)  # source-specific extras

    # Full-text search vector (auto-updated via trigger in production)
    search_vector       = Column(TSVECTOR)

    source   = relationship("Source", back_populates="events")
    entity_links = relationship("EntityEvent", back_populates="event")

    __table_args__ = (
        Index("ix_raw_events_published_at", "published_at"),
        Index("ix_raw_events_platform", "platform"),
        Index("ix_raw_events_is_processed", "is_processed"),
    )


class Entity(Base):
    """
    A resolved, deduplicated entity — a real-world person, account, or identifier.
    One entity can have many aliases across platforms (EntityAlias).
    This is the central concept in ILA — everything connects here.
    """
    __tablename__ = "entities"

    id                  = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    entity_type         = Column(Enum(EntityType), nullable=False, index=True)
    primary_identifier  = Column(String(512), nullable=False)  # the "canonical" ID
    display_name        = Column(String(256))
    risk_score          = Column(Float, default=0.0, index=True)
    risk_level          = Column(Enum(RiskLevel), default=RiskLevel.LOW, index=True)
    influence_score     = Column(Float, default=0.0)    # Neo4j PageRank
    anomaly_score       = Column(Float, default=0.0)
    sentiment_avg       = Column(Float, default=0.0)    # avg across all events
    event_count         = Column(Integer, default=0)
    first_seen          = Column(DateTime(timezone=True), server_default=func.now())
    last_seen           = Column(DateTime(timezone=True), server_default=func.now())
    is_flagged          = Column(Boolean, default=False, index=True)
    investigation_notes = Column(Text)
    risk_factors        = Column(JSONB, default=list)   # top-3 contributing factors
    metadata_           = Column("metadata", JSONB, default=dict)

    aliases     = relationship("EntityAlias", back_populates="entity", cascade="all, delete-orphan")
    events      = relationship("EntityEvent", back_populates="entity")
    alerts      = relationship("RiskAlert", back_populates="entity")

    __table_args__ = (
        Index("ix_entities_risk_score", "risk_score"),
        Index("ix_entities_primary_identifier", "primary_identifier"),
    )


class EntityAlias(Base):
    """
    All known identifiers for an entity across platforms.
    e.g. Entity "Raju Kumar" → Phone +91-9876543210 + @raju_t (Telegram) + raju@gmail.com
    """
    __tablename__ = "entity_aliases"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    entity_id       = Column(UUID(as_uuid=False), ForeignKey("entities.id"), nullable=False, index=True)
    alias_type      = Column(Enum(EntityType), nullable=False)
    alias_value     = Column(String(512), nullable=False)
    platform        = Column(String(64))
    confidence      = Column(Float, default=1.0)    # 0.0–1.0 how sure we are this links
    resolution_method = Column(String(64))          # "exact", "fuzzy", "manual", "graph"
    first_seen      = Column(DateTime(timezone=True), server_default=func.now())
    is_verified     = Column(Boolean, default=False)

    entity = relationship("Entity", back_populates="aliases")

    __table_args__ = (
        UniqueConstraint("entity_id", "alias_value", name="uq_entity_alias"),
        Index("ix_entity_aliases_value", "alias_value"),
    )


class EntityEvent(Base):
    """
    Many-to-many link between Entity and RawEvent.
    An event can mention multiple entities; an entity appears in many events.
    """
    __tablename__ = "entity_events"

    id         = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    entity_id  = Column(UUID(as_uuid=False), ForeignKey("entities.id"), nullable=False, index=True)
    event_id   = Column(UUID(as_uuid=False), ForeignKey("raw_events.id"), nullable=False, index=True)
    role       = Column(String(64), default="mentioned")  # "author", "mentioned", "recipient"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    entity = relationship("Entity", back_populates="events")
    event  = relationship("RawEvent", back_populates="entity_links")

    __table_args__ = (
        UniqueConstraint("entity_id", "event_id", name="uq_entity_event"),
    )


class RiskAlert(Base):
    """
    A scored, analyst-facing alert surfaced by the intelligence pipeline.
    This is what appears in the Alert Inbox.
    """
    __tablename__ = "risk_alerts"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    entity_id       = Column(UUID(as_uuid=False), ForeignKey("entities.id"), nullable=False, index=True)
    alert_type      = Column(Enum(AlertType), nullable=False, index=True)
    title           = Column(String(512), nullable=False)
    description     = Column(Text)
    risk_score      = Column(Float, nullable=False, index=True)
    risk_level      = Column(Enum(RiskLevel), nullable=False, index=True)
    status          = Column(Enum(AlertStatus), default=AlertStatus.NEW, index=True)
    trigger_event_id = Column(UUID(as_uuid=False), ForeignKey("raw_events.id"))
    matched_pattern = Column(String(256))           # e.g. "Fraud Template #3"
    risk_factors    = Column(JSONB, default=list)   # top-3 reasons
    evidence_data   = Column(JSONB, default=dict)   # raw facts supporting the alert
    reviewed_by     = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    reviewed_at     = Column(DateTime(timezone=True))
    analyst_note    = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    entity            = relationship("Entity", back_populates="alerts")
    reviewed_by_user  = relationship("User", back_populates="alerts_reviewed",
                                     foreign_keys=[reviewed_by])

    __table_args__ = (
        Index("ix_risk_alerts_created_at", "created_at"),
        Index("ix_risk_alerts_risk_score_status", "risk_score", "status"),
    )


class EvidencePackage(Base):
    """
    A generated PDF evidence package for a specific entity / investigation.
    Created on-demand when analyst clicks "Export Evidence".
    """
    __tablename__ = "evidence_packages"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    entity_id       = Column(UUID(as_uuid=False), ForeignKey("entities.id"), index=True)
    generated_by    = Column(UUID(as_uuid=False), ForeignKey("users.id"))
    case_id         = Column(String(64), unique=True)   # human-readable: ILA-2026-00042
    file_path       = Column(String(512))
    entities_included = Column(JSONB, default=list)     # list of entity_ids in this package
    events_count    = Column(Integer, default=0)
    analyst_note    = Column(Text)
    legal_disclaimer = Column(Text)
    generated_at    = Column(DateTime(timezone=True), server_default=func.now())
    expires_at      = Column(DateTime(timezone=True))   # auto-delete after retention period
