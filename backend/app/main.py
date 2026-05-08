"""
ILA — Intelligence Layer for Analytics
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.db.session import engine, SessionLocal, Base
from app.api.v1.auth import router as auth_router, seed_default_user
from app.api.v1.api_endpoints import alerts_router, entities_router, dashboard_router, search_router


# ─────────────────────────────────────────
# STARTUP / SHUTDOWN
# ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ILA Backend starting up...")

    # Create all tables if they don't exist yet
    # (Alembic handles this in production — this is a dev safety net)
    Base.metadata.create_all(bind=engine)

    # Seed default user for Day 1 testing
    db = SessionLocal()
    try:
        seed_default_user(db)
    finally:
        db.close()

    logger.info("ILA Backend ready ✓")
    yield
    logger.info("ILA Backend shutting down...")


# ─────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────

app = FastAPI(
    title="ILA — Intelligence Layer for Analytics",
    version="0.1.0",
    description="Sovereign digital threat monitoring platform for India's defense agencies.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

app.include_router(auth_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(entities_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "ILA Backend", "version": "0.1.0"}