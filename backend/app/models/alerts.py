from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    id = Column(String, primary_key=True, index=True)
    entity_id = Column(String, ForeignKey("entities.id"))
    alert_type = Column(String)
    risk_score = Column(Float)
    status = Column(String, default="new") 
    created_at = Column(DateTime(timezone=True), server_default=func.now())