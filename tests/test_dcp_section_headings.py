"""Two extraction defects found by READING a council PDF, not by inference.

canterbury_bankstown chapter-4-3 carries 22 real "SECTION N-TITLE" headings and
extracted SEVEN sections. Reading the rendered pages and comparing them against
pdfplumber's output found three things, in this order:

  1. The chapter is NOT two-column. `preflight_two_column` reports 37 of 39 pages
     two-column; the pages are plainly single-column and pdfplumber extracts them
     perfectly. detect_two_column_words asks whether an individual WORD spans the
     middle 16% of the page -- single words almost never do, while single-column
     LINES always do -- so ordinary prose reads as two columns. NOT fixed here: a
     line-based replacement gives a false NEGATIVE on genuinely two-column hornsby
     pages, and a false negative is worse. Recorded, not shipped.

  2. SECTION_RE missed "SECTION 1-INTRODUCTION" entirely and matched
     "O1 To ensure that..." -- an objective marker -- as a section.

  3. classify_toc_or_divider_page called every content page a contents page,
     because they carry 9-11 numbered CONTROLS and the test was a raw count.

Together these are the difference between 7 sections and 36.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_extract_changed import (  # noqa: E402
    DCPExtractor, classify_toc_or_divider_page, split_page_at_headings,
)

SECTION_RE = DCPExtractor.SECTION_RE


def groups(text):
    m = SECTION_RE.match(text)
    return DCPExtractor._match_groups(SECTION_RE, m) if m else None


class TestSectionHeadings:
    def test_the_prefix_word_format_now_matches(self):
        assert groups("SECTION 1-INTRODUCTION") == ("1", "INTRODUCTION")
        assert groups("SECTION 2-CONTRIBUTORY BUILDINGS (RANKINGS 1 AND 2)") == (
            "2", "CONTRIBUTORY BUILDINGS (RANKINGS 1 AND 2)")
        assert groups("SECTION 17-SUBDIVISION AND LOT CONSOLIDATION") == (
            "17", "SUBDIVISION AND LOT CONSOLIDATION")

    def test_an_en_dash_and_a_colon_both_work(self):
        assert groups("SECTION 3\u2013FORM, MASSING AND SCALE")[0] == "3"
        assert groups("SECTION 4: INFILL DEVELOPMENT")[0] == "4"

    def test_the_ORIGINAL_formats_are_unchanged(self):
        # Additive on purpose: every council matching before must still match,
        # identically. A "fix" that re-sections the whole corpus is not a fix.
        assert groups("4.3 Heritage Conservation Areas") == (
            "4.3", "Heritage Conservation Areas")
        assert groups("B1 WASTE") == ("B1", "WASTE")
        assert groups("2 Good Design") == ("2", "Good Design")

    def test_prose_is_still_not_a_heading(self):
        assert groups("The removal of a tree deemed by Council in writing") is None
        assert groups("section 4 of the Act applies") is None

    def test_a_prefix_heading_is_preferred_over_a_bare_number(self):
        # Extraction takes ONE heading per page. On a real CB page the sub-item
        # "4.6 Solid to void ratios..." sits ABOVE the real "SECTION 5-ROOFS..."
        # heading, so without this the page is filed under 4.6 and the section is
        # lost entirely.
        page = ("4.6 Solid to void ratios of elevations\n"
                "some body text here about windows and doors\n"
                "SECTION 5-ROOFS, DORMERS, CHIMNEYS AND SKYLIGHTS\n")
        m = DCPExtractor._find_heading(SECTION_RE, page)
        assert DCPExtractor._match_groups(SECTION_RE, m)[0] == "5"


class TestZoneCodesAndYearsAreNotHeadings:
    """2026-09-17: a line opening with a bare year or a residential zone code matched SECTION_RE, so
    a table row or figure label started a section and real rules were filed under a junk key --
    11 live provisions across 6 councils. The review gate auto-rejected those keys, which blocked
    city_of_sydney section 3 and georges_river part 3 from committing. Lines are verbatim from
    production text."""

    def code(self, page):
        m = DCPExtractor._find_heading(SECTION_RE, page)
        return DCPExtractor._match_groups(SECTION_RE, m)[0] if m else None

    def test_a_zone_list_line_does_not_start_a_section(self):
        page = ("R1 General Residential or R2 Low Density Residential.\n"  # noqa: zone-codes  (verbatim PDF text)
                "(3) Signage is only permitted to be illuminated while a premises is open\n"
                "3.16.2 Illumination of signs\n")
        assert self.code(page) == "3.16.2"

    def test_a_table_row_alone_is_not_a_heading(self):
        assert self.code("R2 Low Density Residential ≤ Two (2) lots – 3m\n") is None
        assert self.code("R3 Medium Height limit:\n") is None

    def test_a_year_is_not_a_section_number(self):
        assert self.code("2012 Western Distributor\nErskine Street\n") is None
        assert self.code("2025 Riverwood Estate. Amendment 9\n") is None

    def test_real_letter_and_number_codes_still_match(self):
        for line, want in (("B3 General Development Controls", "B3"), ("E1 Caddens", "E1"),  # noqa: zone-codes  (DCP chapter keys)
                           ("C2 Woollahra Heritage Conservation Area", "C2"), ("3.2 Building setbacks", "3.2"),
                           ("2 Good Design", "2"), ("R10 Road reserves", "R10")):
            assert self.code(line + "\n") == want, line

    def test_a_table_cell_number_above_a_zone_row_is_not_a_heading(self):
        """georges_river part 3 p43, verbatim: with the R2 row skipped, SECTION_RE's whitespace spanned
        the line break and read "6" / "R3 Medium Density Residential..." as section 6. The page's
        real heading is 3.16.2."""
        page = ("Zone Number of lots per Width of access handle\n"
                "R2 Low Density Residential ≤ Two (2) lots – 3m\n"
                "6\n"
                "R3 Medium Density Residential > Two (2) lots – 6m\n"
                "IN2 Light Industrial 2 6m\n"
                "Table 5: Battle-axe lots – access requirements\n"
                "3.16.2 Roads, Vehicular Access and Car Parking\n")
        assert self.code(page) == "3.16.2"

    def test_zone_named_headings_on_one_line_still_match(self):
        """Confusable negatives: a real heading that names a zone sits on one line, and a number on
        its own line above an ordinary title is not a zone table row."""
        assert self.code("4.2 R2 Low Density Residential\n") == "4.2"
        assert self.code("6 R3 Medium Density Residential zone controls\n") == "6"
        assert self.code("6\nSubdivision controls\n") == "6"

    def test_the_multi_heading_splitter_skips_them_too(self):
        page = ("tail of the previous section\n3.1 Access handles\nZone Width\n"
                "R2 Low Density Residential ≤ Two (2) lots – 3m\n3.2 Driveways\nbody\n")
        parts = split_page_at_headings(page, SECTION_RE)
        assert len(parts) == 3
        assert parts[1].startswith("3.1 Access handles") and "R2 Low Density Residential" in parts[1]
        assert parts[2].startswith("3.2 Driveways")


class TestContentsPageVsControlsPage:
    CONTENTS = ("CONTENTS\n"
                "Section 1 - Introduction ...........................\n"
                "Section 2 - Contributory buildings .................\n"
                "Section 3 - Form, massing and scale ................\n"
                "Section 4 - Infill development .....................\n"
                "Section 5 - Roofs and dormers ......................\n")
    CONTROLS = ("SECTION 4-INFILL DEVELOPMENT\n"
                "4.1 New development must respond to the prevailing scale.\n"
                "4.2 Building height must not exceed the streetscape norm.\n"
                "4.3 Setbacks must align with the established building line.\n"
                "4.4 Roof pitch must be consistent with contributory buildings.\n"
                "4.5 Materials must be selected to complement the area.\n"
                "4.6 Solid to void ratios must reflect the period character.\n")

    def test_a_real_contents_page_is_still_suppressed(self):
        suppress, discard = classify_toc_or_divider_page(self.CONTENTS, SECTION_RE)
        assert suppress is True and discard is False

    def test_a_page_of_numbered_CONTROLS_is_NOT_suppressed(self):
        # THE FIX. These pages carry 9-11 heading-shaped lines in the real
        # document, tripped the old `toc_hits >= 5` test, and were suppressed --
        # so canterbury_bankstown chapter-4-3 produced 7 sections from a document
        # with 22. Reading the PDF is what found it.
        suppress, discard = classify_toc_or_divider_page(self.CONTROLS, SECTION_RE)
        assert suppress is False, "a page of controls was called a contents page"
        assert discard is False

    def test_a_section_DIVIDER_page_still_suppresses_AND_discards(self):
        # Unchanged behaviour, and the ordering that protects it: a divider also
        # reads as a contents page, so it is tested FIRST. Folding it into the
        # contents branch would drop discard=True and re-corrupt the two sections
        # the 2026-09-05 fix was written for.
        divider = ("SECTION 5\n"
                   "5.1 Roofs\n"
                   "5.2 Dormers\n"
                   "5.3 Chimneys\n")
        suppress, discard = classify_toc_or_divider_page(divider, SECTION_RE)
        assert suppress is True and discard is True

    def test_the_classifier_is_not_constant(self):
        assert classify_toc_or_divider_page(self.CONTENTS, SECTION_RE)[0] is True
        assert classify_toc_or_divider_page(self.CONTROLS, SECTION_RE)[0] is False
