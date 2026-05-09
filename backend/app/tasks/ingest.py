"""
Ingestion Tasks

This module contains ingestion-related Celery tasks for the ILA backend.
"""

import logging
from typing import Dict, Any

from app.worker import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="ingest_mock_batch_task")
def ingest_mock_batch_task(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock ingestion task for batch event ingestion.

    Args:
        batch_data: batch payload to ingest

    Returns:
        Task status and metadata
    """
    logger.info("Running ingest_mock_batch_task")
    try:
        # In production, this would normalize and persist incoming raw events.
        processed_count = len(batch_data.get("events", []))
        return {
            "status": "success",
            "processed_count": processed_count,
            "message": "Batch ingestion completed"
        }
    except Exception as exc:
        logger.exception("Error in ingest_mock_batch_task")
        raise self.retry(countdown=30, exc=exc, max_retries=3)
