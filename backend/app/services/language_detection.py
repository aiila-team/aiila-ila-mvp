"""
services/language_detection.py
──────────────────────────────────────────────────────────────────────────────
Language Detection Service for ILA — Intelligence Layer for Analytics

Responsibility:
  Detect the language of each incoming raw_events.content and map it to a
  value in the Language enum defined in models/__init__.py.

  Result is stored in:
      raw_events.content_language  (Enum(Language))

Why this matters for ILA:
  - Downstream sentiment analysis (IndicBERT) needs to know whether text is
    Hindi/Urdu/Bengali etc. to pick the right tokenizer path.
  - Multilingual OCR (Day 5) uses this to select Tesseract language packs.
  - The analyst dashboard filters alerts by language for regional desks.

Library: langdetect
  - Wrapper around Google's language-detection library (Naive Bayes on
    character n-gram profiles).
  - Supports 55 languages including all ILA-relevant Indic scripts.
  - Non-deterministic by default → we seed it for reproducibility.
  - Falls back to Language.UNKNOWN on any failure (short text, mixed script,
    encoding issues).

Supported Language enum values (from models/__init__.py):
    en  → English
    hi  → Hindi  (Devanagari)
    ur  → Urdu   (Nastaliq / Devanagari transliteration)
    bn  → Bengali
    ta  → Tamil
    te  → Telugu
    mr  → Marathi (Devanagari — distinct profile from Hindi)
    pa  → Punjabi (Gurmukhi)
    unknown → anything else / detection failure

Design decisions:
  - We call detect_langs() (returns ranked list) rather than detect()
    (returns single top result) so we can apply a minimum-confidence gate.
  - CONFIDENCE_THRESHOLD = 0.70 → below this we return UNKNOWN to avoid
    mis-labelling short, mixed, or transliterated text.
  - Minimum text length = 20 chars; below this langdetect is unreliable.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from langdetect import detect_langs, LangDetectException
from langdetect.lang_detect_exception import ErrorCode
from langdetect import DetectorFactory
from loguru import logger

# ── Reproducibility seed ──────────────────────────────────────────────────────
# langdetect uses a random seed internally; fix it so the same text always
# returns the same result across Celery workers.
DetectorFactory.seed = 42

# ── Configuration ─────────────────────────────────────────────────────────────

CONFIDENCE_THRESHOLD: float = 0.70
"""
Minimum probability for a language detection result to be accepted.
Below this we return UNKNOWN rather than guess.
Rationale: Indic language text in Roman script (Hinglish, Romanagari)
often scores 0.4–0.65 for 'hi' — too low to rely on. 0.70 empirically
eliminates most false positives while catching clear Devanagari/Bengali/Tamil.
"""

MIN_TEXT_LENGTH: int = 20
"""
Minimum character count before attempting detection.
langdetect frequently misclassifies texts shorter than ~15–20 chars.
"""

# ── Language Code Mapping ─────────────────────────────────────────────────────
# Maps langdetect ISO 639-1 codes → Language enum string values
# from models/__init__.py Language enum.
#
# Note on Urdu: langdetect returns "ur" but also sometimes misclassifies
# Urdu Nastaliq as "fa" (Farsi). We map "fa" → "ur" as a pragmatic
# approximation given ILA's Indian threat context.
#
# Note on Marathi vs Hindi: both use Devanagari. langdetect distinguishes
# them based on vocabulary. Confidence is often lower for Marathi (~0.65–0.80)
# so setting threshold at 0.70 may occasionally return UNKNOWN for short
# Marathi texts — acceptable for MVP.

_LANGDETECT_TO_LANGUAGE_ENUM: dict[str, str] = {
    "en": "en",
    "hi": "hi",
    "ur": "ur",
    "fa": "ur",   # Farsi misclassification of Urdu Nastaliq → treat as Urdu
    "bn": "bn",
    "ta": "ta",
    "te": "te",
    "mr": "mr",
    "pa": "pa",
}

# ── Data Contract ─────────────────────────────────────────────────────────────

@dataclass
class LanguageDetectionResult:
    """
    Return value of LanguageDetectionService.detect().

    Fields:
        language      : Language enum value string (e.g. "hi", "en", "unknown")
                        Store this directly in raw_events.content_language
        confidence    : Detection probability 0.0–1.0
                        (0.0 means unknown / below threshold)
        raw_code      : The raw ISO 639-1 code returned by langdetect
                        (None if detection failed entirely)
        all_candidates: Full ranked list from langdetect, for debug logging
                        [(lang_code, probability), ...]
    """
    language: str
    confidence: float
    raw_code: Optional[str]
    all_candidates: list[tuple[str, float]]

    @property
    def is_indic(self) -> bool:
        """True if the detected language is one of ILA's supported Indic languages."""
        return self.language in ("hi", "ur", "bn", "ta", "te", "mr", "pa")

    @property
    def is_unknown(self) -> bool:
        return self.language == "unknown"


# ── Service ───────────────────────────────────────────────────────────────────

