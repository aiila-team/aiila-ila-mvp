from sqlalchemy import Column, String, Integer, Boolean
from app.core.database import Base

class Source(Base):
    __tablename__ = "sources"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    source_type = Column(String) 
    reliability_tier = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)