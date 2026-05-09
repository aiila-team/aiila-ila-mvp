"""
Entity Resolution Task

This module contains the Celery task for resolving entities from enriched events
and updating the entity database with aliases and relationships.
"""

import logging
from typing import Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session
from app.worker import celery
from app.db.session import SessionLocal
from app.models import RawEvent, Entity, EntityAlias, EntityEvent
from app.services.entity_resolution import EntityResolutionService

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="resolve_entity_task")
def resolve_entity_task(self, event_id: str) -> Dict[str, Any]:
    """
    Resolve entities from an enriched event and update entity database.

    Args:
        event_id: UUID string of the enriched raw event

    Returns:
        Dict containing resolution results and status
    """
    try:
        event_uuid = UUID(event_id)
        logger.info(f"Starting entity resolution for event {event_id}")

        # Get database session
        db = SessionLocal()

        try:
            # Fetch the raw event
            event = db.query(RawEvent).filter(RawEvent.id == event_uuid).first()
            if not event:
                logger.error(f"Event {event_id} not found")
                return {"status": "error", "message": "Event not found"}

            if not event.is_processed or not event.extracted_entities:
                logger.warning(f"Event {event_id} not enriched yet, skipping resolution")
                return {"status": "skipped", "message": "Event not enriched"}

            # Initialize entity resolution service
            resolver = EntityResolutionService(db)

            resolved_entities = []
            created_entities = []
            updated_entities = []

            # Process each extracted entity
            for entity_data in event.extracted_entities:
                entity_type = entity_data.get("type")
                entity_value = entity_data.get("value")
                confidence = entity_data.get("confidence", 1.0)

                if not entity_type or not entity_value:
                    continue

                # Resolve the entity
                resolution_result = resolver.resolve_entity(entity_value, entity_type, confidence)

                if resolution_result["action"] == "created":
                    created_entities.append(resolution_result["entity_id"])
                elif resolution_result["action"] == "updated":
                    updated_entities.append(resolution_result["entity_id"])

                resolved_entities.append(resolution_result["entity_id"])

                # Create entity-event relationship
                entity_event = EntityEvent(
                    entity_id=resolution_result["entity_id"],
                    event_id=event.id,
                    relevance_score=confidence,
                    context=f"Extracted from {entity_type}: {entity_value}"
                )
                db.add(entity_event)

                # Update entity metadata (event_count, last_seen)
                entity = db.query(Entity).filter(Entity.id == resolution_result["entity_id"]).first()
                if entity:
                    # Increment event count (simplified - in production, use proper counters)
                    entity.metadata_ = entity.metadata_ or {}
                    entity.metadata_["event_count"] = entity.metadata_.get("event_count", 0) + 1
                    entity.updated_at = db.func.now()

            db.commit()
            logger.info(f"Successfully resolved {len(resolved_entities)} entities for event {event_id}")

            return {
                "status": "success",
                "event_id": event_id,
                "entities_resolved": len(resolved_entities),
                "entities_created": len(created_entities),
                "entities_updated": len(updated_entities)
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error resolving entities for event {event_id}: {str(e)}")
            raise self.retry(countdown=60, exc=e, max_retries=3)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to resolve entities for event {event_id}: {str(e)}")
        return {"status": "error", "message": str(e)}