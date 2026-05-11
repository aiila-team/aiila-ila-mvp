"""
services/ocr_service.py
──────────────────────────────────────────────────────────────────────────────
Multilingual OCR Service — ILA Day 5

What it does:
  Downloads an image from a URL and runs Tesseract 5.0 OCR with support
  for Hindi, Urdu, Bengali, and English language packs. Returns the
  extracted text as a plain string.

Why this matters for ILA:
  Threat actors frequently share screenshots of UPI transactions,
  WhatsApp conversations, and Aadhaar/PAN card images. These contain
  entity data (phone numbers, UPI IDs, names) that regex/NER cannot
  extract from raw event text alone — they're embedded in pixels.

Prerequisites (Docker image / EC2 setup by Sridhar):
  apt-get install -y tesseract-ocr tesseract-ocr-hin tesseract-ocr-urd
                     tesseract-ocr-ben tesseract-ocr-eng
  pip install pytesseract pillow requests

Tesseract language codes:
  eng = English
  hin = Hindi (Devanagari)
  urd = Urdu (Nastaliq)
  ben = Bengali

Input:  image URL (http/https)
Output: extracted text string (empty string on failure)

Celery task: ocr_task(event_id) — triggered when raw_events.metadata
  contains {"has_image": true, "image_url": "https://..."}
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from loguru import logger

# ── Configuration ──────────────────────────────────────────────────────────────

TESSERACT_LANGUAGES: str = os.getenv(
    "TESSERACT_LANGS", "eng+hin+ben+urd"
)
"""
Tesseract language string. Order matters — put the most likely language first.
eng+hin+ben+urd covers ~90% of ILA's Indian threat data.
Add tam/tel for South Indian content.
"""

TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "tesseract")
"""Path to tesseract binary. Override if not on PATH."""

DOWNLOAD_TIMEOUT_SEC: int = 15
"""HTTP request timeout for downloading images."""

MAX_IMAGE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
"""Refuse images larger than this to prevent memory abuse."""

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/jpg", "image/png",
    "image/webp", "image/tiff", "image/bmp", "image/gif",
}

OCR_CONFIG: str = "--oem 3 --psm 6"
"""
Tesseract OCR engine mode + page segmentation mode:
  --oem 3  : LSTM neural net (best accuracy, requires Tesseract 4+)
  --psm 6  : Assume uniform block of text (good for screenshots)
  Other useful values:
    --psm 11 : Sparse text (good for mixed image/text pages)
    --psm 3  : Fully automatic (default — good for natural documents)
