"""DQ-78: City of Sydney locality maps put their street labels into the provision text.

110 served provisions carried them, e.g. "Zen B H i i t a n h S n d S in fi t g e r e S ld y e tr s t
ee S t t d ree E t n l A e li y s o h t P t m A a v r o enu k e r e R S oa t M r F o d i x e t B c A u
e h v r e r t e o ll w n R s u o R e a o d ad", which is Zenith Street, Bindfield Street and their
neighbours read one glyph at a time off the map graphic. The rows are NOT dropped: the prose after
the map carries the locality's controls (DQ-78's corrected remedy, 2026-08-15).

The pages are built here rather than committed as fixtures: reportlab draws the same shape the real
pages have (a dense vector drawing with tiny Arial-Bold labels inside it, prose outside), which is
what the filter keys on, and a fixture PDF could not be diffed in review.

prior-art-checked: tests/test_dcp_extraction_fidelity.py covers doubled glyphs, test_dcp_section_headings.py
covers heading detection, test_ocr_fallback.py covers the OCR route; none builds a page with a vector
drawing or exercises _extract_page_text's geometry filters (grep 'curves', 'map', 'reportlab' in tests/,
2026-09-18).
"""
import io
import os
import sys

import pdfplumber
import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_extract_changed import _extract_page_text, _strip_map_labels  # noqa: E402

MAP_BOX = (170, 500, 520, 740)   # x0, y0, x1, y1 in reportlab (origin bottom-left)


def _page(map_curves=400, label="ZENITH STREET", label_size=4.5, prose_y=470,
          tiny_outside=True, superscript_in_box=False):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    x0, y0, x1, y1 = MAP_BOX
    for i in range(map_curves):          # the map: many small vector strokes
        x = x0 + (i * 7) % (x1 - x0)
        y = y0 + (i * 11) % (y1 - y0)
        c.bezier(x, y, x + 4, y + 3, x + 8, y - 3, x + 12, y + 1)
    c.setFont("Helvetica-Bold", label_size)
    for i, word in enumerate(label.split()):   # street labels, one per position
        c.drawString(x0 + 30 + i * 40, y0 + 60 + i * 25, word)
    c.setFont("Helvetica", 10)
    c.drawString(170, prose_y, "This locality is bounded by Ashmore Street to the north.")
    c.drawString(170, prose_y - 14, "Buildings are to be no more than 9.5m in height.")
    if superscript_in_box:               # a prose line that sits inside the drawing's box
        c.setFont("Helvetica", 10)
        c.drawString(180, y0 + 20, "A site area of 450m")
        c.setFont("Helvetica", 5)
        c.drawString(263, y0 + 24, "2")
    if tiny_outside:
        c.setFont("Helvetica", 5)
        c.drawString(180, prose_y - 40, "th")
    c.showPage()
    c.save()
    buf.seek(0)
    return pdfplumber.open(buf).pages[0]


class TestMapLabelStrip:
    def test_street_labels_go_and_the_prose_stays(self):
        text = _extract_page_text(_page(), "city_of_sydney")
        assert "ZENITH" not in text and "STREET" not in text
        assert "This locality is bounded by Ashmore Street to the north." in text
        assert "9.5m" in text

    def test_other_councils_are_untouched(self):
        """Scoped to the council whose pages carry these maps; every other council reads as before."""
        assert "ZENITH" in _extract_page_text(_page(), "woollahra")

    def test_a_page_without_a_map_is_untouched(self):
        """A few rule lines or a rounded table corner is not a map."""
        text = _extract_page_text(_page(map_curves=20), "city_of_sydney")
        assert "ZENITH" in text

    def test_a_superscript_on_a_prose_line_inside_the_box_survives(self):
        """The liability case: dropping the 2 of 450m2 would serve a site area of 450m."""
        text = _extract_page_text(_page(superscript_in_box=True), "city_of_sydney")
        assert "450m" in text
        line = next(l for l in text.splitlines() if "450m" in l)
        assert "2" in line.replace("450m", "", 1)

    def test_tiny_text_outside_the_map_survives(self):
        assert "th" in _extract_page_text(_page(), "city_of_sydney")

    def test_a_label_at_body_size_inside_the_map_survives(self):
        """Only tiny glyphs are dropped: a 7pt note is left for a human to read."""
        text = _extract_page_text(_page(label="PARK", label_size=7.0), "city_of_sydney")
        assert "PARK" in text

    def test_the_filter_returns_the_page_when_there_is_no_drawing(self):
        page = _page(map_curves=0)
        assert _strip_map_labels(page) is page

    def test_a_diagram_carrying_NUMBERS_is_left_entirely_alone(self):
        """Sections 5 and 6 are building envelope drawings, not locality maps, and their
        tiny text IS the control: "8 STOREYS", "4.5", "SETBACK".

        Measured old-vs-new over the three real City of Sydney sections (2026-09-18):
        section 2 went from 79 scrambled pages to 0 losing only street names, while
        sections 5 and 6 would have lost '8' x178, '31' x2170 and '4.5' x20 beside
        STOREYS, SETBACK, LEVEL and ENVELOPE -- and would STILL have left 70 of 102 and
        57 of 65 pages scrambled. A digit among the labels is what tells the two apart,
        and on a diagram the whole page is left as it was."""
        text = _extract_page_text(_page(label="8 STOREYS"), "city_of_sydney")
        assert "8" in text and "STOREYS" in text

    def test_one_stray_digit_does_not_have_to_be_next_to_the_word_it_saves(self):
        """The guard is page-level on purpose: a drawing's number and its word are
        separate text runs, so keeping only the run with the digit would serve a bare
        '8' with no unit. Either the whole diagram is read, or none of it is."""
        text = _extract_page_text(_page(label="BOUNDARY 31 SETBACK"), "city_of_sydney")
        assert "BOUNDARY" in text and "SETBACK" in text
