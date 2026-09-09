"""Geometric two-column reader — pure-function tests.

prior-art-checked: extends this file's own layout toolkit (preflight/upright);
no existing geometric column reader (the header-pair COUNCIL_COLUMN_CONFIGS path
needs anchor words and per-council boundary_x).
"""
import importlib.util
import os
import sys
from pathlib import Path

# dcp_extract_changed reads R2 credentials with os.environ[...] at module scope, so
# merely importing it explodes without them. On a dev machine that never shows,
# because python-dotenv walks up and finds the repo-root .env — including from a
# worktree, where it reaches the parent checkout's file. CI has no .env, so this
# was the last thing standing between the suite and a clean run there.
# Same setdefault pattern as tests/test_dcp_schema_gate.py; values are unused.
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
           "R2_BUCKET_NAME", "R2_ENDPOINT_URL", "R2_PUBLIC_URL"):
    os.environ.setdefault(_k, "test")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")

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


def staggered_two_col_words():
    # Real PDFs: the two columns' lines do NOT line-wrap in sync, so a left
    # word and its "paired" right word almost never land on the exact same
    # 3px row band. 20 left words on rows 100, 110, 120... and 20 right words
    # offset by 4px (never coinciding with a left row after round(top/3)) --
    # this is the shape that broke the original band-matching version:
    # ashfield/chapter-d-precinct-guidelines, checked against the real PDF,
    # DQ-92, 2026-09-09.
    ws = []
    for i in range(20):
        ws.append(word(f"L{i}", 40, 180, 100 + i * 10))
        ws.append(word(f"R{i}", 320, 540, 104 + i * 10))
    return ws


def test_columnar_staggered_rows_still_grouped_by_column():
    """The original bug: no left/right pair shares a 3px band, so every line
    was single-sided, `two_col` was false throughout, and the page fell
    through to a plain Y-order read -- L0, R0, L1, R1, ... interleaved
    instead of grouped. Fixed version must still emit the whole left column
    before the whole right column."""
    out = columnar(FakePage(staggered_two_col_words()))
    assert out is not None
    assert out.index("L19") < out.index("R0"), (
        "left column must be fully emitted before the right column starts, "
        "even when no line shares a row band across the gutter"
    )


def test_columnar_narrow_gap_heading_stays_full_width():
    """Sol cross-review (HIGH 0.99, 2026-09-09): a full-width heading like
    '5.2.4 Local Infrastructure' can have words on BOTH sides of the gutter
    with ordinary word-spacing between them, no single word individually
    straddling cx. The word-straddle test alone misses this and would split
    it into the left/right buffers, corrupting reading order -- this is the
    ONLY full-width test the pre-fix version had (the `gap_min` check) and
    it must survive this fix, not just the new staggered-row behaviour."""
    ws = two_col_words()
    cx = find_gutter(ws, 600)
    assert cx is not None
    # Two words straddling NEITHER cx-5..cx+5 individually, but with a
    # narrow (~6px) gap between them -- well under gap_min (30 for W=600).
    ws.append(word("LeftHead", cx - 20, cx - 8, 300))
    ws.append(word("RightHead", cx + 2, cx + 20, 300))
    out = columnar(FakePage(ws, width=600))
    assert out is not None
    lines = out.split("\n")
    assert "LeftHead RightHead" in lines, (
        f"narrow-gap heading must be emitted as one full-width line, got: {lines}"
    )


def test_columnar_straddle_still_breaks_a_staggered_run():
    """A genuine full-width line (straddles the gutter) must still end the
    two-column run even when the run's own rows never had same-band
    left+right pairs -- otherwise a real heading gets folded oddly into a
    left/right bucket instead of staying in reading position."""
    ws = staggered_two_col_words()
    # Insert a real straddling line partway through the run, in a Y band
    # (round(top/3)=86) that no L/R word from staggered_two_col_words()
    # occupies, so it doesn't get merged into an existing row's line text.
    ws.append(word("MIDHEADING", 40, 540, 258))
    out = columnar(FakePage(ws))
    assert out is not None
    lines = out.split("\n")
    assert "MIDHEADING" in lines
    mid_idx = lines.index("MIDHEADING")
    before = "\n".join(lines[:mid_idx])
    after = "\n".join(lines[mid_idx + 1:])
    # L0 (top=100) was well before the straddle; L19 (top=290) was well after.
    assert "L0" in before and "L0" not in after
    assert "L19" in after and "L19" not in before
