"""
services/coordinated_detector.py
──────────────────────────────────────────────────────────────────────────────
Coordinated Inauthentic Behaviour Detector — ILA Day 4

What it does:
  Scans raw_events created within the last 1-hour window, groups them by
  MinHash similarity (reuses signatures already stored in minhash_signature),
  and flags clusters of 3+ accounts posting near-identical content as
  "Coordinated Inauthentic Behaviour."

How it works:
  1. Pull all events from the last TIME_WINDOW_MINUTES with stored signatures
  2. Build a temporary LSH index over those signatures
  3. For each event, query the index → collect candidate matches
  4. Union-Find (disjoint-set) to merge candidates into clusters
  5. Any cluster with CLUSTER_MIN_ACCOUNTS distinct author handles → alert

Why MinHash (not full comparison):
  O(n²) pairwise Jaccard on 10k events/hour = 50M comparisons.
  LSH reduces this to O(n · bucket_size) ≈ near-linear.

Alert created:
  AlertType.COORDINATED_INAUTHENTIC in risk_alerts table.
  One alert per cluster per detection run (deduplicated by cluster fingerprint).

Celery beat schedule (beat_schedule.py):
  "coordinated-detection": {
      "task": "tasks.ml_tasks.coordinated_detection_task",
      "schedule": crontab(minute="*/15"),
  }
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np
from datasketch import MinHash, MinHashLSH
from loguru import logger
from sqlalchemy.orm import Session

# ── Configuration ──────────────────────────────────────────────────────────────

TIME_WINDOW_MINUTES: int = 60
"""Look-back window for coordinated activity detection."""

SIMILARITY_THRESHOLD: float = 0.75
"""
Jaccard threshold for grouping posts into a cluster.
Slightly lower than dedup threshold (0.80) to catch lightly paraphrased
coordinated content.
"""

CLUSTER_MIN_ACCOUNTS: int = 3
"""
Minimum distinct author handles in a cluster to trigger an alert.
1 account reposting itself is dedup's job — we want multi-account coordination.
"""

NUM_PERM: int = 64
"""
Fewer perms than deduplication (128) because we rebuild the index
every 15 min from scratch — speed matters here over accuracy.
"""


# ── Data contracts ─────────────────────────────────────────────────────────────

@dataclass
class ContentCluster:
    """A group of events posting near-identical content."""
    cluster_id: str                     # hash fingerprint of sorted event_ids
    event_ids: list[str]
    author_handles: list[str]           # distinct handles in the cluster
    similarity_score: float             # average pairwise Jaccard (approx)
    sample_content: str                 # truncated content of first event
    first_seen: datetime
    last_seen: datetime

    @property
    def account_count(self) -> int:
        return len(set(self.author_handles))

    @property
    def is_coordinated(self) -> bool:
        return self.account_count >= CLUSTER_MIN_ACCOUNTS


@dataclass
class CoordinatedDetectionResult:
    """Return value of CoordinatedDetector.detect()."""
    clusters_found: int
    coordinated_clusters: list[ContentCluster]
    alerts_created: int
    events_scanned: int
    duration_seconds: float


# ── Union-Find ─────────────────────────────────────────────────────────────────

class _UnionFind:
    """Simple Union-Find for merging similar-content event clusters."""

    def __init__(self):
        self._parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self._parent.setdefault(x, x)
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])   # path compression
        return self._parent[x]

    def union(self, x: str, y: str) -> None:
        self._parent[self.find(x)] = self.find(y)

    def groups(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for item in self._parent:
            root = self.find(item)
            result.setdefault(root, []).append(item)
        return result


# ── Text helpers ───────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"[@#]\w+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _minhash_from_list(sig: list[int]) -> MinHash:
    mh = MinHash(num_perm=NUM_PERM)
    # Stored sigs may be 128-perm (dedup); we use first NUM_PERM values
    arr = np.array(sig[:NUM_PERM], dtype=np.uint64)
    if len(arr) < NUM_PERM:
        # Pad with max uint64 (treated as "empty" by MinHash)
        arr = np.pad(arr, (0, NUM_PERM - len(arr)),
                     constant_values=np.iinfo(np.uint64).max)
    mh.hashvalues = arr
    return mh


def _cluster_fingerprint(event_ids: list[str]) -> str:
    return hashlib.md5("|".join(sorted(event_ids)).encode()).hexdigest()[:16]


# ── Core Service ───────────────────────────────────────────────────────────────

class CoordinatedDetector:
    """
    Detects coordinated inauthentic posting in the last TIME_WINDOW_MINUTES.

    Usage (in Celery task):
        from services.coordinated_detector import CoordinatedDetector
        detector = CoordinatedDetector()
        result = detector.detect(db)
        logger.info(f"Found {result.coordinated_clusters} coordinated clusters")
    """

    def detect(self, db: Session) -> CoordinatedDetectionResult:
        import time
        from app.models import RawEvent, RiskAlert, AlertType, AlertStatus, gen_uuid

        t0 = time.time()
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=TIME_WINDOW_MINUTES)

        # ── Step 1: Load recent events with signatures ────────────────────────
        recent = (
            db.query(RawEvent)
            .filter(
                RawEvent.created_at >= cutoff,
                RawEvent.is_duplicate == False,
                RawEvent.minhash_signature.isnot(None),
                RawEvent.author_handle.isnot(None),
            )
            .all()
        )

        if len(recent) < CLUSTER_MIN_ACCOUNTS:
            logger.debug(
                f"[CoordDetector] Only {len(recent)} events in window — skipping."
            )
            return CoordinatedDetectionResult(
                clusters_found=0,
                coordinated_clusters=[],
                alerts_created=0,
                events_scanned=len(recent),
                duration_seconds=round(time.time() - t0, 3),
            )

        logger.info(f"[CoordDetector] Scanning {len(recent)} events in last {TIME_WINDOW_MINUTES}m")

        # ── Step 2: Build temporary LSH index ────────────────────────────────
        lsh = MinHashLSH(threshold=SIMILARITY_THRESHOLD, num_perm=NUM_PERM)
        event_minhashes: dict[str, MinHash] = {}

        for ev in recent:
            try:
                mh = _minhash_from_list(ev.minhash_signature)
                lsh.insert(str(ev.id), mh)
                event_minhashes[str(ev.id)] = mh
            except Exception as exc:
                logger.debug(f"[CoordDetector] Skipping event {ev.id}: {exc}")

        # ── Step 3: Query LSH and union-find clustering ───────────────────────
        uf = _UnionFind()

        for ev in recent:
            eid = str(ev.id)
            mh = event_minhashes.get(eid)
            if mh is None:
                continue
            try:
                candidates = lsh.query(mh)
                for cid in candidates:
                    if cid != eid:
                        uf.union(eid, cid)
            except Exception:
                pass

        # ── Step 4: Build ContentCluster objects ──────────────────────────────
        event_map = {str(ev.id): ev for ev in recent}
        raw_groups = uf.groups()

        clusters: list[ContentCluster] = []
        for root, members in raw_groups.items():
            if len(members) < 2:
                continue

            events_in_cluster = [event_map[m] for m in members if m in event_map]
            handles = [ev.author_handle for ev in events_in_cluster if ev.author_handle]
            times   = [ev.created_at   for ev in events_in_cluster if ev.created_at]

            cluster = ContentCluster(
                cluster_id=_cluster_fingerprint(members),
                event_ids=members,
                author_handles=handles,
                similarity_score=SIMILARITY_THRESHOLD,   # LSH guarantee
                sample_content=(events_in_cluster[0].content or "")[:200],
                first_seen=min(times) if times else datetime.now(timezone.utc),
                last_seen=max(times)  if times else datetime.now(timezone.utc),
            )
            clusters.append(cluster)

        coordinated = [c for c in clusters if c.is_coordinated]
        logger.info(
            f"[CoordDetector] {len(clusters)} clusters found, "
            f"{len(coordinated)} coordinated (≥{CLUSTER_MIN_ACCOUNTS} accounts)"
        )

        # ── Step 5: Create risk alerts ────────────────────────────────────────
        alerts_created = 0
        for cluster in coordinated:
            try:
                created = self._create_alert(db, cluster)
                if created:
                    alerts_created += 1
            except Exception as exc:
                logger.warning(f"[CoordDetector] Alert creation failed: {exc}")

        if alerts_created:
            db.commit()

        return CoordinatedDetectionResult(
            clusters_found=len(clusters),
            coordinated_clusters=coordinated,
            alerts_created=alerts_created,
            events_scanned=len(recent),
            duration_seconds=round(time.time() - t0, 3),
        )

    def _create_alert(self, db: Session, cluster: ContentCluster) -> bool:
        """Create one RiskAlert per coordinated cluster. Idempotent via cluster_id."""
        from app.models import RiskAlert, AlertType, AlertStatus, RiskLevel, gen_uuid

        # Idempotency: don't re-create alert for same cluster fingerprint
        existing = (
            db.query(RiskAlert)
            .filter(RiskAlert.matched_pattern == f"coord:{cluster.cluster_id}")
            .first()
        )
        if existing:
            return False

        unique_handles = list(set(cluster.author_handles))
        alert = RiskAlert(
            id=gen_uuid(),
            alert_type=AlertType.COORDINATED_INAUTHENTIC,
            title=(
                f"Coordinated inauthentic behaviour: "
                f"{cluster.account_count} accounts, "
                f"{len(cluster.event_ids)} posts"
            ),
            description=(
                f"{cluster.account_count} distinct accounts posted near-identical "
                f"content within a {TIME_WINDOW_MINUTES}-minute window. "
                f"Handles: {', '.join(unique_handles[:5])}"
                f"{'...' if len(unique_handles) > 5 else ''}. "
                f"Sample: \"{cluster.sample_content[:120]}...\""
            ),
            risk_score=7.5,                          # coordinated activity = high risk baseline
            risk_level=RiskLevel.HIGH,
            status=AlertStatus.NEW,
            matched_pattern=f"coord:{cluster.cluster_id}",
            risk_factors=[
                {
                    "factor": "Coordinated Inauthentic Behaviour",
                    "detail": (
                        f"{cluster.account_count} accounts, "
                        f"{len(cluster.event_ids)} identical posts "
                        f"in {TIME_WINDOW_MINUTES}min window"
                    ),
                    "contribution": 0.75,
                }
            ],
            evidence_data={
                "cluster_id":      cluster.cluster_id,
                "account_count":   cluster.account_count,
                "event_count":     len(cluster.event_ids),
                "event_ids":       cluster.event_ids[:20],
                "author_handles":  unique_handles[:20],
                "similarity":      cluster.similarity_score,
                "first_seen":      cluster.first_seen.isoformat(),
                "last_seen":       cluster.last_seen.isoformat(),
                "sample_content":  cluster.sample_content,
            },
        )
        db.add(alert)
        db.flush()
        logger.info(
            f"[CoordDetector] Alert created: {cluster.account_count} accounts, "
            f"cluster={cluster.cluster_id}"
        )
        return True


# Module-level singleton
_detector: Optional[CoordinatedDetector] = None


def get_detector() -> CoordinatedDetector:
    global _detector
    if _detector is None:
        _detector = CoordinatedDetector()
    return _detector
