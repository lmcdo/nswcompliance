"""dcp_extract_changed: hold chapters refused twice on the same PDF; read 2 at once in review mode.

Measured 2026-11-03: canterbury_bankstown chapter-7-6 was refused 4 times on one unchanged
file (PageLoss), ~10 minutes each, always ahead of the chapter that needed reading.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import dcp_extract_changed as dx  # noqa: E402


@pytest.mark.parametrize("err", [
    "PageLoss: 2 page(s) holding rules still left out after being read again: [64, 139].",
    "ChunkLoss: 1 of 12 chunks returned NO provisions",
])
def test_a_content_refusal_counts(err):
    assert dx.is_content_refusal(err)


@pytest.mark.parametrize("err", [
    "RateLimitError: Error code: 429 - You have no credits remaining.",
    "AuthenticationError: Error code: 401 - Incorrect API key provided",
    "PDF work timed out after 3600s", "", None,
])
def test_a_temporary_failure_never_counts_toward_a_hold(err):
    """Sutherland ch2 failed twice for credit alone; holding it would have been wrong."""
    assert not dx.is_content_refusal(err)


def test_the_daily_run_holds_a_chapter_refused_twice_on_its_current_pdf():
    q, _ = dx._pending_chapters_sql(None, all_chapters=False)
    assert "NOT " + dx.HELD_FOR_REFUSALS in q
    assert "extract_refused_hash = dcp_chapter_registry.content_hash" in dx.HELD_FOR_REFUSALS
    assert f">= {dx.HOLD_AFTER_REFUSALS}" in dx.HELD_FOR_REFUSALS and dx.HOLD_AFTER_REFUSALS == 2


def test_a_null_hash_is_never_held():
    """coalesce(..., false): NULL = NULL must read as 'not refused', or NOT(...) drops the row."""
    assert dx.HELD_FOR_REFUSALS.startswith("(coalesce(") and ", false)" in dx.HELD_FOR_REFUSALS


def test_a_named_chapter_and_the_audit_run_ignore_the_hold():
    q1, _ = dx._pending_chapters_sql("x", all_chapters=False, chapter_filter="k")
    q2, _ = dx._pending_chapters_sql(None, all_chapters=True)
    assert dx.HELD_FOR_REFUSALS not in q1 and dx.HELD_FOR_REFUSALS not in q2


def test_the_refusal_counter_restarts_on_a_new_pdf():
    sql = dx._record_refusal_sql()
    assert "WHEN extract_refused_hash IS NOT DISTINCT FROM content_hash THEN extract_refusals + 1 ELSE 1" in sql
    assert "extract_refused_hash = content_hash" in sql


# ── run_chapters ────────────────────────────────────────────────────────────

ARGS = SimpleNamespace(dry_run=False, review=True, allow_section_loss=[], allow_area_link_loss=[])
CHAPTERS = [{"id": i, "council": "c", "chapter_key": f"k{i}"} for i in range(5)]


@pytest.fixture()
def fake_db(monkeypatch):
    class Conn:
        def close(self):
            pass
    monkeypatch.setattr(dx.psycopg2, "connect", lambda *a, **k: Conn(), raising=False)
    monkeypatch.setattr(dx.pipeline_run, "tag", lambda c, s: "run")
    monkeypatch.setattr(dx, "revive", lambda c: c)
    return Conn()


@pytest.mark.skipif(sys.platform == "win32", reason="fork only: Windows takes the one-at-a-time path")
def test_results_come_back_in_chapter_order_and_one_crash_fails_only_that_chapter(monkeypatch, fake_db):
    def fake_extract(chapter, s3, conn, **kw):
        if chapter["chapter_key"] == "k2":
            raise RuntimeError("boom")
        return True, {"key": chapter["chapter_key"]}
    monkeypatch.setattr(dx, "extract_chapter", fake_extract)
    out = dx.run_chapters(CHAPTERS, object(), fake_db, ARGS, s3_factory=object)
    assert [o[1]["key"] if o[0] else None for o in out] == ["k0", "k1", None, "k3", "k4"]


def test_live_commit_mode_stays_one_at_a_time(monkeypatch, fake_db):
    seen = []
    monkeypatch.setattr(dx, "extract_chapter", lambda ch, s3, c, **kw: (seen.append(ch["chapter_key"]) or (True, None)))
    live = SimpleNamespace(**{**vars(ARGS), "review": False})
    dx.run_chapters(CHAPTERS, object(), fake_db, live, s3_factory=object)
    assert seen == [c["chapter_key"] for c in CHAPTERS]      # in-process, in order


@pytest.mark.skipif(sys.platform == "win32", reason="fork only: Windows takes the one-at-a-time path")
def test_a_worker_that_dies_reports_its_chapters_as_failed_not_dropped(monkeypatch, fake_db):
    import os
    def fake_extract(chapter, s3, conn, **kw):
        if chapter["chapter_key"] == "k1":
            os._exit(9)                                       # the worker process dies outright
        return True, {"key": chapter["chapter_key"]}
    monkeypatch.setattr(dx, "extract_chapter", fake_extract)
    out = dx.run_chapters(CHAPTERS[:2], object(), fake_db, ARGS, s3_factory=object)
    assert out[1] == (False, None) and out[0][0] is True


def test_a_hold_is_bounded_not_forever():
    """Sol review: a held chapter keeps serving the previous PDF, so it is tried again."""
    assert f"interval '{dx.HOLD_DAYS} days'" in dx.HELD_FOR_REFUSALS and dx.HOLD_DAYS == 7
    assert "extract_refused_at = now()" in dx._record_refusal_sql()


@pytest.mark.skipif(sys.platform == "win32", reason="fork only: Windows takes the one-at-a-time path")
def test_a_finished_chapter_survives_its_worker_dying_on_the_next_one(monkeypatch, fake_db):
    """Measured on Linux 2026-11-03: with a Queue, k0's result died with the worker that
    went on to crash on k2. Worker A: k0 (fast) then k2 (dies); worker B: k1 (slow)."""
    import os
    import time
    def fake_extract(chapter, s3, conn, **kw):
        key = chapter["chapter_key"]
        if key == "k1":
            time.sleep(1.5)
        if key == "k2":
            os._exit(9)
        return True, {"key": key}
    monkeypatch.setattr(dx, "extract_chapter", fake_extract)
    out = dx.run_chapters(CHAPTERS[:3], object(), fake_db, ARGS, s3_factory=object)
    assert out[0] == (True, {"key": "k0"}) and out[1] == (True, {"key": "k1"}) and out[2] == (False, None)
