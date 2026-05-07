from sqlalchemy import Column, String, ForeignKey
from app.core.database import Base

class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(String, primary_key=True, index=True)
    word = Column(String, unique=True, index=True)
    assigned_source = Column(String, ForeignKey("sources.id"), nullable=True)