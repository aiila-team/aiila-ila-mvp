"""
tasks/ingest.py
──────────────────────────────────────────────────────────────────────────────
Ingestion Pipeline — The Entry Point of the ILA Data Pipeline

This module handles the initial ingestion of raw OSINT events into the system.
It reads mock data from JSON files, performs basic validation and deduplication,
and inserts events into the raw_events table. After successful insertion, it
dispatches enrichment tasks for further processing.

Pipeline Stages:
  Stage 1 — Load Data: Read JSON events from mock_events.json
  Stage 2 — Source Management: Find or create Source records
  Stage 3 — Deduplication: Check for existing events by external_id or URL
  Stage 4 — Event Insertion: Create RawEvent records in database
  Stage 5 — Dispatch Enrichment: Trigger enrich_event_task for each new event

Key Features:
  - Production-grade error handling with rollback support
  - Comprehensive logging for monitoring and debugging
  - Type hints and docstrings for maintainability
  - SQLAlchemy 2.x compatible session management
  - No circular imports (imports are done at function level where needed)

Called by:
  - Manual triggers (e.g., from Python scripts)
  - Admin endpoints (future implementation)
  - Scheduled tasks (future implementation)

Calls:
  - tasks/enrich.py → enrich_event_task.delay()
──────────────────────────────────────────────────────────────────────────────
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal
from app.models import Source, RawEvent
from app.worker import celery

# Configure logging
logger = logging.getLogger(__name__)


def load_mock_json() -> List[Dict[str, Any]]:
    """
    Load mock events from the JSON file.

    Returns:
        List of event dictionaries from mock_events.json

    Raises:
        FileNotFoundError: If the mock file doesn't exist
        json.JSONDecodeError: If the JSON is malformed
    """
    mock_file_path = Path(__file__).parent.parent / "mock_data" / "mock_events.json"

    try:
        with open(mock_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Loaded {len(data)} mock events from {mock_file_path}")
            return data
    except FileNotFoundError:
        logger.error(f"Mock events file not found: {mock_file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in mock events file: {e}")
        raise


def get_or_create_source(session, source_name: str) -> Source:
    """
    Find an existing Source by name or create a new one.

    Args:
        session: SQLAlchemy session
        source_name: Name of the source

    Returns:
        Source instance
    """
    # Try to find existing source
    stmt = select(Source).where(Source.name == source_name)
    result = session.execute(stmt)
    source = result.scalar_one_or_none()

    if source:
        logger.debug(f"Found existing source: {source_name}")
        return source

    # Create new source
    source = Source(
        name=source_name,
        source_type="social_media",  # Default type for mock data
        is_active=True
    )
    session.add(source)
    session.flush()  # Get the ID without committing
    logger.info(f"Created new source: {source_name} (ID: {source.id})")
    return source


def is_duplicate_event(session, external_id: str, url: Optional[str]) -> bool:
    """
    Check if an event already exists based on external_id or URL.

    Args:
        session: SQLAlchemy session
        external_id: External identifier from the source
        url: URL of the event (optional)

    Returns:
        True if duplicate exists, False otherwise
    """
    # Check by external_id first (more reliable)
    stmt = select(RawEvent).where(RawEvent.external_id == external_id)
    result = session.execute(stmt)
    if result.scalar_one_or_none():
        logger.debug(f"Duplicate found by external_id: {external_id}")
        return True

    # Check by URL if provided
    if url:
        stmt = select(RawEvent).where(RawEvent.url == url)
        result = session.execute(stmt)
        if result.scalar_one_or_none():
            logger.debug(f"Duplicate found by URL: {url}")
            return True

    return False


def create_raw_event(session, event_data: Dict[str, Any], source: Source) -> RawEvent:
    """
    Create a new RawEvent record from event data.

    Args:
        session: SQLAlchemy session
        event_data: Dictionary containing event information
        source: Associated Source instance

    Returns:
        Created RawEvent instance
    """
    # Parse published_at timestamp
    published_at = None
    if event_data.get("published_at"):
        try:
            # Assume ISO format with Z suffix
            published_at_str = event_data["published_at"].replace('Z', '+00:00')
            published_at = datetime.fromisoformat(published_at_str)
        except ValueError:
            logger.warning(f"Invalid published_at format: {event_data['published_at']}")
            published_at = datetime.now(timezone.utc)

    raw_event = RawEvent(
        source_id=source.id,
        external_id=event_data["external_id"],
        content=event_data["content"],
        content_language=event_data.get("content_language", "unknown"),
        event_type=f"{event_data.get('platform', 'unknown')}_post",  # e.g., "telegram_post"
        timestamp=published_at or datetime.now(timezone.utc),  # Required field
        published_at=published_at,
        url=event_data.get("url"),
        author_handle=event_data.get("author_handle"),
        platform=event_data.get("platform"),
        is_processed=False,
        extracted_entities=[],  # Will be populated by enrichment
        matched_keywords=[],    # Will be populated by enrichment
        created_at=datetime.now(timezone.utc)  # ingested_at
    )

    session.add(raw_event)
    session.flush()  # Get the ID without committing
    logger.debug(f"Created RawEvent: {raw_event.id} for external_id: {event_data['external_id']}")
    return raw_event


@celery.task(name="tasks.ingest_mock_batch_task")
def ingest_mock_batch_task() -> Dict[str, int]:
    """
    Celery task to ingest a batch of mock events into the system.

    This task:
    1. Loads events from mock_events.json
    2. For each event: finds/creates source, checks duplicates, inserts RawEvent
    3. Dispatches enrichment tasks for successfully inserted events
    4. Returns summary statistics

    Returns:
        Dictionary with counts: {"inserted": int, "duplicates": int, "failed": int}
    """
    logger.info("Starting mock batch ingestion task")

    summary = {"inserted": 0, "duplicates": 0, "failed": 0}

    try:
        # Load mock data
        events = load_mock_json()

        with SessionLocal() as session:
            for event_data in events:
                try:
                    # Stage 1: Source Management
                    source_name = event_data["source_name"]
                    source = get_or_create_source(session, source_name)

                    # Stage 2: Deduplication Check
                    external_id = event_data["external_id"]
                    url = event_data.get("url")
                    if is_duplicate_event(session, external_id, url):
                        summary["duplicates"] += 1
                        logger.info(f"Skipped duplicate event: {external_id}")
                        continue

                    # Stage 3: Event Insertion
                    raw_event = create_raw_event(session, event_data, source)
                    summary["inserted"] += 1

                    # Stage 4: Dispatch Enrichment Task
                    # Import here to avoid circular imports
                    from app.tasks.enrich import enrich_event_task
                    enrich_event_task.delay(str(raw_event.id))
                    logger.info(f"Dispatched enrichment for event: {raw_event.id}")

                except KeyError as e:
                    logger.error(f"Missing required field in event data: {e}")
                    summary["failed"] += 1
                except SQLAlchemyError as e:
                    logger.error(f"Database error processing event {event_data.get('external_id', 'unknown')}: {e}")
                    summary["failed"] += 1
                    # Continue processing other events even if one fails
                except Exception as e:
                    logger.error(f"Unexpected error processing event {event_data.get('external_id', 'unknown')}: {e}")
                    summary["failed"] += 1

            # Commit all changes at once
            session.commit()
            logger.info(f"Committed {summary['inserted']} new events to database")

    except Exception as e:
        logger.error(f"Critical error in ingestion task: {e}")
        # Note: We don't increment failed here as it's a batch failure
        raise  # Re-raise to let Celery handle retry/error state

    logger.info(f"Ingestion task completed. Summary: {summary}")
    return summary


# Example manual trigger (for testing)
if __name__ == "__main__":
    # This allows running the task directly for testing
    result = ingest_mock_batch_task()
    print(f"Ingestion result: {result}")
