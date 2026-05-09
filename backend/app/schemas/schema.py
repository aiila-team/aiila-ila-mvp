"""
ILA — Pydantic Schemas
Request/response models for all API endpoints.
Generated with Claude assistance — reviewed by Likhitha
"""

from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator

from app.models import EntityType, AlertStatus, AlertSeverity, UserRole


# ─────────────────────────────────────────
# AUTH SCHEMAS
# ─────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# ENTITY SCHEMAS
# ─────────────────────────────────────────

class AliasOut(BaseModel):
    id: UUID
    alias_type: str
    alias_value: str
    confidence: float
    model_config = {"from_attributes": True}

class EntityOut(BaseModel):
    id: UUID
    entity_type: EntityType
    primary_identifier: str
    display_name: str
    risk_score: float
    risk_level: AlertSeverity
    is_flagged: bool
    aliases: List[AliasOut] = []
    model_config = {"from_attributes": True}

class EntityListOut(BaseModel):
    items: list[EntityOut]
    total: int
    skip: int
    limit: int


# ─────────────────────────────────────────
# ALERT SCHEMAS
# ─────────────────────────────────────────

class AlertOut(BaseModel):
    id: UUID
    entity_id: UUID
    alert_type: str
    severity: AlertSeverity
    status: AlertStatus
    risk_score: float
    title: str
    description: Optional[str]
    risk_factors: Optional[list]
    created_at: datetime
    reviewed_at: Optional[datetime]
    model_config = {"from_attributes": True}

class AlertListOut(BaseModel):
    items: list[AlertOut]
    total: int
    skip: int
    limit: int

class AlertStatusUpdate(BaseModel):
    status: AlertStatus


# ─────────────────────────────────────────
# SOURCE SCHEMAS
# ─────────────────────────────────────────

class SourceCreate(BaseModel):
    name: str
    source_type: str
    url: Optional[str] = None
    tier: int = 2

class SourceOut(BaseModel):
    id: UUID
    name: str
    source_type: str
    url: Optional[str]
    tier: int
    reliability_multiplier: float
    is_active: bool
    last_crawled_at: Optional[datetime]
    events_today: int
    error_message: Optional[str]
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# DASHBOARD SCHEMAS
# ─────────────────────────────────────────

class DashboardStats(BaseModel):
    total_entities: int
    flagged_entities: int
    alerts_today: int
    high_risk_alerts: int
    active_sources: int
    top_risk_entities: list[EntityOut]


# ─────────────────────────────────────────
# EVIDENCE SCHEMAS
# ─────────────────────────────────────────

class EvidenceRequest(BaseModel):
    entity_id: UUID
    investigation_note: Optional[str] = ""

class EvidenceOut(BaseModel):
    id: UUID
    entity_id: UUID
    case_id: Optional[str]
    pdf_path: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────
# ERROR SCHEMA (consistent error responses)
# ─────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None