"""
<<<<<<< HEAD
services/entity_extraction.py
──────────────────────────────────────────────────────────────────────────────
Entity Extraction Service for ILA — Intelligence Layer for Analytics

Responsibility:
  Scan raw, messy text and extract actionable threat-relevant entities using:
    1. spaCy NER   → person names
    2. Custom Regex → Indian-specific identifiers (phone, UPI, email, handles)

Output:
  A list of ExtractedEntity objects (type, value, confidence) that map directly
  to the `extracted_entities` JSONB column in the `raw_events` table.

Entity types produced here align with the EntityType enum in models/__init__.py:
  PERSON, PHONE, EMAIL, UPI_ACCOUNT, SOCIAL_HANDLE, TELEGRAM
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from typing import List, Optional

import spacy
from loguru import logger

# ── Model Loading ─────────────────────────────────────────────────────────────
# Load once at import time; spaCy models are expensive to reload.
# Falls back gracefully if the model is not installed.

_NLP: Optional[spacy.language.Language] = None


def _load_nlp() -> spacy.language.Language:
    global _NLP
    if _NLP is None:
        try:
            _NLP = spacy.load("en_core_web_sm")
            logger.info("spaCy model 'en_core_web_sm' loaded successfully.")
        except OSError:
            logger.warning(
                "spaCy model 'en_core_web_sm' not found. "
                "Run: python -m spacy download en_core_web_sm\n"
                "Person-name extraction will be disabled until model is installed."
            )
            # Return a blank model so regex extraction still works
            _NLP = spacy.blank("en")
    return _NLP


# ── Data Contract ─────────────────────────────────────────────────────────────

@dataclass
class ExtractedEntity:
    """
    A single entity pulled from raw text.

    Fields:
        entity_type  : matches EntityType enum values from models/__init__.py
        value        : the normalized/canonical form of the identifier
        raw_value    : the original string as found in the text (before normalization)
        confidence   : 0.0 – 1.0 (regex rules are deterministic; NER uses spaCy score)
        start_char   : character offset in original text (useful for highlighting)
        end_char     : end offset
    """
    entity_type: str
    value: str
    raw_value: str
    confidence: float
    start_char: int = 0
    end_char: int = 0

    def to_dict(self) -> dict:
        """Serialize for JSONB storage in raw_events.extracted_entities."""
        return asdict(self)


# ── Regex Patterns ────────────────────────────────────────────────────────────
#
# Each pattern is a tuple of (entity_type, compiled_regex, normalizer_fn, confidence)
# Confidence reflects how structurally certain a regex match is.
#
#   PHONE       — Indian mobile numbers (+91 prefix or leading 0/none, 10 digits)
#   UPI_ACCOUNT — UPI VPA format: localpart@provider  (e.g. 9876543210@paytm)
#   EMAIL       — Standard RFC-ish email (relaxed for threat text which is often messy)
#   TELEGRAM    — Telegram handles: @username (3–32 chars, alphanumeric + underscore)
#   SOCIAL_HANDLE — Twitter/X handles: @username (differentiated from Telegram by context)
#   IMEI        — 15-digit IMEI numbers (Indian telecom investigations)
#   CRYPTO_WALLET — Bitcoin/Ethereum wallet addresses

# ─── Normalizers ──────────────────────────────────────────────────────────────

def _norm_phone(raw: str) -> str:
    """
    Normalize any Indian phone variant to +91XXXXXXXXXX canonical form.

    Handles:
      +91-9876543210  →  +919876543210
      +91 98765 43210 →  +919876543210
      09876543210     →  +919876543210
      9876543210      →  +919876543210
      91-9876543210   →  +919876543210
    """
    digits = re.sub(r"\D", "", raw)          # strip all non-digits
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]                  # strip country code
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]                  # strip leading 0
    return f"+91{digits}" if len(digits) == 10 else raw


def _norm_upi(raw: str) -> str:
    """Lowercase and strip spaces from UPI VPA."""
    return raw.strip().lower()


def _norm_email(raw: str) -> str:
    return raw.strip().lower()


def _norm_handle(raw: str) -> str:
    """Lowercase the handle, keep the @."""
    return raw.strip().lower()


def _identity(raw: str) -> str:
    return raw.strip()


# ─── Pattern Registry ─────────────────────────────────────────────────────────

_PATTERNS: list[tuple[str, re.Pattern, callable, float]] = [

    # ── Indian Phone Numbers ──────────────────────────────────────────────────
    # Covers: +91-XXXXXXXXXX, +91 XXXXXXXXXX, 0XXXXXXXXXX, plain 10-digit
    # Indian mobile series start with 6/7/8/9
    (
        "phone",
        re.compile(
            r"""
            (?:(?:\+91|91)[\s\-]?)?   # optional country code
            (?:0)?                     # optional trunk prefix
            [6-9]\d{9}                 # 10-digit mobile number starting 6-9
            """,
            re.VERBOSE,
        ),
        _norm_phone,
        0.95,
    ),

    # ── UPI Virtual Payment Addresses ────────────────────────────────────────
    # Format: alphanumeric/dots/hyphens @ provider_handle
    # Common providers: paytm, gpay, ybl, okaxis, oksbi, ibl, upi, apl, etc.
    # Must appear BEFORE email pattern (UPI is a subset of email-like strings)
    (
        "upi_account",
        re.compile(
            r"""
            (?<![a-zA-Z0-9._%+\-])   # no word char before (avoid partial email match)
            [a-zA-Z0-9.\-_+]{2,64}   # local part (UPI VPA localpart)
            @                         # separator
            (?:                       # known UPI handles (non-capturing)
                paytm|gpay|ybl|okaxis|oksbi|ibl|upi|apl|okhdfcbank|
                okicici|axisbank|sbi|hdfcbank|kotak|indus|federal|
                naviaxis|freecharge|mobikwik|airtel|jio|barodampay|
                allbank|utibankAxispaytm|[a-z]{2,20}  # catch-all for any UPI provider
            )
            (?![a-zA-Z0-9.\-])        # not followed by domain continuation (avoids emails)
            """,
            re.VERBOSE | re.IGNORECASE,
        ),
        _norm_upi,
        0.90,
    ),

    # ── Email Addresses ───────────────────────────────────────────────────────
    # Standard email; runs AFTER UPI so UPI handles are not double-counted
    (
        "email",
        re.compile(
            r"[a-zA-Z0-9._%+\-]{1,64}"   # local part
            r"@"
            r"[a-zA-Z0-9.\-]+"            # domain
            r"\."
            r"[a-zA-Z]{2,10}",            # TLD
        ),
        _norm_email,
        0.92,
    ),

    # ── Telegram Handles ──────────────────────────────────────────────────────
    # @username: 5–32 chars, alphanumeric + underscore, no leading digit
    # Telegram usernames must be 5+ chars; we loosen to 3 to catch short threat handles
    (
        "telegram",
        re.compile(
            r"(?<!\w)"           # word boundary before @
            r"@([a-zA-Z][a-zA-Z0-9_]{2,31})"  # capture group: letter-first username
            r"(?!\w)",           # word boundary after
        ),
        _norm_handle,
        0.85,
    ),

    # ── Twitter / X Handles ───────────────────────────────────────────────────
    # Structurally identical to Telegram handles; context in platform field
    # distinguishes them. We tag as social_handle generically here and let
    # entity_resolution.py refine based on source platform.
    # NOTE: Same regex as Telegram intentionally — platform-aware tagging downstream.
    (
        "social_handle",
        re.compile(
            r"(?<!\w)"
            r"@([a-zA-Z][a-zA-Z0-9_]{2,14})"  # Twitter max 15 chars
            r"(?!\w)",
        ),
        _norm_handle,
        0.80,
    ),

    # ── IMEI Numbers ─────────────────────────────────────────────────────────
    # 15 consecutive digits (Luhn-validated optionally below)
    (
        "imei",
        re.compile(r"(?<!\d)\d{15}(?!\d)"),
        _identity,
        0.75,
    ),

    # ── Crypto Wallet Addresses ───────────────────────────────────────────────
    # Bitcoin P2PKH/P2SH (starts 1 or 3, 25-34 chars)
    # Ethereum (0x + 40 hex chars)
    (
        "crypto_wallet",
        re.compile(
            r"(?:"
            r"(?:0x[a-fA-F0-9]{40})"         # Ethereum
            r"|"
            r"(?:[13][a-km-zA-HJ-NP-Z1-9]{24,33})"  # Bitcoin
            r")"
        ),
        _identity,
        0.88,
    ),
]


# ── Core Extraction Logic ─────────────────────────────────────────────────────

def _extract_by_regex(text: str) -> list[ExtractedEntity]:
    """
    Run all regex patterns against text and return deduplicated ExtractedEntity list.

    Deduplication strategy:
      - Track character spans already claimed by a higher-confidence pattern.
      - If a new match overlaps an existing span, skip it.
      - This prevents UPI handles from also being tagged as emails.
    """
    results: list[ExtractedEntity] = []
    claimed_spans: list[tuple[int, int]] = []  # (start, end) of already-matched regions

    def _spans_overlap(new_start: int, new_end: int) -> bool:
        for s, e in claimed_spans:
            if new_start < e and new_end > s:
                return True
        return False

    # Patterns are ordered by priority (UPI before email, etc.)
    for entity_type, pattern, normalizer, confidence in _PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()

            # Use group(1) if the pattern has a capture group (handles), else group(0)
            raw_value = match.group(1) if match.lastindex else match.group(0)

            # Skip if this span is already covered by a higher-priority match
            if _spans_overlap(start, end):
                continue

            # Skip handles that are suspiciously short (likely noise)
            if entity_type in ("telegram", "social_handle") and len(raw_value) < 3:
                continue

            # Validate IMEI with Luhn algorithm
            if entity_type == "imei" and not _luhn_check(raw_value):
                continue

            normalized = normalizer(raw_value)
            results.append(
                ExtractedEntity(
                    entity_type=entity_type,
                    value=normalized,
                    raw_value=raw_value,
                    confidence=confidence,
                    start_char=start,
                    end_char=end,
                )
            )
            claimed_spans.append((start, end))

    return results


def _extract_persons_spacy(text: str) -> list[ExtractedEntity]:
    """
    Use spaCy NER to find PERSON entities.
    Returns an ExtractedEntity with confidence derived from spaCy's ent score
    (spaCy doesn't expose per-entity confidence in en_core_web_sm, so we use 0.78
    as a calibrated default for PERSON labels — reflecting the model's ~78% precision
    on out-of-domain Indian names).
    """
    nlp = _load_nlp()
    results: list[ExtractedEntity] = []

    try:
        doc = nlp(text)
    except Exception as exc:
        logger.warning(f"spaCy processing failed: {exc}")
        return results

    seen_names: set[str] = set()

    for ent in doc.ents:
        if ent.label_ not in ("PERSON", "PER"):
            continue

        name = ent.text.strip()

        # Filter noise: single-char names, all-numeric, or already seen
        if len(name) < 2 or name.isdigit() or name.lower() in seen_names:
            continue

        seen_names.add(name.lower())

        results.append(
            ExtractedEntity(
                entity_type="person",
                value=name,
                raw_value=name,
                confidence=0.78,
                start_char=ent.start_char,
                end_char=ent.end_char,
            )
        )

    return results


def _luhn_check(number: str) -> bool:
    """
    Validate a numeric string using the Luhn algorithm.
    Used to filter false-positive IMEI matches.
    """
    digits = [int(d) for d in number if d.isdigit()]
    if not digits:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def _deduplicate_results(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    """
    Final deduplication pass on the combined (regex + NER) results.
    Two entities are considered duplicates if they share the same
    (entity_type, normalized value).
    Keeps the entry with the higher confidence score.
    """
    seen: dict[tuple[str, str], ExtractedEntity] = {}
    for ent in entities:
        key = (ent.entity_type, ent.value.lower())
        if key not in seen or ent.confidence > seen[key].confidence:
            seen[key] = ent
    return list(seen.values())


# ── Public API ────────────────────────────────────────────────────────────────

class EntityExtractionService:
    """
    Main service class. Instantiate once (in a Celery worker or FastAPI lifespan)
    and call extract() on each raw event.

    Usage:
        service = EntityExtractionService()
        entities = service.extract("Contact @raju_op on Telegram or pay 9876543210@paytm")
        # → [ExtractedEntity(telegram, @raju_op, ...), ExtractedEntity(upi_account, ...)]

        # For Celery task / DB storage:
        raw_event.extracted_entities = [e.to_dict() for e in entities]
    """

    def __init__(self, enable_ner: bool = True):
        self.enable_ner = enable_ner
        if enable_ner:
            _load_nlp()  # eagerly load spaCy model at startup

    def extract(self, text: str, source_platform: str = "") -> list[ExtractedEntity]:
        """
        Extract all entities from a raw text string.

        Args:
            text            : Raw content from raw_events.content
            source_platform : Platform hint (e.g. "telegram", "twitter").
                              Used to disambiguate social_handle vs telegram labels.

        Returns:
            List of ExtractedEntity objects, deduplicated, sorted by start_char.
        """
        if not text or not text.strip():
            return []

        # Step 1: Regex-based extraction (phone, UPI, email, handles, IMEI, crypto)
        regex_entities = _extract_by_regex(text)

        # Step 2: spaCy NER for person names
        ner_entities = _extract_persons_spacy(text) if self.enable_ner else []

        # Step 3: Platform-aware handle disambiguation
        # If source is explicitly Telegram, upgrade social_handle → telegram
        if source_platform.lower() == "telegram":
            for ent in regex_entities:
                if ent.entity_type == "social_handle":
                    ent.entity_type = "telegram"
        elif source_platform.lower() in ("twitter", "twitter_x", "x"):
            for ent in regex_entities:
                if ent.entity_type == "telegram":
                    ent.entity_type = "social_handle"

        # Step 4: Combine and deduplicate
        all_entities = regex_entities + ner_entities
        deduped = _deduplicate_results(all_entities)

        # Step 5: Sort by position in text for readability
        deduped.sort(key=lambda e: e.start_char)

        logger.debug(
            f"Extracted {len(deduped)} entities from text "
            f"({len(text)} chars, platform='{source_platform}')"
        )
        return deduped

    def extract_to_dict(self, text: str, source_platform: str = "") -> list[dict]:
        """
        Convenience method that returns serialized dicts for direct JSONB storage.
        Use this in Celery tasks:
            event.extracted_entities = service.extract_to_dict(event.content, event.platform)
        """
        return [e.to_dict() for e in self.extract(text, source_platform)]


# ── Module-level singleton (for import convenience in Celery tasks) ───────────
_default_service: Optional[EntityExtractionService] = None


def get_extraction_service() -> EntityExtractionService:
    """Return the module-level singleton. Safe to call from Celery workers."""
    global _default_service
    if _default_service is None:
        _default_service = EntityExtractionService()
    return _default_service


def extract_entities(text: str, source_platform: str = "") -> list[ExtractedEntity]:
    """
    Top-level convenience function for quick use in Celery enrich_task.

    Example (in tasks/enrich.py):
        from services.entity_extraction import extract_entities
        entities = extract_entities(event.content, event.platform)
        event.extracted_entities = [e.to_dict() for e in entities]
    """
    return get_extraction_service().extract(text, source_platform)
=======
Entity Extraction Service

This module provides regex-based extraction of entities from text content,
including phone numbers, emails, URLs, crypto wallets, usernames, and social handles.
"""

