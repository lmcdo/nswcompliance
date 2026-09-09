"""scripts/dcp_extract_changed.py's OVERSIZED_PDF_SKIP_BYTES guard (DQ-98
stability fix, 2026-09-09).

Real incident: Railway's dcp-extract cron crashed with exit -9 (SIGKILL,
OOM) three separate nights running (2026-09-08/09) on a 139MB
canterbury_bankstown chapter, and because extract_chapter() had no size
check before handing the file to pdfplumber, the OS kill took the WHOLE
process down mid-batch -- every OTHER chapter queued in that night's run
(46 of 47) silently never got extracted either, not just the oversized one.

This guard makes the oversized case a normal, contained per-chapter failure
(same return shape as the existing R2-download-failure path three lines
above it in extract_chapter()) instead of a process-wide crash, so the rest
of a batch still completes. It is NOT the DQ-98 fix itself (chunked
extraction) -- that stays open, registered, deliberately deferred.

Pure-logic tests: no real DB, no real R2, no real PDF. conftest_mocks.py
stubs psycopg2 so importing the module is safe without credentials.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dcp_extract_changed as dx  # noqa: E402


def _chapter(**overrides) -> dict:
    base = {
        "council": "canterbury_bankstown",
        "chapter_key": "chapter-7-6-belmore-and-lakemba",
        "id": 1,
        "r2_current_path": "dcp/canterbury_bankstown/chapter-7-6-belmore-and-lakemba.pdf",
        "r2_version_label": "v1",
        "dcp_name": "Canterbury-Bankstown DCP",
    }
    base.update(overrides)
    return base


class _ReachedExtractor(Exception):
    """Sentinel: raised by a patched DCPExtractor to prove control flow got
    past the size guard, without running a real extraction."""


def _fake_download_to_size(target_size: int):
    """Write a REAL file of exactly target_size bytes (sparse via seek+write
    of the last byte) -- Sol LOW 0.99 on an earlier version of this file:
    a test claiming to exercise the ~30MB boundary but only ever writing 4KB
    would still pass if the threshold silently drifted to e.g. 20MB while
    the 30MB constant stayed put in the docstring. Exact size matters."""
    def _download(bucket, key, local_path):
        with open(local_path, "wb") as f:
            if target_size > 0:
                f.seek(target_size - 1)
                f.write(b"\0")
    return _download


def test_oversized_pdf_is_skipped_without_touching_db_or_extractor_under_dry_run(monkeypatch, tmp_path):
    """dry_run=True: A PDF over OVERSIZED_PDF_SKIP_BYTES is skipped cleanly:
    extract_chapter returns (False, None), and NOTHING downstream of the size
    check runs -- not DCPExtractor, not preflight_layout, not even
    conn.cursor(). This is what actually stops the process-wide crash: the
    guard fires before the memory-heavy pdfplumber.open() calls, not after.
    dry_run=True also proves the "no DB writes" contract of that flag holds
    for the new skip-status write added below (Sol HIGH 0.96), not just the
    original guard."""

    s3 = MagicMock()
    s3.download_file.side_effect = _fake_download_to_size(dx.OVERSIZED_PDF_SKIP_BYTES + 1)

    # conn that raises if ANYTHING touches it -- proves the guard returns
    # before extract_chapter reaches conn.cursor(), under dry_run OR not.
    conn = MagicMock()
    conn.cursor.side_effect = AssertionError(
        "conn.cursor() was called -- the oversized-PDF guard did not short-circuit"
    )

    monkeypatch.setattr(
        dx, "DCPExtractor",
        MagicMock(side_effect=_ReachedExtractor("DCPExtractor should never be constructed")),
    )
    monkeypatch.setattr(
        dx, "preflight_layout",
        MagicMock(side_effect=_ReachedExtractor("preflight_layout should never run")),
    )

    ok, review_data = dx.extract_chapter(_chapter(), s3, conn, dry_run=True, review=False)

    assert (ok, review_data) == (False, None)
    s3.download_file.assert_called_once()
    conn.cursor.assert_not_called()


def test_oversized_pdf_alerts_and_records_status_when_not_previously_alerted(monkeypatch):
    """Sol HIGH 0.96: not dry_run, and this is the FIRST time this exact
    content_hash+size has been seen -- must send a Telegram alert (so a
    human actually sees "this chapter is stuck stale", not just an operator
    reading Railway logs) and persist a distinct oversized_pdf status to
    last_suspect_alert_key/_at (so the staleness is DB-queryable, not just a
    one-shot alert)."""

    s3 = MagicMock()
    s3.download_file.side_effect = _fake_download_to_size(dx.OVERSIZED_PDF_SKIP_BYTES + 1)

    cur = MagicMock()
    # Row exists (active chapter, real id) but last_suspect_alert_key is NULL
    # -- fetchone() on a found row with a NULL column returns (None,), NOT
    # bare None. Bare None means "no row found" (see the is_active test
    # below) -- a DIFFERENT condition this test must not be confused with.
    cur.fetchone.return_value = (None,)
    conn = MagicMock()
    conn.cursor.return_value = cur

    sent = []
    fake_run_monitors = MagicMock()
    fake_run_monitors.send_telegram.side_effect = lambda msg: sent.append(msg)
    monkeypatch.setitem(sys.modules, "run_monitors", fake_run_monitors)

    ok, review_data = dx.extract_chapter(
        _chapter(content_hash="abc123"), s3, conn, dry_run=False, review=False,
    )

    assert (ok, review_data) == (False, None)
    assert len(sent) == 1
    assert "canterbury_bankstown" in sent[0]
    assert "chapter-7-6-belmore-and-lakemba" in sent[0]

    update_calls = [c for c in cur.execute.call_args_list if c.args[0].strip().upper().startswith("UPDATE ")]
    assert len(update_calls) == 1
    params = update_calls[0].args[1]
    assert params[0] == f"abc123::oversized_pdf({dx.OVERSIZED_PDF_SKIP_BYTES + 1})"
    conn.commit.assert_called_once()


def test_oversized_pdf_does_not_realert_on_the_same_unchanged_file(monkeypatch):
    """Sol HIGH 0.96, dedup half: re-checking the SAME too-big PDF (same
    content_hash, same size) every night must NOT spam a fresh Telegram
    alert every time -- exactly the failure mode unalerted_suspects()'s own
    docstring documents happening for weeks with a different alert class
    ("the channel stopped being read"). The status row should still be
    touched (to refresh last_suspect_alert_at / prove it's still live),
    just without a duplicate send."""

    s3 = MagicMock()
    s3.download_file.side_effect = _fake_download_to_size(dx.OVERSIZED_PDF_SKIP_BYTES + 1)

    already_key = f"abc123::oversized_pdf({dx.OVERSIZED_PDF_SKIP_BYTES + 1})"
    cur = MagicMock()
    cur.fetchone.return_value = (already_key,)
    conn = MagicMock()
    conn.cursor.return_value = cur

    sent = []
    fake_run_monitors = MagicMock()
    fake_run_monitors.send_telegram.side_effect = lambda msg: sent.append(msg)
    monkeypatch.setitem(sys.modules, "run_monitors", fake_run_monitors)

    ok, review_data = dx.extract_chapter(
        _chapter(content_hash="abc123"), s3, conn, dry_run=False, review=False,
    )

    assert (ok, review_data) == (False, None)
    assert sent == []  # no duplicate alert
    update_calls = [c for c in cur.execute.call_args_list if c.args[0].strip().upper().startswith("UPDATE ")]
    assert len(update_calls) == 1  # status row still refreshed


def test_oversized_pdf_skips_alert_and_write_when_chapter_no_longer_active(monkeypatch):
    """Sol MEDIUM 0.94: a chapter can be deactivated (is_active=FALSE) between
    batch selection and this code running. The SELECT is scoped to
    is_active=TRUE, so it returns no row for a deactivated chapter -- must
    skip BOTH the Telegram alert and the status write entirely, not act on
    stale batch membership."""

    s3 = MagicMock()
    s3.download_file.side_effect = _fake_download_to_size(dx.OVERSIZED_PDF_SKIP_BYTES + 1)

    cur = MagicMock()
    cur.fetchone.return_value = None  # is_active=TRUE filter excluded the row
    conn = MagicMock()
    conn.cursor.return_value = cur

    sent = []
    fake_run_monitors = MagicMock()
    fake_run_monitors.send_telegram.side_effect = lambda msg: sent.append(msg)
    monkeypatch.setitem(sys.modules, "run_monitors", fake_run_monitors)

    ok, review_data = dx.extract_chapter(
        _chapter(content_hash="abc123"), s3, conn, dry_run=False, review=False,
    )

    assert (ok, review_data) == (False, None)
    assert sent == []  # no alert for an inactive chapter
    update_calls = [c for c in cur.execute.call_args_list if c.args[0].strip().upper().startswith("UPDATE ")]
    assert update_calls == []  # no write for an inactive chapter
    conn.commit.assert_not_called()
    conn.rollback.assert_called_once()  # releases any lock, resets transaction state


def test_oversized_pdf_select_locks_the_row_for_update(monkeypatch):
    """Sol MEDIUM 0.98: the read must row-lock (FOR UPDATE) so no other
    transaction can flip is_active on THIS row between the read and the
    write -- without the lock, a deactivation landing in that window would
    still let the (already-decided) Telegram alert fire for a chapter that's
    no longer served."""

    s3 = MagicMock()
    s3.download_file.side_effect = _fake_download_to_size(dx.OVERSIZED_PDF_SKIP_BYTES + 1)

    cur = MagicMock()
    cur.fetchone.return_value = (None,)
    conn = MagicMock()
    conn.cursor.return_value = cur
    monkeypatch.setitem(sys.modules, "run_monitors", MagicMock())

    dx.extract_chapter(_chapter(content_hash="abc123"), s3, conn, dry_run=False, review=False)

    select_calls = [c for c in cur.execute.call_args_list if c.args[0].strip().upper().startswith("SELECT ")]
    assert len(select_calls) == 1
    sql = select_calls[0].args[0].upper()
    assert "FOR UPDATE" in sql
    assert "IS_ACTIVE = TRUE" in sql


def test_pdf_under_threshold_is_not_skipped(monkeypatch):
    """The guard must not false-positive on ordinary, correctly-sized chapters
    -- it should let a normal-sized PDF proceed past the check and reach
    DCPExtractor exactly as before this fix existed. Writes a REAL file at
    exactly threshold-1 bytes (not a 4KB stand-in, Sol LOW 0.99) so a future
    threshold change that silently drifts the boundary would actually be
    caught here."""

    s3 = MagicMock()
    s3.download_file.side_effect = _fake_download_to_size(dx.OVERSIZED_PDF_SKIP_BYTES - 1)

    monkeypatch.setattr(
        dx, "DCPExtractor",
        MagicMock(side_effect=_ReachedExtractor("reached DCPExtractor as expected")),
    )

    conn = MagicMock()

    with pytest.raises(_ReachedExtractor):
        dx.extract_chapter(_chapter(), s3, conn, dry_run=True, review=False)


def test_pdf_at_exact_threshold_is_not_skipped(monkeypatch):
    """Boundary case: the guard is strictly-greater-than (`>`), so a PDF at
    EXACTLY OVERSIZED_PDF_SKIP_BYTES must still proceed, not be skipped."""

    s3 = MagicMock()
    s3.download_file.side_effect = _fake_download_to_size(dx.OVERSIZED_PDF_SKIP_BYTES)

    monkeypatch.setattr(
        dx, "DCPExtractor",
        MagicMock(side_effect=_ReachedExtractor("reached DCPExtractor as expected")),
    )

    conn = MagicMock()

    with pytest.raises(_ReachedExtractor):
        dx.extract_chapter(_chapter(), s3, conn, dry_run=True, review=False)


def test_threshold_matches_documented_dq98_heuristic():
    """Guards against silent drift between this constant and the one
    scripts/dq_probe_oversized_pdf_oom_risk.py reports against -- the two
    are deliberately separate literals (not imported from one another, see
    that script's module docstring), so nothing else keeps them in sync."""
    assert dx.OVERSIZED_PDF_SKIP_BYTES == 30 * 1024 * 1024
