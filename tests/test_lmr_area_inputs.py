"""Break-it tests for the live-measurement module (services/lmr_area_inputs.py). The network is replaced by fakes.

Aim: a failed or odd map response must become None / "cant_tell", never a quiet clear.
"""
import subprocess
import sys
from pathlib import Path

import pytest

from services import lmr_area_decision as dec
from services import lmr_area_inputs as inp

LAT, LNG = -33.8880, 151.1260  # a point in Ashfield
RING = [[LNG, LAT], [LNG + 0.0002, LAT], [LNG + 0.0002, LAT + 0.0002], [LNG, LAT + 0.0002], [LNG, LAT]]


def feats(*attrs):
    return {"features": [{"attributes": a} for a in attrs]}


def fake(monkeypatch, by_key):
    """by_key: substring of the url -> response dict, or None for 'did not answer'."""
    def _get(url, params, post=False):
        for k, v in by_key.items():
            if k in url:
                return v
        return feats()
    monkeypatch.setattr(inp, "_get_json", _get)


# ---- heritage -----------------------------------------------------------------------------------------
@pytest.mark.parametrize("classes,item,cons", [
    (["Item - General"], True, False),
    (["Local Heritage - General"], True, False),
    (["Item - Aboriginal"], True, False),
    (["Conservation Area - General"], False, True),
    (["Heritage Conservation Area", "Conservation Area - Landscape"], False, True),
    ([], False, False),
    (["Aboriginal Object"], None, False),
    (["Aboriginal Place of Heritage Significance"], None, False),
    (["Some New Class"], None, False),
    (["Conservation Area - General", "Item - General"], True, True),
])
def test_heritage_class_mapping(monkeypatch, classes, item, cons):
    fake(monkeypatch, {"MapServer/16/": feats(*[{"LAY_CLASS": c} for c in classes]), "MapServer/221/": feats()})
    h = inp._heritage(RING)
    assert h["item"] is item and h["conservation_area"] is cons and h["state_register"] is False


def test_heritage_failure_is_none_never_clear(monkeypatch):
    fake(monkeypatch, {"MapServer/16/": None, "MapServer/221/": None})
    h = inp._heritage(RING)
    assert h["item"] is None and h["conservation_area"] is None and h["state_register"] is None


def test_heritage_without_a_lot_outline_is_all_none():
    assert inp._heritage(None) == {"item": None, "conservation_area": None, "state_register": None}


def test_state_register_hit_is_reported(monkeypatch):
    fake(monkeypatch, {"MapServer/16/": feats(), "MapServer/221/": feats({"OBJECTID": 1})})
    assert inp._heritage(RING)["state_register"] is True


# ---- layers, lot outline ------------------------------------------------------------------------------
def test_layer_failure_is_none_not_false(monkeypatch):
    fake(monkeypatch, {"MapServer/776/": None})
    assert inp._layer("exclusion", LAT, LNG, RING) == {"point": None, "lot": None}


def test_layer_hit_and_clear(monkeypatch):
    fake(monkeypatch, {"MapServer/776/": feats({"OBJECTID": 1})})
    assert inp._layer("exclusion", LAT, LNG, RING) == {"point": True, "lot": True}
    fake(monkeypatch, {"MapServer/776/": feats()})
    assert inp._layer("exclusion", LAT, LNG, RING) == {"point": False, "lot": False}


def test_layer_without_outline_has_no_lot_answer(monkeypatch):
    fake(monkeypatch, {"MapServer/776/": feats()})
    assert inp._layer("exclusion", LAT, LNG, None) == {"point": False, "lot": None}


def lot_resp(*rings):
    return {"features": [{"attributes": {}, "geometry": {"rings": [r]}} for r in rings]}


