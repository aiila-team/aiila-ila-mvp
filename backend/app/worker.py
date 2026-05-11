"""
Celery Worker Configuration for ILA Backend

This module configures Celery for asynchronous task processing in the intelligence analytics platform.
"""

from celery import Celery
from app.core.config import settings

# Create Celery app instance
celery = Celery(
    "ila_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

# Celery configuration
celery.conf.update(
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

    # Routing (if needed for different queues)
    task_routes={
        "app.tasks.enrich.enrich_event_task": {"queue": "enrichment"},
        "app.tasks.resolve.resolve_entity_task": {"queue": "resolution"},
        "app.tasks.ingest.ingest_mock_batch_task": {"queue": "ingestion"},
    },
)

# Optional: expose alias for best compatibility
# This is the object Celery command line expects by default.
celery_app = celery

if __name__ == "__main__":
    celery.start()