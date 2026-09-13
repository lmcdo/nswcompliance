"""Every rule must cite the page it is on, and carry no page furniture in its text.

Found 2026-09-13 reviewing waverley's 666 queued changes before approval:
  * every rule cited the FIRST page of its part -- all 56 C1 rules said page 167;
  * 234 of 518 rules had the page footer ("WAVERLEY DEVELOPMENT CONTROL PLAN 2022" and
    a page number) inside their text, and 127 had the next page's running header, e.g.
    "...Cultivars or hybrids of listed plant WAVERLEY DEVELOPMENT CONTROL PLAN 2022 35
    B3 Landscaping, Biodiversity and Vegetation Preservation species are not to be...".

A citation that opens the right PDF at the wrong page, and a rule with a stray page
number in it, are both wrong answers served as regulation. The text fragments below
are copied from that extraction.
"""
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
    os.environ.setdefault(_k, "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
_STUBS = ("boto3", "botocore", "pdfplumber", "psycopg2", "dotenv", "enrichment", "enrichment.pipeline")
_saved = {k: sys.modules.get(k) for k in _STUBS}
for _k in _STUBS:
    sys.modules[_k] = MagicMock()
try:
    from dcp_extract_changed import (  # noqa: E402
        COUNCIL_SUBSECTION_PATTERNS, PAGE_MARK, assign_pages_from_markers,
        split_content_at_subsections, strip_page_furniture,
    )
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v

FOOTER = "WAVERLEY DEVELOPMENT CONTROL PLAN 2022"
LANDSCAPE = "B3"


# ---------------------------------------------------------------------------
# 1. Page furniture
# ---------------------------------------------------------------------------

def test_the_running_header_and_the_footer_are_removed():
    page = (f"{LANDSCAPE}\nLandscaping, Biodiversity and Vegetation Preservation\n"
            "3.1.2 Vegetation Clearing Requiring a Permit\n"
            "A Vegetation Clearing Permit is required to clear:\n"
            f"{FOOTER}\n35")
    out = strip_page_furniture(page, "waverley")
    assert out.split("\n") == ["3.1.2 Vegetation Clearing Requiring a Permit",
                               "A Vegetation Clearing Permit is required to clear:"]


def test_a_footer_on_one_line_is_removed_too():
    out = strip_page_furniture(f"(a) Controls apply.\n{FOOTER} 162", "waverley")
    assert out == "(a) Controls apply."


def test_a_body_heading_that_repeats_the_part_name_is_kept():
    """The page where a part begins prints the header AND a body heading. Only the
    header is furniture."""
    page = f"C1\nLow Density Residential\nC1 LOW DENSITY RESIDENTIAL DEVELOPMENT\nThis Part applies to..."
    out = strip_page_furniture(page, "waverley")
    assert out.startswith("C1 LOW DENSITY RESIDENTIAL DEVELOPMENT")


def test_a_number_that_is_not_after_the_footer_title_is_kept():
    """Confusable: a table cell or a control value on its own line at the bottom of a
    page is not a page number unless the footer title sits directly above it."""
    page = "Minimum site area (m2)\n450"
    assert strip_page_furniture(page, "waverley") == page


def test_the_document_title_on_a_cover_page_is_kept():
    page = f"{FOOTER}\nWaverley Council\nMail: PO Box 9"
    assert strip_page_furniture(page, "waverley") == page


def test_other_councils_are_untouched():
    page = f"{LANDSCAPE}\nLandscaping\n(a) text\n{FOOTER}\n35"
    assert strip_page_furniture(page, "ashfield") == page


# ---------------------------------------------------------------------------
# 2. The page each rule is on
# ---------------------------------------------------------------------------

def _range_content(pages):
    """What extract_by_page_ranges builds: each page's text preceded by its marker."""
    return "".join(f"\n\n{PAGE_MARK.format(n=n)}\n{text}" for n, text in pages)


def test_each_rule_cites_the_page_its_heading_is_on():
    content = _range_content([
        (167, "C1 LOW DENSITY RESIDENTIAL DEVELOPMENT\nThis Part applies to low density housing."),
        (168, "1.1 SITE AND BUILDING DESIGN\nObjectives\n(a) To ensure good design."),
        (169, "1.2 SETBACKS\nControls\n(a) The front setback must match the street."),
    ])
    pattern = COUNCIL_SUBSECTION_PATTERNS["waverley"][0]
    split = split_content_at_subsections(content, "C1", "Low Density Residential", 167, 169, [], pattern)
    out = assign_pages_from_markers(split, 167)
    pages = {s["section_number"]: (s["page_start"], s["page_end"]) for s in out}
    assert pages["C1"] == (167, 167)
    assert pages["C1_1_1"] == (168, 168)
    assert pages["C1_1_2"] == (169, 169)


def test_a_rule_running_onto_the_next_page_keeps_its_start_and_records_its_end():
    content = _range_content([
        (60, "7.2 VEHICLE ACCESS\n(a) To prioritise pedestrians."),
        (61, "(b) To design vehicle access safely."),
    ])
    pattern = COUNCIL_SUBSECTION_PATTERNS["waverley"][0]
    split = split_content_at_subsections(content, "B7", "Transport", 60, 61, [], pattern)
    out = assign_pages_from_markers(split, 60)
    rule = next(s for s in out if s["section_number"] == "B7_7_2")
    assert (rule["page_start"], rule["page_end"]) == (60, 61)
    assert rule["pages"] == [60, 61]


def test_no_page_marker_survives_into_the_rule_text():
    content = _range_content([(35, "3.1 CLEARING\n(a) one"), (36, "(b) two")])
    pattern = COUNCIL_SUBSECTION_PATTERNS["waverley"][0]
    split = split_content_at_subsections(content, "B3", "Landscaping", 35, 36, [], pattern)
    out = assign_pages_from_markers(split, 35)
    assert all("⟦" not in s["content"] for s in out)
    assert "(a) one" in out[-1]["content"] and "(b) two" in out[-1]["content"]


def test_page_markers_alone_do_not_make_an_intro_rule_out_of_the_tables():
    """Every range's content now opens with a page marker, so the text before the first
    heading is never empty. A range with no real intro text must still yield no intro
    rule -- before the markers its tables went nowhere, and a table-only rule would be
    new output for every council on the page-range path. The first rule must still cite
    the page its heading is on, so the markers cannot simply be thrown away."""
    dx = sys.modules["dcp_extract_changed"]
    content = _range_content([(40, ""), (41, ""), (42, "1.1 SITE AND BUILDING DESIGN\n(a) To ensure good design.")])
    tables = [{"html": "<table><tr><td>x</td></tr></table>", "page": 40}]
    pattern = COUNCIL_SUBSECTION_PATTERNS["waverley"][0]
    split = split_content_at_subsections(content, "C1", "Low Density Residential", 40, 42, tables, pattern)
    out = dx.DCPExtractor.finalise_ranged_sections(assign_pages_from_markers(split, 40))
    assert [s["section_number"] for s in out] == ["C1_1_1"], "a marker-only intro became a rule"
    assert out[0]["page_start"] == 42


def test_extraction_itself_strips_furniture_and_cites_each_rules_page(monkeypatch):
    """The tests above prove the two functions. This proves extract_by_page_ranges calls
    them: with either call removed from the extractor, every test above stayed green."""
    dx = sys.modules["dcp_extract_changed"]
    page_texts = {
        167: (f"C1\nLow Density Residential\nC1 LOW DENSITY RESIDENTIAL DEVELOPMENT\n"
              f"This Part applies to low density housing.\n{FOOTER}\n159"),
        168: (f"C1\nLow Density Residential\n1.1 SITE AND BUILDING DESIGN\n"
              f"(a) To ensure good design.\n{FOOTER}\n160"),
    }

    class _Pdf:
        pages = [MagicMock() for _ in range(170)]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(dx.pdfplumber, "open", lambda *a, **k: _Pdf())
    extractor = dx.DCPExtractor(dx.Path("waverley.pdf"), "doc", council="waverley")
    monkeypatch.setattr(extractor, "_maybe_route_via_ocr", lambda: None)
    monkeypatch.setattr(extractor, "_page_text", lambda page, n: page_texts.get(n, ""))

    sections = extractor.extract_by_page_ranges(
        [("C1", "Low Density Residential", 167, 168)], COUNCIL_SUBSECTION_PATTERNS["waverley"])

    text = " ".join(s["content"] for s in sections)
    assert FOOTER not in text, "the page footer reached the rule text"
    assert "⟦" not in text, "a page marker reached the rule text"
    pages = {s["section_number"]: s["page_start"] for s in sections}
    assert pages.get("C1_1_1") == 168, f"rule cited page {pages.get('C1_1_1')}, not the page it is on"


def test_a_section_with_no_marker_keeps_the_page_it_was_given():
    out = assign_pages_from_markers([{"section_number": "X", "content": "text",
                                      "page_start": 12, "page_end": 12, "pages": []}], 12)
    assert (out[0]["page_start"], out[0]["page_end"]) == (12, 12)
