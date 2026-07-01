"""Tests for the deterministic content-change gate (scripts/pdf_text_hash.py).

The PDF-reading helpers need pdfplumber + a real PDF, so they're validated out of
band; here we pin the pure normalisation + the re-export decision logic.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from pdf_text_hash import _normalize_text, is_reexport, text_content_hash  # noqa: E402


class TestNormalizeText:
    def test_whitespace_and_case_collapse(self):
        # a re-export that only reflows whitespace / changes case normalises identically
        a = "Front  setback\n\n  is   6m.\tPer clause B3.1"
        b = "front setback is 6m. per clause b3.1"
        assert _normalize_text(a) == _normalize_text(b)

    def test_real_edit_survives_normalisation(self):
        assert _normalize_text("setback is 6m") != _normalize_text("setback is 9m")

    def test_empty(self):
        assert _normalize_text("") == ""
        assert _normalize_text(None) == ""


class TestTextContentHash:
    def test_empty_bytes_hash_is_empty_string(self):
        # unreadable / no-text PDF -> '' (caller treats as no signal)
        assert text_content_hash(b"not a pdf") == ""


class TestIsReexport:
    def test_fails_open_when_no_text(self):
        # if either side has no extractable text, do NOT declare a re-export
        # (fail open -> treated as a real change, nothing silently skipped)
        assert is_reexport(b"not a pdf", b"also not a pdf") is False
