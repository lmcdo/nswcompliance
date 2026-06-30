"""Tests for the TOC-driven extraction helpers in dcp_extract_changed.py.

These cover the pure parsing/decision logic. The full extraction (TOC -> body
locate -> page ranges) is validated against real council PDFs out of band, since
repo tests can't ship large binary fixtures.
"""
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
           "R2_BUCKET_NAME", "R2_ENDPOINT_URL", "R2_PUBLIC_URL"):
    os.environ.setdefault(_k, "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
_STUBS = ("boto3", "botocore", "pdfplumber", "psycopg2", "dotenv", "enrichment", "enrichment.pipeline")
_saved = {k: sys.modules.get(k) for k in _STUBS}
for _k in _STUBS:
    sys.modules[_k] = MagicMock()
sys.modules["dotenv"].load_dotenv = MagicMock()
try:
    from dcp_extract_changed import (  # noqa: E402
        parse_toc_entries, build_toc_ranges, dedupe_ascending,
        toc_disagrees_with_sequential, TOC_DRIVEN_COUNCILS,
    )
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v


class TestParseTocEntries:
    def test_parses_codes_titles_in_order(self):
        toc = (
            "C3.1 RESIDENTIAL GENERAL PROVISIONS ............ 341\n"
            "C3.2 SITE LAYOUT AND BUILDING DESIGN ........... 343\n"
            "C3.10 VIEWS .................................... 366\n"
        )
        out = parse_toc_entries([toc])
        assert [c for c, _ in out] == ["C3.1", "C3.2", "C3.10"]
        assert out[0][1] == "RESIDENTIAL GENERAL PROVISIONS"

    def test_handles_bare_decimal_codes(self):
        toc = "1.2 Name of this plan ...... 4\n3.1.1 Rosemont precinct ...... 20\n"
        out = parse_toc_entries([toc])
        assert [c for c, _ in out] == ["1.2", "3.1.1"]

    def test_dedupes_repeated_codes(self):
        toc = "1.1 Background .... 3\n1.1 Background .... 3\n1.2 Name .... 4\n"
        assert [c for c, _ in parse_toc_entries([toc])] == ["1.1", "1.2"]

    def test_ignores_non_toc_lines(self):
        assert parse_toc_entries(["This is a paragraph of body text with no leaders"]) == []

    def test_only_scans_front_pages(self):
        pages = ["x"] * 20 + ["9.9 Late section ...... 200"]
        assert parse_toc_entries(pages, max_scan=12) == []


class TestBuildTocRanges:
    def test_contiguous_ranges_to_next_start(self):
        located = [("1.1", "A", 5), ("1.2", "B", 9), ("2.0", "C", 14)]
        ranges = build_toc_ranges(located, total_pages=30)
        assert ranges == [
            ("1.1", "A", 5, 8),
            ("1.2", "B", 9, 13),
            ("2.0", "C", 14, 30),
        ]

    def test_single_entry_spans_to_end(self):
        assert build_toc_ranges([("1.0", "X", 3)], 10) == [("1.0", "X", 3, 10)]


class TestDedupeAscending:
    def test_drops_out_of_order_pages(self):
        located = [("1.1", "A", 5), ("1.2", "B", 9), ("1.3", "C", 7), ("1.4", "D", 12)]
        assert dedupe_ascending(located) == [
            ("1.1", "A", 5), ("1.2", "B", 9), ("1.4", "D", 12),
        ]


class TestTocDisagreesWithSequential:
    def test_control_labels_not_in_toc_triggers_override(self):
        # Leichhardt case: sequential found inline control labels, not the real sections.
        seq = ["preamble", "C2", "C4", "C7", "C9", "C13", "C18"]
        toc = ["C3.1", "C3.2", "C3.3", "C3.4", "C3.5", "C3.6", "C3.7", "C3.8"]
        assert toc_disagrees_with_sequential(seq, toc) is True

    def test_nothing_detected_triggers_override(self):
        # Woollahra HCA case: only a preamble blob.
        toc = ["1.1", "1.2", "1.3", "2.1", "2.2"]
        assert toc_disagrees_with_sequential(["preamble"], toc) is True

    def test_matching_codes_keeps_sequential(self):
        codes = ["B3.1", "B3.2", "B3.3", "B3.4", "B3.5"]
        assert toc_disagrees_with_sequential(codes, codes) is False

    def test_tiny_toc_never_overrides(self):
        # Not enough TOC signal to trust it over the body.
        assert toc_disagrees_with_sequential(["X1"], ["1.1", "1.2"]) is False


def test_toc_driven_councils_are_gated():
    # Opt-in gate keeps the override off the ~23 working councils.
    assert "woollahra" in TOC_DRIVEN_COUNCILS
    assert "leichhardt" in TOC_DRIVEN_COUNCILS
    assert "ku_ring_gai" not in TOC_DRIVEN_COUNCILS
