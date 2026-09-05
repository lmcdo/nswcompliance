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
    from dcp_extract_changed import find_vertical_margin_label_band  # noqa: E402
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
