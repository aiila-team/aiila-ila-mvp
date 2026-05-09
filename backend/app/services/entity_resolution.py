"""
Entity Resolution Service

This module provides entity resolution using fuzzy string matching with rapidfuzz
to deduplicate and merge entities based on similarity scores.
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple
from uuid import UUID, uuid4

from rapidfuzz import fuzz
from sqlalchemy.orm import Session
from app.models import Entity, EntityAlias, EntityType

logger = logging.getLogger(__name__)


class EntityResolutionService:
    """Service for resolving and merging entities using fuzzy matching."""

    def __init__(self, db: Session):
        self.db = db
        self.similarity_threshold = 0.85

    def normalize_identifier(self, identifier: str) -> str:
        """
        Normalize an identifier for comparison.

        Args:
            identifier: The raw identifier string

        Returns:
            Normalized identifier
        """
        # Convert to lowercase
        normalized = identifier.lower()

        # Remove common prefixes/suffixes
        normalized = re.sub(r'^@+', '', normalized)
        normalized = re.sub(r'^https?://', '', normalized)

        # Remove punctuation and extra spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity score between two strings.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score between 0 and 1
        """
        # Use weighted combination of different fuzzy metrics
        ratio = fuzz.ratio(str1, str2) / 100.0
        token_sort = fuzz.token_sort_ratio(str1, str2) / 100.0
        token_set = fuzz.token_set_ratio(str1, str2) / 100.0

        # Weighted average favoring token-based metrics for entity names
        similarity = (ratio * 0.3) + (token_sort * 0.4) + (token_set * 0.3)

        return similarity

    def find_existing_entity(self, identifier: str, entity_type: str) -> Optional[Entity]:
        """
        Find existing entity by exact or fuzzy match.

        Args:
            identifier: The entity identifier to search for
            entity_type: Type of entity (phone, email, etc.)

        Returns:
            Existing Entity if found, None otherwise
        """
        normalized_id = self.normalize_identifier(identifier)

        # First, try exact match on aliases
        alias = self.db.query(EntityAlias).filter(
            EntityAlias.alias_value == identifier,
            EntityAlias.alias_type == entity_type
        ).first()

        if alias:
            return alias.entity

        # Then, try fuzzy match on aliases
        aliases = self.db.query(EntityAlias).filter(
            EntityAlias.alias_type == entity_type
        ).all()

        best_match = None
        best_score = 0.0

        for alias in aliases:
            normalized_alias = self.normalize_identifier(alias.alias_value)
            similarity = self.calculate_similarity(normalized_id, normalized_alias)

            if similarity > best_score and similarity >= self.similarity_threshold:
                best_score = similarity
                best_match = alias.entity

        return best_match

    def resolve_entity(self, identifier: str, entity_type: str, confidence: float = 1.0) -> Dict[str, Any]:
        """
        Resolve an entity identifier to an existing or new entity.

        Args:
            identifier: The entity identifier
            entity_type: Type of entity
            confidence: Confidence score of the extraction

        Returns:
            Dict with resolution result
        """
        # Try to find existing entity
        existing_entity = self.find_existing_entity(identifier, entity_type)

        if existing_entity:
            # Update existing entity
            self.create_or_update_alias(existing_entity.id, entity_type, identifier, confidence)
            return {
                "action": "updated",
                "entity_id": existing_entity.id,
                "entity": existing_entity
            }
        else:
            # Create new entity
            entity_type_enum = self._map_entity_type(entity_type)
            new_entity = Entity(
                entity_type=entity_type_enum,
                primary_identifier=identifier,
                display_name=identifier,
                metadata_={"created_from": entity_type}
            )

            self.db.add(new_entity)
            self.db.flush()  # Get the ID

            # Create alias
            self.create_or_update_alias(new_entity.id, entity_type, identifier, confidence)

            return {
                "action": "created",
                "entity_id": new_entity.id,
                "entity": new_entity
            }

    def create_or_update_alias(self, entity_id: UUID, alias_type: str, alias_value: str, confidence: float = 1.0):
        """
        Create or update an entity alias.

        Args:
            entity_id: ID of the entity
            alias_type: Type of alias (phone, email, etc.)
            alias_value: The alias value
            confidence: Confidence score
        """
        # Check if alias already exists
        existing_alias = self.db.query(EntityAlias).filter(
            EntityAlias.entity_id == entity_id,
            EntityAlias.alias_type == alias_type,
            EntityAlias.alias_value == alias_value
        ).first()

        if existing_alias:
            # Update confidence if higher
            if confidence > existing_alias.confidence:
                existing_alias.confidence = confidence
                existing_alias.is_verified = confidence > 0.9
        else:
            # Create new alias
            new_alias = EntityAlias(
                entity_id=entity_id,
                alias_type=alias_type,
                alias_value=alias_value,
                confidence=confidence,
                is_verified=confidence > 0.9
            )
            self.db.add(new_alias)

    def _map_entity_type(self, entity_type: str) -> EntityType:
        """
        Map string entity type to EntityType enum.

        Args:
            entity_type: String representation of entity type

        Returns:
            EntityType enum value
        """
        type_mapping = {
            "phone": EntityType.PERSON,
            "email": EntityType.PERSON,
            "telegram_handle": EntityType.PERSON,
            "twitter_handle": EntityType.PERSON,
            "username": EntityType.PERSON,
            "crypto_wallet": EntityType.ORGANIZATION,  # Could be person or org
            "url": EntityType.ORGANIZATION,
        }

        return type_mapping.get(entity_type, EntityType.OTHER)