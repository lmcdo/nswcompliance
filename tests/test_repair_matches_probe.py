"""A repair must cover exactly what its metric counts, or the row cannot close.

THIS ALREADY WENT WRONG. The DQ-76 repair carried a brace class of
[-A-Za-z0-9]; the probe was widened to any brace; the two drifted, and the
repair pass reported success at 0 while 103 rows still held '{}', '{ : }' and
'{ t h }'. Nothing failed. The metric said clean because the repair had fixed
everything the metric could still see.

Both files carry a comment saying the predicates must stay identical. A comment
is not a guard, and the whole ledger exists because prose claims decay. So this
asserts it.

No database. These are string constants, compared as strings.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dq_probe_live  # noqa: E402
import repair_tex_residue  # noqa: E402


def _normalise(sql: str) -> str:
    """Collapse whitespace so formatting differences are not failures.

    The predicates are embedded in a SELECT in one file and used as a bare
    WHERE fragment in the other, so they are wrapped differently on purpose.
    What must match is the condition itself.
    """
    return re.sub(r"\s+", " ", sql).strip()


#: probe id -> the repair pass that is supposed to clear it
PAIRS = [("DQ-76", "tex"), ("DQ-77", "units")]


def _probe_predicate(probe_sql: str) -> str:
    """The condition inside the probe's outer `AND ( ... )`.

    The probe wraps its predicate in a SELECT; the repair holds the bare
    condition. Comparing the whole strings would always differ, so the wrapper
    is stripped and the conditions compared directly.
    """
    flat = _normalise(probe_sql)
    marker = "v2_is_actionable AND ("
    idx = flat.index(marker) + len(marker)
    return flat[idx:].rstrip().rstrip(")")


@pytest.mark.parametrize("dq_id,pass_name", PAIRS)
def test_repair_predicate_EQUALS_the_probe_predicate(dq_id, pass_name):
    """The repair must cover EXACTLY what the metric counts.

    This asserted CONTAINMENT until the adversarial reviewer pointed out that
    containment permits the repair to be NARROWER than the probe - which is
    precisely the drift that already happened, when a brace class of
    [-A-Za-z0-9] left 103 rows unrepaired while the metric read 0. A test that
    allows the failure it was written to prevent is worse than no test, because
    it looks like cover.

    Equality is the right property in both directions: narrower and the row can
    never reach zero; wider and the repair edits served text the metric is not
    watching.
    """
    _, probe_sql, _, _ = dq_probe_live.PROBES[dq_id]
    _dq, repair_pred, _fn, _inv, _name = repair_tex_residue.PASSES[pass_name]
    assert _normalise(repair_pred) == _probe_predicate(probe_sql), (
        f"{pass_name} repair predicate differs from {dq_id}'s probe predicate.\n"
        f"repair: {_normalise(repair_pred)}\n"
        f"probe : {_probe_predicate(probe_sql)}"
    )


@pytest.mark.parametrize("dq_id,pass_name", PAIRS)
def test_dropping_an_OR_arm_from_the_repair_is_caught(dq_id, pass_name):
    """Guard the guard, in the direction that actually failed.

    The reviewer's specific scenario: the probe grows an arm, the repair does
    not, and the repair reports zero against its own narrower predicate while
    rows matched only by the new arm keep serving corrupt text.
    """
    _, probe_sql, _, _ = dq_probe_live.PROBES[dq_id]
    _dq, repair_pred, _fn, _inv, _name = repair_tex_residue.PASSES[pass_name]
    arms = [a for a in _normalise(repair_pred).split(" OR ") if a.strip()]
    if len(arms) < 2:
        pytest.skip("single-arm predicate has no arm to drop")
    narrowed = " OR ".join(arms[:-1])
    assert narrowed != _probe_predicate(probe_sql), (
        "dropping an OR arm from the repair still matched the probe, so the "
        "equality check would not notice a narrowing")


@pytest.mark.parametrize("dq_id,pass_name", PAIRS)
def test_pass_declares_the_row_it_clears(dq_id, pass_name):
    """The pass table must name the row, so the two cannot be mismatched."""
    declared = repair_tex_residue.PASSES[pass_name][0]
    assert declared == dq_id


def test_every_pass_maps_to_a_real_probe():
    """A pass pointing at a probe id that does not exist would never be run."""
    for pass_name, (dq_id, *_rest) in repair_tex_residue.PASSES.items():
        assert dq_id in dq_probe_live.PROBES, (
            f"pass '{pass_name}' claims to clear {dq_id}, which is not a probe")


def test_the_containment_check_can_fail():
    """Guard the guard: prove the assertion is not vacuously true.

    A containment test written against two strings that are always equal would
    pass forever. This shows a drifted predicate is actually rejected.
    """
    probe = "SELECT count(*) FROM t WHERE (a ~ 'x' OR b LIKE '%{%')"
    drifted = "a ~ 'x'"                       # repair covers less than the probe
    assert _normalise(drifted) in _normalise(probe)      # containment holds
    wider = "a ~ 'x' OR c ~ 'y'"              # repair covers something unwatched
    assert _normalise(wider) not in _normalise(probe)


# --------------------------------------------------------------------------
# the refusal gate: control SYMBOLS, not just control words
# --------------------------------------------------------------------------
#
# unknown_commands() matched [A-Za-z]+ only, so an escaped literal slipped past:
# "S = \{1, 2\}" reported no unknown command, the brace rule then ate the
# escaped braces, and the digit invariant still passed because no digit moved.
# A backslash before punctuation exists precisely to make that character
# literal, so removing it changes the text.

unknown_commands = repair_tex_residue.unknown_commands


@pytest.mark.parametrize("text,expected", [
    (r"S = \{1, 2\} applies", ["{", "}"]),
    (r"a 50\% reduction", ["%"]),
    (r"the \_ separator", ["_"]),
    (r"Smith \& Jones", ["&"]),
])
def test_escaped_literals_are_refused(text, expected):
    assert unknown_commands(text) == expected


@pytest.mark.parametrize("text", [
    r"\mathsf { m } only",
    r"\pmb { s } is the setback",
    "plain text with 900 mm and no commands",
])
def test_presentation_only_and_clean_text_are_not_refused(text):
    assert unknown_commands(text) == []


def test_semantic_words_are_still_refused():
    """The original class must not regress while adding the symbol case."""
    assert unknown_commands(r"ratio \div 2") == ["div"]
    assert unknown_commands(r"C = \frac { X } 3") == ["frac"]


# ---------------------------------------------------------------------------
# The DQ-77 signature must span a LINE, not a document.
#
# 2026-09-10: the ratchet went red with DQ-77 declared fixed and its probe
# reading 1. The row was not a recurrence of the unit split. It was DQ-78's map
# scramble -- id 122374, a canterbury_bankstown height control committed to the
# served set on 2026-09-09 with map labels interleaved -- where a '2', an 'a'
# and an 'm' landed on three consecutive lines and the '[ap] m' signature,
# written for '7 p m', matched across the newlines because it used \s.
#
# Narrowing a live metric is the move this ledger exists to distrust, so the
# narrowing gets the test rather than the comment: every documented real
# signature must still match, and the scramble shape must not. Without the
# second half this is a metric quietly taught to stop seeing.
# ---------------------------------------------------------------------------

#: Verbatim from the DQ-77 row's own sampled evidence, plus the m2 form.
REAL_UNIT_SPLITS = [
    "900 m m of a side boundary",
    "600 m m",
    "150 m m diameter sewer main",
    "no building within 4 m m of the rear boundary",
    "hours of operation are 7 a m to 7 p m",
    "deliveries must not occur after 10 p m",
    "a minimum site area of 450 m 2",
    "a volume of 12 m 3",
    "built in the early 20 t h century",
]

#: The scramble shape the narrowing exists to exclude: characters on their own
#: lines, lifted off a map figure. Taken from served row id 122374.
SCRAMBLE_ACROSS_LINES = [
    "l o in u k n ( d 12\na\nm ry ) Roosevelt Avenue 6 storeys",
    "8\nm\nm\n12",
    "20\nt\nh",
    "7\np\nm",
]


def _py_predicate(text: str) -> bool:
    """The probe's four signatures, as Python regexes over one string.

    Postgres' `~` and Python's `re.search` agree on this subset -- character
    classes, `+`, and a digit lookbehind-free prefix. `\M` (Postgres' end-of-
    word) is written as `\b` here, which is what it means for these strings.
    """
    pats = [
        r"[0-9][ \t]+m[ \t]+m\b",
        r"[0-9][ \t]+m[ \t]+[23]\b",
        r"[0-9][ \t]+[ap][ \t]+m\b",
        r"[0-9][ \t]+t[ \t]+h\b",
    ]
    return any(re.search(p, text) for p in pats)


@pytest.mark.parametrize("text", REAL_UNIT_SPLITS)
def test_a_real_unit_split_is_still_caught(text):
    """The narrowing must not blind the metric to what it was written for."""
    assert _py_predicate(text), f"narrowed signature stopped seeing: {text!r}"


@pytest.mark.parametrize("text", SCRAMBLE_ACROSS_LINES)
def test_a_scramble_across_newlines_is_not_a_unit_split(text):
    """DQ-78's defect must not be counted as DQ-77's.

    A metric mixing the two can be driven to zero by neither remedy -- the
    DQ-77 row has said so since 2026-08-15; this is the part that enforces it.
    """
    assert not _py_predicate(text), f"scramble counted as a unit split: {text!r}"


@pytest.mark.parametrize("text", REAL_UNIT_SPLITS)
def test_the_repair_transform_still_repairs_what_the_probe_still_counts(text):
    """Predicate and transform were narrowed together; prove it on real text."""
    repaired = repair_tex_residue.repair_units(text)
    assert repaired != text, f"probe counts it but the repair no longer fixes it: {text!r}"
    assert not _py_predicate(repaired), f"repair left the signature behind: {repaired!r}"
    # The pass's own invariant: only spaces removed, never a character.
    assert repair_tex_residue.nonspace(repaired) == repair_tex_residue.nonspace(text)
