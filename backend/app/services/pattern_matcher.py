"""
services/pattern_matcher.py
──────────────────────────────────────────────────────────────────────────────
Pattern Matcher + Composite Risk Scorer — ILA Day 3 Afternoon

Two responsibilities in one file:
  1. PatternMatcher  — evaluate fraud_templates.json rules against entity data
  2. RiskScorer      — compute the composite 0–10 risk score

Composite Risk Score Formula (from MVP plan):
  risk_score = (
      anomaly_score        * 0.30   ← Isolation Forest signal
    + pattern_match_score  * 0.25   ← fraud template match strength
    + network_centrality   * 0.20   ← graph connectivity (Neo4j PageRank)
    + velocity_score       * 0.15   ← activity rate (txn/post per hour)
    + sentiment_score      * 0.10   ← negative sentiment (IndicBERT)
  ) * source_reliability_multiplier

All component scores are normalised to [0.0, 1.0] before weighting.
Final score is scaled to [0.0, 10.0] for analyst readability.

Usage (in tasks/enrich.py or a dedicated score_risk_task):
    from services.pattern_matcher import compute_risk_score, RiskInput

    risk_input = RiskInput(
        entity_type       = "upi_account",
        anomaly_score     = 0.87,
        sentiment_score   = -0.72,   # from sentiment.py
        network_centrality = 0.45,   # from Neo4j PageRank
        source_reliability = 1.0,    # source.reliability_multiplier
        features          = {
            "transaction_count_1h": 47,
            "unique_recipients_1h": 23,
            "avg_amount_deviation": 3.4,
            "post_frequency_1h":    0,
            "has_upi_alias":        True,
            "has_crypto_alias":     False,
        },
        has_crypto_alias  = False,
        has_upi_alias     = True,
    )
    result = compute_risk_score(risk_input)
    # result.final_score    → 8.34
    # result.risk_level     → "high"
    # result.top_factors    → ["Anomaly: 47 txn/h", "Template FT-001 matched", ...]
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from loguru import logger

# ── Template loading ───────────────────────────────────────────────────────────

_TEMPLATES_PATH: str = os.getenv(
    "FRAUD_TEMPLATES_PATH",
    str(Path(__file__).parent.parent / "data" / "fraud_templates.json"),
)

def _load_templates() -> list[dict]:
    """Load and cache fraud_templates.json. Called once at import time."""
    try:
        with open(_TEMPLATES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        templates = data.get("templates", [])
        logger.info(f"Loaded {len(templates)} fraud pattern templates from {_TEMPLATES_PATH}")
        return templates
    except FileNotFoundError:
        logger.error(f"fraud_templates.json not found at {_TEMPLATES_PATH}. Pattern matching disabled.")
        return []
    except json.JSONDecodeError as exc:
        logger.error(f"Invalid JSON in fraud_templates.json: {exc}")
        return []

_TEMPLATES: list[dict] = _load_templates()


# ── Risk level thresholds (mirrors models/__init__.py RiskLevel) ───────────────

def _score_to_level(score_0_to_10: float) -> str:
    if score_0_to_10 >= 8.5:
        return "critical"
    if score_0_to_10 >= 6.5:
        return "high"
    if score_0_to_10 >= 4.0:
        return "medium"
    return "low"


# ── Input / Output contracts ───────────────────────────────────────────────────

@dataclass
class RiskInput:
    """
    All the data needed to compute a composite risk score for one entity.

    Fields that come from other services:
      anomaly_score      ← anomaly_detector.detect_anomaly()       (0–1)
      sentiment_score    ← sentiment.analyze_sentiment()           (-1 to +1)
      network_centrality ← Neo4j PageRank score on entity node     (0–1)
      source_reliability ← source.reliability_multiplier           (0.3–1.5)
      features           ← same dict passed to anomaly_detector    (raw values)
      entity_type        ← entity.entity_type string
    """
    # Required ML/graph signals
    anomaly_score: float = 0.0
    sentiment_score: float = 0.0        # -1.0 to +1.0 (will be converted to 0–1)
    network_centrality: float = 0.0

    # Source multiplier
    source_reliability: float = 1.0     # default tier-2 multiplier

    # Raw feature dict (same as anomaly_detector input)
    features: dict = field(default_factory=dict)

    # Entity context (used by pattern matcher)
    entity_type: str = "unknown"
    has_crypto_alias: bool = False
    has_upi_alias: bool = False
    device_change_flag: bool = False
    domain_similarity_score: float = 0.0
    domain_age_days: int = 999
    linked_domain_count: int = 0
    network_hop_distance: int = 99


@dataclass
class RiskScoreResult:
    """
    The complete output of compute_risk_score().

    Fields:
      final_score        : 0.0–10.0 (store in entities.risk_score)
      risk_level         : "low" | "medium" | "high" | "critical"
      component_scores   : Each weighted component before summing
      matched_templates  : List of matched fraud template IDs + names
      top_factors        : Human-readable top-3 risk factors (for entities.risk_factors)
      pattern_match_score: Raw pattern match score before weighting (0–1)
    """
    final_score: float
    risk_level: str
    component_scores: dict[str, float]
    matched_templates: list[dict]
    top_factors: list[dict]
    pattern_match_score: float


# ═════════════════════════════════════════════════════════════════════════════
# PATTERN MATCHER
# ═════════════════════════════════════════════════════════════════════════════

class PatternMatcher:
    """
    Evaluates all fraud pattern templates against a RiskInput.

    Condition operators supported:
      gte, lte, gt, lt, eq, neq, in, not_in

    Template modes:
      "all" (default) → ALL conditions must pass
      "any"           → AT LEAST ONE condition must pass
    """

    def __init__(self, templates: list[dict] = _TEMPLATES):
        self._templates = templates

    def evaluate(self, risk_input: RiskInput) -> tuple[float, list[dict]]:
        """
        Evaluate all templates against the input.

        Returns:
            (pattern_match_score, matched_templates)
            pattern_match_score: 0.0–1.0 (weighted sum of matched template weights)
            matched_templates:   list of {id, name, weight, alert_type} dicts
        """
        matched: list[dict] = []
        total_weight = 0.0

        # Build a flat lookup dict from RiskInput for condition evaluation
        lookup = self._build_lookup(risk_input)

        for tmpl in self._templates:
            if self._template_matches(tmpl, lookup):
                matched.append({
                    "id":         tmpl["id"],
                    "name":       tmpl["name"],
                    "weight":     tmpl["weight"],
                    "alert_type": tmpl["alert_type"],
                    "severity":   tmpl["severity"],
                })
                total_weight += tmpl["weight"]

        # Normalise to [0, 1] — if multiple templates match, cap at 1.0
        pattern_score = min(1.0, total_weight / 1.0)

        if matched:
            logger.debug(
                f"Pattern matcher: {len(matched)} template(s) matched | "
                f"score={pattern_score:.3f} | "
                f"ids={[m['id'] for m in matched]}"
            )

        return round(pattern_score, 4), matched

    def _build_lookup(self, r: RiskInput) -> dict[str, Any]:
        """
        Flatten RiskInput + features into a single dict for condition evaluation.
        Condition 'field' values reference keys in this dict.
        """
        lookup: dict[str, Any] = {
            # From features dict
            **r.features,
            # Direct RiskInput fields
            "entity_type":            r.entity_type,
            "anomaly_score":          r.anomaly_score,
            "sentiment_score":        r.sentiment_score,
            "network_centrality":     r.network_centrality,
            "has_crypto_alias":       r.has_crypto_alias,
            "has_upi_alias":          r.has_upi_alias,
            "device_change_flag":     r.device_change_flag,
            "domain_similarity_score":r.domain_similarity_score,
            "domain_age_days":        r.domain_age_days,
            "linked_domain_count":    r.linked_domain_count,
            "network_hop_distance":   r.network_hop_distance,
        }
        # Defaults for features not in the input
        lookup.setdefault("transaction_count_1h",  0.0)
        lookup.setdefault("unique_recipients_1h",  0.0)
        lookup.setdefault("avg_amount_deviation",  0.0)
        lookup.setdefault("post_frequency_1h",     0.0)
        lookup.setdefault("unique_platforms_1h",   1.0)
        lookup.setdefault("keyword_hit_rate",      0.0)
        lookup.setdefault("reply_ratio",           0.0)
        return lookup

    def _template_matches(self, template: dict, lookup: dict[str, Any]) -> bool:
        """Returns True if the template's conditions are satisfied."""
        conditions = template.get("conditions", [])
        mode = template.get("mode", "all")

        if not conditions:
            return False

        results = [self._check_condition(c, lookup) for c in conditions]

        if mode == "any":
            return any(results)
        return all(results)     # mode == "all" (default)

    @staticmethod
    def _check_condition(condition: dict, lookup: dict[str, Any]) -> bool:
        """Evaluate a single condition rule against the lookup dict."""
        field   = condition.get("field")
        op      = condition.get("operator")
        target  = condition.get("value")

        if field is None or op is None:
            return False

        # Get actual value from lookup; skip condition if field not present
        actual = lookup.get(field)
        if actual is None:
            # Field not in lookup — condition cannot be evaluated → not matched
            return False

        try:
            if op == "gte":
                return float(actual) >= float(target)
            elif op == "lte":
                return float(actual) <= float(target)
            elif op == "gt":
                return float(actual) > float(target)
            elif op == "lt":
                return float(actual) < float(target)
            elif op == "eq":
                # Handle bool comparison carefully
                if isinstance(target, bool):
                    return bool(actual) == target
                return actual == target
            elif op == "neq":
                return actual != target
            elif op == "in":
                return actual in target
            elif op == "not_in":
                return actual not in target
            else:
                logger.warning(f"Unknown operator '{op}' in pattern condition")
                return False
        except (TypeError, ValueError) as exc:
            logger.debug(f"Condition eval error ({field} {op} {target}): {exc}")
            return False


