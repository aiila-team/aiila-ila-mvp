"""
services/deduplication.py
──────────────────────────────────────────────────────────────────────────────
Deduplication Service for ILA — Intelligence Layer for Analytics

Responsibility:
  Detect near-duplicate content in the raw_events stream to:
    - Prevent the same propaganda/spam post from inflating entity risk scores
    - Avoid re-processing content that is structurally identical
    - Surface coordinated inauthentic behavior (same content, many accounts)

Approach:
  MinHash + LSH (Locality-Sensitive Hashing) via the `datasketch` library.
  MinHash generates a compact signature (hash vector) for each document.
  LSH buckets signatures so that similar documents land in the same bucket
  without requiring O(n²) pairwise comparison.

Thresholds:
  SIMILARITY_THRESHOLD = 0.80  → documents sharing ≥80% Jaccard similarity
                                  are considered near-duplicates.
  NUM_PERM             = 128   → number of hash permutations (higher = more
                                  accurate, more memory). 128 is the sweet spot
                                  for threat-text volume at MVP scale.

Integration:
  - Celery enrich_task calls DuplicationService.check() with event content.
  - If is_duplicate=True → set raw_events.is_duplicate=True and
    raw_events.duplicate_of=<original_event_id>, skip further enrichment.
  - The minhash_signature is stored in raw_events.minhash_signature (JSONB)
    so the LSH index can be rebuilt after a restart.

Storage note:
  The in-memory LSH index is rebuilt at worker startup from stored signatures.
  This is sufficient for MVP. Phase 2 should persist the LSH index to Redis
  using datasketch's redis storage backend.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from datasketch import MinHash, MinHashLSH
from loguru import logger

# ── Configuration Constants ───────────────────────────────────────────────────

NUM_PERMUTATIONS: int = 128
"""
Number of hash permutations for MinHash.
Higher → more accurate Jaccard estimate, more memory (each perm = one int64).
128 perms → ~±3% Jaccard estimation error at MVP scale.
"""

SIMILARITY_THRESHOLD: float = 0.80
"""
Jaccard similarity threshold above which two documents are near-duplicates.
0.80 → allows minor edits (timestamps, usernames swapped) while catching
       copy-paste spam and rephrased propaganda.
