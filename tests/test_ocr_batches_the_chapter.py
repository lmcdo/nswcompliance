"""OCR was asked for on every big chapter, and could never answer.

fetch_ocr_page_texts posted the whole chapter as one request. Measured against the live
endpoint 2026-09-19: ~28.4s a page, and the response only arrives when the last page is
done. A 3-page slice returned 200 in 85.3s; an 8-page slice was killed by the 120s
silence cap after 133.3s, with the shipped code printing

    [OCR] fetch failed (Read timed out. (read timeout=120)) -- staying on text layer

city_of_sydney/section-3 is 141 pages, northern_beaches 273, city_of_sydney/section-5
366. Every chapter large enough to matter asked for OCR, waited two minutes, gave up and
served its garbled text layer without a word — because falling back is the designed
behaviour on failure, and nothing distinguishes "OCR said no" from "OCR was never needed".

It was never the trigger: text_layer_garbled() returns True for both those chapters, so
OCR was already being requested. The request simply could not complete.

The same 8-page slice now returns 8 clean pages in 3 batches, and the map plate that read
'r r r i v i e g g e h h p d t t u .' scores 0.000 on the single-letter-token ratio.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SRC = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")


def _mod():
    import dcp_extract_changed
    return dcp_extract_changed


class TestOneRequestPerChapterIsGone:
    def test_the_pdf_is_sent_in_batches(self):
        m = _mod()
        assert m.OCR_PAGES_PER_REQUEST >= 1
        assert "for n, first in enumerate(range(0, expected_pages, OCR_PAGES_PER_REQUEST)" in SRC

    def test_a_batch_fits_inside_the_silence_cap(self):
        """The cap is silence between bytes, and the endpoint sends nothing until the last
        page of a batch is done. 3 pages measured 85.3s against a 120s cap; 4 would be
        ~114s and 8 measured 133.3s and failed."""
        m = _mod()
        assert m.OCR_PAGES_PER_REQUEST * 28.4 < m.OCR_READ_TIMEOUT, (
            f"{m.OCR_PAGES_PER_REQUEST} pages at the measured 28.4s/page exceeds the "
            f"{m.OCR_READ_TIMEOUT}s silence cap — batches would time out as before")

    def test_the_posted_body_is_the_slice_not_the_whole_file(self):
        """Posting open(pdf_path).read() again would send the whole chapter per batch:
        every request would carry 15MB and OCR the same 141 pages."""
        assert "data=blob," in SRC
        assert 'data=open(pdf_path, "rb").read()' not in SRC


class TestTheDeadlineScalesWithTheWork:
    def test_a_fixed_deadline_would_still_kill_every_real_chapter(self):
        """At ~28s a page a flat 600s stops at about page 21, so the chapters this fix
        exists for would fail anyway — the same bug one level up.

        Driven, not recomputed: an earlier version of this test did the max() itself and
        therefore passed while the code used a flat constant. It is asserted against the
        source, and the behaviour is pinned by the clock test below."""
        driver = SRC[SRC.index("def fetch_ocr_page_texts"):SRC.index("def _fetch_ocr_batch")]
        scaled = "deadline = max(OCR_TOTAL_DEADLINE, expected_pages * OCR_SECONDS_PER_PAGE)"
        assert scaled in driver, "the deadline no longer scales with the chapter"
        m = _mod()
        assert max(m.OCR_TOTAL_DEADLINE, 141 * m.OCR_SECONDS_PER_PAGE) > 141 * 28.4

    def test_small_chapters_keep_the_old_floor(self):
        """Confusable negative: scaling must not shorten anything. A 5-page chapter keeps
        the 600s it had."""
        m = _mod()
        assert max(m.OCR_TOTAL_DEADLINE, 5 * m.OCR_SECONDS_PER_PAGE) == m.OCR_TOTAL_DEADLINE

    def test_the_per_page_budget_has_headroom_over_what_was_measured(self):
        """28.4s cold, 17-21s warm. A budget at or under the cold cost would abandon a
        chapter that was merely unlucky with container starts."""
        m = _mod()
        assert m.OCR_SECONDS_PER_PAGE > 28.4

    def test_the_budget_is_announced_before_the_work_starts(self):
        """A two-hour job that says nothing until it finishes is indistinguishable from a
        hang — which is how the 120s failure stayed invisible."""
        assert 'budget {deadline / 60:.0f} min' in SRC

    def test_the_clock_is_checked_between_batches(self):
        """The existing note records three measured attempts at bounding total duration
        in-thread, all defeated because iter_content blocks INSIDE the read. Between
        batches nothing is blocked, so this is the first place the deadline is real."""
        driver = SRC[SRC.index("def fetch_ocr_page_texts"):SRC.index("def _fetch_ocr_batch")]
        assert "spent = _time.monotonic() - started" in driver
        assert "if spent > deadline:" in driver


class TestAShortAnswerCannotShiftThePages:
    """PR #836's defect: a response with fewer pages than the PDF maps OCR text onto the
    wrong source pages. Batching multiplies the chances, so it is checked per batch AND
    in total."""

    def test_each_batch_must_return_its_own_page_count(self):
        batch = SRC[SRC.index("def _fetch_ocr_batch"):]
        assert "if len(pages) != expected_pages:" in batch

    def test_the_total_is_checked_as_well(self):
        driver = SRC[SRC.index("def fetch_ocr_page_texts"):SRC.index("def _fetch_ocr_batch")]
        assert "if len(out) != expected_pages:" in driver

    def test_one_failed_batch_abandons_the_whole_chapter(self):
        """Half a chapter of OCR text spliced onto half a chapter of garbled text layer
        would be worse than either: the page numbers would be right and the text wrong."""
        driver = SRC[SRC.index("def fetch_ocr_page_texts"):SRC.index("def _fetch_ocr_batch")]
        assert "if got is None:" in driver
        assert driver.count("return None") >= 3

    def test_the_failure_names_the_pages_that_failed(self):
        assert "pages {first + 1}-{first + count}" in SRC


class TestItRunsWithoutTheNetwork:
    """Drives the real driver with the batch POST stubbed, so the ordering, the slicing
    and the contract checks are exercised rather than described."""

    @staticmethod
    def _pdf(tmp_path, pages: int) -> Path:
        pytest.importorskip("pypdf")
        from pypdf import PdfWriter
        w = PdfWriter()
        for _ in range(pages):
            w.add_blank_page(width=200, height=200)
        p = tmp_path / "x.pdf"
        with open(p, "wb") as f:
            w.write(f)
        return p

    def test_pages_come_back_in_order_across_batches(self, tmp_path, monkeypatch):
        m = _mod()
        pdf = self._pdf(tmp_path, 8)
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        seen = []

        def fake(url, token, blob, expected_pages, label):
            seen.append((label, expected_pages))
            n = len(seen)
            return [f"batch{n}-page{i}" for i in range(expected_pages)]

        monkeypatch.setattr(m, "_fetch_ocr_batch", fake)
        out = m.fetch_ocr_page_texts(pdf, expected_pages=8)
        assert out is not None and len(out) == 8
        assert out[0] == "batch1-page0" and out[3] == "batch2-page0"
        assert [n for _lbl, n in seen] == [3, 3, 2], "the last batch must be the remainder"

    def test_a_failing_batch_returns_None_and_stops(self, tmp_path, monkeypatch):
        m = _mod()
        pdf = self._pdf(tmp_path, 8)
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        calls = []

        def fake(url, token, blob, expected_pages, label):
            calls.append(label)
            return None if len(calls) == 2 else ["x"] * expected_pages

        monkeypatch.setattr(m, "_fetch_ocr_batch", fake)
        assert m.fetch_ocr_page_texts(pdf, expected_pages=8) is None
        assert len(calls) == 2, "it kept going after a batch failed"

    def test_no_url_still_returns_None_without_slicing(self, tmp_path, monkeypatch):
        m = _mod()
        pdf = self._pdf(tmp_path, 4)
        monkeypatch.delenv("MODAL_OCR_URL", raising=False)
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        assert m.fetch_ocr_page_texts(pdf, expected_pages=4) is None

    def test_a_long_chapter_is_not_abandoned_at_the_old_flat_deadline(self, tmp_path,
                                                                      monkeypatch):
        """The clock is driven forward past 600s mid-chapter. Under the flat deadline the
        run is abandoned; under a budget that scales it finishes. This is the test the
        arithmetic one could not do."""
        import time as _t
        m = _mod()
        pdf = self._pdf(tmp_path, 30)          # 10 batches, budget 30*45 = 1350s
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        ticks = iter([0] + [80 * i for i in range(1, 40)])   # 80s a batch -> past 600s at batch 8
        monkeypatch.setattr(_t, "monotonic", lambda: next(ticks))
        monkeypatch.setattr(m, "_fetch_ocr_batch",
                            lambda url, tok, blob, n, label: ["p"] * n)
        out = m.fetch_ocr_page_texts(pdf, expected_pages=30)
        assert out is not None and len(out) == 30, (
            "a 30-page chapter was abandoned even though its budget is 1350s — the "
            "deadline is not scaling with the work")

    def test_a_chapter_that_really_overruns_IS_abandoned(self, tmp_path, monkeypatch):
        """Confusable negative: the budget must still bound something, or this fix just
        removes the guard."""
        import time as _t
        m = _mod()
        pdf = self._pdf(tmp_path, 30)
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        ticks = iter([0] + [500 * i for i in range(1, 40)])  # 500s a batch -> past 1350s early
        monkeypatch.setattr(_t, "monotonic", lambda: next(ticks))
        monkeypatch.setattr(m, "_fetch_ocr_batch",
                            lambda url, tok, blob, n, label: ["p"] * n)
        assert m.fetch_ocr_page_texts(pdf, expected_pages=30) is None

    def test_an_unreadable_pdf_returns_None_instead_of_raising(self, tmp_path, monkeypatch):
        """Found by an existing test breaking, not by reading the code. Slicing parses
        the PDF, which posting its bytes never did, so a truncated or malformed file now
        raises where it used to sail through. fetch_ocr_page_texts is documented to
        return None on ANY failure so the caller stays on the text layer — an exception
        escaping it would take down the whole nightly run instead of skipping one
        chapter."""
        m = _mod()
        bad = tmp_path / "bad.pdf"
        bad.write_bytes(b"%PDF-1.4\n")          # a header and nothing else
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        monkeypatch.setattr(m, "_fetch_ocr_batch",
                            lambda *a, **k: pytest.fail("posted an unreadable PDF"))
        assert m.fetch_ocr_page_texts(bad, expected_pages=1) is None

    def test_the_slice_really_holds_the_pages_asked_for(self, tmp_path):
        pytest.importorskip("pypdf")
        from pypdf import PdfReader
        import io
        m = _mod()
        pdf = self._pdf(tmp_path, 10)
        blob = m._ocr_pdf_slice(pdf, first=4, count=3)
        assert blob is not None
        assert len(PdfReader(io.BytesIO(blob)).pages) == 3

    def test_a_slice_past_the_end_is_truncated_not_padded(self, tmp_path):
        """The last batch of a chapter whose page count is not a multiple of the batch
        size. Padding would break the per-batch count check for the wrong reason."""
        pytest.importorskip("pypdf")
        from pypdf import PdfReader
        import io
        m = _mod()
        pdf = self._pdf(tmp_path, 5)
        blob = m._ocr_pdf_slice(pdf, first=3, count=3)
        assert len(PdfReader(io.BytesIO(blob)).pages) == 2
