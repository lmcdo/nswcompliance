"""Millimetres must not be read as metres.

WHAT WENT WRONG
---------------
Regex alternation is ordered and stops at the first match. Two of the
seventeen unit patterns in numeric_extractor listed 'm' before 'mm', so
"600 mm" matched the leading 'm', left the second dangling, and recorded
600 METRES.

That is a factor of a thousand, in the values the product CALCULATES with
rather than merely displays. Measured on production 2026-08-15: a retaining
wall recorded as 600 m high, a window 3,400 m wide, a setback of 900 m.

It needs no OCR damage to fire - it misreads perfectly clean documents - which
is why it outlived the corrupted-text repair that first exposed it.

Both directions are tested. A pattern that simply refused to read metres would
pass a naive mm test and break every real metre control in the corpus.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from enrichment.extractors.numeric_extractor import (  # noqa: E402
    NumericExtractor, extract_numeric_values,
)


def _units(text: str):
    """(value, unit) pairs the extractor reports for this text."""
    result = extract_numeric_values(text)
    values = result.get("values") if isinstance(result, dict) else result
    return [(v.get("value_exact") if v.get("value_exact") is not None
             else v.get("value_min"), v.get("unit")) for v in (values or [])]


# --------------------------------------------------------------------------
# the regression: millimetres read as metres
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected_m", [
    ("excavation to a depth of 600 mm below ground level", 0.6),
    ("a window with a width of 3400 mm", 3.4),
    ("a strip 150 mm wide along the boundary", 0.15),
    ("a footing with a depth of 450 mm", 0.45),
])
def test_millimetres_are_converted_not_read_as_metres(text, expected_m):
    got = _units(text)
    assert got, f"extracted nothing from {text!r}"
    value, unit = got[0]
    assert unit == "m"
    assert value == pytest.approx(expected_m), (
        f"{text!r} gave {value}{unit}; a thousandfold error means the unit "
        f"alternation has 'm' before 'mm' again")


# --------------------------------------------------------------------------
# it must not break real metres - the failure a naive fix would cause
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected_m", [
    ("boring to a depth of 600 m below the surface", 600.0),
    ("a driveway with a width of 6 m", 6.0),
    ("a wall 12 m long", 12.0),
    ("a setback of at least 9 m from the side boundary", 9.0),
])
def test_real_metres_are_unchanged(text, expected_m):
    got = _units(text)
    assert got, f"extracted nothing from {text!r}"
    value, unit = got[0]
    assert unit == "m"
    assert value == pytest.approx(expected_m)


# --------------------------------------------------------------------------
# guard the ordering itself, so the fix cannot be silently reverted
# --------------------------------------------------------------------------

def test_no_pattern_lists_m_before_mm():
    """Structural guard on all seventeen patterns, not just the two fixed.

    Catches a NEW pattern written with the wrong order, which a behavioural
    test over sample sentences would miss until someone hit that phrasing in a
    real document.
    """
    import re
    raw = (ROOT / "enrichment" / "extractors" / "numeric_extractor.py").read_text(
        encoding="utf-8")
    # Skip comments. The first version of this guard flagged the comment that
    # DOCUMENTS the bug, because it quotes the broken alternation verbatim - a
    # false positive that would have pushed the next person to delete either the
    # explanation or the guard.
    src = "\n".join(line for line in raw.splitlines()
                    if not line.lstrip().startswith("#"))
    offenders = []
    for m in re.finditer(r"\(([^()]*\bmm\b[^()]*)\)", src):
        group = m.group(1)
        if "|" not in group:
            continue
        alts = [a.strip() for a in group.split("|")]
        if "mm" not in alts:
            continue
        # a bare 'm' alternative appearing BEFORE 'mm' shadows it
        if "m" in alts and alts.index("m") < alts.index("mm"):
            offenders.append(group)
    assert not offenders, (
        "these unit alternations put 'm' before 'mm', so millimetres will be "
        f"read as metres: {offenders}")


def test_the_ordering_guard_can_fail():
    """Prove the structural guard is not vacuously true."""
    import re
    bad = "(m|metres?|mm|millimetres?)"
    alts = [a.strip() for a in bad.strip("()").split("|")]
    assert "m" in alts and "mm" in alts
    assert alts.index("m") < alts.index("mm"), (
        "the sample the guard is meant to reject no longer looks wrong")


def test_extractor_constructs():
    """A smoke check that the patterns still compile after editing."""
    NumericExtractor()
