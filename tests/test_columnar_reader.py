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


# ===========================================================================
# Hypothesis property-based invariants
#
# Added 2026-09-09, same session as the DQ-92 fix above: every hand-picked
# test in this file was written AFTER a specific real-PDF failure was found
# (mine, or one of the two Sol cross-review caught on push). Hand-picked
# cases only cover shapes someone already thought of. These generate random
# word geometries -- word counts, stagger amounts, gutter position, page
# width -- searching for a shape nobody picked by hand, same discipline as
# tests/test_flood_truth.py's existing Hypothesis suite (that file's
# established pattern: try/except HAS_HYPOTHESIS gate, @given + @settings,
# one INVARIANT per test, reused verbatim below rather than inventing a new
# style for this file).
# ===========================================================================

try:
    from hypothesis import given, strategies as st, settings, assume
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

if HAS_HYPOTHESIS:

    _TOKEN_RE = __import__("re").compile(r"\S+")

    def _tokens(text: str) -> list[str]:
        """Exact-token split, so 'R1' checks never accidentally match inside
        'R10'..'R19' via substring search -- .count()/in on the raw string
        would silently pass a real bug (or, as first written, fail on a
        phantom one). Word text here never contains internal whitespace."""
        return _TOKEN_RE.findall(text)

    @st.composite
    def two_column_page(draw, min_words=32, max_words=48):
        """A random valid two-column word layout: n_left words on the left,
        n_right on the right, each row's top position independently jittered
        (mimicking real PDFs, where the two columns' lines are NOT
        vertically synced -- the exact shape that broke the pre-fix
        version). No straddling line. Left/right x-ranges are pinned to the
        outer 30% of the page on each side, well clear of the 40-60% band
        _find_gutter scans -- guarantees a real gutter is always detected,
        so tests don't spend their budget on unrepresentative layouts where
        detection itself is the coin flip rather than the grouping logic
        under test. min_words defaults to 32, not lower: _find_gutter
        hard-requires len(words) >= 30 (scripts/dcp_extract_changed.py:714)
        before it even looks for a gutter -- a lower floor here just makes
        Hypothesis discard nearly every case as "no gutter", a
        test-construction bug rather than a code finding (this file's own
        FailedHealthCheck history, twice, before landing on this floor).
        Returns (words, page_width, n_left, n_right)."""
        page_width = draw(st.floats(min_value=400, max_value=1000))
        n_left = draw(st.integers(min_value=max(1, min_words // 2), max_value=max_words // 2))
        n_right = draw(st.integers(min_value=max(1, min_words // 2), max_value=max_words // 2))
        left_x0 = draw(st.floats(min_value=page_width * 0.02, max_value=page_width * 0.15))
        left_x1 = draw(st.floats(min_value=left_x0 + 5, max_value=page_width * 0.30))
        right_x0 = draw(st.floats(min_value=page_width * 0.70, max_value=page_width * 0.85))
        right_x1 = draw(st.floats(min_value=right_x0 + 5, max_value=page_width * 0.98))
        words = []
        top = 100.0
        for i in range(n_left):
            jitter = draw(st.floats(min_value=0, max_value=9))
            words.append(word(f"L{i}", left_x0, left_x1, top + jitter))
            top += draw(st.floats(min_value=8, max_value=14))
        top = 100.0
        for i in range(n_right):
            jitter = draw(st.floats(min_value=0, max_value=9))
            words.append(word(f"R{i}", right_x0, right_x1, top + jitter))
            top += draw(st.floats(min_value=8, max_value=14))
        return words, page_width, n_left, n_right

    @given(data=two_column_page())
    @settings(max_examples=300)
    def test_hyp_no_word_lost_or_duplicated(data):
        """INVARIANT: every word that goes in comes out exactly once,
        regardless of stagger, word count, or gutter position -- whether
        columnar() groups by column or (correctly, per test above) falls
        back to plain extraction, the STRING CONTENT must be conserved."""
        words, width, n_left, n_right = data
        out = columnar(FakePage(words, width=width))
        assume(out is not None)  # only a real two-column page is in scope here
        toks = _tokens(out)
        for i in range(n_left):
            assert toks.count(f"L{i}") == 1, f"L{i} lost or duplicated: {out!r}"
        for i in range(n_right):
            assert toks.count(f"R{i}") == 1, f"R{i} lost or duplicated: {out!r}"

    @given(data=two_column_page())
    @settings(max_examples=300)
    def test_hyp_left_column_precedes_right_column(data):
        """INVARIANT: the exact bug this session found and fixed, generalised.
        With no straddling line anywhere on the page, every left-column word
        must appear before every right-column word in the output -- for ANY
        stagger amount, word count, or gutter position, not just the one
        hand-picked shape in test_columnar_staggered_rows_still_grouped_by_column."""
        words, width, n_left, n_right = data
        out = columnar(FakePage(words, width=width))
        assume(out is not None)
        toks = _tokens(out)
        last_left = max(toks.index(f"L{i}") for i in range(n_left))
        first_right = min(toks.index(f"R{i}") for i in range(n_right))
        assert last_left < first_right, (
            f"a right-column word appeared before the left column finished "
            f"(n_left={n_left}, n_right={n_right}, width={width}): {out!r}"
        )

    @given(
        data=two_column_page(),
        heading_gap=st.floats(min_value=0, max_value=200),
    )
    @settings(max_examples=200)
    def test_hyp_straddling_heading_always_intact(data, heading_gap):
        """INVARIANT: Sol's finding, generalised. A line whose words span
        both sides of the gutter (individually straddling) must always
        appear as one intact, unfragmented line -- for any heading
        position, not just the one hand-picked mid-run insertion in
        test_columnar_straddle_still_breaks_a_staggered_run."""
        words, width, n_left, n_right = data
        cx = find_gutter(words, width)
        assume(cx is not None)  # construction pins this true nearly always
        heading_top = 100 + heading_gap
        words = list(words) + [word("HEADSTRADDLE", cx - 15, cx + 15, heading_top)]
        out = columnar(FakePage(words, width=width))
        assume(out is not None)
        assert "HEADSTRADDLE" in _tokens(out), (
            f"straddling heading was fragmented instead of staying intact: {out!r}"
        )
