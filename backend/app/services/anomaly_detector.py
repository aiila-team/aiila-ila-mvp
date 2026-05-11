"""
services/anomaly_detector.py
──────────────────────────────────────────────────────────────────────────────
Anomaly Detection Service — ILA Day 3 Afternoon

Algorithm : Isolation Forest  (scikit-learn)
Features  : Transaction velocity + social posting velocity
Output    : Float in [0.0, 1.0]  — 0.0 = normal, 1.0 = extreme anomaly

How Isolation Forest works (for the team):
  It randomly partitions the feature space into trees. Anomalous points
  are isolated in fewer splits because they're sparse — they get a short
  path length. Normal points require many splits. We invert the raw
  anomaly score (which is negative for anomalies in sklearn) to get
  a clean 0→1 scale.

Feature set (MVP):
  transaction_count_1h      — # UPI/financial transactions in last 1 hour
  unique_recipients_1h      — # distinct recipients in last 1 hour
  avg_amount_deviation      — z-score of transaction amount vs entity baseline
  post_frequency_1h         — # posts/messages in last 1 hour
  unique_platforms_1h       — # distinct platforms active on in last 1 hour
  keyword_hit_rate          — fraction of recent posts matching threat keywords
  reply_ratio               — replies / total posts (bot behaviour signal)

Model lifecycle:
  1. At startup: try to load a pre-trained model from disk (MODEL_PATH).
  2. If not found: fit on synthetic "normal" baseline data and save.
  3. Production (Phase 2): retrain nightly on confirmed-normal entities.

Thread safety: one model instance per worker process (Celery prefork).
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from loguru import logger
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# ── Configuration ──────────────────────────────────────────────────────────────

MODEL_PATH: str = os.getenv(
    "ANOMALY_MODEL_PATH", "/models/isolation_forest.joblib"
)
SCALER_PATH: str = os.getenv(
    "ANOMALY_SCALER_PATH", "/models/isolation_forest_scaler.joblib"
)

CONTAMINATION: float = 0.05   # expected fraction of anomalies in training data
N_ESTIMATORS: int = 100        # number of isolation trees
RANDOM_STATE: int = 42

# Feature column order — MUST match _features_to_vector() and training data
FEATURE_NAMES: list[str] = [
    "transaction_count_1h",
    "unique_recipients_1h",
    "avg_amount_deviation",
    "post_frequency_1h",
    "unique_platforms_1h",
    "keyword_hit_rate",
    "reply_ratio",
]

# Default values when a feature is missing from the input dict
FEATURE_DEFAULTS: dict[str, float] = {
    "transaction_count_1h":   0.0,
    "unique_recipients_1h":   0.0,
    "avg_amount_deviation":   0.0,
    "post_frequency_1h":      0.0,
    "unique_platforms_1h":    1.0,
    "keyword_hit_rate":       0.0,
    "reply_ratio":            0.0,
}


# ── Feature extraction helper ──────────────────────────────────────────────────

def _features_to_vector(features: dict) -> np.ndarray:
    """
    Convert a feature dict to a numpy row vector.
    Missing keys use FEATURE_DEFAULTS.
    Values are clipped to sane ranges to prevent outlier pollution.
    """
    vec = []
    for name in FEATURE_NAMES:
        val = float(features.get(name, FEATURE_DEFAULTS[name]))
        # Clip to reasonable maxima (prevents single extreme value
        # from dominating the isolation splits)
        if name == "transaction_count_1h":
            val = min(val, 10_000)
        elif name == "unique_recipients_1h":
            val = min(val, 5_000)
        elif name == "avg_amount_deviation":
            val = max(-10.0, min(val, 10.0))   # z-score range
        elif name == "post_frequency_1h":
            val = min(val, 5_000)
        elif name in ("keyword_hit_rate", "reply_ratio"):
            val = max(0.0, min(val, 1.0))       # must be 0–1
        vec.append(val)
    return np.array(vec, dtype=np.float32).reshape(1, -1)


# ── Synthetic baseline training data ──────────────────────────────────────────
# Used when no pre-trained model exists.
# Represents "normal" entity behaviour patterns.
# 1500 synthetic samples across 7 features.

def _generate_baseline_training_data(n_samples: int = 1500) -> np.ndarray:
    """
    Generate synthetic "normal" samples for initial model fitting.
    All distributions are calibrated to realistic Indian threat-context ranges.

    Normal behaviour heuristics:
      - UPI transactions: 0–15/hour for individuals, up to 50 for merchants
      - Unique recipients: 1–10 for individuals
      - Amount deviation: z-score mostly within ±2
      - Post frequency: 0–20/hour for humans, up to 50 for news accounts
      - Unique platforms: 1–3 (most people use 1–2 platforms)
      - Keyword hit rate: near 0 for normal accounts
      - Reply ratio: 0.2–0.8 for typical social accounts
    """
    rng = np.random.default_rng(42)

    # Each column: (distribution_fn, args)
    data = np.column_stack([
        rng.exponential(scale=3.0,  size=n_samples),   # transaction_count_1h
        rng.exponential(scale=2.0,  size=n_samples),   # unique_recipients_1h
        rng.normal(loc=0.0, scale=0.8, size=n_samples),# avg_amount_deviation
        rng.exponential(scale=5.0,  size=n_samples),   # post_frequency_1h
        rng.integers(1, 4,          size=n_samples).astype(float),  # unique_platforms
        rng.beta(a=0.5, b=10.0,    size=n_samples),   # keyword_hit_rate (mostly near 0)
        rng.beta(a=2.0, b=3.0,     size=n_samples),   # reply_ratio (0.2–0.7 range)
    ])

    # Clip to feature bounds
    data[:, 0] = np.clip(data[:, 0], 0, 500)
    data[:, 1] = np.clip(data[:, 1], 0, 200)
    data[:, 2] = np.clip(data[:, 2], -5, 5)
    data[:, 3] = np.clip(data[:, 3], 0, 500)
    data[:, 4] = np.clip(data[:, 4], 1, 5)
    data[:, 5] = np.clip(data[:, 5], 0, 1)
    data[:, 6] = np.clip(data[:, 6], 0, 1)

    return data.astype(np.float32)


# ── Model singleton ────────────────────────────────────────────────────────────

class _AnomalyModel:
    _instance: Optional["_AnomalyModel"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._model: Optional[IsolationForest] = None
        self._scaler: Optional[StandardScaler] = None
        self._is_ready = False

    @classmethod
    def get(cls) -> "_AnomalyModel":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = cls()
                    inst._load_or_train()
                    cls._instance = inst
        return cls._instance

    def _load_or_train(self) -> None:
        """Load model from disk if it exists, otherwise train on baseline data."""
        if Path(MODEL_PATH).exists() and Path(SCALER_PATH).exists():
            try:
                self._model = joblib.load(MODEL_PATH)
                self._scaler = joblib.load(SCALER_PATH)
                self._is_ready = True
                logger.info(f"Anomaly model loaded from {MODEL_PATH}")
                return
            except Exception as exc:
                logger.warning(f"Could not load saved model: {exc}. Retraining.")

        logger.info("Training anomaly model on synthetic baseline data...")
        self._train_and_save()

    def _train_and_save(self) -> None:
        """Fit Isolation Forest on synthetic baseline and persist to disk."""
        X_train = _generate_baseline_training_data(n_samples=1500)

        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X_train)

        self._model = IsolationForest(
            n_estimators=N_ESTIMATORS,
            contamination=CONTAMINATION,
            random_state=RANDOM_STATE,
            n_jobs=-1,          # use all CPU cores
            warm_start=False,
        )
        self._model.fit(X_scaled)
        self._is_ready = True

        # Persist to disk
        try:
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            joblib.dump(self._model,  MODEL_PATH)
            joblib.dump(self._scaler, SCALER_PATH)
            logger.info(f"Anomaly model saved to {MODEL_PATH}")
        except Exception as exc:
            logger.warning(f"Could not save anomaly model: {exc}")

        logger.info("Anomaly model training complete.")

    def score(self, features: dict) -> float:
        """
        Score a single feature dict. Returns anomaly score in [0.0, 1.0].
        0.0 = completely normal, 1.0 = extreme anomaly.
        """
        if not self._is_ready or self._model is None:
            logger.warning("Anomaly model not ready; returning 0.0")
            return 0.0

        try:
            vec = _features_to_vector(features)
            vec_scaled = self._scaler.transform(vec)

            # decision_function returns negative scores for anomalies.
            # Lower (more negative) = more anomalous.
            raw_score = float(self._model.decision_function(vec_scaled)[0])

            # Normalise to [0, 1]:
            # decision_function range is roughly [-0.5, 0.5].
            # We map: -0.5 → 1.0 (anomaly), +0.5 → 0.0 (normal)
            anomaly_score = 1.0 - (raw_score + 0.5)
            anomaly_score = max(0.0, min(1.0, anomaly_score))
            return round(anomaly_score, 4)

        except Exception as exc:
            logger.error(f"Anomaly scoring failed: {exc}")
            return 0.0

    def retrain(self, X_new: np.ndarray) -> None:
        """
        Retrain the model with new data (Phase 2 — nightly retraining).
        Combines existing synthetic baseline with confirmed-normal real data.

        Args:
            X_new: np.ndarray of shape (N, 7) — feature matrix of normal entities.
        """
        with self._lock:
            X_baseline = _generate_baseline_training_data(1000)
            X_combined = np.vstack([X_baseline, X_new])

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_combined)

            model = IsolationForest(
                n_estimators=N_ESTIMATORS,
                contamination=CONTAMINATION,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )
            model.fit(X_scaled)

            self._model = model
            self._scaler = scaler
            joblib.dump(self._model,  MODEL_PATH)
            joblib.dump(self._scaler, SCALER_PATH)
            logger.info(f"Anomaly model retrained on {len(X_new)} new samples.")


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_anomaly(features: dict) -> float:
    """
    Primary public function. Compute anomaly score for a feature dict.

    Args:
        features: Dict with any subset of FEATURE_NAMES.
                  Missing keys use FEATURE_DEFAULTS (no KeyError).

    Returns:
        Float in [0.0, 1.0].
        0.0 = completely normal behaviour.
        1.0 = extreme anomaly — likely bot / mule / coordinated account.

    Example:
        score = detect_anomaly({
            "transaction_count_1h": 47,
            "unique_recipients_1h": 23,
            "avg_amount_deviation": 3.4,
            "post_frequency_1h":    0,
        })
        # → 0.87  (high anomaly — 47 transactions, 23 recipients in 1 hour)

    Usage in pattern_matcher.py:
        anomaly_score = detect_anomaly(entity_features)  # weight 0.30
    """
    return _AnomalyModel.get().score(features)


def preload_model() -> None:
    """
    Eagerly load / train the anomaly model at worker startup.
    Call from @worker_ready signal in celery_app.py.
    """
    _AnomalyModel.get()
    logger.info("Anomaly model preloaded.")
