"""One PDF holding several plans: extract only the pages a chapter owns.

THE GAP THIS CLOSES. The extractor reads whatever PDF a registry row points at
and extracts the WHOLE file. Four PDFs are already covered by more than one
active row with no way to say which pages belong to which (DQ-109: bayside,
burwood, fairfield, camden — 11 rows), so running them would produce one
complete copy of the document per row, live and served. cumberland is the same
gap from the other side (DQ-107): one row over a file holding five sub-plans
whose section codes collide, so no applicability config can be written for it.

TWO DESIGN DECISIONS THIS FILE PINS, because getting either wrong is expensive:

1. **The trigger is a SHARED PDF, not the mere presence of a page range.**
   `page_start`/`page_end` already carry three meanings across 229 active rows
   — measured 2026-09-24: 121 use them as a page COUNT (start at 1), 14 mean
   "content begins after the front matter" (ashfield `chapter-e1-heritage`
   p3–392 with 348 live provisions; `waverley-dcp-2022` p12–473 with 602), and
   0 mean a slice. Honouring the columns wherever they appear would change
   extraction for 2,717 live provisions in one step.

2. **Page numbers are NOT rebased.** Cutting a new PDF would renumber pages
   8–25 as 1–18, and every citation link behind those provisions points into
   the ORIGINAL document. So the range filters which pages are read while
   `page_num` keeps meaning the page in the file a reader will open.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


class FakePage:
    def __init__(self, n):
        self.n = n


class FakePdf:
    def __init__(self, n):
        self.pages = [FakePage(i) for i in range(1, n + 1)]


def _extractor(page_range=None, pages=54):
    from dcp_extract_changed import DCPExtractor

    ex = DCPExtractor(Path("nope.pdf"), "doc", council="cumberland",
                      page_range=page_range)
    return ex, FakePdf(pages)


class TestOwnedPages:
    def test_no_range_yields_the_whole_document(self):
        """The default. 135 registry rows own their PDF outright and must see
        exactly what they see today."""
        ex, pdf = _extractor(None, pages=54)
        got = [n for n, _ in ex._owned_pages(pdf)]
        assert got == list(range(1, 55))

    def test_a_range_yields_only_its_own_pages(self):
        ex, pdf = _extractor((8, 25), pages=54)
        assert [n for n, _ in ex._owned_pages(pdf)] == list(range(8, 26))

    def test_page_numbers_are_the_ORIGINAL_ones(self):
        """The decision that protects every citation link. A slice starting at
        page 8 must report 8, not 1 — the link behind the provision opens the
        original 54-page file."""
        ex, pdf = _extractor((8, 25), pages=54)
        first_num, first_page = next(iter(ex._owned_pages(pdf)))
        assert first_num == 8, "page numbers were rebased; citation links now lie"
        assert first_page.n == 8, "the wrong page object was handed over"

    def test_the_five_cumberland_sub_parts_do_not_overlap(self):
        """Its Part B is five plans in one file. Ranges measured from the live
        rows' pdf_page values."""
        seen = set()
        for lo, hi in ((8, 25), (31, 35), (39, 41), (45, 49), (53, 54)):
            ex, pdf = _extractor((lo, hi), pages=54)
            pages = {n for n, _ in ex._owned_pages(pdf)}
            assert not (pages & seen), f"{lo}-{hi} overlaps an earlier sub-part"
            seen |= pages

    def test_an_end_past_the_document_is_clamped_not_fatal(self):
        """A stale range is a number being wrong, not content being wrong.
        Refusing here would stall a chapter on arithmetic while the
        completeness guard downstream already compares what was extracted
        against what is live."""
        ex, pdf = _extractor((40, 9999), pages=54)
        assert [n for n, _ in ex._owned_pages(pdf)] == list(range(40, 55))

    def test_a_start_below_one_is_clamped(self):
        ex, pdf = _extractor((0, 3), pages=54)
        assert [n for n, _ in ex._owned_pages(pdf)] == [1, 2, 3]

    def test_a_range_entirely_past_the_end_yields_nothing_rather_than_everything(self):
        """The dangerous failure would be treating an impossible range as 'no
        range' and extracting the whole file — the duplication this exists to
        stop."""
        ex, pdf = _extractor((90, 99), pages=54)
        assert [n for n, _ in ex._owned_pages(pdf)] == []


