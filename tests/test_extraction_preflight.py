"""Preflight layout detector — pure-function tests.

prior-art-checked: extends the extractor's own fidelity toolkit; no existing
pre-extraction layout detector to reuse (guard hits were SEPP markdown parsers).
"""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "dcp_extract_changed", Path(__file__).parent.parent / "scripts" / "dcp_extract_changed.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules.setdefault("dcp_extract_changed", mod)
spec.loader.exec_module(mod)

detect = mod.detect_two_column_words
suspect_reason = mod.suspect_reason
detect_repealed = mod.detect_repealed_stamp

W = 600.0  # page width


def col(x, n):
    """n words of width 80 starting at x."""
    return [(x, x + 80.0)] * n


def test_two_column_page_detected():
    spans = col(40, 40) + col(340, 40)  # left band + right band, no gutter crossers
    assert detect(spans, W) is True


def test_single_column_full_width_not_detected():
    spans = [(40.0, 560.0)] * 60  # every word crosses the middle
    assert detect(spans, W) is False


def test_prose_column_with_margin_notes_not_detected():
    # 90% body words crossing centre + a few margin labels
    spans = [(60.0, 540.0)] * 54 + col(20, 6)
    assert detect(spans, W) is False


def test_sparse_page_not_detected():
    assert detect(col(40, 10) + col(340, 10), W) is False


def test_zero_width_page_safe():
    assert detect(col(40, 40) + col(340, 40), 0.0) is False


def test_suspect_reason_preflight_two_column():
    r = suspect_reason({
        "diff": {},
        "preflight": {"two_column_fail": True, "two_column_pages": 30, "text_pages": 100},
    })
    assert r is not None and "preflight_two_column" in r


def test_suspect_reason_preflight_empty_layer():
    r = suspect_reason({
        "diff": {},
        "preflight": {"empty_layer_fail": True, "empty_text_pages": 5, "total_pages": 7},
    })
    assert r is not None and "preflight_empty_layer" in r


def test_suspect_reason_clean_preflight_is_none():
    assert suspect_reason({"diff": {}, "preflight": {"two_column_fail": False}}) is None


# ── Repealed-stamp front-matter guard (Woollahra failure class, 2026-07-29) ──

def test_repealed_stamp_woollahra_amendment_footer():
    texts = ["Chapter C1\nPaddington Heritage Conservation Area",
             "Repealed by WDCP 2015 Amendment No. 13 on 12 October 2020\nbody text"]
    hit = detect_repealed(texts)
    assert hit == "Repealed by WDCP 2015 Amendment No. 13 on 12 October 2020"


def test_repealed_stamp_pre2015_variant():
    # c2/c3/f1 archive files use the terse form with no space before the year
    assert detect_repealed(["Repealed by WDCP2015 on 23/05/15"]) is not None


def test_repealed_stamp_case_insensitive_and_indented():
    assert detect_repealed(["   REPEALED BY Amendment No. 7"]) is not None


def test_repealed_prose_mid_line_not_matched():
    # Amendment-history prose mentions repeal mid-sentence — must NOT reject
    texts = ["This chapter replaces the controls that were repealed by Amendment 5."]
    assert detect_repealed(texts) is None


def test_repealed_clean_front_matter_none():
    texts = ["Chapter A1\nIntroduction",
             "CHAPTER A1 APPROVED ON 27 APRIL 2015\nLast amended on 24 February 2026", ""]
    assert detect_repealed(texts) is None


def test_repealed_empty_and_none_pages_safe():
    assert detect_repealed(["", None, ""]) is None
