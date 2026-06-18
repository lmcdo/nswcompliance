"""Regression guard for DCP setback taxonomy (Bug 2).

Setbacks must reach the constraint engine *typed* (front/rear/side) so they feed
the footprint calc and lift confidence. The DB stores typed values in
``dcp_setback_controls.control_type`` and ``fetch_dcp_setbacks`` surfaces them as
``semantic_type``; the consumption seam
(:func:`services.constraint_arithmetic._dcp_controls_from_setback_rows`) must
prefer ``semantic_type`` over the ``prescribed`` / ``site_derived`` *kind*.

These tests lock that contract: if extraction ever regressed to an untyped
``prescribed`` control, the canary test would fail because the value would no
longer route into a front/rear/side slot.
"""

from services.constraint_arithmetic import (
    _dcp_controls_from_setback_rows,
    _get_dcp_value,
)


def _row(**kw):
    """A fetch_dcp_setbacks-shaped setback row dict."""
    base = {"dev_type": "dwelling_house", "value_min": 6.0, "unit": "m"}
    base.update(kw)
    return base


# --- Expected use: semantic_type produces typed controls -------------------

def test_semantic_type_yields_typed_control_types():
    rows = [
        _row(semantic_type="front_setback", value_min=6.0),
        _row(semantic_type="rear_setback", value_min=6.0),
        _row(semantic_type="side_setback", value_min=1.5),
    ]
    controls = _dcp_controls_from_setback_rows(rows)
    assert [c.control_type for c in controls] == [
        "front_setback",
        "rear_setback",
        "side_setback",
    ]


def test_typed_controls_route_to_front_rear_side():
    controls = _dcp_controls_from_setback_rows([
        _row(semantic_type="front_setback", value_min=6.0),
        _row(semantic_type="rear_setback", value_min=6.0),
        _row(semantic_type="side_setback", value_min=1.5),
    ])
    assert _get_dcp_value(controls, "front_setback", "dwelling_house") == 6.0
    assert _get_dcp_value(controls, "rear_setback", "dwelling_house") == 6.0
    assert _get_dcp_value(controls, "side_setback", "dwelling_house") == 1.5


# --- The core contract: semantic_type wins over the prescribed kind --------

def test_semantic_type_beats_prescribed_kind():
    """control_type='prescribed' is the KIND; semantic_type is the real control."""
    row = _row(semantic_type="front_setback", control_type="prescribed")
    [control] = _dcp_controls_from_setback_rows([row])
    assert control.control_type == "front_setback"
    # And it routes correctly into the front slot.
    assert _get_dcp_value([control], "front_setback", "dwelling_house") == 6.0


def test_falls_back_to_control_type_when_semantic_absent():
    row = _row(control_type="rear_setback")  # no semantic_type
    [control] = _dcp_controls_from_setback_rows([row])
    assert control.control_type == "rear_setback"


# --- Failure canary: an untyped 'prescribed' control must NOT match ---------

def test_prescribed_only_row_does_not_feed_setbacks():
    """If a setback ever arrives untyped (only the 'prescribed' kind), it must
    not silently match a front/rear/side lookup — that is the Bug 2 failure
    mode. This canary fails loudly if extraction regresses to untyped."""
    row = _row(control_type="prescribed")  # no semantic_type, no typed control
    [control] = _dcp_controls_from_setback_rows([row])
    assert control.control_type == "prescribed"
    for slot in ("front_setback", "rear_setback", "side_setback"):
        assert _get_dcp_value([control], slot, "dwelling_house") is None


# --- Edge cases: value coercion + defaults ---------------------------------

def test_requirement_freetext_kept_as_condition_not_value():
    row = {"semantic_type": "front_setback", "requirement": "as per streetscape"}
    [control] = _dcp_controls_from_setback_rows([row])
    assert control.value_min is None
    assert control.condition == "as per streetscape"


def test_requirement_numeric_with_unit_is_coerced():
    row = {"semantic_type": "side_setback", "requirement": "1.5m"}
    [control] = _dcp_controls_from_setback_rows([row])
    assert control.value_min == 1.5


def test_value_max_and_unit_defaults():
    row = {"semantic_type": "front_setback", "value_min": 4.5, "value_max": "9m"}
    [control] = _dcp_controls_from_setback_rows([row])
    assert control.value_max == 9.0
    assert control.unit == "m"  # default when not supplied


def test_dev_type_defaults_to_dwelling_house():
    row = {"semantic_type": "front_setback", "value_min": 6.0}
    [control] = _dcp_controls_from_setback_rows([row])
    assert control.dev_type == "dwelling_house"


def test_clause_ref_fallback_used_when_row_has_no_clause():
    row = {"semantic_type": "front_setback", "value_min": 6.0}
    [control] = _dcp_controls_from_setback_rows([row], clause_ref="DCP 3.2")
    assert control.source_ref == "DCP 3.2"


def test_row_clause_beats_fallback():
    row = {"semantic_type": "front_setback", "value_min": 6.0, "clause": "4.1.1"}
    [control] = _dcp_controls_from_setback_rows([row], clause_ref="DCP 3.2")
    assert control.source_ref == "4.1.1"


def test_empty_rows_return_empty_list():
    assert _dcp_controls_from_setback_rows([]) == []
