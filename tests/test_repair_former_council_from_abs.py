"""decide(): a lot moves only when it is clearly inside one former LGA and disagrees."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "repair_former_council_from_abs",
    Path(__file__).resolve().parent.parent / "scripts" / "repair_former_council_from_abs.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def test_victoria_street_ashfield_moves_from_marrickville():
    # 162/137 Victoria St Ashfield: stored marrickville (nearest-precinct guess), ABS says Ashfield.
    assert mod.decide("marrickville", "ashfield", 300.0, 20.0) == "ashfield"


def test_edge_lot_is_left_alone():
    assert mod.decide("marrickville", "ashfield", 12.0, 20.0) is None


def test_agreeing_lot_is_left_alone():
    assert mod.decide("Ashfield", "ashfield", 300.0, 20.0) is None


def test_outside_every_polygon_is_left_alone():
    assert mod.decide("leichhardt", None, None, 20.0) is None


def test_null_current_is_filled_when_deep():
    assert mod.decide(None, "leichhardt", 80.0, 20.0) == "leichhardt"
