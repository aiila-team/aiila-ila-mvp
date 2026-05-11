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
from app.api.v1.graph import router as graph_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.sources import router as sources_router
from app.api.v1.investigations import router as investigations_router
from app.core.errors import register_exception_handlers
from app.core.config import evidence_dir_path


# ─────────────────────────────────────────
# STARTUP / SHUTDOWN
# ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ILA Backend starting up...")

    evidence_dir_path()

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

    # Close Neo4j driver on shutdown
    try:
        from app.core.neo4j import close_neo4j_driver
        close_neo4j_driver()
        logger.info("Neo4j driver closed")
    except Exception as e:
        logger.error(f"Error closing Neo4j driver: {e}")


# ─────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────

app = FastAPI(
    title="ILA — Intelligence Layer for Analytics",
    version="0.1.0",
    description=(
        "Sovereign digital threat monitoring platform for India's defense agencies. "
        "Key flows: ingestion → enrichment → risk alerts; graph APIs on `/api/v1/graph`; "
        "evidence PDFs on `POST /api/v1/evidence`."
    ),
    lifespan=lifespan,
    openapi_tags=[
        {"name": "auth", "description": "JWT login and session."},
        {"name": "alerts", "description": "Alert inbox, SSE stream, status workflow."},
        {"name": "entities", "description": "Entity profiles and timelines."},
        {"name": "dashboard", "description": "Aggregate KPIs and charts."},
        {"name": "search", "description": "Full-text search (PostgreSQL tsvector when available)."},
        {"name": "evidence", "description": "ReportLab PDF evidence packages."},
        {"name": "sources", "description": "Configured OSINT sources and health."},
        {"name": "investigations", "description": "Case-style entity groupings."},
        {"name": "graph", "description": "Neo4j-backed relationship search."},
    ],
)

register_exception_handlers(app)

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
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(sources_router, prefix="/api/v1")
app.include_router(investigations_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1/graph")


@app.get("/api/v1/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "ILA Backend", "version": "0.1.0"}
