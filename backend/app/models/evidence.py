from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class EvidencePackage(Base):
    __tablename__ = "evidence_packages"
    id = Column(String, primary_key=True, index=True)
    entity_id = Column(String, ForeignKey("entities.id"))
    analyst_id = Column(String, ForeignKey("users.id"))
    file_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())