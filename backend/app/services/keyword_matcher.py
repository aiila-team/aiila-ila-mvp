"""
Keyword-based alerting — exact, wildcard (fnmatch), and phrase matching.

Used by the enrichment pipeline (tasks/enrich.py) against the keywords table.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models import Keyword


@dataclass
class KeywordHit:
    keyword_id: str
    word: str
    category: str
    match_kind: str  # exact | wildcard | phrase


def _corpus(content: Optional[str], translated: Optional[str]) -> str:
    parts = []
    if content:
        parts.append(content.lower())
    if translated:
        parts.append(translated.lower())
    return " ".join(parts)


def _is_fnmatch_pattern(word: str) -> bool:
    return any(ch in word for ch in "*?[]")


def _phrase_pattern(word: str) -> Optional[str]:
    w = word.strip()
    if len(w) >= 2 and w[0] == '"' and w[-1] == '"':
        return w[1:-1].strip().lower()
    if " " in w:
        return w.lower()
    return None


def _match_one(word: str, corpus: str) -> Optional[str]:
    """Return match_kind if word matches corpus."""
    if not word or not corpus:
        return None

    if _is_fnmatch_pattern(word):
        pat = word.lower()
        for token in re.split(r"\s+", corpus):
            if token and fnmatch.fnmatch(token, pat):
                return "wildcard"
        if fnmatch.fnmatch(corpus, pat):
            return "wildcard"
        return None

    phrase = _phrase_pattern(word)
    if phrase is not None:
        if phrase in corpus:
            return "phrase"
        return None

    if word.lower() in corpus:
        return "exact"
    return None


def find_keyword_hits(db: Session, content: str, translated: Optional[str] = None) -> List[KeywordHit]:
    """
    Scan text against all active keywords. Increments Keyword.match_count per hit.
    """
    corpus = _corpus(content, translated)
    if not corpus.strip():
        return []

    active: List[Keyword] = (
        db.query(Keyword).filter(Keyword.is_active == True).order_by(Keyword.word).all()  # noqa: E712
    )
    hits: List[KeywordHit] = []

    for kw in active:
        kind = _match_one(kw.word, corpus)
        if not kind:
            continue
        try:
            kw.match_count = (kw.match_count or 0) + 1
        except Exception:
            pass
        hits.append(
            KeywordHit(
                keyword_id=str(kw.id),
                word=kw.word,
                category=kw.category or "general",
                match_kind=kind,
            )
        )

    return hits


def hits_to_json(hits: Iterable[KeywordHit]) -> List[dict]:
    return [
        {"id": h.keyword_id, "word": h.word, "category": h.category, "match_kind": h.match_kind}
        for h in hits
    ]
