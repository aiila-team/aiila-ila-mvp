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
from enum import Enum
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text, JSON, Index, UniqueConstraint,
    ForeignKey, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


# Utility function for generating UUIDs
def gen_uuid():
    return uuid.uuid4()


# ─────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────

class EntityType(str, Enum):
    PERSON = "person"
    PHONE = "phone"
    EMAIL = "email"
    TELEGRAM = "telegram"
    SOCIAL_HANDLE = "social_handle"
    UPI_ACCOUNT = "upi_account"
    IMEI = "imei"
    CRYPTO_WALLET = "crypto_wallet"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EVENT = "event"
    OTHER = "other"


class SourceType(str, Enum):
    TELEGRAM_PUBLIC = "telegram_public"
    UPI_TRANSACTION = "upi_transaction"
    TWITTER_X = "twitter_x"
    RSS_NEWS = "rss_news"
    DARK_WEB = "dark_web"
    OTHER = "other"


class Language(str, Enum):
    EN = "en"
    HI = "hi"
    UR = "ur"
    BN = "bn"
    TA = "ta"
    TE = "te"
    MR = "mr"
    PA = "pa"
    UNKNOWN = "unknown"


class AlertStatus(str, Enum):
    NEW = "new"
    INVESTIGATING = "investigating"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

AlertSeverity = RiskLevel


class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    USER = "user"


class AlertType(str, Enum):
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    MALICIOUS_INTENT = "malicious_intent"
    DATA_LEAK = "data_leak"
    FINANCIAL_FRAUD = "financial_fraud"
    COORDINATED_INAUTHENTIC = "coordinated_inauthentic"
    KEYWORD_MATCH = "keyword_match"
    ANOMALY_DETECTED = "anomaly_detected"
    NETWORK_CLUSTER = "network_cluster"
    PROPAGANDA = "propaganda"
    OTHER = "other"


# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # e.g., 'social_media', 'news', 'intelligence'
    tier = Column(Integer, default=2)
    url = Column(String)
    description = Column(Text)
    credibility_score = Column(Float, default=0.5)
    reliability_multiplier = Column(Float, default=1.0)
    last_crawled_at = Column(DateTime(timezone=True))
    events_today = Column(Integer, default=0)
    error_message = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    raw_events = relationship("RawEvent", back_populates="source")


class RawEvent(Base):
    __tablename__ = "raw_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"))
    external_id = Column(String)
    content = Column(Text, nullable=False)
    content_language = Column(String, default="unknown")
    translated_content = Column(Text)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    published_at = Column(DateTime(timezone=True))
    url = Column(String)
    author_handle = Column(String)
    platform = Column(String)
    metadata_ = Column("metadata", JSON)
    is_processed = Column(Boolean, default=False)
    extracted_entities = Column(JSON)  # JSONB in PostgreSQL
    matched_keywords = Column(JSON)
    sentiment_score = Column(Float)
    anomaly_score = Column(Float)
    content_hash = Column(String)  # For deduplication
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(UUID(as_uuid=True), ForeignKey("raw_events.id"), nullable=True)
    minhash_signature = Column(JSON)  # MinHash vector for LSH deduplication
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source = relationship("Source", back_populates="raw_events")
    entity_events = relationship("EntityEvent", back_populates="event", cascade="all, delete-orphan")
    entities = relationship(
        "Entity",
        secondary="entity_events",
        back_populates="raw_events",
        viewonly=True,
    )
    risk_alerts = relationship("RiskAlert", back_populates="raw_event")


