"""Golden/snapshot regression guard for the capacity engine.

PURPOSE
-------
Freeze ``compute_constraint_arithmetic`` output across ~20 representative input
shapes so that any code change which moves a stable number fails the build with a
readable diff. This is the "did we break the engine while working on it?" guard
described in the loop-engineering discussion — a REGRESSION check, not a
correctness oracle (see tests/golden/capacity_scenarios.py for the distinction).

HOW IT WORKS
------------
- The engine is a pure function, so outputs are deterministic with no DB/API.
- On each run we recompute every scenario and compare to tests/golden/
  capacity_golden.json.
- To (re)generate the golden file after an INTENTIONAL behaviour change:
      UPDATE_GOLDEN=1 python -m pytest tests/test_capacity_golden.py
  then eyeball the git diff of capacity_golden.json before committing — every
  changed number is a behaviour change you are signing off on.

Beyond the snapshot, a few explicit invariants are asserted directly so a careless
regeneration cannot silently reintroduce a known bug (GATE-2b override leak; the
Burwood-class conflicting-setback resolution).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from services.constraint_arithmetic import compute_constraint_arithmetic
from tests.golden.capacity_scenarios import scenarios

GOLDEN_PATH = Path(__file__).parent / "golden" / "capacity_golden.json"


def _run(kwargs: dict) -> dict:
    """Run one scenario and return its JSON-serialisable output dict."""
    result = compute_constraint_arithmetic(**kwargs)
    # mode="json" renders the ConstraintType enum + nested models as plain JSON.
    return result.model_dump(mode="json")


def _current() -> dict[str, dict]:
    return {s["name"]: _run(s["kwargs"]) for s in scenarios()}


def _maybe_regenerate() -> None:
    """Write the golden file when UPDATE_GOLDEN is set or it does not yet exist."""
    if os.environ.get("UPDATE_GOLDEN") or not GOLDEN_PATH.exists():
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_text(
            json.dumps(_current(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


_maybe_regenerate()

_SCENARIO_NAMES = [s["name"] for s in scenarios()]


@pytest.fixture(scope="module")
def golden() -> dict[str, dict]:
    assert GOLDEN_PATH.exists(), (
        "capacity_golden.json is missing. Regenerate with "
        "UPDATE_GOLDEN=1 python -m pytest tests/test_capacity_golden.py"
    )
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def test_golden_covers_every_scenario(golden):
    """The golden file and the scenario list must not drift apart."""
    assert set(golden.keys()) == set(_SCENARIO_NAMES), (
        "Golden file and scenario list disagree — regenerate with UPDATE_GOLDEN=1."
    )


@pytest.mark.parametrize("name", _SCENARIO_NAMES)
def test_scenario_matches_golden(name, golden):
    """Each scenario's current output must equal its frozen snapshot."""
    expected = golden[name]
    kwargs = next(s["kwargs"] for s in scenarios() if s["name"] == name)
    actual = _run(kwargs)
    assert actual == expected, (
        f"Capacity engine output changed for '{name}'.\n"
        f"If this change is INTENTIONAL, regenerate the golden file and review the "
        f"diff:\n    UPDATE_GOLDEN=1 python -m pytest tests/test_capacity_golden.py\n"
    )


# --- Hard invariants (independent of the snapshot) -------------------------
# These lock the two audit findings the snapshot alone could not protect from a
# careless golden regeneration.

def test_gate2b_override_does_not_leak_across_forms():
    """A dual_occupancy height bonus must not lift a dwelling_house (PR #519)."""
    kwargs = next(
        s["kwargs"] for s in scenarios()
        if s["name"] == "gate2b_override_form_mismatch_not_applied"
    )
    r = compute_constraint_arithmetic(**kwargs)
    assert r.sepp_overrides_applied == [], "Mismatched-form override was applied."
    # Effective height must remain the LEP value (8.5), not the 9.5 bonus.
    assert r.effective_height_m == 8.5


def test_conflicting_setbacks_pick_conservative_and_flag():
    """Two front setbacks (9m, 15m) -> the larger min is chosen and a gap flagged."""
    kwargs = next(
        s["kwargs"] for s in scenarios()
        if s["name"] == "conflicting_setbacks_conservative"
    )
    r = compute_constraint_arithmetic(**kwargs)
    assert r.setback_front_m == 15.0
    assert any("setback" in g.lower() or "conflict" in g.lower() for g in r.gaps), (
        "A conflicting-setback resolution must surface a data gap for verification."
    )
