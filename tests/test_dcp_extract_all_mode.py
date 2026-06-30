"""Tests for the --all (re-extract-all) chapter selection in dcp_extract_changed.py.

--all drops the needs_extraction byte-change filter so EVERY active chapter is
re-extracted and diffed vs the approved baseline (the scheduled detector cadence).
is_active + r2_current_path remain required in both modes.
"""
import os
import sys
from unittest.mock import MagicMock

# The module reads R2/DB env at import time — set dummies before importing.
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
           "R2_BUCKET_NAME", "R2_ENDPOINT_URL", "R2_PUBLIC_URL"):
    os.environ.setdefault(_k, "test")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")

# Stub heavy module deps so the pure SQL-builder imports without them — then RESTORE
# sys.modules so the stubs do not leak into other tests (e.g. enrichment.pipeline,
# which test_gemini_stage3_routing imports for real).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
_STUBS = ("boto3", "botocore", "pdfplumber", "psycopg2", "dotenv", "enrichment", "enrichment.pipeline")
_saved = {k: sys.modules.get(k) for k in _STUBS}
for _k in _STUBS:
    sys.modules[_k] = MagicMock()
sys.modules["dotenv"].load_dotenv = MagicMock()
try:
    from dcp_extract_changed import _pending_chapters_sql  # noqa: E402
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v


class TestPendingChaptersSql:
    def test_reactive_default_keeps_needs_extraction_filter(self):
        q, p = _pending_chapters_sql(None, all_chapters=False)
        assert "needs_extraction = TRUE" in q
        assert "is_active = TRUE" in q and "r2_current_path IS NOT NULL" in q
        assert p == []

    def test_all_mode_drops_needs_extraction_filter(self):
        q, p = _pending_chapters_sql(None, all_chapters=True)
        assert "needs_extraction" not in q
        assert "is_active = TRUE" in q and "r2_current_path IS NOT NULL" in q
        assert p == []

    def test_council_filter_adds_param_in_both_modes(self):
        for allc in (True, False):
            q, p = _pending_chapters_sql("ku_ring_gai", all_chapters=allc)
            assert "council = %s" in q
            assert p == ["ku_ring_gai"]

    def test_ordering_preserved(self):
        for allc in (True, False):
            q, _ = _pending_chapters_sql(None, all_chapters=allc)
            assert q.rstrip().endswith("ORDER BY council, sort_order")

    def test_all_mode_still_scopes_to_active_with_a_path(self):
        # Safety: --all must NOT pull inactive or path-less chapters
        q, _ = _pending_chapters_sql(None, all_chapters=True)
        assert "is_active = TRUE" in q
        assert "r2_current_path IS NOT NULL" in q

    def test_all_mode_only_text_dcps_with_provisions(self):
        # --all must skip spatial/map "chapters" that have an r2_current_path but no
        # extractable text: require existing current provisions for the chapter.
        q, _ = _pending_chapters_sql(None, all_chapters=True)
        assert "EXISTS (SELECT 1 FROM regulatory_provisions rp" in q
        assert "rp.source_council = dcp_chapter_registry.council" in q
        assert "rp.source_chapter_key = dcp_chapter_registry.chapter_key" in q
        assert "rp.is_current = TRUE" in q

    def test_reactive_mode_has_no_provisions_filter(self):
        # First extractions (no provisions yet) must still flow through the reactive
        # path, so it must NOT carry the EXISTS-provisions scope.
        q, _ = _pending_chapters_sql(None, all_chapters=False)
        assert "regulatory_provisions" not in q