# ═════════════════════════════════════════════════════════════════════════════
# COMPOSITE RISK SCORER
# ═════════════════════════════════════════════════════════════════════════════

# Module-level matcher singleton
_matcher = PatternMatcher()


def compute_risk_score(risk_input: RiskInput) -> RiskScoreResult:
    """
    Compute the composite risk score for an entity.

    Formula (all components in [0, 1] before weighting):
      risk_score_0_1 = (
          anomaly_score        * 0.30
        + pattern_match_score  * 0.25
        + network_centrality   * 0.20
        + velocity_score       * 0.15
        + sentiment_score_norm * 0.10
      ) * source_reliability_multiplier

    Final score is scaled to [0, 10].

    Args:
        risk_input: RiskInput dataclass with all signals populated.

    Returns:
        RiskScoreResult with final_score, risk_level, components, and factors.
    """

    # ── Component 1: Anomaly score (already 0–1) ──────────────────────────────
    anomaly = max(0.0, min(1.0, risk_input.anomaly_score))

    # ── Component 2: Pattern match score ─────────────────────────────────────
    pattern_score, matched_templates = _matcher.evaluate(risk_input)

    # ── Component 3: Network centrality (already 0–1 from PageRank) ──────────
    centrality = max(0.0, min(1.0, risk_input.network_centrality))

    # ── Component 4: Velocity score ───────────────────────────────────────────
    # Derived from raw feature values.
    # High transaction/post rate → high velocity score.
    velocity = _compute_velocity_score(risk_input.features)

    # ── Component 5: Sentiment score (convert -1…+1 → 0…1) ───────────────────
    # Negative sentiment is a risk signal, so we invert:
    #   -1.0 (very negative) → 1.0 (max risk contribution)
    #    0.0 (neutral)       → 0.5
    #   +1.0 (positive)      → 0.0 (no risk contribution)
    sentiment_norm = (1.0 - risk_input.sentiment_score) / 2.0
    sentiment_norm = max(0.0, min(1.0, sentiment_norm))

    # ── Weighted sum ──────────────────────────────────────────────────────────
    weights = {
        "anomaly":          0.30,
        "pattern_match":    0.25,
        "network_centrality": 0.20,
        "velocity":         0.15,
        "sentiment":        0.10,
    }
    components = {
        "anomaly":            round(anomaly,          4),
        "pattern_match":      round(pattern_score,    4),
        "network_centrality": round(centrality,       4),
        "velocity":           round(velocity,         4),
        "sentiment":          round(sentiment_norm,   4),
    }

    weighted_sum = sum(
        components[name] * weights[name]
        for name in weights
    )

    # Apply source reliability multiplier (0.3 – 1.5)
    multiplier = max(0.1, min(1.5, risk_input.source_reliability))
    score_0_1 = weighted_sum * multiplier

    # Scale to 0–10
    final_score = round(min(10.0, score_0_1 * 10.0), 2)
    risk_level = _score_to_level(final_score)

    # ── Top-3 risk factors for analyst explainability ─────────────────────────
    top_factors = _build_top_factors(
        components=components,
        weights=weights,
        matched_templates=matched_templates,
        risk_input=risk_input,
    )

    logger.debug(
        f"Risk score computed | score={final_score} | level={risk_level} | "
        f"components={components} | multiplier={multiplier}"
    )

    return RiskScoreResult(
        final_score=final_score,
        risk_level=risk_level,
        component_scores=components,
        matched_templates=matched_templates,
        top_factors=top_factors,
        pattern_match_score=pattern_score,
    )


