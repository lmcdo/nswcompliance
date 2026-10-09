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
