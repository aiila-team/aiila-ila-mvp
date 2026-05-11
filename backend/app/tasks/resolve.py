"""
Entity Resolution Task — optional Celery path aligned with enrich.extracted_entities.
"""

import logging
from typing import Any, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from app.worker import celery
from app.core.database import SessionLocal
from app.models import RawEvent, EntityEvent, gen_uuid
from app.services.entity_resolution import EntityResolutionService
from app.tasks.risk import score_risk_task

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="resolve_entity_task")
def resolve_entity_task(self, event_id: str) -> Dict[str, Any]:
    """Resolve entities from an enriched event (JSON shape: entity_type, value, confidence)."""
    try:
        event_uuid = UUID(event_id)
        logger.info("Starting entity resolution for event %s", event_id)

        db: Session = SessionLocal()
        resolver = EntityResolutionService()

        try:
            event = db.query(RawEvent).filter(RawEvent.id == event_uuid).first()
            if not event:
                logger.error("Event %s not found", event_id)
                return {"status": "error", "message": "Event not found"}

            if not event.is_processed or not event.extracted_entities:
                logger.warning("Event %s not enriched yet, skipping resolution", event_id)
                return {"status": "skipped", "message": "Event not enriched"}

            resolved_ids: list[str] = []

            for entity_data in event.extracted_entities:
                entity_type = entity_data.get("entity_type")
                entity_value = entity_data.get("value")
                confidence = float(entity_data.get("confidence") or 1.0)

                if not entity_type or not entity_value:
                    continue

                entity = resolver.resolve(
                    db,
                    entity_type=entity_type,
                    value=entity_value,
                    confidence=confidence,
                    source_platform=event.platform or "",
                    source_event_id=str(event.id),
                )
                if not entity:
                    continue

                exists = (
                    db.query(EntityEvent)
                    .filter(
                        EntityEvent.entity_id == entity.id,
                        EntityEvent.event_id == event.id,
                    )
                    .first()
                )
                if not exists:
                    db.add(
                        EntityEvent(
                            id=gen_uuid(),
                            entity_id=entity.id,
                            event_id=event.id,
                            relevance_score=confidence,
                            context=f"Extracted from {entity_type}: {entity_value}",
                        )
                    )

                resolved_ids.append(str(entity.id))

            db.commit()
            logger.info("Resolved %s entities for event %s", len(resolved_ids), event_id)

            for eid in resolved_ids:
                try:
                    score_risk_task.delay(eid)
                except Exception as exc:
                    logger.warning("Failed to dispatch score_risk_task for %s: %s", eid, exc)

            return {
                "status": "success",
                "event_id": event_id,
                "entities_resolved": len(resolved_ids),
            }

        except Exception as e:
            db.rollback()
            logger.error("Error resolving entities for event %s: %s", event_id, e)
            raise self.retry(countdown=60, exc=e, max_retries=3) from e
        finally:
            db.close()

    except Exception as e:
        logger.error("Failed to resolve entities for event %s: %s", event_id, e)
        return {"status": "error", "message": str(e)}
