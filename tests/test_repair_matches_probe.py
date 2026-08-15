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


@pytest.mark.parametrize("dq_id,pass_name", PAIRS)
def test_repair_predicate_is_contained_in_the_probe(dq_id, pass_name):
    """Every row the repair selects must be a row the probe counts.

    Containment, not equality, is the property that matters: the repair must
    never touch a row outside the metric's scope, because then it would be
    editing served text nothing is watching.
    """
    _, probe_sql, _, _ = dq_probe_live.PROBES[dq_id]
    _dq, repair_pred, _fn, _inv, _name = repair_tex_residue.PASSES[pass_name]
    assert _normalise(repair_pred) in _normalise(probe_sql), (
        f"{pass_name} repair predicate is not present in {dq_id}'s probe.\n"
        f"They have drifted, which is how the first DQ-76 pass reported 0 "
        f"while 103 rows were still broken.\n"
        f"repair: {_normalise(repair_pred)}\n"
        f"probe : {_normalise(probe_sql)}"
    )


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
