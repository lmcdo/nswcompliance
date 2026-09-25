"""The marrickville cause: a chunk that returns nothing must not pass silently.

PROVEN 2026-09-12, not inferred. ai_extract_chapter splits a chapter into
AI_CHUNK_PAGES-page chunks. A chunk could return zero provisions and the function
collected nothing for it and moved on -- no count, no flag, no error.

  marrickville/part4-s1-low-density   55pp, chunks 1-30 and 31-55
    every stored row sits on page 31, so chunk 1 produced nothing
    all 14 sampled "missing" sections (4.1.1, 4.1.10 … 4.1.15.1) are IN the PDF,
    on pages 3-29 -- inside that empty chunk

Across three chapters, 42 of 42 checked missing sections were present in the
document inside a chunk that yielded nothing. ZERO were absent from the PDF: the
contents page was not lying, the extractor lost a chunk.

These tests exist because the guard must be shown capable of FIRING. A guard that
cannot fire is what this whole repair is about -- coverage_gap passed its own
tests for two and a half months while being structurally unable to fail.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ai_extractor import (  # noqa: E402
    CHUNK_LOSS_MIN_TEXT_CHARS, RULE_PAGE_MIN_CHARS, ChunkLoss, _is_contents_page,
    _rule_bearing_pages,
)


class _Page:
    def __init__(self, text):
        self._t = text

    def extract_text(self):
        if self._t is None:
            raise RuntimeError("pypdf cannot read this page")
        return self._t


class _Reader:
    def __init__(self, texts):
        self.pages = [_Page(t) for t in texts]


class TestChunkTextMeasurement:
    RULE = "development must comply with the controls. "

    def test_rule_bearing_pages_are_measured_per_page(self):
        r = _Reader([self.RULE * 2, "", self.RULE * 8])
        assert _rule_bearing_pages(r, 0, 3) == [(1, len(self.RULE) * 2), (3, len(self.RULE) * 8)]

    def test_a_blank_chunk_has_no_rule_bearing_page(self):
        assert _rule_bearing_pages(_Reader(["", "", ""]), 0, 3) == []

    def test_a_page_that_cannot_be_read_counts_as_rule_bearing(self):
        # Erring the other way would let an unreadable page masquerade as blank
        # and silence the guard -- the failure direction this repair exists for.
        assert _rule_bearing_pages(_Reader([None]), 0, 1) == [(1, CHUNK_LOSS_MIN_TEXT_CHARS)]

    def test_range_past_the_end_does_not_raise(self):
        assert _rule_bearing_pages(_Reader([self.RULE]), 0, 99) == [(1, len(self.RULE))]

    def test_contents_and_history_pages_hold_no_rule(self):
        # Leichhardt part-c-s2 pages 1-12, refused twice on 2026-09-24.
        contents = "\n".join(f"c2.1.{i} objectives and controls ............. {100 + i}"
                              for i in range(12))
        history = ("The first phase of settlement followed the subdivision of the "
                   "estate into small lots for workers' cottages near the wharves. ") * 20
        assert _rule_bearing_pages(_Reader([contents] * 5 + [history] * 7), 0, 12) == []

    def test_an_unworded_control_still_counts_by_its_label(self):
        # Cross-review: "Retain existing trees" carries none of the rule words.
        page = "C1 Existing trees along the northern boundary are kept.\nC2 Bicycle racks near the entry."
        assert _rule_bearing_pages(_Reader([page]), 0, 1) != []

    def test_a_table_of_numeric_standards_is_not_a_contents_page(self):
        # Cross-review: every line ends in a digit, but no dot leaders.
        table = "\n".join(f"Maximum building height zone {i}   8.{i}" for i in range(10))
        assert _is_contents_page(table) is False
        contents = "\n".join(f"4.{i} Heading ..................... {10 + i}" for i in range(10))
        assert _is_contents_page(contents) is True


class TestGuardFires:
    """The guard must raise on the real shape, and stay quiet on the benign one."""

    def _run(self, monkeypatch, page_texts, chunk_pages, responses, page_lines=None):
        """Drive ai_extract_chapter with a fake reader and fake model calls.
        `page_lines` is what the page-coverage check sees ({} = nothing to check)."""
        import ai_extractor as ai
        import page_coverage as pc
        monkeypatch.setattr(pc, "pdf_page_lines", lambda _p: page_lines or {})

        monkeypatch.setattr(ai, "chunk_ranges",
                            lambda total, chunk=chunk_pages: [
                                (s, min(s + chunk_pages, total))
                                for s in range(0, total, chunk_pages)])
        monkeypatch.setattr(ai, "_subset_bytes", lambda reader, a, b: b"pdf")
        calls = {"n": 0}

        def fake_call(model, pdf_bytes, prompt):
            i = calls["n"]
            calls["n"] += 1
            return responses[i] if i < len(responses) else []

        monkeypatch.setattr(ai, "_call_and_parse_with_empty_retry", fake_call)

        class FakePdfReader:
            def __init__(self, _path):
                self.pages = _Reader(page_texts).pages

        import types
        fake_pypdf = types.ModuleType("pypdf")
        fake_pypdf.PdfReader = FakePdfReader
        monkeypatch.setitem(sys.modules, "pypdf", fake_pypdf)
        return ai.ai_extract_chapter("ignored.pdf", model="mistral")

    def test_the_marrickville_shape_raises(self, monkeypatch):
        # 55 pages, 30-page chunks. Chunk 1 (pages 1-30) is dense with text and
        # returns NOTHING; chunk 2 returns provisions. Before the guard this
        # committed a chapter missing 30 pages and said nothing.
        pages = ["control text " * 400] * 55
        with pytest.raises(ChunkLoss) as exc:
            self._run(monkeypatch, pages, 30,
                      [[], [{"code": "4.1.12", "title": "Roof", "text": "x"}]])
        msg = str(exc.value)
        assert "1 of 2 chunks" in msg
        assert "1-30" in msg

    def test_a_genuinely_blank_chunk_does_NOT_raise(self, monkeypatch):
        # The confusable negative. A cover/plate/scanned-image chunk legitimately
        # yields nothing, and failing on it would block chapters that are fine.
        pages = ["control text " * 400] * 30 + [""] * 25
        out = self._run(monkeypatch, pages, 30,
                        [[{"code": "4.1", "title": "T", "text": "x"}], []])
        assert len(out) == 1

    def test_a_chapter_where_every_chunk_yields_does_not_raise(self, monkeypatch):
        pages = ["control text " * 400] * 55
        out = self._run(monkeypatch, pages, 30,
                        [[{"code": "4.1", "title": "A", "text": "x"}],
                         [{"code": "4.2", "title": "B", "text": "y"}]])
        assert len(out) == 2

    def test_a_single_chunk_chapter_that_yields_nothing_raises(self, monkeypatch):
        # marrickville/part2-s01-urban-design is 18pp with 2 rows and 1.3% of its
        # text captured -- the same defect inside one chunk.
        pages = ["control text " * 400] * 18
        with pytest.raises(ChunkLoss):
            self._run(monkeypatch, pages, 30, [[]])

    def test_the_error_names_the_pages_that_were_lost(self, monkeypatch):
        # An operator has to know WHICH pages to go and look at; "extraction
        # failed" is not actionable.
        pages = ["control text " * 400] * 90
        with pytest.raises(ChunkLoss) as exc:
            self._run(monkeypatch, pages, 30,
                      [[{"code": "1.1", "title": "A", "text": "x"}], [], []])
        msg = str(exc.value)
        assert "31-60" in msg and "61-90" in msg
        assert "2 of 3 chunks" in msg


class TestAttributionGuard:
    """The OTHER marrickville defect: the text arrives, the addressing does not."""

    def _g(self, extracted, toc):
        from ai_extractor import attribution_collapsed
        return attribution_collapsed(set(extracted), set(toc))

    def test_the_stormwater_shape_is_flagged(self):
        # 40 provisions all filed under "2.25", against 19 listed sections.
        toc = {"2.25." + str(i) for i in range(1, 20)}
        extracted = {"2.25 C" + str(i) for i in range(1, 41)}
        collapsed, sections, listed = self._g(extracted, toc)
        assert collapsed is True
        assert sections == 1 and listed == 19

    def test_a_properly_attributed_chapter_is_not_flagged(self):
        toc = {"2.25." + str(i) for i in range(1, 20)}
        extracted = {"2.25." + str(i) + " C1" for i in range(1, 18)}
        collapsed, sections, _ = self._g(extracted, toc)
        assert collapsed is False and sections == 17

    def test_coverage_gap_stays_SILENT_on_the_same_input(self):
        # The reason this guard has to exist. A parent code covers its children
        # by the dotted-prefix rule, so coverage_gap sees nothing wrong with a
        # chapter filed entirely under 2.25.
        from ai_extractor import coverage_gap
        toc = {"2.25." + str(i) for i in range(1, 20)}
        extracted = {"2.25 C" + str(i) for i in range(1, 41)}
        ratio, _missing = coverage_gap(extracted, toc)
        assert ratio is not None
        collapsed, _, _ = self._g(extracted, toc)
        assert collapsed is True, "the guard must catch what coverage_gap cannot"

    def test_a_toc_too_small_to_judge_does_not_flag(self):
        # Not a pass being handed out: an unreadable contents page is already
        # reported by coverage_unknown, and double-reporting it would make this
        # guard fire on every small chapter.
        collapsed, _, _ = self._g({"1.1 C1"}, {"1.1", "1.2"})
        assert collapsed is False

    def test_the_verdict_is_not_constant(self):
        toc = {"3." + str(i) for i in range(1, 21)}
        assert self._g({"3 C1"}, toc)[0] is True
        assert self._g({"3." + str(i) for i in range(1, 21)}, toc)[0] is False


def test_a_chunk_of_contents_and_history_does_not_raise(monkeypatch):
    """Leichhardt part-c-s2: the model rightly returned nothing for contents
    pages and suburb histories; the guard refused the whole chapter twice."""
    contents = "\n".join(f"c2.1.{i} objectives and controls ............. {100 + i}"
                         for i in range(12))
    history = ("The first phase of settlement followed the subdivision of the estate "
               "into small lots for workers' cottages near the wharves. ") * 20
    rules = "development must comply with the controls. " * 60
    pages = [contents] * 5 + [history] * 7 + [rules] * 12
    out = TestGuardFires()._run(monkeypatch, pages, 12,
                                [[], [{"code": "C2.2.1", "title": "T", "text": "x"}]])
    assert len(out) == 1


def test_one_short_page_of_controls_among_history_still_raises(monkeypatch):
    """Cross-review: measured as a batch total against 1,500 characters, one
    page of controls inside eleven pages of history could fall under the bar."""
    history = ("The first phase of settlement followed the subdivision of the estate "
               "into small lots for workers' cottages near the wharves. ") * 20
    controls = "C1 Buildings must be set back 6m from the street. " * 8   # ~400 chars
    pages = [history] * 11 + [controls]
    with pytest.raises(ChunkLoss):
        TestGuardFires()._run(monkeypatch, pages, 12, [[]])


# -- pages left out inside a batch that returned something ------------------------

_VOCAB = ("awning basement canopy driveway eave fence garage hedge kerb lane "
          "masonry parapet porch roof sill terrace verandah window").split()


def _sent(i):
    """A sentence whose every four-word run is its own: no two share one."""
    w = [_VOCAB[(i * 7 + k * 3) % len(_VOCAB)] + str(i) for k in range(7)]
    return " ".join(w)


def test_a_page_left_out_is_read_again_and_its_rules_kept(monkeypatch):
    """Warringah: every batch returned rules, and 21 pages inside them were
    skipped. The skipped page is now counted by code and read again."""
    lines = {1: [_sent(i) for i in range(6)], 2: [_sent(i) for i in range(10, 16)]}
    first = [{"code": "1.1", "title": "A", "text": " ".join(lines[1])}]
    again = [{"code": "1.2", "title": "B", "text": " ".join(lines[2])}]
    out = TestGuardFires()._run(monkeypatch, ["x"] * 2, 12, [first, again], page_lines=lines)
    assert len(out) == 2


def test_a_rule_page_still_left_out_after_the_reread_refuses_the_chapter(monkeypatch):
    from ai_extractor import PageLoss
    lines = {1: [_sent(i) for i in range(6)],
             2: [_sent(200 + i) + " must" for i in range(6)]}
    first = [{"code": "1.1", "title": "A", "text": " ".join(lines[1])}]
    with pytest.raises(PageLoss) as exc:
        TestGuardFires()._run(monkeypatch, ["x"] * 2, 12, [first, []], page_lines=lines)
    assert "[2]" in str(exc.value)


def test_a_page_without_rule_words_still_left_out_is_allowed(monkeypatch):
    # Warringah pages 2, 13, 14, 139: amendment table, definitions, history.
    lines = {1: [_sent(i) for i in range(6)]}
    lines.update({p: [_sent(p * 100 + i) for i in range(6)] for p in range(2, 7)})
    first = [{"code": "1.1", "title": "A", "text": " ".join(lines[1])}]
    out = TestGuardFires()._run(monkeypatch, ["x"] * 6, 12, [first, []], page_lines=lines)
    assert len(out) == 1
