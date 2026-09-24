"""DQ-109 — several live registry rows over one PDF, none declaring its pages.

The extractor takes whatever PDF a registry row points at and extracts the
WHOLE file: its query selects `r2_current_path` and never `page_start` or
`page_end`. So several active rows on one PDF with no ranges between them
produce one complete copy of the document per row, live and served.

Measured 2026-09-24: 4 PDFs, 11 rows, across bayside, burwood, fairfield and
camden — none extracted, which is the only reason no duplicate exists today.
The chapter names say what was intended: burwood registers
`part-4-residential`, `s4-landscaping` and `s4-table-4-parking` all at
`part-4-residential.pdf`. That is the onboarding default in
`docs/DCP_SCOPE_CONFIG_REFERENCE.md` — roughly six topic chapters, not the
whole DCP — written by someone who expected slicing to exist.

MUTATION NOTE. The distinction this check has to get right is that **a shared
PDF is not itself a defect**:

  * two rows, neither ranged  -> counted. Both extract the whole file.
  * two rows, one ranged      -> NOT counted. The unranged row owns the file
                                 and the ranged one carves a piece out of it,
                                 which is coherent and is the intended shape
                                 once slicing exists.
  * one row on its own PDF    -> NOT counted, ranged or not. 135 rows are in
                                 this state and their `page_start` means
                                 something else entirely (a page count, or
                                 where content begins after front matter).

A detector that counted every shared PDF would report the fix as a defect. One
that counted every row with no range would accuse all 121 rows whose PDF is
their own.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dq_probe_unchecked_rows import probe_109  # noqa: E402


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, *_a, **_k):
        return None

    def fetchall(self):
        return self._rows


def _group(council, rows, unranged, done=0, keys="a, b"):
    """One (council, pdf) group as the probe's GROUP BY yields it."""
    return (council, "r2://some/file.pdf", rows, unranged, done, keys)


class TestTheDuplicatingShapeIsCaught:
    def test_two_unranged_rows_on_one_pdf(self):
        count, detail = probe_109(FakeCursor([_group("camden", 2, 2)]))
        assert count == 1
        assert "WHOLE file" in next(iter(detail))[1]

    def test_it_names_the_chapter_keys_so_the_finding_is_actionable(self):
        _, detail = probe_109(FakeCursor([
            _group("burwood", 3, 3, keys="part-4-residential, s4-landscaping")]))
        note = next(iter(detail))[1]
        assert "part-4-residential" in note and "s4-landscaping" in note

    def test_it_reports_how_many_have_already_run(self):
        """An extracted row beside unranged siblings is worse than none: the
        duplicate would land on top of provisions already being served."""
        _, detail = probe_109(FakeCursor([_group("somewhere", 3, 3, done=1)]))
        assert "1 already extracted" in next(iter(detail))[1]


class TestASharedPdfIsNotItselfADefect:
    def test_one_ranged_row_beside_one_unranged_is_coherent(self):
        """The unranged row owns the file; the ranged one carves a piece out.
        This is the shape the fix produces, so counting it would report the
        remedy as the disease."""
        assert probe_109(FakeCursor([_group("x", 2, 1)]))[0] == 0

    def test_two_rows_that_both_declare_ranges_are_clean(self):
        assert probe_109(FakeCursor([_group("x", 2, 0)]))[0] == 0

    def test_five_rows_with_one_unranged_is_clean(self):
        """Cumberland after the intended fix: five sub-parts with ranges, and
        at most one row owning the whole file."""
        assert probe_109(FakeCursor([_group("cumberland", 5, 1)]))[0] == 0


class TestItCannotAccuseARowThatOwnsItsPdf:
    def test_a_lone_row_is_never_reported(self):
        """The probe's own SQL has `HAVING count(*) > 1`, so a single-row group
        never reaches the Python. Asserted anyway: 135 rows are in this state
        and their page_start means a page count or a content-start offset, not
        a slice. Reporting them would be the 2,717-provision mistake."""
        assert probe_109(FakeCursor([_group("ku_ring_gai", 1, 1)]))[0] == 0

    def test_nothing_at_all_is_clean(self):
        assert probe_109(FakeCursor([])) == (0, {})


class TestItCanRise:
    def test_each_shared_pdf_counts_once(self):
        count, _ = probe_109(FakeCursor([
            _group("bayside", 3, 3), _group("burwood", 3, 3),
            _group("fairfield", 3, 3), _group("camden", 2, 2)]))
        assert count == 4, "a new council registered this way must raise the count"
