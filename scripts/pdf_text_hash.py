"""Deterministic content-change detection for DCP PDFs.

The raw-byte SHA256 (r2_monitor's content_hash) changes whenever a council re-exports
a PDF, even if the wording is identical — a false "change" that triggers needless
re-extraction and review. This module hashes the NORMALISED extracted TEXT instead:
re-exports produce the same text -> same hash -> no false change; a real content edit
changes the text -> different hash -> a real change.

Text extraction via pdfplumber is deterministic (same file -> same text), so this hash
is stable across runs — unlike an AI-vs-AI diff, whose wording wobbles run-to-run
(measured 2026-07-01). Detector = this hash; reader = the AI; approver = the human.

prior-art-checked: reuse not viable because r2_monitor only has a raw-byte sha256
(the source of the false positives) and dcp_extract_changed._normalize_for_diff is
coupled to the heavy extraction module (boto3/enrichment) — this is a standalone,
importable text-normaliser + hash for the monitor.
"""
from __future__ import annotations

import hashlib
import re


def _normalize_text(text: str) -> str:
    """Collapse formatting noise that a re-export changes but a real edit does not:
    lowercase, collapse all runs of whitespace to a single space, strip. Pure."""
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def normalized_pdf_text(pdf_bytes: bytes) -> str:
    """Extract and normalise a PDF's full text. Deterministic (pdfplumber). Returns ''
    if the PDF can't be read (caller then treats it as 'no text signal')."""
    import io
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            parts = [(page.extract_text() or "") for page in pdf.pages]
        return _normalize_text("\n".join(parts))
    except Exception:
        return ""


def text_content_hash(pdf_bytes: bytes) -> str:
    """SHA256 of a PDF's normalised text, or '' if no text could be extracted."""
    text = normalized_pdf_text(pdf_bytes)
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_reexport(old_pdf_bytes: bytes, new_pdf_bytes: bytes) -> bool:
    """True when the two PDFs have identical normalised text (a re-export, not a real
    content change). False if either has no extractable text (fail open -> treat as a
    real change so nothing is silently skipped)."""
    old_h = text_content_hash(old_pdf_bytes)
    new_h = text_content_hash(new_pdf_bytes)
    if not old_h or not new_h:
        return False
    return old_h == new_h
