from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import evidence_dir_path
from app.core.security import get_current_user_id
from app.db.session import get_db
from app.models import EvidencePackage, Entity, gen_uuid
from app.services.evidence_generator import render_evidence_pdf

router = APIRouter(prefix="/evidence", tags=["evidence"])


class EvidenceCreateRequest(BaseModel):
    entity_id: UUID
    investigation_note: str = Field(min_length=1, max_length=20000)
    case_id: str | None = Field(default=None, max_length=256)


class EvidenceCreateResponse(BaseModel):
    evidence_package_id: UUID
    download_url: str
    generated_at: datetime


@router.get("/files/{filename}")
def download_evidence_file(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = evidence_dir_path() / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.post("", response_model=EvidenceCreateResponse, status_code=status.HTTP_201_CREATED)
def create_evidence_package(body: EvidenceCreateRequest, db: Session = Depends(get_db), analyst_id: UUID = Depends(get_current_user_id)):
    ent = db.query(Entity).filter(Entity.id == body.entity_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found")

    case_id = body.case_id or f"CASE-{str(body.entity_id)[:8].upper()}"
    existing = db.query(EvidencePackage).filter(EvidencePackage.case_id == case_id).first()
    if existing:
        return EvidenceCreateResponse(
            evidence_package_id=existing.id,
            download_url=f"/api/v1/evidence/files/{existing.id}.pdf",
            generated_at=existing.generated_at,
        )

    pdf_bytes = render_evidence_pdf(db, str(body.entity_id), body.investigation_note, case_id=case_id)
    pkg_id = gen_uuid()
    fname = f"{pkg_id}.pdf"
    out_path = evidence_dir_path() / fname
    out_path.write_bytes(pdf_bytes)

    pkg = EvidencePackage(
        id=pkg_id,
        entity_id=body.entity_id,
        generated_by=analyst_id,
        case_id=case_id,
        file_path=str(out_path.resolve()),
        entities_included=[str(body.entity_id)],
        events_count=0,
        analyst_note=body.investigation_note,
        legal_disclaimer="Generated for internal use.",
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return EvidenceCreateResponse(evidence_package_id=pkg.id, download_url=f"/api/v1/evidence/files/{pkg_id}.pdf", generated_at=datetime.now(timezone.utc))
