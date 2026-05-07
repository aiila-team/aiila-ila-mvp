from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class RawEvent(Base):
    __tablename__ = "raw_events"
    id = Column(String, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("sources.id"))
    content = Column(String, nullable=False)
    language = Column(String, nullable=True)
    extracted_entities = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())