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


# --- build_lot_search_index Step 9: no nearest-precinct guess -------------------------------
# 162/137 Victoria St Ashfield: inside ABS former Ashfield, inside no precinct outline; the old
# Step 9b took the NEAREST outline (Marrickville precinct 16, 520 m) and served the Marrickville DCP.

def test_victoria_street_build_assigns_ashfield_not_nearest_precinct():
    assert mod.assign("ashfield", 300.0, None) == "ashfield"


def test_edge_lot_outside_every_outline_stays_null():
    # Old Step 9b would have filled this from the nearest outline; now it is left to the suburb map.
    assert mod.assign("ashfield", 5.0, None) is None


def test_edge_lot_takes_the_outline_that_contains_it():
    assert mod.assign("ashfield", 5.0, "Marrickville") == "marrickville"


def test_abs_beats_a_containing_outline_when_deep():
    assert mod.assign("leichhardt", 200.0, "Marrickville") == "leichhardt"


def test_build_step9_has_no_nearest_precinct_query():
    src = (Path(__file__).resolve().parent.parent / "scripts" / "build_lot_search_index.py").read_text(encoding="utf-8")
    step9 = src[src.index("# Step 9:"):src.index("return lot_count", src.index("# Step 9:"))]
    assert "<->" not in step9 and "ST_DWithin" not in step9
    assert "assign_for_lga" in step9
