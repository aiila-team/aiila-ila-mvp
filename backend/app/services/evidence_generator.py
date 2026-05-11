"""
Evidence PDF generation (ReportLab) for analyst-ready packages.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models import Entity, EntityEvent, RawEvent, RiskAlert, Source


def render_evidence_pdf(
    db: Session,
    entity_id: str,
    investigation_note: str,
    case_id: Optional[str] = None,
) -> bytes:
    """
    Build a PDF with AIILA header, case id, graph summary, timeline, sources,
    risk breakdown, disclaimer (uses an existing DB session).
    """
    entity = db.query(Entity).filter(Entity.id == UUID(entity_id)).first()
    if entity is None:
        raise ValueError(f"Entity {entity_id} not found")

    events = (
        db.query(RawEvent)
        .join(EntityEvent, EntityEvent.event_id == RawEvent.id)
        .filter(EntityEvent.entity_id == entity.id)
        .order_by(RawEvent.published_at.desc().nulls_last(), RawEvent.timestamp.desc())
        .limit(40)
        .all()
    )

    alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.entity_id == entity.id)
        .order_by(RiskAlert.created_at.desc())
        .limit(15)
        .all()
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    story: List[Any] = []

    story.append(Paragraph("<b>AIILA — Intelligence Layer for Analytics</b>", styles["Title"]))
    story.append(Paragraph("<i>Evidence package (confidential)</i>", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    cid = case_id or f"CASE-{entity_id[:8].upper()}"
    story.append(Paragraph(f"<b>Case ID:</b> {cid}", styles["Heading2"]))
    story.append(Paragraph(f"<b>Subject entity:</b> {entity.display_name} ({entity.entity_type})", styles["Normal"]))
    story.append(Paragraph(f"<b>Primary identifier:</b> {entity.primary_identifier}", styles["Normal"]))
    story.append(Paragraph(f"<b>Generated (UTC):</b> {datetime.now(timezone.utc).isoformat()}", styles["Normal"]))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("<b>Entity graph summary</b>", styles["Heading2"]))
    graph_lines = [
        f"Risk score: {entity.risk_score or 0:.2f} / 10",
        f"Risk level: {entity.risk_level}",
        f"Events linked: {entity.event_count or 0}",
        f"Flagged: {'yes' if entity.is_flagged else 'no'}",
    ]
    for line in graph_lines:
        story.append(Paragraph(line, styles["BodyText"]))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("<b>Investigation note (analyst)</b>", styles["Heading2"]))
    story.append(Paragraph(investigation_note.replace("\n", "<br/>"), styles["BodyText"]))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("<b>Event timeline (recent)</b>", styles["Heading2"]))
    if not events:
        story.append(Paragraph("No linked raw events.", styles["BodyText"]))
    else:
        rows = [["Time (UTC)", "Platform", "Source / URL", "Snippet"]]
        for ev in events:
            src_name = ""
            if ev.source_id:
                s = db.query(Source).filter(Source.id == ev.source_id).first()
                src_name = s.name if s else ""
            ts = (ev.published_at or ev.timestamp or ev.created_at)
            ts_s = ts.strftime("%Y-%m-%d %H:%M") if ts else "—"
            snippet = (ev.content or "")[:120].replace("\n", " ")
            rows.append([ts_s, ev.platform or "—", src_name or (ev.url or "—")[:40], snippet])
        t = Table(rows, colWidths=[1.1 * inch, 0.9 * inch, 1.3 * inch, 2.7 * inch])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a365d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(t)
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("<b>Source attribution</b>", styles["Heading2"]))
    story.append(
        Paragraph(
            "Each row references the originating collection or publisher where available.",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("<b>Risk score breakdown</b>", styles["Heading2"]))
    factors = entity.risk_factors or []
    if isinstance(factors, list) and factors:
        for f in factors[:12]:
            if isinstance(f, dict):
                story.append(
                    Paragraph(
                        f"• {f.get('factor', 'factor')}: {f.get('detail', '')} (weight {f.get('weight', '')})",
                        styles["BodyText"],
                    )
                )
            else:
                story.append(Paragraph(f"• {f}", styles["BodyText"]))
    else:
        story.append(Paragraph("No structured risk factors recorded for this entity.", styles["BodyText"]))
    story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("<b>Related alerts (recent)</b>", styles["Heading2"]))
    if not alerts:
        story.append(Paragraph("No alerts on file.", styles["BodyText"]))
    else:
        for a in alerts:
            story.append(
                Paragraph(
                    f"• [{a.created_at}] {a.title} — {a.status} / {a.risk_level}",
                    styles["BodyText"],
                )
            )

    story.append(Spacer(1, 0.25 * inch))
    story.append(
        Paragraph(
            "<b>Legal disclaimer:</b> This document is generated for authorized intelligence "
            "analysis purposes only. It may contain unverified open-source information and must "
            "not be used as sole evidence for enforcement action without independent corroboration "
            "and legal review.",
            styles["BodyText"],
        )
    )

    doc.build(story)
    return buf.getvalue()


def generate_evidence_pdf(entity_id: str, investigation_note: str) -> bytes:
    """Public API: open a short-lived session and return PDF bytes."""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        return render_evidence_pdf(db, entity_id, investigation_note, case_id=None)
    finally:
        db.close()
