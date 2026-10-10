"""The DQ-142 generator refuses a figure that is not in its own quote.

prior-art-checked: reuse not viable because the generator is new in this PR.
"""
import importlib.util
import os
import sys
import types

sys.modules.setdefault("psycopg2", types.ModuleType("psycopg2"))
_spec = importlib.util.spec_from_file_location(
    "dq142", os.path.join(os.path.dirname(__file__), "..", "scripts", "dq142_build_controls_migration.py"))
dq142 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dq142)


def test_figure_in_quote_passes():
    assert dq142.value_in_quotes(6, "m", ["set back a minimum of 6 metres from the street"])


def test_metres_written_as_mm_passes():
    assert dq142.value_in_quotes(0.9, "m", ["a minimum 900 mm setback at ground level"])


def test_percent_passes():
    assert dq142.value_in_quotes(35, "%", ["35% of the site area is deep soil"])


def test_figure_absent_is_refused():
    assert not dq142.value_in_quotes(8, "m", ["set back a minimum of 6 metres"])


def test_digit_inside_a_larger_number_is_refused():
    # 5 must not match 5.5 or 15; 1.5 must not match 11.5
    assert not dq142.value_in_quotes(5, "m", ["a 5.5m minimum, or 15% of the site"])
    assert not dq142.value_in_quotes(1.5, "m", ["setback of 11.5m"])


def test_mm_inside_a_larger_number_is_refused():
    assert not dq142.value_in_quotes(0.9, "m", ["a 1900 mm wall"])


def test_greater_of_rule_is_refused():
    assert not dq142.single_figure_rule(None, ["30% of the site length or 10 metres, whichever is greater"])


def test_different_figure_each_side_is_refused():
    assert not dq142.single_figure_rule(None, ["1m on one side and 2.5m on the other"])


def test_neighbour_average_in_condition_is_refused():
    assert not dq142.single_figure_rule("or the average of the immediate neighbours", ["a 5.5m minimum"])


def test_plain_minimum_passes():
    assert dq142.single_figure_rule(None, ["0.9 metres from any side boundary"])


def test_road_type_and_width_limbs_are_refused():
    assert not dq142.single_figure_rule("9 m to designated roads", ["6m to local roads"])
    assert not dq142.single_figure_rule("buildings to occupy a maximum of 80% of the lot width", ["1.5 metres"])


def test_unit_must_match():
    assert not dq142.value_in_quotes(35, "%", ["a setback of 35 metres"])
    assert not dq142.value_in_quotes(20, "m", ["20% of the site"])
