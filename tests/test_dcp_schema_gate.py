"""Tests for the schema gate + SUSPECT alert formatting in dcp_extract_changed.py.

The schema gate is the content-side complement to the count-drop guard: a
re-extraction can have the right COUNT but garbage CONTENT. It flags a chapter
SUSPECT only on UNAMBIGUOUS extraction-failure artifacts (so it stays
high-precision and does not cry wolf on benign formatting quirks).
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
        is_schema_fail, suspect_reason, build_suspect_alert,
        SERIOUS_ARTIFACT_LABELS, SCHEMA_FAIL_MIN_PROVISIONS, SCHEMA_FAIL_RATIO,
    )
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v


class TestIsSchemaFail:
    def test_high_serious_rate_fails(self):
        assert is_schema_fail(100, 20) is True   # 20% > 10%

    def test_just_above_ratio_fails(self):
        assert is_schema_fail(100, 11) is True

    def test_at_or_below_ratio_passes(self):
        assert is_schema_fail(100, 10) is False  # 10% is not > 10%
        assert is_schema_fail(100, 3) is False

    def test_small_chapter_never_fails(self):
        # Below the min-provisions floor, ratios are too noisy to trust.
        assert is_schema_fail(SCHEMA_FAIL_MIN_PROVISIONS - 1, 9) is False
        assert is_schema_fail(5, 5) is False

    def test_zero_provisions_is_safe(self):
        assert is_schema_fail(0, 0) is False

    def test_constants_sane(self):
        assert 0 < SCHEMA_FAIL_RATIO < 1
        assert SCHEMA_FAIL_MIN_PROVISIONS >= 1
        # Only unambiguous extraction-failure labels — benign formatting excluded.
        assert "latex_tokens" in SERIOUS_ARTIFACT_LABELS
        assert "word_cross_references" in SERIOUS_ARTIFACT_LABELS
        assert "bare_page_numbers" not in SERIOUS_ARTIFACT_LABELS
        assert "short_provision" not in SERIOUS_ARTIFACT_LABELS


class TestSuspectReason:
    def test_count_drop_takes_priority(self):
        rd = {"diff": {"status": "count_drop", "total_new": 5, "total_old": 40},
              "schema_fail": True}
        r = suspect_reason(rd)
        assert r is not None and r.startswith("count_drop")

    def test_schema_fail_reported_when_no_count_drop(self):
        rd = {"diff": {"status": "ok"}, "schema_fail": True,
              "serious_artifact_provisions": 12, "total_provisions": 30}
        r = suspect_reason(rd)
        assert r is not None and r.startswith("schema_fail")

    def test_clean_chapter_is_not_suspect(self):
        rd = {"diff": {"status": "ok"}, "schema_fail": False}
        assert suspect_reason(rd) is None

    def test_missing_diff_is_not_suspect(self):
        assert suspect_reason({"schema_fail": False}) is None


class TestBuildSuspectAlert:
    def test_none_when_no_suspects(self):
        clean = [{"council": "c", "chapter_key": "k", "diff": {"status": "ok"}, "schema_fail": False}]
        assert build_suspect_alert("c", clean) is None

    def test_lists_each_suspect_with_reason(self):
        suspect = [
            {"council": "wingecarribee", "chapter_key": "ch-a",
             "diff": {"status": "count_drop", "total_new": 3, "total_old": 50}, "schema_fail": False},
            {"council": "wingecarribee", "chapter_key": "ch-b",
             "diff": {"status": "ok"}, "schema_fail": True,
             "serious_artifact_provisions": 9, "total_provisions": 40},
        ]
        msg = build_suspect_alert("wingecarribee", suspect)
        assert msg is not None
        assert "2 SUSPECT" in msg
        assert "ch-a" in msg and "ch-b" in msg
        assert "count_drop" in msg and "schema_fail" in msg

    def test_filters_out_clean_chapters(self):
        mixed = [
            {"council": "c", "chapter_key": "good", "diff": {"status": "ok"}, "schema_fail": False},
            {"council": "c", "chapter_key": "bad",
             "diff": {"status": "count_drop", "total_new": 1, "total_old": 30}, "schema_fail": False},
        ]
        msg = build_suspect_alert("c", mixed)
        assert msg is not None
        assert "bad" in msg
        assert "good" not in msg
        assert "1 SUSPECT" in msg
