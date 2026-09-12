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
    DCPExtractor, classify_toc_or_divider_page,
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
