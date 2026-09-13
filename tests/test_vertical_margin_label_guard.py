"""Tests for find_vertical_margin_label_band() in dcp_extract_changed.py -- the
guard that detects a running section-title banner some DCP PDF generators print
sideways down a page's margin as individually-positioned UPRIGHT glyphs (one
letter per short line), rather than one rotated text run. pdfplumber's own
rotation flag (upright=False, see _upright_only) does not catch this -- every
glyph reports upright=True; only the stacked geometry gives it away.

Pure decision-logic tests (no PDF I/O), per this module's own convention (see
sibling tests/test_section_divider_guard.py). Every positive and false-positive
fixture below is VERBATIM word geometry captured from
marrickville/part7-s3-sex-industry's real, already-downloaded source PDF
(2026-09-05 investigation) -- not invented coordinates. Left uncaught, this
defect interleaved single letters into real body text, breaking heading
detection for the very next section and silently swallowing 7 real sections
(7.3.8-7.3.14) into whichever section was still open.
"""
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
           "R2_BUCKET_NAME", "R2_ENDPOINT_URL", "R2_PUBLIC_URL"):
    os.environ.setdefault(_k, "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
_STUBS = ("boto3", "botocore", "pdfplumber", "psycopg2", "dotenv", "enrichment", "enrichment.pipeline")
_saved = {k: sys.modules.get(k) for k in _STUBS}
for _k in _STUBS:
    sys.modules[_k] = MagicMock()
sys.modules["dotenv"].load_dotenv = MagicMock()
try:
    from dcp_extract_changed import (  # noqa: E402
        _strip_vertical_margin_label, find_vertical_margin_label_band,
    )
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v


def _w(text, x0, x1, top, bottom):
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": bottom}


# Verbatim capture: marrickville/part7-s3-sex-industry.pdf, page 25, all 38
# words in the x0=557.91/x1=571.95 band -- the running margin title
# "7.3 Sex Industry and Adult Business Premises", one letter per line.
REAL_MARGIN_LABEL_WORDS = [
    _w("7", 557.91, 571.95, 524.59, 530.99), _w(".", 557.91, 571.95, 530.95, 534.15),
    _w("3", 557.91, 571.95, 534.15, 540.55), _w("S", 557.91, 571.95, 547.03, 554.71),
    _w("e", 557.91, 571.95, 554.71, 561.11), _w("x", 557.91, 571.95, 561.07, 567.47),
    _w("I", 557.91, 571.95, 570.63, 573.83), _w("n", 557.91, 571.95, 573.79, 580.82),
    _w("d", 557.91, 571.95, 580.85, 587.89), _w("u", 557.91, 571.95, 587.82, 594.85),
    _w("s", 557.91, 571.95, 594.88, 601.28), _w("t", 557.91, 571.95, 601.24, 605.07),
    _w("r", 557.91, 571.95, 605.07, 609.55), _w("y", 557.91, 571.95, 609.55, 615.95),
    _w("a", 557.91, 571.95, 619.08, 625.49), _w("n", 557.91, 571.95, 625.49, 632.52),
    _w("d", 557.91, 571.95, 632.44, 639.47), _w("A", 557.91, 571.95, 642.61, 650.93),
    _w("d", 557.91, 571.95, 650.93, 657.96), _w("u", 557.91, 571.95, 657.96, 664.99),
    _w("l", 557.91, 571.95, 665.04, 668.24), _w("t", 557.91, 571.95, 668.15, 671.99),
    _w("B", 557.91, 571.95, 675.22, 683.53), _w("u", 557.91, 571.95, 683.53, 690.56),
    _w("s", 557.91, 571.95, 690.56, 696.96), _w("i", 557.91, 571.95, 696.81, 700.01),
    _w("n", 557.91, 571.95, 700.01, 707.04), _w("e", 557.91, 571.95, 707.11, 713.52),
    _w("s", 557.91, 571.95, 713.47, 719.88), _w("s", 557.91, 571.95, 719.83, 726.24),
    _w("P", 557.91, 571.95, 729.58, 737.26), _w("r", 557.91, 571.95, 737.26, 741.74),
    _w("e", 557.91, 571.95, 741.74, 748.14), _w("m", 557.91, 571.95, 748.06, 758.29),
    _w("i", 557.91, 571.95, 758.29, 761.49), _w("s", 557.91, 571.95, 761.38, 767.78),
    _w("e", 557.91, 571.95, 767.74, 774.14), _w("s", 557.91, 571.95, 774.1, 780.5),
]

# Verbatim capture: same PDF, page 6 -- a real Objectives list where every
# bullet happens to start with "To" at the same left-margin x. A false
# positive for "short + narrow + same column", the exact confusable this
# guard must reject.
REAL_OBJECTIVES_TO_BULLETS = [
    _w("To", 127.58, 138.15, 95.34, 106.38),
    _w("To", 127.58, 138.15, 124.50, 135.54),
    _w("To", 127.58, 138.15, 191.58, 202.62),
    _w("To", 127.58, 138.15, 220.74, 231.78),
    _w("To", 127.58, 138.15, 262.53, 273.57),
    _w("To", 127.58, 138.15, 304.41, 315.45),
]

# Verbatim capture 2026-09-13: the words sharing a line with the page-25 title's glyphs,
# the nearest one per glyph. The body column ends ~143pt left of the title.
MARRICKVILLE_P25_LINE_MATES = [
    _w("without", 356.87, 399.61, 523.23, 535.23), _w("the", 372.73, 385.32, 553.79, 564.83),
    _w("of", 395.42, 402.97, 566.39, 577.43), _w("the", 389.26, 401.85, 604.34, 615.38),
    _w("be", 377.91, 387.98, 616.94, 627.98), _w("breaks", 387.33, 414.41, 654.74, 665.78),
    _w("as", 389.92, 399.37, 667.34, 678.38), _w("to", 405.80, 413.35, 680.06, 691.10),
    _w("harm", 392.22, 412.84, 692.66, 703.70), _w("any", 396.99, 411.49, 743.89, 754.93),
    _w("sexual", 388.28, 414.39, 756.49, 767.53),
]
# Verbatim capture 2026-09-13: page 21 of the same chapter carries the same title glyphs
# (identical geometry) with body text 33.4-38.9pt from 6 of them.
MARRICKVILLE_P21_WORDS_NEAR_TITLE = [
    _w("Otherwise", 479.36, 516.16, 566.98, 576.94), _w("and", 488.72, 502.39, 625.69, 635.65),
    _w("wipe", 504.66, 521.45, 625.69, 635.65), _w("client;", 485.72, 507.08, 649.33, 659.29),
    _w("a", 495.32, 499.86, 660.85, 670.81), _w("daily", 502.16, 518.99, 660.85, 670.81),
    _w("contaminated", 457.67, 506.80, 743.89, 753.85), _w("continued...", 482.26, 524.56, 766.81, 776.77),
]

# Verbatim capture 2026-09-13: waverley DCP 2022 page 129, B15 15.3 Objectives. Seven "To"
# bullets 2.4pt apart -- contiguous, short, alphabetic, one (x0, x1) -- with each bullet's
# own next word 2.5pt to its right. The old guard stripped this band and cut
# "(a) To develop" to "(a) develop" and "Arcades" to "ades".
WAVERLEY_P129_TO_BULLETS = [
    _w("To", 160.93, 172.15, 135.79, 146.83), _w("To", 160.93, 172.15, 162.55, 173.59),
    _w("To", 160.93, 172.15, 175.99, 187.03), _w("To", 160.92, 172.14, 189.42, 200.46),
    _w("To", 160.92, 172.14, 202.86, 213.90), _w("To", 160.93, 172.15, 216.30, 227.34),
    _w("To", 160.93, 172.15, 229.73, 240.77),
]
WAVERLEY_P129_LINE_MATES = [
    _w("develop", 176.18, 211.97, 135.79, 146.83), _w("increase", 174.73, 212.02, 162.55, 173.59),
    _w("ensure", 174.61, 205.31, 175.99, 187.03), _w("expand", 174.60, 207.52, 189.42, 200.46),
    _w("promotes", 174.72, 218.15, 202.86, 213.90), _w("increase", 174.73, 212.02, 216.30, 227.34),
    _w("provide", 174.73, 208.79, 229.73, 240.77),
]

# Verbatim capture 2026-09-13: waverley page 7, A1 1.4 policy list. Twelve "o" sub-bullets
# stacked 2.4pt apart, each 11.4pt left of its item. The old guard stripped this band and
# turned "STATUTORY" into "STATUT RY" and "applies" into "appies" elsewhere on the page.
WAVERLEY_P7_SUB_BULLETS = [
    _w("o", 174.56, 181.19, 604.99, 616.03), _w("o", 174.58, 181.20, 618.43, 629.47),
    _w("o", 174.56, 181.19, 631.86, 642.90), _w("o", 174.58, 181.20, 645.30, 656.34),
    _w("o", 174.59, 181.21, 658.74, 669.78), _w("o", 174.60, 181.22, 672.06, 683.10),
    _w("o", 174.60, 181.22, 685.50, 696.54), _w("o", 174.61, 181.23, 698.93, 709.97),
    _w("o", 174.61, 181.23, 712.37, 723.41), _w("o", 174.62, 181.24, 725.80, 736.84),
    _w("o", 174.62, 181.24, 739.24, 750.28), _w("o", 174.63, 181.26, 752.68, 763.72),
]
WAVERLEY_P7_LINE_MATES = [
    _w("Waverley", 192.57, 235.01, 600.93, 611.97), _w("Our", 192.57, 209.50, 627.80, 638.84),
    _w("Local", 192.58, 215.63, 641.24, 652.28), _w("Public", 192.59, 219.58, 654.67, 665.71),
    _w("Development", 192.60, 253.18, 668.00, 679.04), _w("Planning", 192.60, 231.16, 681.43, 692.47),
    _w("Tree", 192.62, 212.87, 694.87, 705.91), _w("Tree", 192.62, 212.87, 708.31, 719.35),
    _w("Heritage", 192.63, 231.00, 721.74, 732.78), _w("Public", 192.63, 219.61, 735.18, 746.22),
    _w("Inter-War", 192.64, 236.57, 748.61, 759.65),
]


class TestVerticalMarginLabelDetected:
    def test_real_marrickville_page25_margin_label(self):
        band = find_vertical_margin_label_band(REAL_MARGIN_LABEL_WORDS)
        assert band is not None
        x0, x1 = band
        assert x0 == 557.91 - 0.5
        assert x1 == 571.95 + 0.5

    def test_band_covers_only_the_contiguous_run(self):
        # A stray short word at the SAME (x0, x1) but far below the real run
        # (a real gap, e.g. a page footer number reusing the same column by
        # coincidence) must not be pulled into the returned band or block
        # detection of the real contiguous run.
        words = REAL_MARGIN_LABEL_WORDS + [_w("9", 557.91, 571.95, 820.0, 828.0)]
        band = find_vertical_margin_label_band(words)
        assert band is not None


class TestConfusableNegatives:
    def test_objectives_bullets_all_starting_with_to(self):
        """Real 'To ...' objectives list, same left margin, short first word --
        must NOT be flagged. This is the exact false positive an earlier
        version of this guard produced (caught before merge, 2026-09-05)."""
        assert find_vertical_margin_label_band(REAL_OBJECTIVES_TO_BULLETS) is None

    def test_stacked_numeric_column_is_not_a_label(self):
        # A page-number or fee-schedule column: short, same narrow x, tightly
        # stacked (would pass the contiguity test) -- but numeric, not a
        # label. The alpha-majority requirement must reject it.
        words = [_w(str(n), 500.0, 512.0, 100.0 + n * 8, 106.0 + n * 8) for n in range(10)]
        assert find_vertical_margin_label_band(words) is None

    def test_too_few_stacked_letters_is_not_a_label(self):
        # Below MIN_RUN even though perfectly contiguous and alphabetic --
        # a real short word broken into few enough glyphs to be coincidence.
        words = [
            _w("O", 400.0, 412.0, 100.0, 108.0),
            _w("K", 400.0, 412.0, 108.0, 116.0),
        ]
        assert find_vertical_margin_label_band(words) is None

    def test_wide_words_are_never_candidates(self):
        # Ordinary prose: words wider than a single glyph's bbox, one per
        # line, same left margin (a normal justified paragraph). Must not be
        # mistaken for a stacked single-character run no matter how many
        # lines share the same left edge.
        words = [
            _w(text, 72.0, 72.0 + len(text) * 6.0, 100.0 + i * 14.0, 108.0 + i * 14.0)
            for i, text in enumerate(
                ["Development", "applications", "must", "demonstrate", "compliance", "with", "clause", "4.6"]
            )
        ]
        assert find_vertical_margin_label_band(words) is None

    def test_empty_word_list(self):
        assert find_vertical_margin_label_band([]) is None

    def test_words_missing_geometry_keys_are_skipped_not_fatal(self):
        words = [{"text": "x"}, {"text": "y", "x0": None, "x1": None}]
        assert find_vertical_margin_label_band(words) is None


class TestAStackedListMarkerIsNotAMarginTitle:
    """Found 2026-09-13: contiguous stacked list markers passed every earlier check, and
    stripping their band deleted letters from 27 of waverley's 602 rules."""

    def test_the_real_title_is_still_found_with_its_page_text_beside_it(self):
        band = find_vertical_margin_label_band(REAL_MARGIN_LABEL_WORDS + MARRICKVILLE_P25_LINE_MATES)
        assert band == (557.91 - 0.5, 571.95 + 0.5)

    def test_to_bullets_with_their_words_beside_them_are_not_a_title(self):
        words = WAVERLEY_P129_TO_BULLETS + WAVERLEY_P129_LINE_MATES
        assert find_vertical_margin_label_band(words) is None

    def test_sub_bullets_with_their_items_beside_them_are_not_a_title(self):
        words = WAVERLEY_P7_SUB_BULLETS + WAVERLEY_P7_LINE_MATES
        assert find_vertical_margin_label_band(words) is None

    def test_the_title_with_body_text_33pt_from_some_letters_is_still_a_title(self):
        """Page 21: body text within 33-39pt of 6 of the 38 glyphs. A single 'no word
        within 40pt' rule rejected this real title, letting it interleave into the text."""
        band = find_vertical_margin_label_band(REAL_MARGIN_LABEL_WORDS + MARRICKVILLE_P21_WORDS_NEAR_TITLE)
        assert band == (557.91 - 0.5, 571.95 + 0.5)

    def test_one_stray_word_beside_one_letter_does_not_undo_a_title(self):
        """Confusable: a page number or callout 10pt beside a single glyph of the real
        title. One glyph of 38 beside a word is a title with a neighbour, not a list."""
        g = REAL_MARGIN_LABEL_WORDS[20]
        stray = _w("12", g["x0"] - 10.0 - 8.0, g["x0"] - 10.0, g["top"], g["bottom"])
        band = find_vertical_margin_label_band(REAL_MARGIN_LABEL_WORDS + [stray])
        assert band == (557.91 - 0.5, 571.95 + 0.5)

    def test_markers_19pt_from_their_words_are_still_not_a_title(self):
        """Confusable boundary: the page-129 bullets with every word moved 19pt away."""
        moved = [_w(m["text"], b["x1"] + 19.0, b["x1"] + 19.0 + (m["x1"] - m["x0"]), m["top"], m["bottom"])
                 for b, m in zip(WAVERLEY_P129_TO_BULLETS, WAVERLEY_P129_LINE_MATES)]
        assert find_vertical_margin_label_band(WAVERLEY_P129_TO_BULLETS + moved) is None


class _FakePage:
    """extract_words() returns fixture words; filter() records that the page was cut."""

    def __init__(self, words, width=595.28, bbox=None):
        self._words = words
        self.width = width
        self.bbox = bbox if bbox is not None else (0.0, 0.0, width, 842.0)
        self.filtered = False

    def extract_words(self):
        return self._words

    def filter(self, fn):
        self.filtered = True
        return "filtered page"


class TestThePageStripUsesTheCheck:
    def test_a_page_with_a_to_bullet_list_is_left_untouched(self):
        page = _FakePage(WAVERLEY_P129_TO_BULLETS + WAVERLEY_P129_LINE_MATES)
        assert _strip_vertical_margin_label(page) is page
        assert not page.filtered, "body letters in the bullet column would be deleted"

    def test_a_page_with_a_real_margin_title_is_still_stripped(self):
        page = _FakePage(REAL_MARGIN_LABEL_WORDS + MARRICKVILLE_P25_LINE_MATES)
        assert _strip_vertical_margin_label(page) == "filtered page"


def _moved(bullets, mates, gap):
    """Each line's word moved to `gap` points right of its marker."""
    return [_w(m["text"], b["x1"] + gap, b["x1"] + gap + (m["x1"] - m["x0"]), m["top"], m["bottom"])
            for b, m in zip(bullets, mates)]


class TestATitleSitsInThePageMargin:
    """Cross-review 2026-09-13: markers 20pt or more from their words pass the neighbour
    check. A real title also sits in the page's outer margin (92.6-93.6% across on all 12
    marrickville pages); every waverley false stack sat at 17.8-30.5%."""

    W = 595.28

    def test_markers_21pt_from_their_words_in_the_text_column_are_not_a_title(self):
        words = WAVERLEY_P129_TO_BULLETS + _moved(WAVERLEY_P129_TO_BULLETS, WAVERLEY_P129_LINE_MATES, 21.0)
        assert find_vertical_margin_label_band(words) is not None, "fixture no longer passes the neighbour check"
        assert find_vertical_margin_label_band(words, self.W) is None

    def test_the_real_title_in_the_right_margin_is_found_with_the_page_width(self):
        words = REAL_MARGIN_LABEL_WORDS + MARRICKVILLE_P21_WORDS_NEAR_TITLE
        assert find_vertical_margin_label_band(words, self.W) == (557.91 - 0.5, 571.95 + 0.5)

    def test_an_isolated_stack_in_the_middle_of_the_page_is_left_alone(self):
        shifted = [_w(g["text"], g["x0"] - 260.0, g["x1"] - 260.0, g["top"], g["bottom"])
                   for g in REAL_MARGIN_LABEL_WORDS]
        assert find_vertical_margin_label_band(shifted) is not None, "fixture no longer passes the neighbour check"
        assert find_vertical_margin_label_band(shifted, self.W) is None

    def test_on_a_page_whose_box_starts_at_x100_the_margin_is_measured_from_the_box(self):
        """Cross-review: a page box spanning x=100..695. An isolated stack at x=550 is inside
        that page's text column; measured from x=0 it looked like the right margin."""
        stack = [_w("To", 550.0, 561.2, b["top"], b["bottom"]) for b in WAVERLEY_P129_TO_BULLETS]
        assert find_vertical_margin_label_band(stack, self.W) is not None, "fixture no longer exercises the offset"
        page = _FakePage(stack, width=self.W, bbox=(100.0, 0.0, 100.0 + self.W, 842.0))
        assert _strip_vertical_margin_label(page) is page
        assert not page.filtered, "a stack inside an offset page's text column would be deleted"

    def test_the_real_title_on_an_offset_page_is_still_stripped(self):
        shifted = [_w(g["text"], g["x0"] + 100.0, g["x1"] + 100.0, g["top"], g["bottom"])
                   for g in REAL_MARGIN_LABEL_WORDS]
        page = _FakePage(shifted, width=self.W, bbox=(100.0, 0.0, 100.0 + self.W, 842.0))
        assert _strip_vertical_margin_label(page) == "filtered page"

    def test_the_page_strip_passes_the_page_width(self):
        page = _FakePage(WAVERLEY_P129_TO_BULLETS + _moved(WAVERLEY_P129_TO_BULLETS, WAVERLEY_P129_LINE_MATES, 21.0))
        assert _strip_vertical_margin_label(page) is page
        assert not page.filtered, "a list in the text column would be deleted"
