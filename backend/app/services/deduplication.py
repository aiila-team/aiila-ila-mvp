"""
Deduplication Service

This module provides content deduplication using hashing and similarity comparison
to identify duplicate events.
"""

import hashlib
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from app.models import RawEvent

logger = logging.getLogger(__name__)


class DeduplicationService:
    """Service for detecting duplicate content in events."""

    def __init__(self, db: Session):
        self.db = db
        self.similarity_threshold = 0.95  # For content similarity

    def content_hash(self, content: str) -> str:
        """
        Generate a hash of the content for duplicate detection.

        Args:
            content: The text content to hash

        Returns:
            SHA256 hash of the normalized content
        """
        # Normalize content for hashing
        normalized = content.lower().strip()
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def check_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate similarity between two content strings.

        Args:
            content1: First content string
            content2: Second content string

        Returns:
            Similarity score between 0 and 1
        """
        # Simple Jaccard similarity for demonstration
        # In production, you might use more sophisticated NLP methods
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def find_duplicate(self, content: str, exclude_event_id: Optional[UUID] = None) -> Optional[RawEvent]:
        """
        Find a duplicate event for the given content.

        Args:
            content: The content to check for duplicates
            exclude_event_id: Event ID to exclude from search

        Returns:
            Duplicate RawEvent if found, None otherwise
        """
        content_hash = self.content_hash(content)

        # First, check for exact hash matches
        query = self.db.query(RawEvent).filter(RawEvent.content_hash == content_hash)
        if exclude_event_id:
            query = query.filter(RawEvent.id != exclude_event_id)

        exact_match = query.first()
        if exact_match:
            return exact_match

        # Then, check for similar content (more expensive, limit to recent events)
        recent_events = self.db.query(RawEvent).filter(
            RawEvent.id != exclude_event_id if exclude_event_id else True
        ).order_by(RawEvent.created_at.desc()).limit(1000).all()

        for event in recent_events:
            similarity = self.check_similarity(content, event.content)
            if similarity >= self.similarity_threshold:
                return event

        return None

    def mark_as_duplicate(self, event: RawEvent, duplicate_of: RawEvent):
        """
        Mark an event as a duplicate of another.

        Args:
            event: The event to mark as duplicate
            duplicate_of: The original event
        """
        event.is_duplicate = True
        event.duplicate_of = duplicate_of.id
        logger.info(f"Marked event {event.id} as duplicate of {duplicate_of.id}")


def check_duplicates(db: Session, content: str, event_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Check if content is duplicate and return duplicate information.

    Args:
        db: Database session
        content: Content to check
        event_id: Current event ID to exclude

    Returns:
        Dict with duplicate status and information
    """
    service = DeduplicationService(db)
    duplicate = service.find_duplicate(content, event_id)

    if duplicate:
        return {
            "is_duplicate": True,
            "duplicate_of": duplicate.id,
            "duplicate_event": duplicate
        }
    else:
        return {
            "is_duplicate": False
        }