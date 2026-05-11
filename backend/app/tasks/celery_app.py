"""
Celery App Configuration for ILA Backend Tasks

This module configures the Celery application instance for asynchronous task processing.
"""

from celery import Celery
from app.core.config import settings

# Create Celery app instance
celery_app = Celery(
    "ila_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,

    # Result backend settings
    result_expires=3600,  # 1 hour

    # Routing
    task_routes={
        "app.tasks.enrich.enrich_event_task": {"queue": "enrichment"},
        "app.tasks.resolve.resolve_entity_task": {"queue": "resolution"},
        "app.tasks.ingest.ingest_mock_batch_task": {"queue": "ingestion"},
        "app.tasks.ml_tasks.*": {"queue": "ml"},
        "app.tasks.neo4j_sync.sync_entity_to_graph_task": {"queue": "graph"},
        "app.tasks.risk.run_pagerank_task": {"queue": "ml"},
    },
)

if __name__ == "__main__":
    celery_app.start()