def _compute_velocity_score(features: dict) -> float:
    """
    Derive a 0–1 velocity score from raw feature values.

    Uses a sigmoid-like normalisation:
      transaction_count_1h: 0 → 0.0, 50 → ~1.0
      post_frequency_1h:    0 → 0.0, 100 → ~1.0
    Takes the max of the two so high activity on EITHER dimension is flagged.
    """
    txn_rate  = float(features.get("transaction_count_1h", 0.0))
    post_rate = float(features.get("post_frequency_1h",    0.0))

    # Normalise: divide by typical "max normal" values
    # transaction: 50/h is extreme, post: 100/h is extreme
    txn_norm  = min(1.0, txn_rate  / 50.0)
    post_norm = min(1.0, post_rate / 100.0)

    # Take the higher of the two signals
    return round(max(txn_norm, post_norm), 4)


def _build_top_factors(
    components: dict[str, float],
    weights: dict[str, float],
    matched_templates: list[dict],
    risk_input: RiskInput,
) -> list[dict]:
    """
    Build a human-readable top-3 risk factor list.
    Stored in entities.risk_factors (JSONB) and shown in the analyst UI.

    Format: [{"factor": "...", "detail": "...", "contribution": 0.XX}, ...]
    """
    # Compute each component's absolute contribution to the final score
    contributions = [
        {
            "key":          name,
            "label":        _COMPONENT_LABELS[name],
            "contribution": round(components[name] * weights[name], 4),
            "raw_value":    components[name],
        }
        for name in components
    ]

    # Sort by contribution descending
    contributions.sort(key=lambda x: x["contribution"], reverse=True)

    factors = []
    for item in contributions[:3]:
        detail = _format_factor_detail(item["key"], item["raw_value"], risk_input)
        factors.append({
            "factor":       item["label"],
            "detail":       detail,
            "contribution": item["contribution"],
        })

    # Inject matched template names as context (append to factor detail)
    if matched_templates and factors:
        template_names = ", ".join(t["id"] for t in matched_templates[:2])
        factors[0]["detail"] += f" | Matched: {template_names}"

    return factors


