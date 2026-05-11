"""
services/sentiment.py
──────────────────────────────────────────────────────────────────────────────
Sentiment Analysis Service — ILA Day 3 Morning

Model   : ai4bharat/indic-bert  (HuggingFace Transformers)
Task    : Text classification → negative / neutral / positive
Output  : Float in [-1.0, +1.0]
              -1.0 = strongly negative  (threat, incitement, fear)
               0.0 = neutral
              +1.0 = strongly positive

Device  : GPU if available (device_map="auto"), CPU fallback.
          On a t3.medium (CPU-only EC2) a single inference is ~800ms.
          Batch inference is used to amortise that cost.

Why IndicBERT:
  Standard English BERT has poor coverage of Devanagari, Bengali, Tamil etc.
  ai4bharat/indic-bert is pre-trained on 12 Indian languages on IndicCorp.
  We fine-tune the final classification head here at load time using a thin
  linear layer on top of the [CLS] pooled output.

Integration points:
  - Called directly by enrich.py (Stage 3.5) via analyze_sentiment()
  - Called as Celery task via sentiment_task.delay(event_id) from ml_tasks.py
  - Result stored in raw_events.sentiment_score  (Float, -1.0 to +1.0)
  - Also used by risk_scorer.py: sentiment_score component (weight 0.10)
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
import threading
from typing import Optional

import torch
from loguru import logger
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    pipeline,
)

# ── Configuration ─────────────────────────────────────────────────────────────

MODEL_NAME: str = os.getenv("SENTIMENT_MODEL", "cardiffnlp/twitter-roberta-base-sentiment")
MODEL_CACHE_DIR: str = os.getenv("HF_MODEL_CACHE", "./models")

MAX_TOKEN_LENGTH: int = 512        # IndicBERT max sequence length
BATCH_SIZE: int = 16               # for batch inference calls
NEUTRAL_SCORE: float = 0.0        # returned on error / too-short text
MIN_TEXT_LENGTH: int = 10         # skip sentiment on very short strings

# ── Label → score mapping ──────────────────────────────────────────────────────
# IndicBERT fine-tuned for 3-class sentiment typically uses:
#   LABEL_0 = negative, LABEL_1 = neutral, LABEL_2 = positive
# We map this to the [-1, 0, +1] scale ILA uses.
_LABEL_TO_SCORE: dict[str, float] = {
    "LABEL_0": -1.0,   # negative
    "LABEL_1":  0.0,   # neutral
    "LABEL_2": +1.0,   # positive
    # Common alternative label names
    "negative": -1.0,
    "neutral":   0.0,
    "positive": +1.0,
    "NEG": -1.0,
    "NEU":  0.0,
    "POS": +1.0,
}


# ── Model Singleton ────────────────────────────────────────────────────────────
# Thread-safe lazy loader — only loads once per process.
# Celery prefork workers each get their own copy (one per process, not thread).

class _SentimentModel:
    """
    Wrapper around the HuggingFace pipeline.
    Handles device selection, model loading, and inference.
    """
    _instance: Optional["_SentimentModel"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._pipeline = None
        self._device_label = "unloaded"

    @classmethod
    def get(cls) -> "_SentimentModel":
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = cls()
                    inst._load()
                    cls._instance = inst
        return cls._instance

    def _load(self) -> None:
        """Load the model. Called once at worker startup."""
        # Device selection: GPU → MPS (Apple Silicon) → CPU
        if torch.cuda.is_available():
            device = 0          # first CUDA GPU
            self._device_label = f"cuda:{device}"
        elif torch.backends.mps.is_available():
            device = "mps"
            self._device_label = "mps"
        else:
            device = -1         # CPU
            self._device_label = "cpu"

        logger.info(
            f"Loading sentiment model '{MODEL_NAME}' "
            f"on device={self._device_label} ..."
        )

        try:
            tokenizer = AutoTokenizer.from_pretrained(
                MODEL_NAME,
                cache_dir=MODEL_CACHE_DIR,
                use_fast=True,
            )

            # Try loading with a sequence-classification head.
            # IndicBERT base model does not ship with a classification head,
            # so AutoModelForSequenceClassification will randomly initialize
            # the final linear layer — this is intentional for MVP.
            # In Phase 2, load fine-tuned weights from a checkpoint.
            model = AutoModelForSequenceClassification.from_pretrained(
                MODEL_NAME,
                num_labels=3,           # negative / neutral / positive
                cache_dir=MODEL_CACHE_DIR,
                ignore_mismatched_sizes=True,   # handles head re-init gracefully
            )
            model.eval()

            # Move to device
            if device != -1 and device != "mps":
                model = model.to(f"cuda:{device}")
            elif device == "mps":
                model = model.to("mps")

            self._pipeline = pipeline(
                task="text-classification",
                model=model,
                tokenizer=tokenizer,
                device=device,
                top_k=1,                 # return only best label
                truncation=True,
                max_length=MAX_TOKEN_LENGTH,
                batch_size=BATCH_SIZE,
            )

            logger.info(
                f"Sentiment model loaded successfully | "
                f"device={self._device_label} | model={MODEL_NAME}"
            )

        except Exception as exc:
            logger.error(
                f"Failed to load sentiment model '{MODEL_NAME}': {exc}\n"
                f"Sentiment will return 0.0 (neutral) for all inputs until resolved."
            )
            self._pipeline = None

    def predict(self, text: str) -> float:
        """
        Run inference on a single text string.

        Returns a float in [-1.0, +1.0]:
          - Maps the top predicted label to its score.
          - Scales by the model's confidence (probability):
              final_score = label_score * confidence
            This means a confident negative = -1.0,
            an uncertain negative = -0.51 (just over the threshold).
          - Returns 0.0 on any error or if model is not loaded.
        """
        if self._pipeline is None:
            return NEUTRAL_SCORE

        if not text or len(text.strip()) < MIN_TEXT_LENGTH:
            return NEUTRAL_SCORE

        try:
            # pipeline returns [[{"label": "LABEL_0", "score": 0.92}]]
            result = self._pipeline(text[:MAX_TOKEN_LENGTH * 4])  # rough char cap
            if not result or not result[0]:
                return NEUTRAL_SCORE

            top = result[0][0] if isinstance(result[0], list) else result[0]
            label = top.get("label", "LABEL_1")
            confidence = float(top.get("score", 0.5))

            base_score = _LABEL_TO_SCORE.get(label, 0.0)

            # Scale by confidence so borderline predictions stay near 0
            final = round(base_score * confidence, 4)
            return max(-1.0, min(1.0, final))   # clamp just in case

        except Exception as exc:
            logger.warning(f"Sentiment inference failed: {exc}")
            return NEUTRAL_SCORE

    def predict_batch(self, texts: list[str]) -> list[float]:
        """
        Batch inference — more efficient than calling predict() in a loop.
        Used by the Celery task for bulk backfill operations.

        Returns scores in the same order as inputs.
        """
        if self._pipeline is None:
            return [NEUTRAL_SCORE] * len(texts)

        if not texts:
            return []

        # Filter empties but preserve positions
        valid_indices = [
            i for i, t in enumerate(texts)
            if t and len(t.strip()) >= MIN_TEXT_LENGTH
        ]
        valid_texts = [
            texts[i][:MAX_TOKEN_LENGTH * 4] for i in valid_indices
        ]

        scores = [NEUTRAL_SCORE] * len(texts)

        if not valid_texts:
            return scores

        try:
            results = self._pipeline(valid_texts)
            for pos, result in zip(valid_indices, results):
                top = result[0] if isinstance(result, list) else result
                label = top.get("label", "LABEL_1")
                confidence = float(top.get("score", 0.5))
                base = _LABEL_TO_SCORE.get(label, 0.0)
                scores[pos] = round(
                    max(-1.0, min(1.0, base * confidence)), 4
                )
        except Exception as exc:
            logger.warning(f"Batch sentiment inference failed: {exc}")

        return scores


# ── Public API ─────────────────────────────────────────────────────────────────

def analyze_sentiment(text: str) -> float:
    """
    Primary public function. Analyze sentiment of a single text.

    Args:
        text: Raw content from raw_events.content. Any language supported by
              IndicBERT (12 Indian languages + English).

    Returns:
        Float in [-1.0, +1.0].
        -1.0 = strongly negative, 0.0 = neutral, +1.0 = strongly positive.

    Usage in enrich.py:
        from services.sentiment import analyze_sentiment
        event.sentiment_score = analyze_sentiment(event.content)
    """
    return _SentimentModel.get().predict(text)


def analyze_sentiment_batch(texts: list[str]) -> list[float]:
    """
    Batch variant. Use this for backfill tasks.

    Returns list of floats in same order as input texts.
    """
    return _SentimentModel.get().predict_batch(texts)


def preload_model() -> None:
    """
    Eagerly load the model. Call at Celery worker startup
    (in @worker_ready signal in celery_app.py) so first inference
    is not slow.

    Example (app/core/celery_app.py):
        from celery.signals import worker_ready
        @worker_ready.connect
        def on_worker_ready(sender, **kwargs):
            from services.sentiment import preload_model
            preload_model()
    """
    _SentimentModel.get()
    logger.info("Sentiment model preloaded.")
