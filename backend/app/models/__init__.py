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

from app.db.session import Base


# ─────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────

class EntityType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EVENT = "event"
    OTHER = "other"


class AlertStatus(str, Enum):
    NEW = "new"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
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
    OTHER = "other"


# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # e.g., 'social_media', 'news', 'intelligence'
    url = Column(String)
    credibility_score = Column(Float, default=0.5)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    raw_events = relationship("RawEvent", back_populates="source")


class RawEvent(Base):
    __tablename__ = "raw_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"))
    content = Column(Text, nullable=False)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    metadata_ = Column("metadata", JSON)
    processed = Column(Boolean, default=False)
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
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    primary_identifier = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    risk_score = Column(Float, default=0.0)
    risk_level = Column(SQLEnum(RiskLevel), default=RiskLevel.LOW)
    is_flagged = Column(Boolean, default=False)
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
    alias_type = Column(String, nullable=False)  # e.g., 'username', 'email', 'phone'
    alias_value = Column(String, nullable=False)
    platform = Column(String)  # e.g., 'twitter', 'facebook'
    confidence = Column(Float, default=1.0)
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
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.NEW)
    severity = Column(SQLEnum(RiskLevel), default=RiskLevel.LOW)
    title = Column(String, nullable=False)
    description = Column(Text)
    evidence = Column(JSON)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    entity = relationship("Entity", back_populates="risk_alerts")
    raw_event = relationship("RawEvent", back_populates="risk_alerts")
    assignee = relationship("User")


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword = Column(String, nullable=False, unique=True)
    category = Column(String)
    risk_weight = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EvidencePackage(Base):
    __tablename__ = "evidence_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("risk_alerts.id"))
    title = Column(String, nullable=False)
    content = Column(JSON)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())


# Import User from user.py
from .user import User