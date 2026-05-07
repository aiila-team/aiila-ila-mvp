from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Entity(Base):
    __tablename__ = "entities"
    id = Column(String, primary_key=True, index=True)
    entity_type = Column(String, index=True) 
    primary_identifier = Column(String, unique=True, index=True)
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EntityAlias(Base):
    __tablename__ = "entity_aliases"
    id = Column(String, primary_key=True, index=True)
    entity_id = Column(String, ForeignKey("entities.id"))
    alias_value = Column(String, index=True)

class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(String, primary_key=True, index=True)
    source_entity_id = Column(String, ForeignKey("entities.id"))
    target_entity_id = Column(String, ForeignKey("entities.id"))
    relationship_type = Column(String) 
    weight = Column(Float, default=1.0)