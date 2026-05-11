"""
Database session — delegates to app.core.database so ORM models and FastAPI
share one engine, Base metadata, and SessionLocal.
"""

from app.core.database import engine, SessionLocal, Base


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
