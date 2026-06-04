from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models import EvidencePackage, Investigation, gen_uuid

router = APIRouter(prefix="/investigations", tags=["investigations"])


class InvestigationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    notes: str | None = None
    entity_ids: list[UUID] = Field(default_factory=list)
    evidence_package_id: UUID | None = None
    case_metadata: dict[str, Any] | None = None


class InvestigationOut(BaseModel):
    id: UUID
    title: str
    status: str
    analyst_id: UUID | None
    notes: str | None
    entity_ids: list[str]
    evidence_package_id: UUID | None
    case_metadata: dict[str, Any] | None
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


@router.post("", response_model=InvestigationOut, status_code=status.HTTP_201_CREATED)
def create_investigation(body: InvestigationCreate, db: Session = Depends(get_db), analyst_id: UUID = Depends(get_current_user_id)):
    if body.evidence_package_id:
        pkg = db.query(EvidencePackage).filter(EvidencePackage.id == body.evidence_package_id).first()
        if not pkg:
            raise HTTPException(status_code=404, detail="Evidence package not found")

    inv = Investigation(
        id=gen_uuid(),
        title=body.title,
        status="open",
        analyst_id=analyst_id,
        notes=body.notes,
        entity_ids=[str(x) for x in body.entity_ids],
        evidence_package_id=body.evidence_package_id,
        metadata_=body.case_metadata,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return _serialize(inv)


@router.get("", response_model=list[InvestigationOut])
def list_investigations(db: Session = Depends(get_db), _: UUID = Depends(get_current_user_id)):
    invs = db.query(Investigation).order_by(Investigation.created_at.desc()).all()
    return [_serialize(x) for x in invs]


@router.get("/{investigation_id}", response_model=InvestigationOut)
def get_investigation(investigation_id: UUID, db: Session = Depends(get_db), _: UUID = Depends(get_current_user_id)):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return _serialize(inv)


class InvestigationUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    status: str | None = None
    entity_ids: list[UUID] | None = None
    evidence_package_id: UUID | None = None
    case_metadata: dict[str, Any] | None = None


@router.put("/{investigation_id}", response_model=InvestigationOut)
def update_investigation(
    investigation_id: UUID,
    body: InvestigationUpdate,
    db: Session = Depends(get_db),
    _: UUID = Depends(get_current_user_id)
):
    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    if body.title is not None:
        inv.title = body.title
    if body.notes is not None:
        inv.notes = body.notes
    if body.status is not None:
        inv.status = body.status
    if body.entity_ids is not None:
        inv.entity_ids = [str(x) for x in body.entity_ids]
    if body.evidence_package_id is not None:
        inv.evidence_package_id = body.evidence_package_id
    if body.case_metadata is not None:
        inv.metadata_ = body.case_metadata

    db.commit()
    db.refresh(inv)
    return _serialize(inv)


def _serialize(inv: Investigation) -> InvestigationOut:
    return InvestigationOut(
        id=inv.id,
        title=inv.title,
        status=inv.status,
        analyst_id=inv.analyst_id,
        notes=inv.notes,
        entity_ids=list(inv.entity_ids or []),
        evidence_package_id=inv.evidence_package_id,
        case_metadata=inv.metadata_,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
    )
