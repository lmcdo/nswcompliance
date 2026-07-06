"""Field-coverage ratchet tests (S3) — a brief layer may gain fields, never lose them.

The ratchet also runs standalone in pre-push (step 1c); running it here too
means CI and any pytest invocation enforce the same lock. The check() unit
tests pin the semantics the gate depends on — in particular that a RENAME
(add+remove, same field count) is a loss, not a wash.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from brief_field_coverage_ratchet import (  # noqa: E402
    BASELINE_PATH,
    _collect_field_map,
    check,
    collect_from_roots,
)


def test_current_models_satisfy_checked_in_baseline():
    """THE ratchet: current code must not have lost any locked field."""
    import json

    with open(BASELINE_PATH, encoding="utf-8") as fh:
        baseline = json.load(fh)
    assert len(baseline) >= 50  # baseline exists and is substantive
    assert check(_collect_field_map(), baseline) == 0


def test_field_loss_fails():
    assert check({"M": ["a"]}, {"M": ["a", "b"]}) == 1


def test_rename_is_a_loss_not_a_wash():
    # same field count — a naive count-based ratchet would pass this
    assert check({"M": ["a", "c"]}, {"M": ["a", "b"]}) == 1


def test_model_disappearing_fails():
    assert check({}, {"M": ["a"]}) == 1


def test_pure_addition_passes():
    assert check({"M": ["a", "b", "c"], "New": ["x"]}, {"M": ["a", "b"]}) == 0


def test_identical_passes():
    assert check({"M": ["a", "b"]}, {"M": ["a", "b"]}) == 0


def test_name_collision_with_different_fields_raises():
    """Two reachable models with the same class name but different fields:
    silently keeping first-seen would leave the second unlocked (a hole in the
    ratchet), so collection must fail loudly."""
    from pydantic import BaseModel, create_model

    first = create_model("ClashModel", x=(int, 0))
    second = create_model("ClashModel", y=(int, 0))

    class HolderA(BaseModel):
        a: first = None

    class HolderB(BaseModel):
        b: second = None

    with pytest.raises(RuntimeError, match="collision"):
        collect_from_roots([HolderA, HolderB])


def test_parametrised_datafields_recurse_to_payload_models():
    """DataField[Optional[X]] must contribute X's fields to the lock (the walk
    can't stop at the envelope, or payload models are never ratcheted)."""
    current = _collect_field_map()
    assert "FloodDetail" in current            # reached only via DataField[...]
    assert "TerrainAnalysisDetail" in current  # explicit root (ForwardRef gap)
    assert "DataField" in current
    assert not any("[" in name for name in current)  # no fragile parametrised names
