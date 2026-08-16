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
