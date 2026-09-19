"""Three ways a one-hour extraction fails that a one-minute extraction never did.

Batching OCR (#1142) turned one request into forty-seven and a two-minute job into an
hour. Every one of these was found by RUNNING the real extractor on
city_of_sydney/section-3-general-provisions, not by reading it:

1. The chapter is killed at 20 minutes, and the error blames memory.
   `[ERROR] extraction process was killed by signal 15 (out of memory is the usual
   cause)` — on a host with memory to spare. Signal 15 is SIGTERM, which is what the
   PARENT sends on timeout; the OOM killer sends 9. The timeout path terminates the
   child, so its exit code says "signal", and the signal branch answered with the wrong
   cause. That misdirection cost real time.

2. One transient blip loses the hour. `batch 1/47 failed (RemoteDisconnected('Remote end
   closed connection without response'))` — a Modal cold start — and the chapter fell
   back to its garbled text layer. Abandoning on first failure is right for data
   integrity and wrong for finishing: at a 2% per-batch failure rate a 47-batch run
   fails more often than it succeeds.

3. The database connection does not outlive the PDF work. `psycopg2.OperationalError:
   server closed the connection unexpectedly` at diff_provisions — the connection is
   opened once for the batch and sits idle throughout.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SRC = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")


def _mod():
    import dcp_extract_changed
    return dcp_extract_changed


class TestATimeoutDoesNotMasqueradeAsOutOfMemory:
    def test_a_timeout_says_so_and_names_the_budget(self):
        m = _mod()
        payload, err = m.interpret_isolated_result(None, -15, timed_out=True, budget=6000)
        assert payload is None
        assert "6000s budget" in err
        assert "Not a memory problem" in err
        assert "DCP_PDF_TIMEOUT" in err, "the message must say how to give it longer"

    def test_a_REAL_signal_kill_still_reports_a_signal_kill(self):
        """Confusable negative, and the reason the timeout flag is passed rather than
        inferred: a genuine OOM kill arrives as SIGKILL with no timeout, and must keep
        pointing at memory. Both arrive as 'result is None' with a negative exit code."""
        m = _mod()
        payload, err = m.interpret_isolated_result(None, -9)
        assert "killed by signal 9" in err
        assert "out of memory" in err
        assert "budget" not in err

    def test_the_timeout_branch_is_checked_before_the_signal_branch(self):
        """Order is load-bearing. A timeout is followed by terminate(), so the exit code
        is negative in BOTH cases; if the signal branch ran first it would always win and
        the timeout message would be unreachable — which is what it was."""
        body = SRC[SRC.index("def interpret_isolated_result"):]
        body = body[:body.index("if not result.get(\"ok\")")]
        assert body.index("if timed_out:") < body.index("if exitcode is not None and exitcode < 0:")

    def test_the_parent_tells_the_interpreter_which_happened(self):
        """It cannot be worked out from the exit code, so it must be passed."""
        assert "timed_out=timed_out, budget=budget" in SRC
        assert "timed_out = True" in SRC


class TestTheBudgetFitsTheWorkItContains:
    def test_a_long_chapter_gets_more_than_the_flat_default(self, monkeypatch):
        m = _mod()
        monkeypatch.delenv("DCP_PDF_TIMEOUT", raising=False)
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        assert m.pdf_work_budget_seconds(141) > 141 * 27, (
            "a 141-page chapter costs ~62 min of OCR; a budget under that kills it")

    def test_a_chapter_without_OCR_keeps_exactly_the_old_bound(self, monkeypatch):
        """Confusable negative: this must not loosen the cap for work that was already
        fast. A hung chapter with no OCR still gets 20 minutes, not two hours."""
        m = _mod()
        monkeypatch.delenv("DCP_PDF_TIMEOUT", raising=False)
        monkeypatch.delenv("MODAL_OCR_URL", raising=False)
        assert m.pdf_work_budget_seconds(366) == m.PDF_WORK_TIMEOUT_SECONDS

    def test_an_unknown_page_count_keeps_the_old_bound(self, monkeypatch):
        m = _mod()
        monkeypatch.delenv("DCP_PDF_TIMEOUT", raising=False)
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        assert m.pdf_work_budget_seconds(None) == m.PDF_WORK_TIMEOUT_SECONDS

    def test_an_operators_explicit_number_wins(self, monkeypatch):
        """Someone who sets DCP_PDF_TIMEOUT is answering this exact question and must not
        be silently overridden — including downwards."""
        m = _mod()
        monkeypatch.setenv("DCP_PDF_TIMEOUT", "900")
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        assert m.pdf_work_budget_seconds(366) == m.PDF_WORK_TIMEOUT_SECONDS

    def test_the_page_count_is_read_in_the_parent_and_never_raises(self, tmp_path):
        """It only decides how long to WAIT. A broken PDF has its own errors downstream,
        so failing to count its pages must fall back, not refuse."""
        m = _mod()
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"not a pdf at all")
        assert m._page_count_for_budget(bad) is None


class TestOneBlipDoesNotLoseTheHour:
    def _pdf(self, tmp_path, pages):
        pytest.importorskip("pypdf")
        from pypdf import PdfWriter
        w = PdfWriter()
        for _ in range(pages):
            w.add_blank_page(width=200, height=200)
        p = tmp_path / "x.pdf"
        with open(p, "wb") as f:
            w.write(f)
        return p

    def test_a_transient_batch_failure_is_retried(self, tmp_path, monkeypatch):
        m = _mod()
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        monkeypatch.setattr(m, "OCR_RETRY_BACKOFF_SECONDS", 0)
        calls = []

        def flaky(url, tok, blob, n, label):
            calls.append(label)
            return None if len(calls) == 1 else ["p"] * n      # first attempt blips
        monkeypatch.setattr(m, "_fetch_ocr_batch", flaky)
        out = m.fetch_ocr_page_texts(self._pdf(tmp_path, 6), expected_pages=6)
        assert out is not None and len(out) == 6, "one blip still lost the chapter"
        assert len(calls) == 3, f"expected retry then two batches, got {calls}"

    def test_a_dead_endpoint_does_not_cost_47_batches_x_3(self, tmp_path, monkeypatch):
        """The whole-chapter cap. Retrying every batch of a systematically broken
        endpoint would turn 47 calls into 141 and waste an hour proving it is broken."""
        m = _mod()
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        monkeypatch.setattr(m, "OCR_RETRY_BACKOFF_SECONDS", 0)
        calls = []
        monkeypatch.setattr(m, "_fetch_ocr_batch",
                            lambda *a, **k: calls.append(1) or None)
        assert m.fetch_ocr_page_texts(self._pdf(tmp_path, 30), expected_pages=30) is None
        assert len(calls) <= 1 + m.OCR_BATCH_RETRIES, (
            f"a dead endpoint cost {len(calls)} calls; it should give up on the first "
            f"batch after its retries")

    def test_it_still_abandons_the_chapter_when_retries_run_out(self, tmp_path, monkeypatch):
        """Retrying must not turn into committing half a chapter. A batch that never
        succeeds still abandons the whole thing."""
        m = _mod()
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        monkeypatch.setattr(m, "OCR_RETRY_BACKOFF_SECONDS", 0)
        monkeypatch.setattr(m, "_fetch_ocr_batch", lambda *a, **k: None)
        assert m.fetch_ocr_page_texts(self._pdf(tmp_path, 9), expected_pages=9) is None

    def test_a_healthy_run_retries_nothing(self, tmp_path, monkeypatch):
        m = _mod()
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        calls = []
        monkeypatch.setattr(m, "_fetch_ocr_batch",
                            lambda url, tok, blob, n, label: calls.append(label) or ["p"] * n)
        assert m.fetch_ocr_page_texts(self._pdf(tmp_path, 9), expected_pages=9) is not None
        assert len(calls) == 3, "a healthy run must cost exactly one call per batch"


class TestTheConnectionOutlivesThePdfWork:
    def test_the_connection_asks_for_keepalives(self):
        """The connection is opened once for the batch and sits idle through an hour of
        PDF work, so the pooler reaps it and the next query dies. libpq keepalives keep
        the socket alive without the application polling."""
        assert "keepalives=1" in SRC
        assert "keepalives_idle=" in SRC
        assert "keepalives_interval=" in SRC and "keepalives_count=" in SRC

    def test_the_idle_interval_is_shorter_than_a_single_ocr_batch(self):
        """A keepalive less frequent than the gaps it covers would not prevent anything.
        One batch is ~85s, and the whole extraction is idle on the DB throughout."""
        m = _mod()
        idle = int(SRC.split("keepalives_idle=")[1].split(",")[0])
        assert idle < m.OCR_PAGES_PER_REQUEST * 28.4
