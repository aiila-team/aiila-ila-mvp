import os

os.environ.setdefault("ILA_SQLITE", "1")

from app.core.database import Base, engine, SessionLocal
from app.models import Entity, EntityType, gen_uuid
from app.services.evidence_generator import render_evidence_pdf


def test_render_evidence_pdf_minimal():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        e = Entity(
            id=gen_uuid(),
            entity_type=EntityType.PERSON,
            primary_identifier="test-user",
            display_name="Test User",
            risk_score=3.0,
        )
        db.add(e)
        db.commit()
        pdf = render_evidence_pdf(db, str(e.id), "Unit test note.", case_id="UT-1")
        assert pdf[:4] == b"%PDF"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
