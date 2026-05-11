import os

# Must be set before importing app.core.database
os.environ["ILA_SQLITE"] = "1"
os.environ.setdefault("SECRET_KEY", "pytest-secret-key-do-not-use")
os.environ.setdefault("POSTGRES_PASSWORD", "unused")
os.environ.setdefault("NEO4J_PASSWORD", "unused")

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine, SessionLocal
from app.db.session import get_db
from app.main import app


@pytest.fixture(scope="function")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