def test_lot_must_contain_the_point_and_smallest_wins(monkeypatch):
    big = [[LNG - 0.01, LAT - 0.01], [LNG + 0.01, LAT - 0.01], [LNG + 0.01, LAT + 0.01], [LNG - 0.01, LAT + 0.01], [LNG - 0.01, LAT - 0.01]]
    small = [[LNG - 0.0001, LAT - 0.0001], [LNG + 0.0001, LAT - 0.0001], [LNG + 0.0001, LAT + 0.0001], [LNG - 0.0001, LAT + 0.0001], [LNG - 0.0001, LAT - 0.0001]]
    elsewhere = [[LNG + 0.05, LAT], [LNG + 0.051, LAT], [LNG + 0.051, LAT + 0.001], [LNG + 0.05, LAT + 0.001], [LNG + 0.05, LAT]]
    fake(monkeypatch, {"NSW_Property": lot_resp(big, small), "NSW_Cadastre": None})
    assert inp.fetch_lot_rings(LAT, LNG) == small
    fake(monkeypatch, {"NSW_Property": lot_resp(elsewhere), "NSW_Cadastre": lot_resp(elsewhere)})
    assert inp.fetch_lot_rings(LAT, LNG) is None  # a neighbour's outline is never used
    fake(monkeypatch, {"NSW_Property": None, "NSW_Cadastre": None})
    assert inp.fetch_lot_rings(LAT, LNG) is None


def test_lot_falls_back_to_the_cadastre_when_the_property_layer_fails(monkeypatch):
    small = [[LNG - 0.0001, LAT - 0.0001], [LNG + 0.0001, LAT - 0.0001], [LNG + 0.0001, LAT + 0.0001], [LNG - 0.0001, LAT + 0.0001], [LNG - 0.0001, LAT - 0.0001]]
    fake(monkeypatch, {"NSW_Property": None, "NSW_Cadastre": lot_resp(small)})
    assert inp.fetch_lot_rings(LAT, LNG) == small


def test_lga_failure_and_blank_are_none(monkeypatch):
    fake(monkeypatch, {"FeatureServer/8": None})
    assert inp._lga(LAT, LNG) is None
    fake(monkeypatch, {"FeatureServer/8": feats({"lganame": "  "})})
    assert inp._lga(LAT, LNG) is None
    fake(monkeypatch, {"FeatureServer/8": feats({"lganame": "INNER WEST"})})
    assert inp._lga(LAT, LNG) == "INNER WEST"


# ---- gather -------------------------------------------------------------------------------------------
def stations_doc(near_name="Ashfield station"):
    fac = dec.LawFacts.load()
    out = []
    for nm in fac.names("schedule_11_stations") + fac.names("schedule_12_stations"):
        near = nm == near_name
        out.append({"name": nm, "lat": LAT + (0.003 if near else 3.0), "lon": LNG, "entrances": [], "no_mapped_entrance": True})
    return {"stations": out}


def quiet(monkeypatch):
    fake(monkeypatch, {"FeatureServer/8": feats({"lganame": "INNER WEST"})})
    monkeypatch.setattr(inp, "town_centre_polygons", lambda *a, **k: [])


def test_no_lot_outline_means_no_distances(monkeypatch):
    quiet(monkeypatch)
    monkeypatch.setattr(inp, "fetch_lot_rings", lambda *a: None)
    m = inp.gather(LAT, LNG, stations=stations_doc())
    assert m["straight_m"] is None and m["walk"] is None
    assert dec.decide(m)["lmr"]["answer"] != "yes"


def test_station_file_missing_a_listed_station_blocks_distances(monkeypatch):
    quiet(monkeypatch)
    doc = stations_doc()
    doc["stations"].pop()
    m = inp.gather(LAT, LNG, rings=RING, stations=doc)
    assert m["straight_m"] is None and "lacks" in m["distance_note"]


def test_area_check_never_raises_and_never_yes_on_failure(monkeypatch):
    monkeypatch.setattr(inp, "gather", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    r = inp.area_check(LAT, LNG)
    assert r["lmr"]["answer"] == "cant_tell" and "boom" in r["lmr"]["detail"]


def test_projection_dependent_tests_pass_in_a_clean_interpreter():
    """tests/conftest_mocks.py replaces pyproj with a stub whose transform returns (0, 0), so geometry tests cannot run in
    this process. They live in tests/test_lmr_area_gather.py and run here in a child pytest that skips the stubs."""
    repo = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-m", "pytest", "--noconftest", "-q", "-p", "no:cacheprovider",
                        "tests/test_lmr_area_gather.py"], cwd=repo, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]


