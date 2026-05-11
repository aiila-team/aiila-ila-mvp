"""
services/source_reliability.py
──────────────────────────────────────────────────────────────────────────────
Source Reliability Scoring Service — ILA Day 4

Responsibility:
  Assign a reliability multiplier (0.3 – 1.5) to every data source.
  This multiplier feeds directly into the composite risk score formula:

      risk_score = weighted_sum * source_reliability_multiplier

  A high-confidence government source (1.5x) amplifies signals.
  A suspected disinformation channel (0.3x) dampens them.

Tier System:
  Tier 1 (1.5x) — Government portals, verified security agencies, accredited
                   news agencies (ANI, PTI, DD News)
  Tier 2 (1.0x) — Mainstream news (NDTV, TOI, Hindustan Times), verified
                   social accounts with blue checkmarks
  Tier 3 (0.7x) — Unverified social media, anonymous Telegram channels,
                   citizen journalism
  Tier 4 (0.3x) — Dark web sources, suspected disinformation outlets,
                   anonymous tipsters

Config:  data/source_tiers.json  (loaded at import, cached)
DB sync: After scoring, updates sources.reliability_multiplier column.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

# ── Config path ────────────────────────────────────────────────────────────────

_TIERS_PATH: str = os.getenv(
    "SOURCE_TIERS_PATH",
    str(Path(__file__).parent.parent / "data" / "source_tiers.json"),
)

# ── Tier multipliers ───────────────────────────────────────────────────────────

TIER_MULTIPLIERS: dict[str, float] = {
    "tier1": 1.5,
    "tier2": 1.0,
    "tier3": 0.7,
    "tier4": 0.3,
}

DEFAULT_TIER       = "tier3"
DEFAULT_MULTIPLIER = TIER_MULTIPLIERS[DEFAULT_TIER]


# ── Load source tiers config ───────────────────────────────────────────────────

def _load_tiers() -> dict:
    """Load source_tiers.json. Returns empty dict on failure."""
    try:
        with open(_TIERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Source tiers config loaded from {_TIERS_PATH}")
        return data
    except FileNotFoundError:
        logger.warning(f"source_tiers.json not found at {_TIERS_PATH}. Using defaults.")
        return {}
    except json.JSONDecodeError as exc:
        logger.error(f"Invalid JSON in source_tiers.json: {exc}")
        return {}


_TIERS_CONFIG: dict = _load_tiers()


# ── Data contract ──────────────────────────────────────────────────────────────

@dataclass
class SourceReliabilityResult:
    """
    Result of scoring one source.

    Fields:
        tier              : "tier1" | "tier2" | "tier3" | "tier4"
        multiplier        : float (0.3 – 1.5)
        matched_rule      : which rule matched (domain/keyword/explicit)
        confidence        : how confident we are in this tier assignment
    """
    tier: str
    multiplier: float
    matched_rule: str
    confidence: float


# ── Core scoring logic ─────────────────────────────────────────────────────────

class SourceReliabilityService:
    """
    Scores a source's reliability tier based on:
      1. Explicit mapping in source_tiers.json (highest priority)
      2. Domain pattern matching (e.g. *.gov.in → tier1)
      3. Source type heuristics (e.g. source_type="dark_web" → tier4)
      4. Default: tier3

    Usage:
        svc = SourceReliabilityService()
        result = svc.score_source(source)
        source.reliability_multiplier = result.multiplier
        source.tier = result.tier
    """

    def __init__(self):
        self._explicit: dict[str, str] = {}    # name/url → tier
        self._domain_patterns: list[tuple[re.Pattern, str]] = []
        self._type_map: dict[str, str] = {}
        self._build_lookup()

    def _build_lookup(self) -> None:
        """Build fast lookup structures from the loaded JSON config."""
        cfg = _TIERS_CONFIG

        # Explicit source name mappings
        for tier, entries in cfg.get("explicit_sources", {}).items():
            for entry in entries:
                self._explicit[entry.lower()] = tier

        # Domain pattern rules (supports wildcards via regex)
        for tier, patterns in cfg.get("domain_patterns", {}).items():
            for pat in patterns:
                # Convert glob-style * to regex .*
                regex = re.compile(
                    re.escape(pat).replace(r"\*", ".*"),
                    re.IGNORECASE,
                )
                self._domain_patterns.append((regex, tier))

        # Source type → tier mapping
        self._type_map = cfg.get("source_type_tiers", {
            "government":         "tier1",
            "verified_news":      "tier1",
            "mainstream_news":    "tier2",
            "verified_social":    "tier2",
            "rss":                "tier2",
            "social_media":       "tier3",
            "telegram":           "tier3",
            "anonymous":          "tier3",
            "dark_web":           "tier4",
            "disinformation":     "tier4",
            "unverified":         "tier3",
        })

        logger.debug(
            f"SourceReliabilityService built: "
            f"{len(self._explicit)} explicit, "
            f"{len(self._domain_patterns)} domain patterns, "
            f"{len(self._type_map)} type rules"
        )

    def score(
        self,
        name: str = "",
        url: str = "",
        source_type: str = "",
        current_tier: Optional[str] = None,
    ) -> SourceReliabilityResult:
        """
        Score a source and return its reliability tier + multiplier.

        Args:
            name         : sources.name
            url          : sources.url
            source_type  : sources.source_type
            current_tier : sources.tier (if already set — highest priority)

        Returns:
            SourceReliabilityResult
        """
        # Priority 1: use current tier if already explicitly assigned in DB
        if current_tier and current_tier in TIER_MULTIPLIERS:
            return SourceReliabilityResult(
                tier=current_tier,
                multiplier=TIER_MULTIPLIERS[current_tier],
                matched_rule="explicit_db_tier",
                confidence=1.0,
            )

        name_lower = (name or "").lower().strip()
        url_lower  = (url  or "").lower().strip()

        # Priority 2: explicit name match from config
        for key in (name_lower, url_lower):
            if key in self._explicit:
                tier = self._explicit[key]
                return SourceReliabilityResult(
                    tier=tier,
                    multiplier=TIER_MULTIPLIERS[tier],
                    matched_rule=f"explicit_config:{key}",
                    confidence=0.99,
                )

        # Priority 3: domain pattern match
        for pattern, tier in self._domain_patterns:
            if url_lower and pattern.search(url_lower):
                return SourceReliabilityResult(
                    tier=tier,
                    multiplier=TIER_MULTIPLIERS[tier],
                    matched_rule=f"domain_pattern:{pattern.pattern}",
                    confidence=0.90,
                )

        # Priority 4: source type heuristic
        stype = (source_type or "").lower().strip()
        if stype in self._type_map:
            tier = self._type_map[stype]
            return SourceReliabilityResult(
                tier=tier,
                multiplier=TIER_MULTIPLIERS[tier],
                matched_rule=f"source_type:{stype}",
                confidence=0.80,
            )

        # Priority 5: keyword scan on name
        tier = self._keyword_scan(name_lower, url_lower)
        return SourceReliabilityResult(
            tier=tier,
            multiplier=TIER_MULTIPLIERS[tier],
            matched_rule="keyword_heuristic",
            confidence=0.65,
        )

    def score_source(self, source) -> SourceReliabilityResult:
        """
        Convenience: score a SQLAlchemy Source ORM object directly.

        Usage:
            result = svc.score_source(source_obj)
            source_obj.reliability_multiplier = result.multiplier
            source_obj.tier = result.tier
        """
        return self.score(
            name=getattr(source, "name", ""),
            url=getattr(source, "url", ""),
            source_type=getattr(source, "source_type", ""),
            current_tier=getattr(source, "tier", None),
        )

    def _keyword_scan(self, name: str, url: str) -> str:
        """Fallback: scan name/URL for tier-indicative keywords."""
        combined = f"{name} {url}"

        tier1_keywords = (
            "gov.in", "nic.in", "mha.gov", "cbi.gov", "ib.gov",
            "ndtv.com", "aninews", "ptinews", "ddnews",
            "police.gov", "army.mil", "mod.gov",
        )
        tier4_keywords = (
            "onion", "darkweb", "dark-web", "leaks", "telegram/anon",
            "disinformation", "propaganda_channel",
        )

        for kw in tier4_keywords:
            if kw in combined:
                return "tier4"
        for kw in tier1_keywords:
            if kw in combined:
                return "tier1"

        return DEFAULT_TIER


# ── Module-level singleton ─────────────────────────────────────────────────────

_svc: Optional[SourceReliabilityService] = None


def get_reliability_service() -> SourceReliabilityService:
    global _svc
    if _svc is None:
        _svc = SourceReliabilityService()
    return _svc


def score_source_url(url: str, source_type: str = "") -> float:
    """
    Quick one-liner: get the multiplier for a URL.
    Used in ingest.py when a new source is registered.
    """
    return get_reliability_service().score(url=url, source_type=source_type).multiplier