_COMPONENT_LABELS: dict[str, str] = {
    "anomaly":            "Transaction/Behaviour Anomaly",
    "pattern_match":      "Fraud Pattern Match",
    "network_centrality": "Graph Network Centrality",
    "velocity":           "Activity Velocity",
    "sentiment":          "Negative Sentiment",
}


def _format_factor_detail(key: str, value: float, r: RiskInput) -> str:
    """Return a concrete, data-driven detail string for each factor."""
    if key == "anomaly":
        txn = r.features.get("transaction_count_1h", 0)
        return f"Anomaly score {value:.2f} — {txn:.0f} transactions in last hour"
    elif key == "pattern_match":
        return f"Pattern match score {value:.2f} across {len(_TEMPLATES)} templates"
    elif key == "network_centrality":
        return f"Network centrality {value:.2f} (PageRank — highly connected node)"
    elif key == "velocity":
        txn = r.features.get("transaction_count_1h", 0)
        posts = r.features.get("post_frequency_1h", 0)
        return f"Velocity score {value:.2f} — {txn:.0f} txn/h, {posts:.0f} posts/h"
    elif key == "sentiment":
        return (
            f"Sentiment {r.sentiment_score:.2f} "
            f"({'negative' if r.sentiment_score < -0.3 else 'neutral/positive'})"
        )
    return f"Score {value:.2f}"


# ── Convenience top-level function ────────────────────────────────────────────

def score_entity(
    anomaly_score: float = 0.0,
    sentiment_score: float = 0.0,
    network_centrality: float = 0.0,
    source_reliability: float = 1.0,
    features: Optional[dict] = None,
    entity_type: str = "unknown",
    **kwargs,
) -> RiskScoreResult:
    """
    Thin wrapper around compute_risk_score() for quick calls without
    manually constructing a RiskInput dataclass.

    Usage in tasks/enrich.py or score_risk_task:
        from services.pattern_matcher import score_entity
        result = score_entity(
            anomaly_score=0.87,
            sentiment_score=-0.65,
            network_centrality=0.40,
            source_reliability=1.0,
            features={"transaction_count_1h": 47, ...},
            entity_type="upi_account",
            has_upi_alias=True,
        )
        entity.risk_score   = result.final_score
        entity.risk_level   = result.risk_level
        entity.risk_factors = result.top_factors
    """
    return compute_risk_score(
        RiskInput(
            anomaly_score=anomaly_score,
            sentiment_score=sentiment_score,
            network_centrality=network_centrality,
            source_reliability=source_reliability,
            features=features or {},
            entity_type=entity_type,
            has_crypto_alias=kwargs.get("has_crypto_alias", False),
            has_upi_alias=kwargs.get("has_upi_alias", False),
            device_change_flag=kwargs.get("device_change_flag", False),
            domain_similarity_score=kwargs.get("domain_similarity_score", 0.0),
            domain_age_days=kwargs.get("domain_age_days", 999),
            linked_domain_count=kwargs.get("linked_domain_count", 0),
            network_hop_distance=kwargs.get("network_hop_distance", 99),
        )
    )
