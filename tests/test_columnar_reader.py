"""Geometric two-column reader — pure-function tests.

prior-art-checked: extends this file's own layout toolkit (preflight/upright);
no existing geometric column reader (the header-pair COUNCIL_COLUMN_CONFIGS path
needs anchor words and per-council boundary_x).
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

find_gutter = mod._find_gutter
columnar = mod._columnar_text


def word(text, x0, x1, top):
    return {"text": text, "x0": float(x0), "x1": float(x1), "top": float(top), "bottom": float(top) + 8}


def two_col_words():
    # 20 left words (x 40-180), 20 right words (x 320-540), interleaved y
    ws = []
    for i in range(20):
        ws.append(word(f"L{i}", 40, 180, 100 + i * 10))
        ws.append(word(f"R{i}", 320, 540, 100 + i * 10))
    return ws


def single_col_words():
    return [word(f"W{i}", 40, 540, 100 + i * 10) for i in range(40)]


def test_gutter_found_two_column():
    cx = find_gutter(two_col_words(), 600)
    assert cx is not None and 180 <= cx <= 320


def test_no_gutter_single_column():
    assert find_gutter(single_col_words(), 600) is None


def test_gutter_sparse_page_none():
    assert find_gutter([word("a", 40, 80, 10)] * 5, 600) is None


class FakePage:
    def __init__(self, words, width=600):
        self._w = words
        self.width = width

    def extract_words(self):
        return self._w


def test_columnar_reads_left_then_right():
    out = columnar(FakePage(two_col_words()))
    assert out is not None
    # all left labels appear before all right labels in the emitted text
    assert out.index("L0") < out.index("R0")
    assert out.index("L19") < out.index("R0")


def test_columnar_single_column_returns_none():
    assert columnar(FakePage(single_col_words())) is None


def test_columnar_full_width_heading_kept_in_place():
    ws = two_col_words()
    ws.insert(0, word("HEADING", 40, 540, 60))  # full-width line above the columns
    out = columnar(FakePage(ws))
    assert out is not None and out.split("\n")[0].startswith("HEADING")
