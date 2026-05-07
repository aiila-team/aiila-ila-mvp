from fastapi import FastAPI
from app.api.v1.auth import router as auth_router
from app.core.database import Base, engine
from app.models.user import User

# Create all database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ILA Backend",
    version="0.1.0"
)

app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "ILA Backend"
    }