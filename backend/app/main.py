from fastapi import FastAPI
from loguru import logger

from app.core.database import Base, engine
from app.models.user import User
# --- ADD THIS IMPORT ---
from app.api.v1.auth import router as auth_router 

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ILA Backend",
    version="0.1.0"
)

# --- ADD THIS LINE TO REGISTER THE ROUTES ---
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "ILA Backend"
    }