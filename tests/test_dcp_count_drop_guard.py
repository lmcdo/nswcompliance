"""Tests for the count-drop fail-loud guard in dcp_extract_changed.py.

A re-extraction that yields far fewer provisions than the approved baseline is
almost always a broken parse / scanned PDF, not a real amendment. The guard:
- is_count_drop(): pure threshold (total_old > 20 and 0 < total_new < 75% of old)
- diff_provisions(): sets status='count_drop' with PRECEDENCE over 'restructure'
  (so the commit path never full-replaces / wipes on a suspect extraction)
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
        is_count_drop, diff_provisions,
        build_provision_text, build_ref_number,
        COUNT_DROP_MIN_BASELINE, COUNT_DROP_RATIO,
    )
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v


class _FakeCursor:
    """Minimal cursor: diff_provisions does one execute() + fetchall()."""
    def __init__(self, old_rows):
        self._rows = old_rows

    def execute(self, *a, **k):
        return None

    def fetchall(self):
        return self._rows

    def close(self):
        return None


def _section(n, content="body text here"):
    return {
        "section_number": f"S{n}", "section_title": "T", "content": content,
        "tables": [], "page_start": 1, "page_end": 1,
    }


def _old_rows(doc, n, content="body text here"):
    # (ref_number, provision_text, pdf_page) built from the SAME builder the diff
    # uses for new sections, so unchanged sections compare equal (not "changed").
    rows = []
    for i in range(n):
        sec = _section(i, content=content)
        rows.append((build_ref_number(doc, sec["section_number"]),
                     build_provision_text(sec), 1))
    return rows


class TestIsCountDrop:
    def test_clear_drop_is_flagged(self):
        assert is_count_drop(30, 5) is True

    def test_just_below_ratio_is_flagged(self):
        # 0.75 * 30 = 22.5 -> 22 is a drop
        assert is_count_drop(30, 22) is True

    def test_at_or_above_ratio_is_not_a_drop(self):
        assert is_count_drop(30, 23) is False   # 23 >= 22.5
        assert is_count_drop(30, 30) is False

    def test_small_baseline_never_flags(self):
        # total_old must exceed COUNT_DROP_MIN_BASELINE (20)
        assert is_count_drop(COUNT_DROP_MIN_BASELINE, 1) is False
        assert is_count_drop(20, 1) is False
        assert is_count_drop(21, 1) is True

    def test_zero_new_is_not_count_drop(self):
        # total_new == 0 is a map/spatial chapter (handled as map_change), not a drop
        assert is_count_drop(30, 0) is False

    def test_ratio_constant_sane(self):
        assert 0 < COUNT_DROP_RATIO < 1


class TestDiffProvisionsCountDrop:
    def test_suspect_extraction_sets_count_drop(self):
        cur = _FakeCursor(_old_rows("doc", 30))
        new_sections = [_section(i) for i in range(5)]  # only 5 of 30 survive
        diff = diff_provisions(new_sections, "council", "ch", "doc", cur)
        assert diff["status"] == "count_drop"
        assert diff["total_old"] == 30
        assert diff["total_new"] == 5

    def test_count_drop_takes_precedence_over_restructure(self):
        # 30 -> 5 is also >50% changed (would be 'restructure'); count_drop must win
        # so the commit path skips instead of full-replacing (wiping).
        cur = _FakeCursor(_old_rows("doc", 30))
        diff = diff_provisions([_section(i) for i in range(5)], "c", "ch", "doc", cur)
        assert diff["status"] == "count_drop"
        assert diff["status"] != "restructure"

    def test_full_wholesale_change_is_still_restructure_not_count_drop(self):
        # Same count (30 -> 30) but every provision changed: a real restructure,
        # NOT a count drop. The guard must not hijack this.
        cur = _FakeCursor(_old_rows("doc", 30, content="old body"))
        new_sections = [_section(i, content="completely different new body") for i in range(30)]
        diff = diff_provisions(new_sections, "c", "ch", "doc", cur)
        assert diff["status"] == "restructure"

    def test_minor_change_stays_ok(self):
        # 30 -> 28 (2 removed) is within tolerance: not a drop, not a restructure.
        cur = _FakeCursor(_old_rows("doc", 30))
        diff = diff_provisions([_section(i) for i in range(28)], "c", "ch", "doc", cur)
        assert diff["status"] == "ok"
        assert diff["total_old"] == 30 and diff["total_new"] == 28
