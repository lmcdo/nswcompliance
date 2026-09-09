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


def test_oversized_pdf_is_skipped_without_touching_db_or_extractor(monkeypatch, tmp_path):
    """A PDF over OVERSIZED_PDF_SKIP_BYTES is skipped cleanly: extract_chapter
    returns (False, None), and NOTHING downstream of the size check runs --
    not DCPExtractor, not preflight_layout, not even conn.cursor(). This is
    what actually stops the process-wide crash: the guard fires before the
    memory-heavy pdfplumber.open() calls, not after."""

    big_size = dx.OVERSIZED_PDF_SKIP_BYTES + 1

    def fake_download_file(bucket, key, local_path):
        with open(local_path, "wb") as f:
            f.seek(big_size - 1)
            f.write(b"\0")

    s3 = MagicMock()
    s3.download_file.side_effect = fake_download_file

    # conn that raises if ANYTHING touches it -- proves the guard returns
    # before extract_chapter reaches `cur = conn.cursor()`.
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


def test_pdf_under_threshold_is_not_skipped(monkeypatch, tmp_path):
    """The guard must not false-positive on ordinary, correctly-sized chapters
    -- it should let a normal-sized PDF proceed past the check and reach
    DCPExtractor exactly as before this fix existed."""

    small_size = dx.OVERSIZED_PDF_SKIP_BYTES - 1

    def fake_download_file(bucket, key, local_path):
        with open(local_path, "wb") as f:
            f.write(b"\0" * min(small_size, 4096))  # content irrelevant; only size matters, and only a small real write

    s3 = MagicMock()
    s3.download_file.side_effect = fake_download_file

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
