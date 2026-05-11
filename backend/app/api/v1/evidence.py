"""
POST /api/v1/evidence — generate PDF evidence package and persist metadata.
"""

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


@router.get("/files/{filename}", summary="Download a generated evidence PDF")
def download_evidence_file(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF downloads are supported")
    path = evidence_dir_path() / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)


class EvidenceCreateRequest(BaseModel):
    """Request body to generate an evidence PDF for one entity."""

    entity_id: UUID = Field(description="Primary entity this package focuses on.")
    investigation_note: str = Field(
        min_length=1,
        max_length=20000,
        description="Analyst narrative included in the PDF.",
        json_schema_extra={"examples": ["Cross-reference with Source A traffic spike on 2026-05-01."]},
    )
    case_id: str | None = Field(
        default=None,
        max_length=256,
        description="Optional external case reference printed on the cover page.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "entity_id": "00000000-0000-0000-0000-000000000001",
                    "investigation_note": "Entity tied to coordinated inauthentic amplification.",
                    "case_id": "OPS-2026-114",
                }
            ]
        }
    }


class EvidenceCreateResponse(BaseModel):
    evidence_package_id: UUID
    download_url: str
    generated_at: datetime

    model_config = {"json_schema_extra": {"examples": [{"evidence_package_id": "...", "download_url": "/api/v1/evidence/files/uuid.pdf", "generated_at": "2026-05-11T12:00:00Z"}]}}


@router.post(
    "",
    response_model=EvidenceCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate evidence PDF",
    responses={
        201: {"description": "Package stored; client may GET download_url"},
        404: {"description": "Entity not found"},
    },
)
def create_evidence_package(
    body: EvidenceCreateRequest,
    db: Session = Depends(get_db),
    analyst_id: UUID = Depends(get_current_user_id),
):
    ent = db.query(Entity).filter(Entity.id == body.entity_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found")

    pdf_bytes = render_evidence_pdf(
        db,
        str(body.entity_id),
        body.investigation_note,
        case_id=body.case_id,
    )

    pkg_id = gen_uuid()
    fname = f"{pkg_id}.pdf"
    out_dir = evidence_dir_path()
    out_path = out_dir / fname
    out_path.write_bytes(pdf_bytes)

    cid = body.case_id or f"CASE-{str(body.entity_id)[:8].upper()}"
    pkg = EvidencePackage(
        id=pkg_id,
        entity_id=body.entity_id,
        analyst_id=analyst_id,
        case_id=cid,
        title=f"Evidence — {ent.display_name}",
        content={
            "entity_id": str(body.entity_id),
            "case_id": cid,
            "investigation_note": body.investigation_note,
        },
        included_entity_ids=[str(body.entity_id)],
        case_metadata={"generated_by": str(analyst_id)},
        file_path=str(out_path.resolve()),
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)

    download_url = f"/api/v1/evidence/files/{pkg_id}.pdf"
    return EvidenceCreateResponse(
        evidence_package_id=pkg.id,
        download_url=download_url,
        generated_at=datetime.now(timezone.utc),
    )
