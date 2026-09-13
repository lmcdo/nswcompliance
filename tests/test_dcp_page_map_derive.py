"""Part boundaries read from each page's running header, instead of a hardcoded map.

Waverley's hardcoded map described a 473-page version of a 448-page document. The
pages themselves carry their part code at the top ("C1 / Low Density Residential"),
so the boundaries can be read, not remembered. These tests pin the rules measured on
the real PDF on 2026-09-13, each with the confusable case that would break it:

  contents lines like "B1 Waste 4"     are NOT headers
  annexures after a part               do NOT join that part
  a figure-only page inside a part     DOES belong to it
  a part code resuming later           means the header is not a part marker: refuse
  too few pages with a header          nothing to read: refuse

The fixture pages are shaped on real waverley page tops, not invented structure.
The codes here are DCP part keys, not planning zones.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_page_map_gate import (  # noqa: E402
    HEADER_MIN_PAGE_COVERAGE, derive_ranges_from_headers, page_part_codes,
)

WASTE = "B1"
LOW_DENSITY = "C1"


def part_page(code, title, body="(a) Development must comply with the controls."):
    return f"{code}\n{title}\n{body}"


def document():
    """A 24-page document shaped like waverley: cover, contents, the waste part with a
    figure-only page inside it, that part's annexures, the low-density part, then the
    definitions."""
    pages = [
        "WAVERLEY DEVELOPMENT\nCONTROL PLAN 2022",                        # 1 cover
        "TABLE OF CONTENTS\nPart B General Provisions\nB1 Waste 4",       # 2 contents
    ]
    pages += [part_page(WASTE, "Waste") for _ in range(3, 7)]             # 3-6
    pages += [""]                                                        # 7 figure only
    pages += [part_page(WASTE, "Waste") for _ in range(8, 10)]            # 8-9
    pages += ["Annexures\nAnnexure B1-1\nWaste and Recycling Generation Rates"] * 3  # 10-12
    pages += [part_page(LOW_DENSITY, "Low Density Residential") for _ in range(13, 21)]  # 13-20
    pages += ["DEFINITIONS\nNote: Terms used in this Plan are defined"] * 4         # 21-24
    return pages


def test_parts_are_read_off_the_pages():
    assert derive_ranges_from_headers(document()) == [
        (WASTE, "Waste", 3, 9),
        (LOW_DENSITY, "Low Density Residential", 13, 20),
    ]


def test_a_contents_line_is_not_a_header():
    ranges = derive_ranges_from_headers(document())
    assert all(start != 2 for _, _, start, _ in ranges), "the contents page opened a part"


def test_annexures_after_a_part_are_not_carried_into_it():
    """Carrying the last code forward would have filed waverley's Bondi Junction,
    Beachfront and village-centre annexures under the part printed before them. The
    waste part must end at its last headed page, 9, not at 12."""
    waste = next(r for r in derive_ranges_from_headers(document()) if r[0] == WASTE)
    assert waste[3] == 9


def test_a_figure_only_page_inside_a_part_belongs_to_it():
    waste = next(r for r in derive_ranges_from_headers(document()) if r[0] == WASTE)
    assert waste[2] <= 7 <= waste[3]


def test_a_part_resuming_after_another_part_is_refused():
    pages = document()
    pages[21] = part_page(WASTE, "Waste")   # the first part resumes after the second began
    assert derive_ranges_from_headers(pages) == []


def test_too_few_headers_is_refused_not_guessed():
    pages = ["plain body text with no running header"] * 20
    pages[0] = part_page(WASTE, "Waste")
    assert 1 / 20 < HEADER_MIN_PAGE_COVERAGE
    assert derive_ranges_from_headers(pages) == []
    assert derive_ranges_from_headers([]) == []


def test_the_ranges_and_the_gate_read_headers_the_same_way():
    """One definition of a header. If derive_ranges_from_headers ever recognised a page
    page_part_codes does not (or the reverse), the gate would grade the ranges against a
    different reading of the same document."""
    pages = document()
    ranges = derive_ranges_from_headers(pages)
    headed = page_part_codes(pages)
    covered = {p for _, _, a, b in ranges for p in range(a, b + 1)}
    assert set(headed) <= covered
    assert all(headed.get(a) == code and headed.get(b) == code for code, _, a, b in ranges)


def test_a_positive_and_a_refusal_together():
    """A derivation broken into always returning [] would pass every refusal test above."""
    good = derive_ranges_from_headers(document())
    bad = derive_ranges_from_headers(["no header"] * 10)
    assert good and bad == []