import re
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Service for extracting various types of entities from text."""

    def __init__(self):
        # Regex patterns for entity extraction
        self.patterns = {
            "phone": re.compile(
                r'(\+?\d{1,3}[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})',
                re.IGNORECASE
            ),
            "email": re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                re.IGNORECASE
            ),
            "url": re.compile(
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
                re.IGNORECASE
            ),
            "crypto_wallet": re.compile(
                r'\b(0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})\b',
                re.IGNORECASE
            ),
            "telegram_handle": re.compile(
                r'@([a-zA-Z0-9_]{5,32})',
                re.IGNORECASE
            ),
            "twitter_handle": re.compile(
                r'@([a-zA-Z0-9_]{1,15})(?=\s|$|[^a-zA-Z0-9_@])',
                re.IGNORECASE
            ),
            "username": re.compile(
                r'\b[a-zA-Z0-9_]{3,30}\b',
                re.IGNORECASE
            ),
        }

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from the given text.

        Args:
            text: The text content to analyze

        Returns:
            List of extracted entities with type, value, and confidence
        """
        entities = []

        # Extract phone numbers
        for match in self.patterns["phone"].findall(text):
            phone = ''.join(match).strip()
            if phone and len(phone) >= 10:
                entities.append({
                    "type": "phone",
                    "value": phone,
                    "confidence": 0.95
                })

        # Extract emails
        for match in self.patterns["email"].findall(text):
            entities.append({
                "type": "email",
                "value": match,
                "confidence": 0.98
            })

        # Extract URLs
        for match in self.patterns["url"].findall(text):
            try:
                parsed = urlparse(match)
                if parsed.netloc:
                    entities.append({
                        "type": "url",
                        "value": match,
                        "confidence": 0.90
                    })
            except:
                continue

        # Extract crypto wallets
        for match in self.patterns["crypto_wallet"].findall(text):
            entities.append({
                "type": "crypto_wallet",
                "value": match,
                "confidence": 0.99
            })

        # Extract Telegram handles
        for match in self.patterns["telegram_handle"].findall(text):
            entities.append({
                "type": "telegram_handle",
                "value": f"@{match}",
                "confidence": 0.85
            })

        # Extract Twitter handles
        for match in self.patterns["twitter_handle"].findall(text):
            entities.append({
                "type": "twitter_handle",
                "value": f"@{match}",
                "confidence": 0.85
            })

        # Extract usernames (lower confidence, only if not already captured)
        existing_values = {e["value"] for e in entities}
        for match in self.patterns["username"].findall(text):
            if match not in existing_values and not match.isdigit():
                entities.append({
                    "type": "username",
                    "value": match,
                    "confidence": 0.60
                })

        # Remove duplicates based on value
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity["type"], entity["value"])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)

        logger.info(f"Extracted {len(unique_entities)} unique entities")
        return unique_entities


# Global instance for easy import
extractor = EntityExtractor()


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Convenience function to extract entities from text.

    Args:
        text: The text content to analyze

    Returns:
        List of extracted entities
    """
    return extractor.extract_entities(text)
>>>>>>> backend-day2