class LanguageDetectionService:
    """
    Stateless language detection service. Safe to instantiate once per
    Celery worker and call from multiple tasks.

    Usage (in tasks/enrich.py):
        from services.language_detection import LanguageDetectionService

        _lang_svc = LanguageDetectionService()

        @app.task
        def enrich_event_task(event_id: str):
            event = db.get(RawEvent, event_id)
            result = _lang_svc.detect(event.content)
            event.content_language = result.language   # e.g. "hi"
            db.commit()

    Or use the top-level convenience function:
        from services.language_detection import detect_language
        lang = detect_language(event.content)   # returns "hi", "en", "unknown", etc.
    """

    def __init__(
        self,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
        min_text_length: int = MIN_TEXT_LENGTH,
    ):
        self.confidence_threshold = confidence_threshold
        self.min_text_length = min_text_length
        logger.info(
            f"LanguageDetectionService initialized | "
            f"threshold={confidence_threshold} | min_len={min_text_length}"
        )

    def detect(self, text: str) -> LanguageDetectionResult:
        """
        Detect the language of `text` and return a LanguageDetectionResult.

        Args:
            text: Raw content from raw_events.content. May contain URLs,
                  handles, mixed scripts, or Indic text.

        Returns:
            LanguageDetectionResult. Always returns a result — never raises.
            On any failure (too short, exception, low confidence) → language="unknown"
        """
        _UNKNOWN = LanguageDetectionResult(
            language="unknown",
            confidence=0.0,
            raw_code=None,
            all_candidates=[],
        )

        if not text or not text.strip():
            return _UNKNOWN

        # Strip URLs and handles before detection — they skew the classifier
        # toward English because they're ASCII regardless of the actual language.
        cleaned = _preprocess_for_detection(text)

        if len(cleaned) < self.min_text_length:
            logger.debug(
                f"Text too short after preprocessing ({len(cleaned)} chars), "
                f"returning UNKNOWN. Original length: {len(text)}"
            )
            return _UNKNOWN

        # Run langdetect
        try:
            candidates = detect_langs(cleaned)  # returns list of Language objects
        except LangDetectException as exc:
            if exc.code == ErrorCode.CantDetectError:
                logger.debug(f"langdetect: CantDetectError on text of length {len(cleaned)}")
            else:
                logger.warning(f"langdetect failed: {exc}")
            return _UNKNOWN
        except Exception as exc:
            logger.error(f"Unexpected error in language detection: {exc}")
            return _UNKNOWN

        if not candidates:
            return _UNKNOWN

        # candidates is a list of langdetect Language objects with .lang and .prob
        all_candidates = [(c.lang, round(c.prob, 4)) for c in candidates]
        top = candidates[0]

        # Apply confidence gate
        if top.prob < self.confidence_threshold:
            logger.debug(
                f"Top language '{top.lang}' confidence {top.prob:.3f} below threshold "
                f"{self.confidence_threshold}. Returning UNKNOWN. "
                f"Candidates: {all_candidates}"
            )
            return LanguageDetectionResult(
                language="unknown",
                confidence=round(top.prob, 4),
                raw_code=top.lang,
                all_candidates=all_candidates,
            )

        # Map to Language enum value
        mapped = _LANGDETECT_TO_LANGUAGE_ENUM.get(top.lang)

        if mapped is None:
            # Language detected but not in ILA's supported set
            logger.debug(
                f"Detected language '{top.lang}' (conf={top.prob:.3f}) not in "
                f"ILA supported set. Returning UNKNOWN."
            )
            return LanguageDetectionResult(
                language="unknown",
                confidence=round(top.prob, 4),
                raw_code=top.lang,
                all_candidates=all_candidates,
            )

        logger.debug(
            f"Language detected: '{mapped}' (raw='{top.lang}', conf={top.prob:.3f})"
        )

        return LanguageDetectionResult(
            language=mapped,
            confidence=round(top.prob, 4),
            raw_code=top.lang,
            all_candidates=all_candidates,
        )

    def detect_batch(self, texts: list[str]) -> list[LanguageDetectionResult]:
        """
        Detect language for a batch of texts.
        langdetect has no native batch API, so this is a simple loop.
        Suitable for Celery batch tasks.

        Args:
            texts: List of raw content strings.

        Returns:
            List of LanguageDetectionResult in same order as input.
        """
        return [self.detect(t) for t in texts]


# ── Text Preprocessing ────────────────────────────────────────────────────────

def _preprocess_for_detection(text: str) -> str:
    """
    Strip noise that skews language detection toward English:
      - URLs (https://..., www....)
      - @handles and #hashtags
      - Emojis and special symbols (keep letters, digits, spaces, punctuation)
      - Collapse whitespace

    Deliberately keeps:
      - Indic script characters (Devanagari, Bengali, Tamil, Telugu, etc.)
      - Punctuation (helps n-gram profiles)
      - Numbers (low impact on language detection)
    """
    import re
    import unicodedata

    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)

    # Remove @handles and #hashtags
    text = re.sub(r"[@#]\w+", " ", text)

    # Remove emoji and symbols (keep letters, marks, numbers, punctuation, spaces)
    # Unicode categories: L=letter, M=mark, N=number, P=punctuation, Z=separator
    cleaned_chars = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith(("L", "M", "N", "P", "Z")):
            cleaned_chars.append(ch)
        else:
            cleaned_chars.append(" ")  # replace symbol/emoji with space

    text = "".join(cleaned_chars)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ── Module-level singleton ────────────────────────────────────────────────────

_default_service: Optional[LanguageDetectionService] = None


def get_language_service() -> LanguageDetectionService:
    """Return the module-level singleton. Safe to call from Celery workers."""
    global _default_service
    if _default_service is None:
        _default_service = LanguageDetectionService()
    return _default_service


def detect_language(text: str) -> str:
    """
    Convenience function for use in Celery enrich_task.
    Returns the Language enum value string directly.

    Example (tasks/enrich.py):
        from services.language_detection import detect_language
        event.content_language = detect_language(event.content)
        # → "hi", "en", "bn", "unknown", etc.
    """
    return get_language_service().detect(text).language


def detect_language_full(text: str) -> LanguageDetectionResult:
    """
    Convenience function returning the full result object.
    Use when you also need confidence or candidate list for logging/debugging.
    """
    return get_language_service().detect(text)
