from fastapi import FastAPI

from app.api.v1.api_endpoints import router as v1_router
from app.api.v1.auth import router as auth_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.graph import router as graph_router
from app.api.v1.investigations import router as investigations_router
from app.api.v1.sources import router as sources_router

app = FastAPI(
    title="ILA Backend",
    version="0.1.0"
)

app.include_router(v1_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(sources_router, prefix="/api/v1")
app.include_router(investigations_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service": "ILA Backend"
    }