class Entity(Base):
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(SQLEnum(EntityType, native_enum=False), nullable=False)
    primary_identifier = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(SQLEnum(RiskLevel, native_enum=False), default=RiskLevel.LOW)
    influence_score = Column(Float, default=0.0)
    anomaly_score = Column(Float, default=0.0)
    sentiment_avg = Column(Float, default=0.0)
    event_count = Column(Integer, default=0)
    first_seen = Column(DateTime(timezone=True))
    last_seen = Column(DateTime(timezone=True))
    is_flagged = Column(Boolean, default=False)
    investigation_notes = Column(Text)
    risk_factors = Column(JSON)
    description = Column(Text)
    metadata_ = Column("metadata", JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    aliases = relationship("EntityAlias", back_populates="entity")
    entity_events = relationship("EntityEvent", back_populates="entity", cascade="all, delete-orphan")
    raw_events = relationship(
        "RawEvent",
        secondary="entity_events",
        back_populates="entities",
        viewonly=True,
    )
    risk_alerts = relationship("RiskAlert", back_populates="entity")

    __table_args__ = (
        Index('idx_entity_type', 'entity_type'),
        Index('idx_entity_risk_score', 'risk_score'),
        UniqueConstraint('entity_type', 'primary_identifier', name='uq_entity_type_identifier'),
    )


class EntityAlias(Base):
    __tablename__ = "entity_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"))
    alias_type = Column(String, nullable=False)  # e.g., 'phone', 'email', 'telegram'
    alias_value = Column(String, nullable=False)
    platform = Column(String)  # e.g., 'telegram', 'twitter'
    confidence = Column(Float, default=1.0)
    resolution_method = Column(String, default="exact")
    is_verified = Column(Boolean, default=False)
    metadata_ = Column("metadata", JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    entity = relationship("Entity", back_populates="aliases")

    __table_args__ = (
        Index('idx_alias_value', 'alias_value'),
        UniqueConstraint('entity_id', 'alias_type', 'alias_value', name='uq_entity_alias'),
    )


class EntityEvent(Base):
    __tablename__ = "entity_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"))
    event_id = Column(UUID(as_uuid=True), ForeignKey("raw_events.id"))
    relevance_score = Column(Float, default=1.0)
    role = Column(String, default="mentioned")
    context = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    entity = relationship("Entity", back_populates="entity_events")
    event = relationship("RawEvent", back_populates="entity_events")


class RiskAlert(Base):
    __tablename__ = "risk_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"))
    event_id = Column(UUID(as_uuid=True), ForeignKey("raw_events.id"))
    alert_type = Column(SQLEnum(AlertType, native_enum=False), nullable=False)
    status = Column(SQLEnum(AlertStatus, native_enum=False), default=AlertStatus.NEW)
    severity = Column(SQLEnum(RiskLevel, native_enum=False), default=RiskLevel.LOW)
    title = Column(String, nullable=False)
    description = Column(Text)
    risk_score = Column(Float)
    risk_level = Column(SQLEnum(RiskLevel, native_enum=False))
    trigger_event_id = Column(UUID(as_uuid=True))
    matched_pattern = Column(String)
    risk_factors = Column(JSON)
    evidence_data = Column(JSON)
    reviewed_by = Column(UUID(as_uuid=True))
    reviewed_at = Column(DateTime(timezone=True))
    analyst_note = Column(Text)
    evidence = Column(JSON)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (Index("idx_risk_alerts_created_at", "created_at"),)

    # Relationships
    entity = relationship("Entity", back_populates="risk_alerts")
    raw_event = relationship("RawEvent", back_populates="risk_alerts")
    assignee = relationship("User")
    status_history = relationship(
        "AlertStatusHistory", back_populates="alert", cascade="all, delete-orphan"
    )


class AlertStatusHistory(Base):
    """Audit trail for PATCH /alerts/{id}/status workflow transitions."""

    __tablename__ = "alert_status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("risk_alerts.id"), nullable=False)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    analyst_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    analyst_note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    alert = relationship("RiskAlert", back_populates="status_history")


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    word = Column(String, nullable=False, unique=True)
    category = Column(String)
    language = Column(String, default="en")
    risk_weight = Column(Float, default=1.0)
    match_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EvidencePackage(Base):
    __tablename__ = "evidence_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("risk_alerts.id"), nullable=True)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True)
    analyst_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    case_id = Column(String, nullable=True)
    title = Column(String, nullable=False)
    content = Column(JSON)
    included_entity_ids = Column(JSON)
    case_metadata = Column(JSON)
    file_path = Column(String)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False, default="Investigation")
    status = Column(String, nullable=False, default="open")
    analyst_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes = Column(Text)
    entity_ids = Column(JSON, default=list)
    evidence_package_id = Column(UUID(as_uuid=True), ForeignKey("evidence_packages.id"), nullable=True)
    metadata_ = Column("metadata", JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Import User from user.py
from .user import User