"""


# ── Data contract ──────────────────────────────────────────────────────────────

@dataclass
class OCRResult:
    """
    Return value of OCRService.extract_from_url().

    Fields:
        text          : Extracted text (empty string if nothing found or error)
        language_hint : Which Tesseract language packs were used
        confidence    : Tesseract mean confidence (0–100), -1 if unavailable
        image_url     : The URL that was processed
        error         : Error message if extraction failed, else None
        char_count    : Length of extracted text
    """
    text: str
    language_hint: str
    confidence: float
    image_url: str
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.text.strip())

    @property
    def char_count(self) -> int:
        return len(self.text)


# ── Core Service ───────────────────────────────────────────────────────────────

class OCRService:
    """
    Stateless OCR service. Safe to instantiate once per Celery worker.

    Usage:
        svc = OCRService()
        result = svc.extract_from_url("https://cdn.telegram.org/file/xxx.jpg")
        if result.success:
            print(result.text)   # extracted text with phone numbers, UPI IDs etc.

    In Celery task:
        from services.ocr_service import OCRService
        _ocr = OCRService()

        @celery_app.task
        def ocr_task(event_id: str):
            event = db.get(RawEvent, event_id)
            image_url = (event.metadata_ or {}).get("image_url")
            if not image_url:
                return
            result = _ocr.extract_from_url(image_url)
            if result.success:
                # Append OCR text to event content so enrich pipeline picks it up
                event.content = (event.content or "") + "\\n[OCR]\\n" + result.text
                event.is_processed = False   # re-trigger enrichment
                db.commit()
                enrich_event_task.delay(event_id)
    """

    def __init__(self, languages: str = TESSERACT_LANGUAGES):
        self.languages = languages
        self._check_tesseract()

    def _check_tesseract(self) -> None:
        """Warn at startup if tesseract is not found on PATH."""
        import shutil
        if not shutil.which(TESSERACT_CMD):
            logger.warning(
                f"Tesseract binary '{TESSERACT_CMD}' not found on PATH. "
                f"OCR will fail until Tesseract is installed.\n"
                f"Install: apt-get install -y tesseract-ocr "
                f"tesseract-ocr-hin tesseract-ocr-ben tesseract-ocr-urd"
            )

    # ── Public API ─────────────────────────────────────────────────────────────

    def extract_from_url(self, image_url: str) -> OCRResult:
        """
        Download an image from a URL and extract text via Tesseract.

        Args:
            image_url: HTTP/HTTPS URL of the image to process.

        Returns:
            OCRResult with extracted text and metadata.
            Never raises — errors are captured in OCRResult.error.
        """
        _EMPTY = OCRResult(
            text="",
            language_hint=self.languages,
            confidence=-1.0,
            image_url=image_url,
        )

        if not image_url or not image_url.startswith(("http://", "https://")):
            _EMPTY.error = "invalid_url"
            return _EMPTY

        # Step 1: Download image
        image_bytes, content_type, download_error = self._download(image_url)
        if download_error:
            _EMPTY.error = download_error
            return _EMPTY

        # Step 2: Run OCR
        return self._run_ocr(image_bytes, image_url)

    def extract_from_bytes(self, image_bytes: bytes, source_url: str = "") -> OCRResult:
        """
        Run OCR on raw image bytes (e.g. already downloaded content).
        Useful when the image is fetched by a separate step.
        """
        return self._run_ocr(image_bytes, source_url)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _download(self, url: str) -> tuple[Optional[bytes], str, Optional[str]]:
        """
        Download image bytes from URL.
        Returns: (bytes_or_None, content_type, error_or_None)
        """
        try:
            resp = requests.get(
                url,
                timeout=DOWNLOAD_TIMEOUT_SEC,
                stream=True,
                headers={"User-Agent": "ILA-OCR/1.0"},
            )
            resp.raise_for_status()

            # Content-type check
            ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if ct not in ALLOWED_CONTENT_TYPES and not ct.startswith("image/"):
                return None, ct, f"unsupported_content_type:{ct}"

            # Size check (streaming — read up to MAX_IMAGE_BYTES)
            chunks = []
            total = 0
            for chunk in resp.iter_content(chunk_size=65536):
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_IMAGE_BYTES:
                    return None, ct, f"image_too_large:{total}bytes"

            return b"".join(chunks), ct, None

        except requests.Timeout:
            return None, "", "download_timeout"
        except requests.HTTPError as e:
            return None, "", f"http_error:{e.response.status_code}"
        except requests.RequestException as e:
            return None, "", f"download_failed:{e}"

    def _run_ocr(self, image_bytes: bytes, source_url: str) -> OCRResult:
        """Run Tesseract on image bytes and return OCRResult."""
        try:
            import pytesseract
            from PIL import Image

            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

            img = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if needed (Tesseract doesn't handle RGBA/P well)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            # Get text + confidence data
            text = pytesseract.image_to_string(
                img,
                lang=self.languages,
                config=OCR_CONFIG,
            ).strip()

            # Try to get mean confidence
            confidence = -1.0
            try:
                data = pytesseract.image_to_data(
                    img,
                    lang=self.languages,
                    config=OCR_CONFIG,
                    output_type=pytesseract.Output.DICT,
                )
                confs = [
                    int(c) for c in data.get("conf", [])
                    if str(c).lstrip("-").isdigit() and int(c) >= 0
                ]
                confidence = round(sum(confs) / len(confs), 1) if confs else -1.0
            except Exception:
                pass

            logger.debug(
                f"[OCR] Extracted {len(text)} chars from {source_url[:60]} | "
                f"conf={confidence} | lang={self.languages}"
            )

            return OCRResult(
                text=text,
                language_hint=self.languages,
                confidence=confidence,
                image_url=source_url,
            )

        except ImportError as e:
            err = f"missing_dependency:{e}"
            logger.error(f"[OCR] {err} — install pytesseract and Pillow")
            return OCRResult(
                text="", language_hint=self.languages,
                confidence=-1.0, image_url=source_url, error=err,
            )
        except Exception as e:
            logger.warning(f"[OCR] Tesseract failed for {source_url}: {e}")
            return OCRResult(
                text="", language_hint=self.languages,
                confidence=-1.0, image_url=source_url,
                error=f"ocr_failed:{e}",
            )


# ── Celery Task ────────────────────────────────────────────────────────────────

def register_ocr_task(celery_app):
    """
    Register the OCR Celery task.
    Called from app/core/celery_app.py after app is created.

    We use a factory pattern here so this file stays importable
    without a running Celery app (important for unit tests).
    """
    _ocr_service = OCRService()

    @celery_app.task(
        bind=True,
        name="tasks.ocr_task",
        max_retries=2,
        default_retry_delay=30,
        acks_late=True,
        time_limit=120,
    )
    def ocr_task(self, event_id: str) -> dict:
        """
        Celery task: extract text from an image attachment on a raw event.

        Triggered when:
            raw_events.metadata contains {"has_image": True, "image_url": "..."}

        Writes back:
            Appends extracted text to raw_events.content
            Sets raw_events.is_processed = False to re-trigger enrichment
        """
        from app.core.database import SessionLocal
        from app.models import RawEvent
        from app.tasks.enrich import enrich_event_task

        logger.info(f"[ocr_task] START event_id={event_id}")

        db = SessionLocal()
        try:
            event: Optional[RawEvent] = db.get(RawEvent, event_id)
            if event is None:
                return {"event_id": event_id, "success": False, "error": "not_found"}

            metadata = event.metadata_ or {}
            image_url = metadata.get("image_url") or metadata.get("photo_url")

            if not image_url:
                return {"event_id": event_id, "success": False, "error": "no_image_url"}

            result = _ocr_service.extract_from_url(image_url)

            if result.success:
                # Append OCR text to content so enrich pipeline sees it
                ocr_block = f"\n\n[OCR_EXTRACTED]\n{result.text}"
                event.content = (event.content or "") + ocr_block
                event.is_processed = False   # re-queue for enrichment
                db.commit()

                # Re-trigger enrichment with the new OCR content
                enrich_event_task.delay(event_id)

                logger.info(
                    f"[ocr_task] DONE event_id={event_id} | "
                    f"chars={result.char_count} | conf={result.confidence}"
                )
                return {
                    "event_id":   event_id,
                    "char_count": result.char_count,
                    "confidence": result.confidence,
                    "success":    True,
                }
            else:
                logger.warning(
                    f"[ocr_task] OCR failed for event {event_id}: {result.error}"
                )
                return {
                    "event_id": event_id,
                    "success":  False,
                    "error":    result.error,
                }

        except Exception as exc:
            raise self.retry(exc=exc, countdown=30)
        finally:
            db.close()

    return ocr_task


# ── Module-level singleton ─────────────────────────────────────────────────────

_default_ocr: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    global _default_ocr
    if _default_ocr is None:
        _default_ocr = OCRService()
    return _default_ocr