# ---- flood and coastal measurements -----------------------------------------------------------------
NEW_LAYER_KEYS = ("georges_catchment", "hn_catchment", "coastal_vuln", "coastal_wetlands", "littoral")


def test_fetch_layers_measures_the_five_new_maps_on_the_lot_outline(monkeypatch):
    fake(monkeypatch, {"FeatureServer/8": feats({"lganame": "LIVERPOOL"})})
    out = inp.fetch_layers(LAT, LNG, RING)
    for k in NEW_LAYER_KEYS:
        assert out[k] == {"point": False, "lot": False}, k
    assert out["lga"] == "LIVERPOOL"


def test_each_new_map_uses_its_own_layer_and_a_failure_is_none(monkeypatch):
    seen = []

    def _get(url, params, post=False):
        seen.append(url)
        return None if "MapServer/251/" in url else feats()
    monkeypatch.setattr(inp, "_get_json", _get)
    out = inp.fetch_layers(LAT, LNG, RING)
    assert out["coastal_vuln"] == {"point": None, "lot": None}                  # failed -> None, never False
    assert out["coastal_wetlands"] == {"point": False, "lot": False}
    for frag in ("MapServer/147/", "MapServer/157/", "MapServer/251/", "CoastalManagementSEPP/CoastalManagementSEPP/MapServer/1/",
                 "CoastalManagementSEPP/CoastalManagementSEPP/MapServer/3/"):
        assert any(frag in u for u in seen), frag


def test_flood_function_is_called_only_for_a_council_s164g_names(monkeypatch):
    calls = []

    def flood(wkt):
        calls.append(wkt)
        return {"value": False, "reason": "covered council, whole lot clear"}
    assert inp._flood_answer("Inner West", RING, flood) is None and calls == []            # not named: never asked
    assert inp._flood_answer(None, RING, flood) is None and calls == []                    # council unknown: never asked
    r = inp._flood_answer("CITY OF NEWCASTLE", RING, flood)
    assert r["value"] is False and len(calls) == 1 and calls[0].startswith("POLYGON((")
    assert inp._flood_answer("Newcastle", None, flood)["value"] is False and calls[1] is None   # no outline: the point answer, WKT None


def test_flood_function_failures_and_odd_answers_are_unknown_never_clear():
    assert inp._flood_answer("Newcastle", RING, lambda w: {"value": None})["value"] is None
    assert inp._flood_answer("Newcastle", RING, lambda w: {"value": "no"})["value"] is None      # a string is not a bool
    assert inp._flood_answer("Newcastle", RING, lambda w: None)["value"] is None

    def boom(w):
        raise RuntimeError("database down")
    r = inp._flood_answer("Newcastle", RING, boom)
    assert r["value"] is None and "failed" in r["reason"]


def test_a_newcastle_lot_is_a_yes_only_when_flood_says_clear():
    lay = {"tod_map": CLEAR_L, "accelerated": CLEAR_L, "exclusion": CLEAR_L, "bushfire": CLEAR_L, "lga": "CITY OF NEWCASTLE",
           "heritage": {"item": False, "conservation_area": False, "state_register": False},
           **{k: CLEAR_L for k in NEW_LAYER_KEYS}}
    base = {**lay, "sched12_straight_m": 5000.0, "straight_m": 300.0, "walk": {"m": 200.0, "anchor": "A", "entrance_id": "e", "valid": True}}
    assert dec.decide({**base, "flood_planning": {"value": False}})["lmr"]["answer"] == "yes"
    assert dec.decide({**base, "flood_planning": {"value": True}})["lmr"]["answer"] == "no"
    assert dec.decide({**base, "flood_planning": {"value": None}})["lmr"]["answer"] == "cant_tell"
    assert dec.decide(base)["lmr"]["answer"] == "cant_tell"                                        # never supplied
    assert {x["para"] for x in dec.decide({**base, "flood_planning": {"value": False}})["not_checked"]} == {"h", "i"}


CLEAR_L = {"point": False, "lot": False}
