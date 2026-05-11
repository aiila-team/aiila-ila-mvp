"""
tasks/enrich.py
──────────────────────────────────────────────────────────────────────────────
Enrichment Pipeline — The Brain of the ILA Celery Worker

This file is the central nervous system of the entire ILA data pipeline.
Every raw event that enters the system flows through here before it becomes
an actionable alert in the analyst's inbox.

Pipeline Stages (in order):
  Stage 0 — Guard: fetch event, check it exists, not already processed
  Stage 1 — Deduplication: MinHash+LSH → flag & skip duplicates early
  Stage 2 — Language Detection: langdetect → raw_events.content_language
  Stage 3 — Entity Extraction: spaCy NER + Regex → raw_events.extracted_entities
  Stage 4 — Keyword Matching: scan text vs active keywords → raw_events.matched_keywords
  Stage 5 — Entity Resolution: fuzzy-match extracted entities → entities table
  Stage 6 — Entity–Event Linking: write entity_events join rows
  Stage 7 — Neo4j Sync: dispatch sync_entity_to_graph_task per resolved entity
  Stage 8 — Mark Processed: set is_processed=True, commit

All stages write to PostgreSQL via SQLAlchemy. Neo4j sync is fire-and-forget
(dispatched as a separate Celery task). The whole pipeline is designed so that
if the worker crashes after Stage N, re-running the task is safe:
  - Dedup check is idempotent (LSH query before insert)
  - Entity resolution uses INSERT OR UPDATE (upsert)
  - entity_events has a UniqueConstraint so re-linking is a no-op

Entry points:
  enrich_event_task(event_id)       — process one event
  enrich_batch_task(event_ids)      — process a list (fan-out)
  enrich_unprocessed_task()         — sweep DB for all is_processed=False events

Called by:
  tasks/ingest.py  → after inserting a new RawEvent
  Admin endpoint   → POST /api/v1/admin/reprocess/{event_id}

Calls:
  services/deduplication.py        → check_duplicate()
  services/language_detection.py   → detect_language()
  services/entity_extraction.py    → extract_entities()
  services/entity_resolution.py    → EntityResolutionService  (Day 2 PM — Likhita)
  tasks/neo4j_sync.py              → sync_entity_to_graph_task.delay()
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Optional

from celery import Task, chord, group
from celery.utils.log import get_task_logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.anomaly_detector import detect_anomaly
from app.services.source_reliability import score_source_url

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models import (
    RawEvent,
    Entity,
    EntityAlias,
    EntityEvent,
    RiskAlert,
    AlertType,
    AlertStatus,
    RiskLevel,
    Source,
    gen_uuid,
)

# ── Service imports (all built in services/ directory) ────────────────────────
from app.services.deduplication import get_dedup_service, DeduplicationResult
from app.services.language_detection import detect_language
from app.services.entity_extraction import extract_entities, ExtractedEntity
from app.services.entity_resolution import EntityResolutionService
from app.services.keyword_matcher import find_keyword_hits, hits_to_json

# Neo4j sync task (fire-and-forget after entity resolution)
from app.tasks.neo4j_sync import sync_entity_to_graph_task

logger = get_task_logger(__name__)

# ── Module-level service singletons ──────────────────────────────────────────
# Instantiated once per Celery worker process.
# entity_resolution is stateful (holds fuzzy-match cache) so keep it alive.

_resolution_service = EntityResolutionService()

# ── Constants ─────────────────────────────────────────────────────────────────

RISK_ALERT_THRESHOLD: float = 6.5
"""
Entities with risk_score >= this value after enrichment get a RiskAlert created.
Matches the threshold defined in the MVP plan and risk_scorer.py.
"""

KEYWORD_ALERT_MIN_MATCHES: int = 1
"""
Minimum number of keyword matches in an event to trigger a KEYWORD_MATCH alert.
Set to 1 for MVP so every match surfaces.
"""

# ── Pipeline Result ───────────────────────────────────────────────────────────

class EnrichmentResult:
    """
    Tracks what happened during a single event's enrichment.
    Returned from _run_pipeline() and logged at the end.
    """

    def __init__(self, event_id: str):
        self.event_id = event_id
        self.skipped = False
        self.skip_reason: str = ""
        self.is_duplicate = False
        self.duplicate_of: Optional[str] = None
        self.language: str = "unknown"
        self.entities_extracted: int = 0
        self.keywords_matched: list[str] = []
        self.entities_resolved: list[str] = []     # entity UUIDs
        self.neo4j_tasks_dispatched: int = 0
        self.alerts_created: int = 0
        self.error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict:
        return {
            "event_id":                 self.event_id,
            "skipped":                  self.skipped,
            "skip_reason":              self.skip_reason,
            "is_duplicate":             self.is_duplicate,
            "duplicate_of":             self.duplicate_of,
            "language":                 self.language,
            "entities_extracted":       self.entities_extracted,
            "keywords_matched":         self.keywords_matched,
            "entities_resolved":        self.entities_resolved,
            "neo4j_tasks_dispatched":   self.neo4j_tasks_dispatched,
            "alerts_created":           self.alerts_created,
            "error":                    self.error,
        }


# ═════════════════════════════════════════════════════════════════════════════
# PRIMARY TASK
# ═════════════════════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    name="tasks.enrich.enrich_event_task",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=300,         # hard kill after 5 min (prevents zombie tasks)
    soft_time_limit=240,    # sends SoftTimeLimitExceeded 1 min before hard kill
)
def enrich_event_task(self, event_id: str) -> dict:
    """
    Main enrichment task. Runs the full pipeline for one RawEvent.

    Args:
        event_id: UUID string of the RawEvent to process.

    Returns:
        EnrichmentResult.to_dict() — stored in Celery result backend.

    Retry policy:
        Retries up to 3 times on transient DB/service errors with 30s delay.
        Does NOT retry on ValueError (bad data) or if event is not found.
    """
    logger.info(f"[enrich] START event_id={event_id}")
    result = EnrichmentResult(event_id)

    db: Session = SessionLocal()
    try:
        _run_pipeline(db, event_id, result)
    except Exception as exc:
        # Determine if this is worth retrying
        if _is_transient_error(exc):
            logger.warning(
                f"[enrich] Transient error for {event_id}: {exc}. "
                f"Retrying ({self.request.retries + 1}/3)..."
            )
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
        else:
            result.error = f"{type(exc).__name__}: {exc}"
            logger.error(
                f"[enrich] FAILED event_id={event_id} | "
                f"error={result.error}\n{traceback.format_exc()}"
            )
    finally:
        db.close()

    # Final log summary
    if result.skipped:
        logger.info(f"[enrich] SKIPPED event_id={event_id} reason='{result.skip_reason}'")
    elif result.success:
        logger.info(
            f"[enrich] DONE event_id={event_id} | "
            f"lang={result.language} | "
            f"extracted={result.entities_extracted} | "
            f"resolved={len(result.entities_resolved)} | "
            f"alerts={result.alerts_created} | "
            f"neo4j_tasks={result.neo4j_tasks_dispatched}"
        )

    return result.to_dict()


# ═════════════════════════════════════════════════════════════════════════════
# BATCH TASKS
# ═════════════════════════════════════════════════════════════════════════════

@celery_app.task(
    name="tasks.enrich.enrich_batch_task",
    acks_late=True,
)
def enrich_batch_task(event_ids: list[str]) -> dict:
    """
    Fan-out enrichment for a list of event IDs.
    Dispatches one enrich_event_task per event_id and returns immediately.

    Called by: tasks/ingest.py after bulk mock data insertion.

    Args:
        event_ids: List of raw_events.id UUID strings.

    Returns:
        {"dispatched": N} — the Celery task IDs are not tracked here.
    """
    if not event_ids:
        return {"dispatched": 0}

    # group() runs all tasks in parallel across the worker pool
    job = group(enrich_event_task.s(eid) for eid in event_ids)
    job.apply_async()

    logger.info(f"[enrich_batch] Dispatched {len(event_ids)} enrich tasks.")
    return {"dispatched": len(event_ids)}


@celery_app.task(
    name="tasks.enrich.enrich_unprocessed_task",
    acks_late=True,
)
def enrich_unprocessed_task(limit: int = 500) -> dict:
    """
    Periodic sweep: find all unprocessed, non-duplicate events and enrich them.
    Triggered by Celery Beat (beat_schedule.py) as a fallback/catch-up task.

    Schedule suggestion (in beat_schedule.py):
        "enrich-unprocessed-sweep": {
            "task": "tasks.enrich.enrich_unprocessed_task",
            "schedule": crontab(minute="*/10"),   # every 10 minutes
        }

    Args:
        limit: Max events to pick up per sweep (prevents runaway backlogs).

    Returns:
        {"dispatched": N, "found": M}
    """
    db: Session = SessionLocal()
    try:
        unprocessed = (
            db.query(RawEvent.id)
            .filter(
                RawEvent.is_processed == False,
                RawEvent.is_duplicate == False,
            )
            .limit(limit)
            .all()
        )
        event_ids = [str(row.id) for row in unprocessed]
    finally:
        db.close()

    if not event_ids:
        logger.debug("[enrich_unprocessed] No unprocessed events found.")
        return {"dispatched": 0, "found": 0}

    job = group(enrich_event_task.s(eid) for eid in event_ids)
    job.apply_async()

    logger.info(
        f"[enrich_unprocessed] Found {len(event_ids)} unprocessed events. "
        f"Dispatched {len(event_ids)} tasks."
    )
    return {"dispatched": len(event_ids), "found": len(event_ids)}


# ═════════════════════════════════════════════════════════════════════════════
# PIPELINE IMPLEMENTATION
# ═════════════════════════════════════════════════════════════════════════════

def _run_pipeline(db: Session, event_id: str, result: EnrichmentResult) -> None:
    """
    Executes all enrichment stages for a single RawEvent.

    This function owns the full lifecycle:
      - Fetches the event
      - Runs each stage in order
      - Commits once at the end (or after dedup fast-path)
      - Dispatches Neo4j tasks after the DB commit

    Raises on unexpected errors — caller (Celery task) handles retry logic.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 0 — GUARD: Fetch & Validate
    # ─────────────────────────────────────────────────────────────────────────
    event: Optional[RawEvent] = db.get(RawEvent, event_id)

    if event is None:
        result.skipped = True
        result.skip_reason = "event_not_found"
        return

    if event.is_processed:
        result.skipped = True
        result.skip_reason = "already_processed"
        return

    if not event.content or not event.content.strip():
        # Empty content — mark processed so we don't retry endlessly
        event.is_processed = True
        db.commit()
        result.skipped = True
        result.skip_reason = "empty_content"
        return

    logger.debug(
        f"[Stage 0] Event loaded | id={event_id} | "
        f"platform={event.platform} | len={len(event.content)}"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 1 — DEDUPLICATION
    # ─────────────────────────────────────────────────────────────────────────
    dedup_svc = get_dedup_service()
    dedup_result: DeduplicationResult = dedup_svc.check(event_id, event.content)

    # Always persist the signature (even for duplicates, for index rebuild)
    if dedup_result.signature:
        event.minhash_signature = dedup_result.signature

    if dedup_result.is_duplicate:
        event.is_duplicate = True
        event.duplicate_of = dedup_result.duplicate_of
        event.is_processed = True   # skip all further enrichment
        db.commit()

        result.is_duplicate = True
        result.duplicate_of = dedup_result.duplicate_of
        result.skipped = True
        result.skip_reason = (
            f"duplicate_of={dedup_result.duplicate_of} "
            f"(similarity={dedup_result.similarity_score:.3f})"
        )
        logger.debug(
            f"[Stage 1] DUPLICATE detected | "
            f"original={dedup_result.duplicate_of} | "
            f"jaccard={dedup_result.similarity_score:.3f}"
        )
        return

    logger.debug(f"[Stage 1] Dedup passed (unique content)")

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 2 — LANGUAGE DETECTION
    # ─────────────────────────────────────────────────────────────────────────
    detected_lang: str = detect_language(event.content)
    event.content_language = detected_lang
    result.language = detected_lang

    logger.debug(f"[Stage 2] Language detected: {detected_lang}")

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 3 — ENTITY EXTRACTION
    # ─────────────────────────────────────────────────────────────────────────
    extracted: list[ExtractedEntity] = extract_entities(
        event.content,
        source_platform=event.platform or "",
    )

    # Persist as JSONB list in extracted_entities column
    event.extracted_entities = [e.to_dict() for e in extracted]
    result.entities_extracted = len(extracted)

    logger.debug(
        f"[Stage 3] Extracted {len(extracted)} entities: "
        f"{[f'{e.entity_type}:{e.value}' for e in extracted]}"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 4 — KEYWORD MATCHING
    # ─────────────────────────────────────────────────────────────────────────
    matched_keywords: list[dict] = _match_keywords(db, event)
    event.matched_keywords = matched_keywords
    result.keywords_matched = [m["word"] for m in matched_keywords]

    if matched_keywords:
        logger.debug(
            f"[Stage 4] Keywords matched: {result.keywords_matched}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 5 — ENTITY RESOLUTION
    # Fuzzy-match extracted entities → find/create canonical Entity records
    # ─────────────────────────────────────────────────────────────────────────
    resolved_entities: list[Entity] = []

    if extracted:
        resolved_entities = _resolve_entities(db, extracted, event)
        result.entities_resolved = [str(e.id) for e in resolved_entities]
        logger.debug(
            f"[Stage 5] Resolved {len(resolved_entities)} entities: "
            f"{[e.primary_identifier for e in resolved_entities]}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 6 — ENTITY–EVENT LINKING
    # Write entity_events join rows (many-to-many)
    # ─────────────────────────────────────────────────────────────────────────
    if resolved_entities:
        _link_entities_to_event(db, resolved_entities, event)
        logger.debug(f"[Stage 6] Linked {len(resolved_entities)} entities to event")

        # ─────────────────────────────────────────────────────────────────────────
        # STAGE 6.5 — RISK & ANOMALY SCORING (Mythresh's ML Models)
        # Apply Isolation Forest and Source Reliability Multipliers
        # ─────────────────────────────────────────────────────────────────────────
        source_multiplier = score_source_url(
            getattr(event, "url", ""),
            getattr(event, "source_type", ""),
        )

        for entity in resolved_entities:
            features = {
                "transaction_count_1h": len(entity.events) if hasattr(entity, "events") else 0,
            }
            base_score = detect_anomaly(features) * 10.0
            final_score = min(base_score * source_multiplier, 10.0)
            entity.risk_score = final_score

        logger.debug(
            f"[Stage 6.5] ML Risk Scoring applied with multiplier {source_multiplier}x"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 7a — KEYWORD ALERTS
    # If keywords matched, create a KEYWORD_MATCH RiskAlert
    # ─────────────────────────────────────────────────────────────────────────
    if matched_keywords and len(matched_keywords) >= KEYWORD_ALERT_MIN_MATCHES:
        for entity in resolved_entities:
            alert = _create_keyword_alert(db, entity, event, matched_keywords)
            if alert:
                result.alerts_created += 1

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 7b — RISK THRESHOLD ALERTS
    # If any resolved entity's risk_score >= threshold → create a risk alert
    # (risk_score is set by resolve/update logic in entity resolution service)
    # ─────────────────────────────────────────────────────────────────────────
    for entity in resolved_entities:
        if (entity.risk_score or 0.0) >= RISK_ALERT_THRESHOLD:
            alert = _create_risk_threshold_alert(db, entity, event)
            if alert:
                result.alerts_created += 1

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 8 — MARK PROCESSED & COMMIT
    # Single commit for all the writes above
    # ─────────────────────────────────────────────────────────────────────────
    event.is_processed = True
    db.commit()

    logger.debug(f"[Stage 8] DB committed for event {event_id}")

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 9 — NEO4J SYNC (fire-and-forget, after commit)
    # Dispatch one sync_entity_to_graph_task per resolved entity.
    # These run asynchronously — failure here doesn't roll back the DB write.
    # ─────────────────────────────────────────────────────────────────────────
    for entity in resolved_entities:
        try:
            sync_entity_to_graph_task.delay(str(entity.id))
            result.neo4j_tasks_dispatched += 1
        except Exception as exc:
            # Neo4j sync failure is non-fatal for the enrichment pipeline.
            # The bulk_sync_all_entities() script can re-sync later.
            logger.warning(
                f"[Stage 9] Failed to dispatch Neo4j sync for entity "
                f"{entity.id}: {exc}"
            )

    # Also sync POSTED relationship if we have an author handle
    if event.author_handle and event.platform:
        _dispatch_posted_relationship(event)


# ═════════════════════════════════════════════════════════════════════════════
# STAGE HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _match_keywords(db: Session, event: RawEvent) -> list[dict]:
    """
    Stage 4: Scan event text against keywords (exact, wildcard, phrase).
    """
    return hits_to_json(find_keyword_hits(db, event.content or "", event.translated_content))


def _resolve_entities(
    db: Session,
    extracted: list[ExtractedEntity],
    event: RawEvent,
) -> list[Entity]:
    """
    Stage 5: Resolve extracted entities against the PostgreSQL entities table.

    Delegates to EntityResolutionService (services/entity_resolution.py — Likhita).
    That service handles:
      - Exact match on primary_identifier
      - Fuzzy match via rapidfuzz (similarity > 0.85 → same entity)
      - Upsert: CREATE new entity if no match found
      - EntityAlias creation/update

    Returns the list of resolved (possibly newly created) Entity objects.
    All are db-attached and ready for further operations within this session.
    """
    extracted_payloads = [
        {
            "entity_type":    e.entity_type,
            "value":          e.value,
            "confidence":     e.confidence,
            "source_platform": event.platform or "",
            "source_event_id": str(event.id),
        }
        for e in extracted
    ]

    try:
        resolved = _resolution_service.resolve_entities(db, extracted_payloads)
    except Exception as exc:
        logger.warning(
            f"[Stage 5] Batch entity resolution failed for event {event.id}: {exc}"
        )
        return []

    # Deduplicate entities by id in case multiple extracted entities resolve to same record
    unique_entities: list[Entity] = []
    seen_entity_ids: set[str] = set()
    for entity in resolved:
        entity_id_str = str(entity.id)
        if entity_id_str not in seen_entity_ids:
            unique_entities.append(entity)
            seen_entity_ids.add(entity_id_str)

    return unique_entities


def _link_entities_to_event(
    db: Session,
    entities: list[Entity],
    event: RawEvent,
) -> None:
    """
    Stage 6: Write EntityEvent join rows for each resolved entity.

    Role assignment logic:
      - If entity.primary_identifier matches event.author_handle → role="author"
      - Otherwise → role="mentioned"

    UniqueConstraint on (entity_id, event_id) means this is safe to re-run
    (duplicate inserts are silently ignored via on_conflict_do_nothing).
    """
    author_handle_norm = (event.author_handle or "").lower().strip()

    for entity in entities:
        # Determine role
        role = "mentioned"
        if author_handle_norm and (
            entity.primary_identifier.lower() == author_handle_norm
            or any(
                alias.alias_value.lower() == author_handle_norm
                for alias in (entity.aliases or [])
            )
        ):
            role = "author"

        link = EntityEvent(
            id=gen_uuid(),
            entity_id=str(entity.id),
            event_id=str(event.id),
            role=role,
        )
        db.add(link)

    # Flush (not commit) so IDs are available if we need them below.
    # Catch IntegrityError from the UniqueConstraint — means already linked.
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        # Re-attach the event object after rollback
        db.add(event)
        logger.debug(
            f"[Stage 6] IntegrityError on entity_events (already linked). "
            f"Rolled back flush, continuing."
        )


def _create_keyword_alert(
    db: Session,
    entity: Entity,
    event: RawEvent,
    matched_keywords: list[dict],
) -> Optional[RiskAlert]:
    """
    Stage 7a: Create a KEYWORD_MATCH alert for a matched entity.

    One alert is created per entity per event batch (not per keyword).
    All matched keywords for this event are bundled into one alert to
    avoid flooding the analyst inbox.

    Returns the created RiskAlert or None if creation fails.
    """
    keyword_words = [m["word"] for m in matched_keywords]
    categories = list({m["category"] for m in matched_keywords})
    first = keyword_words[0]
    source_label = event.platform or "unknown source"
    if event.source_id:
        src = db.query(Source).filter(Source.id == event.source_id).first()
        if src and src.name:
            source_label = src.name

    # Determine risk level based on entity's current risk score
    risk_score = entity.risk_score or 0.0
    risk_level = _score_to_level(risk_score)

    entity_label = entity.display_name or entity.primary_identifier
    title = f"Keyword '{first}' detected in {source_label} post by {entity_label}"
    if len(keyword_words) > 1:
        title += f" (+{len(keyword_words) - 1} more matches)"
    description = (
        f"Matched keywords: {', '.join(keyword_words)}. "
        f"Categories: {', '.join(categories)}. "
        f"Platform: {event.platform or 'n/a'}. "
        f"Entity risk score: {risk_score:.2f}."
    )

    alert = RiskAlert(
        id=gen_uuid(),
        entity_id=str(entity.id),
        event_id=str(event.id),
        alert_type=AlertType.KEYWORD_MATCH,
        title=title,
        description=description,
        risk_score=risk_score,
        risk_level=risk_level,
        status=AlertStatus.NEW,
        trigger_event_id=str(event.id),
        matched_pattern=f"Keywords: {', '.join(keyword_words[:3])}",
        risk_factors=[
            {
                "factor": "keyword_match",
                "detail": f"Matched: {', '.join(keyword_words)}",
                "weight": 0.25,
            }
        ],
        evidence_data={
            "matched_keywords":  matched_keywords,
            "event_platform":    event.platform,
            "event_url":         event.url,
            "content_snippet":   event.content[:300] if event.content else "",
        },
    )

    try:
        db.add(alert)
        db.flush()
        logger.debug(
            f"[Stage 7a] KEYWORD_MATCH alert created for entity "
            f"{entity.primary_identifier} | keywords={keyword_words}"
        )
        return alert
    except Exception as exc:
        db.rollback()
        db.add(event)   # re-attach after rollback
        logger.warning(f"[Stage 7a] Failed to create keyword alert: {exc}")
        return None


def _create_risk_threshold_alert(
    db: Session,
    entity: Entity,
    event: RawEvent,
) -> Optional[RiskAlert]:
    """
    Stage 7b: Create a risk threshold alert when an entity's score >= 6.5.

    Uses the entity's risk_factors JSONB (written by entity resolution /
    risk_scorer service) as the evidence. Avoids creating duplicate alerts
    by checking for an existing NEW/UNDER_REVIEW alert for the same entity.

    Returns the created RiskAlert or None.
    """
    # Check for existing open alert on this entity to avoid alert flooding
    existing = (
        db.query(RiskAlert)
        .filter(
            RiskAlert.entity_id == str(entity.id),
            RiskAlert.status.in_([AlertStatus.NEW, AlertStatus.UNDER_REVIEW]),
            RiskAlert.alert_type == AlertType.ANOMALY_DETECTED,
        )
        .first()
    )
    if existing:
        # Update the risk score on the existing alert if it changed
        if abs((existing.risk_score or 0) - (entity.risk_score or 0)) > 0.1:
            existing.risk_score = entity.risk_score
            existing.risk_level = _score_to_level(entity.risk_score)
            existing.updated_at = datetime.now(timezone.utc)
            db.flush()
            logger.debug(
                f"[Stage 7b] Updated existing alert score for entity "
                f"{entity.primary_identifier} → {entity.risk_score:.2f}"
            )
        return None   # don't create a duplicate

    risk_score = entity.risk_score or 0.0
    risk_level = _score_to_level(risk_score)

    alert = RiskAlert(
        id=gen_uuid(),
        entity_id=str(entity.id),
        event_id=str(event.id),
        alert_type=AlertType.ANOMALY_DETECTED,
        title=(
            f"High-risk entity detected: "
            f"{entity.display_name or entity.primary_identifier} "
            f"(score {risk_score:.1f}/10)"
        ),
        description=(
            f"Entity '{entity.primary_identifier}' ({entity.entity_type}) "
            f"has reached risk score {risk_score:.2f} — above threshold "
            f"{RISK_ALERT_THRESHOLD}. Triggered by event on "
            f"{event.platform or 'unknown source'}."
        ),
        risk_score=risk_score,
        risk_level=risk_level,
        status=AlertStatus.NEW,
        trigger_event_id=str(event.id),
        matched_pattern="risk_score_threshold",
        risk_factors=entity.risk_factors or [],
        evidence_data={
            "entity_type":          entity.entity_type,
            "primary_identifier":   entity.primary_identifier,
            "event_count":          entity.event_count,
            "anomaly_score":        entity.anomaly_score,
            "sentiment_avg":        entity.sentiment_avg,
            "trigger_event_url":    event.url,
            "trigger_platform":     event.platform,
            "content_snippet":      event.content[:300] if event.content else "",
        },
    )

    try:
        db.add(alert)
        db.flush()
        logger.info(
            f"[Stage 7b] RISK ALERT created for entity "
            f"{entity.primary_identifier} | "
            f"score={risk_score:.2f} | level={risk_level}"
        )
        return alert
    except Exception as exc:
        db.rollback()
        db.add(event)   # re-attach after rollback
        logger.warning(f"[Stage 7b] Failed to create risk alert: {exc}")
        return None


def _dispatch_posted_relationship(event: RawEvent) -> None:
    """
    Stage 9 (supplementary): Fire-and-forget Neo4j POSTED relationship.
    Dispatches directly to the neo4j_sync task's merge_posted method
    via a small wrapper task defined below.
    """
    try:
        sync_posted_relationship_task.delay(
            handle=event.author_handle,
            event_id=str(event.id),
            platform=event.platform or "",
            published_at=(
                event.published_at.isoformat()
                if event.published_at
                else ""
            ),
        )
    except Exception as exc:
        logger.warning(
            f"[Stage 9] Failed to dispatch POSTED relationship for "
            f"handle={event.author_handle}: {exc}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# SUPPLEMENTARY TASKS
# ═════════════════════════════════════════════════════════════════════════════

@celery_app.task(
    name="tasks.enrich.sync_posted_relationship_task",
    max_retries=2,
    default_retry_delay=10,
    acks_late=True,
)
def sync_posted_relationship_task(
    self,
    handle: str,
    event_id: str,
    platform: str,
    published_at: str,
) -> bool:
    """
    Small task that writes the SocialAccount -[:POSTED]-> Event
    relationship into Neo4j.

    Separated from the main enrich task so its retries don't block
    the main pipeline.
    """
    from app.tasks.neo4j_sync import _sync_service, _get_driver
    from neo4j.exceptions import ServiceUnavailable

    try:
        driver = _get_driver()
        with driver.session(database="neo4j") as session:
            return _sync_service.merge_posted_relationship(
                session=session,
                handle=handle,
                event_id=event_id,
                platform=platform,
                published_at=published_at,
            )
    except ServiceUnavailable as exc:
        raise self.retry(exc=exc, countdown=10)
    except Exception as exc:
        logger.warning(
            f"[sync_posted_relationship_task] Failed for handle={handle}: {exc}"
        )
        return False


# ═════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═════════════════════════════════════════════════════════════════════════════

def _score_to_level(score: float) -> str:
    """
    Convert a numeric risk score to a RiskLevel enum string.
    Mirrors the RiskLevel enum thresholds in models/__init__.py.

      LOW:      0.0 – 4.0
      MEDIUM:   4.0 – 6.5
      HIGH:     6.5 – 8.5
      CRITICAL: 8.5 – 10.0
    """
    if score >= 8.5:
        return RiskLevel.CRITICAL
    if score >= 6.5:
        return RiskLevel.HIGH
    if score >= 4.0:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _is_transient_error(exc: Exception) -> bool:
    """
    Determine whether an exception is transient (worth retrying).
    Returns True for DB connection errors, lock timeouts, etc.
    Returns False for programming errors or data issues.
    """
    from sqlalchemy.exc import OperationalError, TimeoutError as SATimeout
    transient_types = (OperationalError, SATimeout, ConnectionError, TimeoutError)
    return isinstance(exc, transient_types)