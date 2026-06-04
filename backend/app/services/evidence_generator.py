from __future__ import annotations

from io import BytesIO
from uuid import UUID

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.models import Entity


def render_evidence_pdf(db: Session, entity_id: str, investigation_note: str, case_id: str | None = None) -> bytes:
    entity = db.query(Entity).filter(Entity.id == UUID(entity_id)).first()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 72
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(72, y, "Evidence Package")
    y -= 28
    pdf.setFont("Helvetica", 11)
    lines = [
        f"Case ID: {case_id or 'N/A'}",
        f"Entity ID: {entity_id}",
        f"Entity: {getattr(entity, 'display_name', None) or getattr(entity, 'primary_identifier', entity_id)}",
        "",
        "Analyst Note:",
        investigation_note,
    ]
    for line in lines:
        for chunk in str(line).splitlines() or [""]:
            pdf.drawString(72, y, chunk[:110])
            y -= 16
            if y < 72:
                pdf.showPage()
                y = height - 72
                pdf.setFont("Helvetica", 11)
    pdf.save()
    return buffer.getvalue()
