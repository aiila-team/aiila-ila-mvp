"""
services/entity_resolution.py
──────────────────────────────────────────────────────────────────────────────
Entity Resolution Service — exact, alias, fuzzy (person), and upsert paths.

Fix (Day 4): replaced `from thefuzz import fuzz` with `from rapidfuzz import fuzz`.
thefuzz is NOT in requirements.txt; rapidfuzz is (v3.9.7) and has identical API.

Generated with Claude assistance — reviewed by Likhitha
──────────────────────────────────────────────────────────────────────────────
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rapidfuzz import fuzz

from app.models import Entity, EntityAlias, EntityType

logger = logging.getLogger(__name__)


class EntityResolutionService:
    def __init__(self, fuzzy_threshold: int = 85):
        self.fuzzy_threshold = fuzzy_threshold

    def normalize_text(self, text: str) -> str:
        return " ".join(text.lower().strip().split())

    def _coerce_entity_type(self, raw: str) -> EntityType:
        if isinstance(raw, EntityType):
            return raw
        try:
            return EntityType(str(raw).lower())
        except ValueError:
            return EntityType.OTHER

    def resolve(
        self,
        db: Session,
        entity_type: str,
        value: str,
        confidence: float = 1.0,
        source_platform: str = "",
        source_event_id: str = "",
    ) -> Optional[Entity]:
        """
        Resolve one extracted surface form to a canonical Entity (find or create).
        Flushes only; never commits — enrichment owns the transaction boundary.
        """
        if not entity_type or not value:
            return None

        et = self._coerce_entity_type(entity_type)
        norm_value = self.normalize_text(value)

        # 1. Exact match
        existing_entity = (
            db.query(Entity)
            .filter(
                Entity.entity_type == et,
                func.lower(Entity.primary_identifier) == norm_value,
            )
            .first()
        )
        if existing_entity:
            return existing_entity

        # 2. Alias lookup
        existing_alias = (
            db.query(EntityAlias)
            .filter(func.lower(EntityAlias.alias_value) == norm_value)
            .first()
        )
        if existing_alias:
            parent = db.query(Entity).filter(Entity.id == existing_alias.entity_id).first()
            if parent:
                return parent

        # 3. Non-person → create immediately (phones, emails, UPI are unique identifiers)
        if et != EntityType.PERSON:
            return self._create_entity(db, et, value)

        # 4. Fuzzy match (persons only, first-character blocking)
        first_char = norm_value[0] if norm_value else ""
        candidates = (
            db.query(Entity)
            .filter(
                Entity.entity_type == EntityType.PERSON,
                func.lower(func.substr(Entity.primary_identifier, 1, 1)) == first_char,
            )
            .all()
        )

        best_match: Optional[Entity] = None
        highest_score = 0
        for person in candidates:
            score = fuzz.token_sort_ratio(norm_value, (person.display_name or "").lower())
            if score > highest_score:
                highest_score = score
                best_match = person

        if highest_score >= self.fuzzy_threshold and best_match:
            logger.info(
                "FUZZY RESOLUTION: %r → %r (score=%s)",
                value,
                best_match.display_name,
                highest_score,
            )
            self._create_alias(db, best_match.id, value, highest_score)
            return best_match

        # 5. Create new person entity
        logger.debug("Created new person entity for: %s", value)
        return self._create_entity(db, EntityType.PERSON, value)

    def resolve_entities(
        self, db: Session, extracted_entities: List[Dict[str, Any]]
    ) -> List[Entity]:
        """Batch helper; does not commit."""
        out: List[Entity] = []
        for ent in extracted_entities:
            e = self.resolve(
                db,
                ent.get("entity_type") or "",
                ent.get("value") or "",
                float(ent.get("confidence") or 1.0),
                str(ent.get("source_platform") or ""),
                str(ent.get("source_event_id") or ""),
            )
            if e:
                out.append(e)
        return out

    def _create_entity(self, db: Session, e_type: EntityType, value: str) -> Entity:
        new_ent = Entity(
            entity_type=e_type,
            primary_identifier=value,
            display_name=value,
            risk_score=0.0,
        )
        db.add(new_ent)
        db.flush()
        return new_ent

    def _create_alias(self, db: Session, parent_id, value: str, score: int) -> None:
        try:
            new_alias = EntityAlias(
                entity_id=parent_id,
                alias_type="name_variation",
                alias_value=value,
                confidence=score / 100.0,
            )
            db.add(new_alias)
            db.flush()
        except IntegrityError:
            db.rollback()  # alias already exists
        except Exception as e:
            logger.debug(f"Could not create alias '{value}': {e}")


_default_resolution: Optional[EntityResolutionService] = None


def get_resolution_service() -> EntityResolutionService:
    global _default_resolution
    if _default_resolution is None:
        _default_resolution = EntityResolutionService()
    return _default_resolution