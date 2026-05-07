from fastapi import FastAPI
from loguru import logger

from app.core.database import Base, engine
from app.models.user import User

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ILA Backend",
    version="0.1.0"
)

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "ILA Backend"
    }