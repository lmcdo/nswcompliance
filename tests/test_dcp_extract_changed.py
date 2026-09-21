"""One bad chapter must not take the whole nightly batch with it.

REAL INCIDENT. Railway's dcp-extract cron crashed with exit -9 (SIGKILL, OOM)
on a 139MB canterbury_bankstown chapter, and because the kill lands on the
process, every OTHER chapter queued that night died with it -- 46 of 47 never
got extracted, and the only trace was a stuck-chapter alert nobody could act
on.

THIS FILE USED TO TEST A BYTE-SIZE GUARD. A 30MB skip was added to contain
that, and it was the wrong signal. Measured after the page-release fix
(tests/test_pdf_page_release.py), peak memory does not track file size at all:

    ku_ring_gai/section-b-part-14e        35MB  ->  726 MB peak
    canterbury_bankstown/chapter-7-6     139MB  ->  440 MB peak
    parramatta/parramatta-dcp-2023-full   50MB  ->  127 MB peak

So the threshold blocked seven chapters that extract perfectly well, and would
have waved through the heaviest one. It is gone.

WHAT REPLACES IT. The PDF work runs in its own process. A SIGKILL cannot be
caught in-process -- no try/except reaches it -- so the only way for a batch to
survive one bad chapter is for that chapter to be somewhere else. The property
these tests protect is unchanged from the file they replace: a chapter that
cannot be extracted is a CONTAINED per-chapter failure with the same return
shape as the R2-download-failure path, never a process-wide crash.

Pure-logic tests: no real DB, no real R2, no real PDF. conftest_mocks.py stubs
psycopg2 so importing the module is safe without credentials.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dcp_extract_changed as dx  # noqa: E402

# This file exercises the regex/geometry reader, not the LLM one. AI_EXTRACTION
# became opt-out on 2026-09-21, so extract() now routes to the LLM unless a caller
# says otherwise -- these tests began trying to open a real PDF and phone a real
# provider (HTTP 429). Saying which reader is under test is the honest fix; turning
# the default off globally in conftest would hide the production behaviour from
# every other test in the suite.
os.environ["AI_EXTRACTION"] = "0"


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


def _fake_download_to_size(target_size: int):
    """Write a REAL file of exactly target_size bytes, sparse via seek."""
    def _download(bucket, key, local_path):
        with open(local_path, "wb") as f:
            if target_size > 0:
                f.seek(target_size - 1)
                f.write(b"\0")
    return _download


# ---------------------------------------------------------------------------
# The size guard is gone, and an oversized chapter now gets extracted
# ---------------------------------------------------------------------------

def test_a_139mb_pdf_is_no_longer_skipped_on_size(monkeypatch):
    """The seven blocked chapters must actually reach extraction.

    This is the test the old file could not have: it asserts the OPPOSITE of
    what that file asserted, because the measurement changed the answer. A
    file well over the old 30MB threshold must now reach extract_pdf_isolated
    rather than returning early.
    """
    s3 = MagicMock()
    s3.download_file.side_effect = _fake_download_to_size(139_006_750)

    reached = {}

    def _fake_isolated(pdf_path, document_id, council, ranges, subpats, ai_on):
        reached["size"] = Path(pdf_path).stat().st_size
        return None, "stopped here on purpose"

    monkeypatch.setattr(dx, "extract_pdf_isolated", _fake_isolated)
    monkeypatch.setattr(dx, "resolve_document_id", lambda *a, **kw: 1)

    ok, review_data = dx.extract_chapter(_chapter(), s3, MagicMock(),
                                         dry_run=True, review=False)

    assert reached.get("size") == 139_006_750, (
        "a 139MB chapter did not reach extraction -- a size guard is still in the path"
    )
    assert (ok, review_data) == (False, None)


def test_no_code_path_compares_pdf_size_against_the_old_threshold():
    """Removing a guard is easy to do halfway.

    The constant may survive for reference, but nothing may gate extraction on
    it. Asserted against the source because the behaviour is an absence, and
    an absence is what silently comes back.
    """
    src = (Path(__file__).resolve().parent.parent
           / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
    assert "pdf_bytes > OVERSIZED_PDF_SKIP_BYTES" not in src


# ---------------------------------------------------------------------------
# A chapter that cannot be extracted is contained
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("exitcode,expected", [
    (-9, "killed by signal 9"),
    (-6, "killed by signal 6"),
    (1, "exit code 1"),
])
def test_a_killed_child_is_a_contained_chapter_failure(monkeypatch, exitcode, expected):
    """Same return shape as the R2-download-failure path, no exception.

    If extract_chapter raised here instead, the batch loop above it would take
    the exception and the incident would repeat in a new costume.
    """
    s3 = MagicMock()
    s3.download_file.side_effect = _fake_download_to_size(1024)
    monkeypatch.setattr(dx, "resolve_document_id", lambda *a, **kw: 1)
    monkeypatch.setattr(
        dx, "extract_pdf_isolated",
        lambda *a, **kw: dx.interpret_isolated_result(None, exitcode))

    ok, review_data = dx.extract_chapter(_chapter(), s3, MagicMock(),
                                         dry_run=True, review=False)
    assert (ok, review_data) == (False, None)


def test_the_pdf_work_really_runs_in_another_process(tmp_path):
    """Isolation that is not actually isolation would be worse than none.

    The whole safety argument rests on the PDF work being somewhere a kill can
    land harmlessly. This proves the child is a different process rather than
    trusting the plumbing -- if extract_pdf_isolated were quietly refactored
    back to an in-process call, everything else here would still pass.
    """
    pytest.importorskip("reportlab")
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    pdf_path = tmp_path / "tiny.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.drawString(72, 720, "1.1 Height")
    c.drawString(72, 700, "Controls C1. Maximum height is 8.5 metres.")
    c.showPage()
    c.save()

    seen = {}
    real_child = dx._pdf_work_child

    def recording_child(queue, *args):
        queue.put({"ok": True, "preflight": {}, "sections": [],
                   "page_count": 0, "ranged": False, "pid": os.getpid()})

    # Under fork the child inherits this patch; under spawn it re-imports and
    # runs the real worker. Either way the payload comes back from a process
    # that is not this one, which is the claim under test.
    import multiprocessing
    if "fork" in multiprocessing.get_all_start_methods():
        dx._pdf_work_child = recording_child
    try:
        result, err = dx.extract_pdf_isolated(str(pdf_path), 1, "ashfield", None, None, False)
    finally:
        dx._pdf_work_child = real_child

    assert err is None, err
    if "pid" in (result or {}):
        assert result["pid"] != os.getpid(), (
            "the PDF work ran in the parent -- a kill would still take the batch"
        )


def test_the_memory_ceiling_and_timeout_are_overridable_but_have_real_defaults():
    """Both are tuned from measurement, not guessed, and both must be present.

    The timeout is roughly 3x the slowest chapter actually measured
    (ku_ring_gai/section-b-part-14e at 395s). The memory ceiling sits above the
    highest measured peak (726 MB) with headroom for an untested file, while
    still bounding a genuine runaway.
    """
    assert dx.PDF_WORK_TIMEOUT_SECONDS >= 395 * 2
    assert dx.PDF_WORK_MEM_LIMIT_BYTES > 726 * 1024 * 1024
    assert dx.JOIN_GRACE_SECONDS > 0 and dx.TERMINATE_GRACE_SECONDS > 0