class TestWhenToSlice:
    """`chapter_page_slice` decides. Its inputs are registry rows."""

    def _cur(self, rows, seen=None):
        """Answers the registry query, then the provisions min/max aggregate.

        `seen` is (min_pdf_page, max_pdf_page) of the chapter's live provisions,
        or None for a chapter that has none yet.
        """
        class C:
            def __init__(self):
                self.calls = 0

            def execute(self, *_a, **_k):
                self.calls += 1
                return None

            def fetchall(self):
                return rows

            def fetchone(self):
                return seen if seen is not None else (None, None)

            def close(self):
                return None
        return C()

    def _call(self, rows, key="mine", seen=None):
        from dcp_extract_changed import chapter_page_slice

        return chapter_page_slice(
            self._cur(rows, seen),
            {"chapter_key": key, "council": "somewhere",
             "r2_current_path": "r2://f.pdf"})

    def test_a_lone_row_is_never_sliced(self):
        """Owns its PDF. This is the 135-row case, including every row whose
        page_start means a page count or a front-matter offset."""
        assert self._call([("mine", 1, 42)]) == (None, None)

    def test_a_lone_row_with_a_content_offset_is_still_not_sliced(self):
        """ashfield chapter-e1-heritage, p3-392, 348 live provisions. Slicing
        it would be the 2,717-provision mistake."""
        assert self._call([("mine", 3, 392)]) == (None, None)

    def test_a_shared_pdf_with_a_range_slices(self):
        rng, refusal = self._call([("mine", 8, 25), ("other", 31, 35)])
        assert rng == (8, 25) and refusal is None

    def test_a_shared_pdf_without_a_range_REFUSES(self):
        rng, refusal = self._call([("mine", None, None), ("other", None, None)])
        assert rng is None
        assert refusal and "duplicate" in refusal

    def test_the_refusal_names_the_rows_it_collides_with(self):
        """burwood's actual shape. A refusal nobody can act on is one that gets
        switched off."""
        _, refusal = self._call(
            [("mine", None, None), ("s4-landscaping", None, None),
             ("s4-table-4-parking", None, None)], key="mine")
        assert "s4-landscaping" in refusal and "s4-table-4-parking" in refusal

    def test_a_half_declared_range_refuses_rather_than_guessing(self):
        """page_start set, page_end NULL. Inventing the end would invent a
        boundary between two councils' plans."""
        rng, refusal = self._call([("mine", 8, None), ("other", None, None)])
        assert rng is None and refusal

    def test_no_pdf_path_is_not_a_slice(self):
        from dcp_extract_changed import chapter_page_slice

        assert chapter_page_slice(
            self._cur([]),
            {"chapter_key": "k", "council": "c",
             "r2_current_path": None}) == (None, None)


class TestAPageCountIsNotASlice:
    """The sharp edge, raised by the pre-push review.

    `page_start`/`page_end` mean a page COUNT on 121 rows and a front-matter
    offset on 14. Once a row SHARES a PDF there is nothing in the columns to
    tell any of those apart from a slice — so an old page-count of 1-100 on a
    400-page shared file would be read as a slice and pages 101-400 would
    vanish silently.

    No row is in that state today (zero shared-PDF rows declare a range,
    measured 2026-09-24), but the fix for DQ-107 and DQ-109 is precisely to add
    ranges to shared-PDF rows. **The intended repair is what creates the
    hazard**, which is why the guard exists before the repair does.

    The evidence is the chapter's own live provisions: what was actually read
    out of the document, not what someone typed into a column.
    """

    _cur = TestWhenToSlice._cur
    _call = TestWhenToSlice._call

    def test_the_reviews_scenario_is_refused(self):
        """Two rows on a 400-page PDF; this one says 1-100 but its provisions
        run to page 380. Extracting on that range drops 280 pages of served
        controls."""
        rng, refusal = self._call(
            [("mine", 1, 100), ("other", None, None)], seen=(3, 380))
        assert rng is None
        assert refusal and "contradicts" in refusal
        assert "1-100" in refusal and "3-380" in refusal

    def test_a_provision_before_the_range_also_refuses(self):
        """A range starting after content that is already live means the start
        is wrong, not just the end."""
        rng, refusal = self._call(
            [("mine", 40, 60), ("other", None, None)], seen=(8, 55))
        assert rng is None and refusal

    def test_a_range_its_provisions_sit_inside_is_honoured(self):
        """The confusable negative. Cumberland's houses sub-part: pages 8-25
        declared, provisions read on pages 8-25."""
        rng, refusal = self._call(
            [("mine", 8, 25), ("other", 31, 35)], seen=(8, 25))
        assert rng == (8, 25) and refusal is None

    def test_a_chapter_with_no_provisions_yet_is_not_judged(self):
        """A new slice has nothing to contradict and nothing to lose. Judging
        it would block every first extraction, which is the whole point of the
        feature."""
        rng, refusal = self._call(
            [("mine", 8, 25), ("other", 31, 35)], seen=(None, None))
        assert rng == (8, 25) and refusal is None