Tune down to 0.70 if coordinated activity uses heavier paraphrasing.
"""

SHINGLE_SIZE: int = 3
"""
Size of character n-grams (shingles) used to represent a document.
3-char shingles work well for short social-media posts (50–500 chars).
Increase to 5 for longer articles.
"""

MIN_TOKEN_LENGTH: int = 20
"""
Documents shorter than this (in chars) are skipped for deduplication.
Very short texts (e.g. "ok", "yes") produce unreliable MinHash signatures.
"""


# ── Data Contract ─────────────────────────────────────────────────────────────

@dataclass
class DeduplicationResult:
    """
    Return type of DeduplicationService.check().

    Fields:
        is_duplicate     : True if the content matches a previously seen document.
        duplicate_of     : event_id of the original document (None if not duplicate).
        similarity_score : Jaccard similarity to the nearest duplicate (0.0–1.0).
        signature        : The MinHash signature as a list of ints (for JSONB storage).

    Usage in Celery enrich_task:
        result = dedup_service.check(event.id, event.content)
        event.is_duplicate     = result.is_duplicate
        event.duplicate_of     = result.duplicate_of
        event.minhash_signature = result.signature   # store for index rebuild
    """
    is_duplicate: bool
    duplicate_of: Optional[str]     # original raw_events.id (UUID string)
    similarity_score: float         # 0.0 if not duplicate
    signature: list[int]            # MinHash hashvalues for persistence


# ── Text Normalization ─────────────────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    """
    Normalize raw social media / news text before shingling.

    Steps:
      1. Unicode NFC normalization (handles Indic script variants)
      2. Lowercase
      3. Strip URLs (they vary across copies of the same post)
      4. Strip @handles and #hashtags (bots change these between posts)
      5. Collapse whitespace
      6. Strip leading/trailing whitespace

    Goal: two posts with the same substantive content but different
    metadata tokens should hash to the same (or very similar) signature.
    """
    # 1. NFC normalization for Devanagari / other Indic scripts
    text = unicodedata.normalize("NFC", text)

    # 2. Lowercase
    text = text.lower()

    # 3. Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)

    # 4. Remove @handles and #hashtags
    text = re.sub(r"[@#]\w+", "", text)

    # 5. Remove punctuation runs (keep single spaces)
    text = re.sub(r"[^\w\s]", " ", text)

    # 6. Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _shingle(text: str, k: int = SHINGLE_SIZE) -> set[str]:
    """
    Generate a set of k-character shingles from normalized text.

    Example (k=3):
        "hello world" → {"hel", "ell", "llo", "lo ", "o w", " wo", "wor", "orl", "rld"}

    Shingle sets are the input to MinHash. Jaccard similarity between two
    shingle sets approximates semantic similarity for short texts.
    """
    if len(text) < k:
        # Text too short to shingle — return the whole text as one shingle
        return {text} if text else set()
    return {text[i : i + k] for i in range(len(text) - k + 1)}


def _build_minhash(shingles: set[str], num_perm: int = NUM_PERMUTATIONS) -> MinHash:
    """
    Build a MinHash object from a set of shingles.

    Each shingle is encoded to bytes (UTF-8) before hashing, which correctly
    handles Indic script characters.
    """
    m = MinHash(num_perm=num_perm)
    for shingle in shingles:
        m.update(shingle.encode("utf-8"))
    return m


# ── Deduplication Service ──────────────────────────────────────────────────────

class DeduplicationService:
    """
    Stateful deduplication service backed by an in-memory MinHash LSH index.

    The LSH index maps event_ids to MinHash signatures. On each call to
    check(), the new document's signature is queried against the index.
    If a match is found above the similarity threshold, the document is
    flagged as a duplicate.

    Thread safety:
      The datasketch LSH index is NOT thread-safe for concurrent writes.
      In Celery, use one service instance per worker process (prefork model).
      Do NOT share across threads (gevent/eventlet concurrency).

    Startup reconstruction:
      Call rebuild_from_stored_signatures() after worker init to reload
      signatures persisted in the raw_events table. See Celery worker
      on_worker_ready signal.

    Example (in tasks/enrich.py):
        from services.deduplication import DeduplicationService
        _dedup = DeduplicationService()

        @app.task
        def enrich_event_task(event_id: str):
            event = db.get(RawEvent, event_id)
            result = _dedup.check(event.id, event.content)
            event.is_duplicate      = result.is_duplicate
            event.duplicate_of      = result.duplicate_of
            event.minhash_signature = result.signature
            if result.is_duplicate:
                event.is_processed = True   # skip further enrichment
                db.commit()
                return
            # ... rest of enrichment ...
    """

    def __init__(
        self,
        threshold: float = SIMILARITY_THRESHOLD,
        num_perm: int = NUM_PERMUTATIONS,
        shingle_size: int = SHINGLE_SIZE,
    ):
        self.threshold = threshold
        self.num_perm = num_perm
        self.shingle_size = shingle_size

        # LSH index: maps band buckets → candidate event_ids
        self._lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)

        # Lookup: event_id → MinHash object (for similarity scoring)
        self._signatures: dict[str, MinHash] = {}

        logger.info(
            f"DeduplicationService initialized | "
            f"threshold={threshold} | num_perm={num_perm} | shingle_k={shingle_size}"
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def check(self, event_id: str, content: str) -> DeduplicationResult:
        """
        Check whether `content` is a near-duplicate of any previously seen document.

        Workflow:
          1. Normalize text
          2. Build shingles → MinHash signature
          3. Query LSH index for candidates
          4. If candidate found → compute exact Jaccard similarity
          5. If similarity ≥ threshold → return is_duplicate=True
          6. If not duplicate → insert into LSH index for future checks
          7. Always return the signature (caller persists it)

        Args:
            event_id : The raw_events.id UUID string (used as LSH key)
            content  : raw_events.content text

        Returns:
            DeduplicationResult with is_duplicate, duplicate_of, similarity_score, signature
        """
        if not content or len(content.strip()) < MIN_TOKEN_LENGTH:
            logger.debug(f"Event {event_id}: content too short for dedup, skipping.")
            return DeduplicationResult(
                is_duplicate=False,
                duplicate_of=None,
                similarity_score=0.0,
                signature=[],
            )

        # Step 1–2: Normalize and compute MinHash
        normalized = _normalize_text(content)
        shingles = _shingle(normalized, self.shingle_size)

        if not shingles:
            return DeduplicationResult(
                is_duplicate=False,
                duplicate_of=None,
                similarity_score=0.0,
                signature=[],
            )

        minhash = _build_minhash(shingles, self.num_perm)
        signature = minhash.hashvalues.tolist()   # convert numpy array → plain list for JSONB

        # Step 3: Query LSH for approximate nearest neighbours
        try:
            # datasketch.MinHashLSH.query() returns a list of Hashable items.
            # Ensure we coerce to `str` here so downstream code and type
            # annotations remain consistent and Pyright can verify types.
            raw_candidates = self._lsh.query(minhash)
            candidates: list[str] = [str(x) for x in raw_candidates]
        except Exception as exc:
            logger.warning(f"LSH query failed for event {event_id}: {exc}")
            candidates = []

        # Step 4: Find the best (highest similarity) candidate
        best_match_id: Optional[str] = None
        best_similarity: float = 0.0

        for candidate_id in candidates:
            if candidate_id == event_id:
                continue  # don't match against self (re-check scenario)
            candidate_mh = self._signatures.get(candidate_id)
            if candidate_mh is None:
                continue
            jaccard = minhash.jaccard(candidate_mh)
            if jaccard > best_similarity:
                best_similarity = jaccard
                best_match_id = candidate_id

        # Step 5: Decide
        is_dup = best_similarity >= self.threshold

        if is_dup:
            logger.info(
                f"DUPLICATE detected: event={event_id} matches {best_match_id} "
                f"(Jaccard={best_similarity:.3f})"
            )
        else:
            # Step 6: Register this document in the index for future queries
            self._insert(event_id, minhash)

        return DeduplicationResult(
            is_duplicate=is_dup,
            duplicate_of=best_match_id if is_dup else None,
            similarity_score=round(best_similarity, 4),
            signature=signature,
        )

    def rebuild_from_stored_signatures(
        self, stored: list[tuple[str, list[int]]]
    ) -> int:
        """
        Rebuild the in-memory LSH index from signatures stored in PostgreSQL.
        Call this at Celery worker startup.

        Args:
            stored : List of (event_id, signature_list) tuples.
                     Query:  SELECT id, minhash_signature FROM raw_events
                             WHERE minhash_signature IS NOT NULL
                             AND is_duplicate = FALSE

        Returns:
            Number of signatures successfully loaded.

        Example (in celery_app.py @worker_ready signal):
            from sqlalchemy import select
            rows = db.execute(
                select(RawEvent.id, RawEvent.minhash_signature)
                .where(RawEvent.minhash_signature.isnot(None))
                .where(RawEvent.is_duplicate == False)
            ).all()
            dedup_service.rebuild_from_stored_signatures(
                [(str(r.id), r.minhash_signature) for r in rows]
            )
        """
        loaded = 0
        for event_id, sig_list in stored:
            if not sig_list:
                continue
            try:
                mh = self._minhash_from_list(sig_list)
                self._insert(event_id, mh)
                loaded += 1
            except Exception as exc:
                logger.warning(f"Failed to reload signature for {event_id}: {exc}")

        logger.info(f"LSH index rebuilt with {loaded} signatures from database.")
        return loaded

    def remove(self, event_id: str) -> bool:
        """
        Remove a document from the LSH index (e.g. when an event is deleted).

        Returns True if the document was present and removed.
        """
        if event_id not in self._signatures:
            return False
        try:
            self._lsh.remove(event_id)
            del self._signatures[event_id]
            return True
        except Exception as exc:
            logger.warning(f"Failed to remove {event_id} from LSH index: {exc}")
            return False

    @property
    def index_size(self) -> int:
        """Number of documents currently in the LSH index."""
        return len(self._signatures)

    # ── Internal Helpers ───────────────────────────────────────────────────────

    def _insert(self, event_id: str, minhash: MinHash) -> None:
        """Insert a MinHash into the LSH index and local signature store."""
        try:
            # LSH insert raises ValueError if key already exists
            if event_id not in self._signatures:
                self._lsh.insert(event_id, minhash)
                self._signatures[event_id] = minhash
        except ValueError:
            # Already inserted — update signature but don't re-insert into LSH
            self._signatures[event_id] = minhash
        except Exception as exc:
            logger.error(f"LSH insert failed for {event_id}: {exc}")

    def _minhash_from_list(self, sig_list: list[int]) -> MinHash:
        """
        Reconstruct a MinHash object from a stored hashvalues list.
        The list is what was stored in raw_events.minhash_signature (JSONB).
        """
        import numpy as np
        mh = MinHash(num_perm=self.num_perm)
        mh.hashvalues = np.array(sig_list, dtype=np.uint64)
        return mh


# ── Module-level singleton ────────────────────────────────────────────────────

_default_dedup: Optional[DeduplicationService] = None


def get_dedup_service() -> DeduplicationService:
    """Return the module-level singleton. One instance per Celery worker process."""
    global _default_dedup
    if _default_dedup is None:
        _default_dedup = DeduplicationService()
    return _default_dedup


def check_duplicate(event_id: str, content: str) -> DeduplicationResult:
    """
    Top-level convenience function for use in tasks/enrich.py.

    Example:
        from services.deduplication import check_duplicate

        result = check_duplicate(str(event.id), event.content)
        event.is_duplicate      = result.is_duplicate
        event.duplicate_of      = result.duplicate_of
        event.minhash_signature = result.signature
    """
    return get_dedup_service().check(event_id, content)
