"""
services/risk_scorer.py
──────────────────────────────────────────────────────────────────────────────
Risk scoring engine for ILA entities.

This service calculates a composite risk score on a 0–10 scale using
multiple intelligence signals, then returns an explainable scoring result.
"""

import logging
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Entity, RawEvent, Source
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)


class RiskScorer:
    """Calculates explainable, normalized entity risk scores."""

    SIGNAL_NAMES = [
        "anomaly_score",
        "pattern_match_score",
        "network_centrality",
        "velocity_score",
        "sentiment_score",
    ]

    def __init__(self):
        self.weights: Dict[str, float] = settings.RISK_SCORE_WEIGHTS
        self.reliability_map: Dict[str, float] = settings.SOURCE_RELIABILITY_MAP
        self.threshold: float = settings.RISK_ALERT_THRESHOLD

    def calculate_risk_score(self, entity_id: str) -> dict[str, Any]:
        """Calculate the composite risk score for a given entity."""
        db = SessionLocal()
        try:
            entity = self._load_entity(db, entity_id)
            events = self._load_entity_events(entity)

            signals = {
                "anomaly_score": self._compute_anomaly_score(entity, events),
                "pattern_match_score": self._compute_pattern_match_score(entity, events),
                "network_centrality": self._compute_network_centrality(entity_id),
                "velocity_score": self._compute_velocity_score(entity, events),
                "sentiment_score": self._compute_sentiment_score(entity, events),
            }

            multiplier = self._compute_source_reliability_multiplier(events)
            raw_score = sum(signals[name] * self.weights.get(name, 0.0) for name in self.SIGNAL_NAMES)
            risk_score = self._normalize(raw_score * multiplier)
            risk_level = self._score_to_level(risk_score)
            explanation = self._build_explanation(signals, multiplier, risk_score)

            return {
                "entity_id": str(entity.id),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "signals": {
                    **signals,
                    "source_reliability_multiplier": multiplier,
                },
                "explanation": explanation,
            }
        finally:
            db.close()

    def _load_entity(self, db: Session, entity_id: str) -> Entity:
        entity = db.query(Entity).filter(Entity.id == UUID(entity_id)).first()
        if entity is None:
            raise ValueError(f"Entity {entity_id} not found")
        return entity

    def _load_entity_events(self, entity: Entity) -> list[RawEvent]:
        # Use the ORM relationship if available; fall back to an explicit query.
        if entity.raw_events is not None:
            return list(entity.raw_events)
        return []

    def _compute_anomaly_score(self, entity: Entity, events: list[RawEvent]) -> float:
        if entity.anomaly_score is not None and entity.anomaly_score > 0:
            value = float(entity.anomaly_score)
        else:
            values = [self._normalize_anomaly(evt.anomaly_score) for evt in events if evt.anomaly_score is not None]
            value = mean(values) if values else 0.0

        value = self._normalize(value)
        logger.debug(f"[risk] anomaly_score={value:.2f} for entity={entity.id}")
        return value

    def _normalize_anomaly(self, raw: float) -> float:
        if raw is None:
            return 0.0
        raw_value = float(raw)
        return raw_value if raw_value > 1.0 else raw_value * 10.0

    def _compute_pattern_match_score(self, entity: Entity, events: list[RawEvent]) -> float:
        total_matches = 0
        for evt in events:
            if isinstance(evt.matched_keywords, list):
                total_matches += len(evt.matched_keywords)

        if total_matches == 0 and entity.is_flagged:
            score = 2.5
        else:
            score = min(10.0, total_matches * 1.8)

        if entity.is_flagged:
            score = min(10.0, score + 1.5)

        logger.debug(f"[risk] pattern_match_score={score:.2f} for entity={entity.id} (matches={total_matches})")
        return self._normalize(score)

    def _compute_network_centrality(self, entity_id: str) -> float:
        try:
            neighbors = graph_service.get_entity_neighbors(entity_id, hops=1)
            degree = max(0, neighbors.node_count - 1)
            score = min(10.0, float(degree))
            logger.debug(f"[risk] network_centrality={score:.2f} for entity={entity_id} (degree={degree})")
            return score
        except Exception as exc:
            logger.warning(f"[risk] Graph lookup failed for centrality of {entity_id}: {exc}")
            return 0.0

    def _compute_velocity_score(self, entity: Entity, events: list[RawEvent]) -> float:
        if not events:
            return 0.0

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        recent_count = sum(1 for evt in events if evt.timestamp and evt.timestamp >= cutoff)
        score = min(10.0, recent_count * 2.0)

        if recent_count >= 10:
            score = 10.0
        elif recent_count >= 5:
            score = max(score, 7.5)

        logger.debug(f"[risk] velocity_score={score:.2f} for entity={entity.id} (recent_count={recent_count})")
        return self._normalize(score)

    def _compute_sentiment_score(self, entity: Entity, events: list[RawEvent]) -> float:
        values = []
        if entity.sentiment_avg is not None:
            values.append(float(entity.sentiment_avg))

        for evt in events:
            if evt.sentiment_score is not None:
                values.append(float(evt.sentiment_score))

        if not values:
            return 0.0

        avg_sentiment = mean(values)
        score = 0.0
        if avg_sentiment < 0:
            score = min(10.0, abs(avg_sentiment) * 10.0)

        logger.debug(f"[risk] sentiment_score={score:.2f} for entity={entity.id} (avg_sentiment={avg_sentiment:.2f})")
        return self._normalize(score)

    def _compute_source_reliability_multiplier(self, events: list[RawEvent]) -> float:
        labels: List[str] = []
        for evt in events:
            if evt.source is None:
                continue
            labels.append(self._classify_source(evt.source))

        if not labels:
            return self.reliability_map.get("MEDIUM", 1.0)

        if "HIGH" in labels:
            return self.reliability_map.get("HIGH", 1.2)
        if "MEDIUM" in labels:
            return self.reliability_map.get("MEDIUM", 1.0)

        return self.reliability_map.get("LOW", 0.8)

    def _classify_source(self, source: Source) -> str:
        score = 0.0
        if source.credibility_score is not None:
            score = float(source.credibility_score)
        elif source.reliability_multiplier is not None:
            score = float(source.reliability_multiplier) / 1.2

        if score >= 0.75:
            return "HIGH"
        if score >= 0.4:
            return "MEDIUM"
        return "LOW"

    def _score_to_level(self, score: float) -> str:
        if score < 3.0:
            return "low"
        if score < 6.0:
            return "medium"
        if score < 8.0:
            return "high"
        return "critical"

    def _build_explanation(self, signals: Dict[str, float], multiplier: float, score: float) -> List[str]:
        explanation: List[str] = []
        if signals["anomaly_score"] >= 7.0:
            explanation.append("Strong anomaly indicators were detected in recent event data.")
        elif signals["anomaly_score"] >= 4.0:
            explanation.append("Anomaly signals are present in the entity's event history.")

        if signals["pattern_match_score"] >= 6.0:
            explanation.append("Pattern matched known risk templates or suspicious keywords.")
        elif signals["pattern_match_score"] >= 3.0:
            explanation.append("Some suspicious patterns were observed in event activity.")

        if signals["network_centrality"] >= 7.0:
            explanation.append("Entity is highly connected in the graph, indicating potential network risk.")
        elif signals["network_centrality"] >= 4.0:
            explanation.append("Entity is connected to multiple other nodes in the graph.")

        if signals["velocity_score"] >= 7.0:
            explanation.append("High event velocity was detected in the past 24 hours.")
        elif signals["velocity_score"] >= 4.0:
            explanation.append("Event frequency is elevated compared to baseline.")

        if signals["sentiment_score"] >= 5.0:
            explanation.append("Negative sentiment is contributing to the entity's risk score.")

        if multiplier > 1.0:
            explanation.append("Source reliability amplified the overall risk score.")
        elif multiplier < 1.0:
            explanation.append("Lower source reliability reduced the final risk score.")

        if not explanation:
            explanation.append("Risk score was calculated using entity history and available intelligence signals.")

        return explanation

    def _normalize(self, value: float) -> float:
        return round(max(0.0, min(10.0, float(value))), 2)
