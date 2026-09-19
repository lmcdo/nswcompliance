"""Three constants sized from a warm idle endpoint, corrected from a real 47-batch run.

The first complete run of city_of_sydney/section-3-general-provisions (141 pages,
2026-09-19) got 44 of 47 batches and then threw all of it away. Its own numbers say why:

    44 batches:  min 68s   median 104s   p90 118s   max 140s
                                              against OCR_READ_TIMEOUT = 120s

The cap sat AT the p90. Batches landed at 118, 118, 119, 119 and 120 seconds. The 85.3s
that justified a 3-page batch came from a warm idle endpoint; under 47 sustained requests
the median is 22% slower and the tail reaches 140s.

Three batches failed. Two were rescued by the retry — the mechanism works — and the third
exhausted a whole-chapter budget of 6, because 11 and 15 had taken two each. A fixed 6
cannot cover 47 batches, the same class of error as a fixed 600s OCR deadline and a fixed
1200s process cap: a constant sized for smaller work.

Then the all-or-nothing rule discarded 138 good pages and re-enqueued the same unreadable
text the run existed to replace. That rule was justified as "half a chapter of OCR spliced
onto half a chapter of garbled text reads as success" — but the alternative it chose was a
WHOLE chapter of garbled text.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SRC = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")

# Every batch duration the real run reported, in seconds.
OBSERVED_MAX = 140
OBSERVED_P90 = 118


def _mod():
    import dcp_extract_changed
    return dcp_extract_changed


class TestTheCapIsAboveTheTailNotInsideIt:
    def test_the_silence_cap_clears_the_worst_observed_batch(self):
        m = _mod()
        assert m.OCR_READ_TIMEOUT > OBSERVED_MAX, (
            f"the cap is {m.OCR_READ_TIMEOUT}s and a real batch took {OBSERVED_MAX}s")

    def test_it_clears_it_with_room_rather_than_by_a_second(self):
        """A cap a hair above the observed maximum is the same coin flip one notch
        along: the maximum was 140s on the run that happened, not a ceiling."""
        m = _mod()
        assert m.OCR_READ_TIMEOUT >= 2 * OBSERVED_MAX

    def test_it_still_calls_a_dead_endpoint_within_minutes(self):
        """Confusable negative. This cap exists to notice silence; raising it without
        limit would turn a dead endpoint into an all-night hang. Total duration is
        bounded by the chapter budget, so this only has to be brisk, not tight."""
        m = _mod()
        assert m.OCR_READ_TIMEOUT <= 600

    def test_a_batch_is_still_sized_to_fit_the_cap(self):
        """The batch size and the cap have to move together. At the MEASURED median of
        ~35s a page under load, three pages is ~104s and must fit with margin."""
        m = _mod()
        assert m.OCR_PAGES_PER_REQUEST * 35 < m.OCR_READ_TIMEOUT / 2


class TestTheRetryBudgetScalesWithTheWork:
    def test_a_47_batch_chapter_gets_more_than_six(self):
        m = _mod()
        assert m.ocr_chapter_retry_budget(47) > 6, (
            "six retries across 47 batches is what lost the run: batches 11 and 15 "
            "took two each and 45 had two left")

    def test_a_small_chapter_keeps_the_floor(self):
        """Confusable negative: scaling must not make a 3-batch chapter stingier."""
        m = _mod()
        assert m.ocr_chapter_retry_budget(3) == m.OCR_CHAPTER_RETRY_MINIMUM

    def test_it_is_still_bounded_well_below_retrying_everything(self):
        """A budget that grows to one-per-batch would let a dead endpoint cost the
        whole wall-clock proving it is dead."""
        m = _mod()
        for batches in (47, 91, 122):
            assert m.ocr_chapter_retry_budget(batches) < batches / 2


class TestOnePagesFailureDoesNotDiscardTheChapter:
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

    def _env(self, monkeypatch, m):
        monkeypatch.setenv("MODAL_OCR_URL", "https://example.invalid")
        monkeypatch.setenv("MODAL_OCR_TOKEN", "t")
        monkeypatch.setattr(m, "OCR_RETRY_BACKOFF_SECONDS", 0)

    def test_the_other_pages_survive_one_dead_batch(self, tmp_path, monkeypatch):
        """The run that prompted this kept 138 of 141 pages and threw them away."""
        m = _mod()
        self._env(monkeypatch, m)
        monkeypatch.setattr(m, "_fetch_ocr_batch",
                            lambda url, tok, blob, n, label:
                            None if label.startswith("5/") else ["ocr"] * n)
        out = m.fetch_ocr_page_texts(self._pdf(tmp_path, 60), expected_pages=60)
        assert out is not None, "one dead batch still discarded the whole chapter"
        assert len(out) == 60
        assert out.count("ocr") == 57, "the surviving pages were not kept"
        assert out[12:15] == ["", "", ""], "the failed batch's pages are not marked"

    def test_a_page_with_no_OCR_falls_back_to_its_text_layer(self):
        """The marker is an empty string, and _page_text must READ it as 'use the text
        layer' rather than as 'this page is blank'. Returning the empty string would
        silently blank a page the reader can still partly use — worse than the defect
        being worked around. Checked in the source because it is the whole meaning of
        the marker."""
        helper = SRC[SRC.index("def _page_text"):]
        helper = helper[:helper.index("def extract(")]
        assert "if ocr:" in helper and "return ocr" in helper
        assert helper.rstrip().endswith("return _extract_page_text(page, self.council)")

    def test_too_many_failed_pages_still_abandons_the_chapter(self, tmp_path, monkeypatch):
        """Confusable negative, and the line between the two designs: keeping 138 of 141
        is plainly better than keeping none, but a chapter that is mostly text layer
        with OCR sprinkled through it is harder to reason about than a clean fallback."""
        m = _mod()
        self._env(monkeypatch, m)
        calls = {"n": 0}

        def mostly_dead(url, tok, blob, n, label):
            calls["n"] += 1
            return ["ocr"] * n if calls["n"] % 5 == 0 else None
        monkeypatch.setattr(m, "_fetch_ocr_batch", mostly_dead)
        assert m.fetch_ocr_page_texts(self._pdf(tmp_path, 60), expected_pages=60) is None

    def test_a_healthy_run_reports_no_failed_pages(self, tmp_path, monkeypatch):
        m = _mod()
        self._env(monkeypatch, m)
        monkeypatch.setattr(m, "_fetch_ocr_batch",
                            lambda url, tok, blob, n, label: ["ocr"] * n)
        out = m.fetch_ocr_page_texts(self._pdf(tmp_path, 30), expected_pages=30)
        assert out is not None and out.count("") == 0

    def test_the_share_cap_is_a_small_minority_of_pages(self):
        m = _mod()
        assert 0 < m.OCR_MAX_FAILED_PAGE_FRACTION <= 0.25
