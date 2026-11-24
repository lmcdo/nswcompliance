"""The walking-distance check answers yes/no only in the pilot councils (data/lmr_walk_scope.json); everywhere else it says not checked."""
import json
from pathlib import Path

import pytest

from services import evidence_statement as es
from services import lmr_area_decision as d
from services.council_key import to_council_key

FACTS = d.LawFacts.load()
REPO = Path(__file__).resolve().parents[1]
PILOT = {"penrith", "wollongong", "waverley", "ku_ring_gai", "inner_west", "blacktown", "northern_beaches", "georges_river", "parramatta", "hornsby"}
NOT_CHECKED = "walk_not_checked_in_this_council"


def _lot(lga, **over):
    m = {"lga": lga, "tod_map": {"point": False, "lot": False}, "accelerated": {"point": False, "lot": False},
         "exclusion": {"point": False, "lot": False}, "bushfire": {"point": False, "lot": False},
         "heritage": {"item": False, "conservation_area": False, "state_register": False},
         "sched12_straight_m": 99999.0, "straight_m": 300.0,
         "walk": {"m": 450.0, "anchor": "Test station", "entrance_id": "e1", "valid": True}}
    m.update(over)
    return m


def _step(lga, **over):
    return d._distance_step(_lot(lga, **over), FACTS)


def test_scope_file_has_exactly_the_ten_pilot_keys_and_each_round_trips():
    doc = json.loads((REPO / "data" / "lmr_walk_scope.json").read_text(encoding="utf-8"))
    names = doc["councils"]
    assert len(names) == 10 and set(names) == PILOT
    for n in names:
        assert to_council_key(n) == n
    assert d.walk_scope() == frozenset(d.norm_lga(n) for n in PILOT)
    assert len(d.walk_scope()) == 10


def test_scope_file_is_valid_json_with_as_of():
    doc = json.loads((REPO / "data" / "lmr_walk_scope.json").read_text(encoding="utf-8"))
    assert isinstance(doc, dict) and isinstance(doc.get("as_of"), str) and len(doc["as_of"]) == 10


def test_dockerfile_copies_the_scope_file():
    text = (REPO / "Dockerfile.python").read_text(encoding="utf-8")
    assert "COPY data/lmr_walk_scope.json ./data/lmr_walk_scope.json" in text


@pytest.mark.parametrize("lga", ["Mosman", "Canterbury-Bankstown", "Woollahra"])
def test_a_council_outside_the_pilot_is_cant_tell_never_a_yes(lga):
    ans, det = _step(lga)
    assert ans == d.CANT
    assert det["reason_code"] == NOT_CHECKED
    assert "is not one of the councils the walking check covers" in det["detail"]
    assert "walk_best_m" not in det and "walk_m" not in det


@pytest.mark.parametrize("lga", [None, "", "   ", 7])
def test_a_missing_or_odd_council_is_cant_tell(lga):
    ans, det = _step(lga)
    assert ans == d.CANT and det["reason_code"] == NOT_CHECKED
    assert "did not answer" in det["detail"]


def test_a_lot_with_no_lga_key_at_all_is_cant_tell():
    m = _lot("Penrith")
    del m["lga"]
    ans, det = d._distance_step(m, FACTS)
    assert ans == d.CANT and "did not answer" in det["detail"]


@pytest.mark.parametrize("lga", ["KU-RING-GAI", "CITY OF PARRAMATTA", "Inner West", "penrith", "Northern Beaches", "Georges River", "Hornsby Shire"])
def test_case_and_spelling_variants_in_the_pilot_answer_normally(lga):
    # a 450 m walk answers yes, a 1500 m walk answers no: a constant CANT would fail both
    assert _step(lga)[0] == d.YES
    assert _step(lga, walk={"m": 1500.0, "anchor": "T", "entrance_id": "e", "valid": True})[0] == d.NO


def test_pilot_council_walk_is_read_not_constant():
    yes, no = _step("Penrith")[1], _step("Penrith", walk={"m": 1500.0, "anchor": "T", "entrance_id": "e", "valid": True})[1]
    assert yes["walk_best_m"] == 450 and no["walk_best_m"] == 1500


def test_straight_line_over_the_limit_is_no_even_outside_the_pilot():
    ans, det = _step("Mosman", straight_m=5000.0)
    assert ans == d.NO and det["reason_code"] == "beyond_straight_line"
    ans, det = _step(None, straight_m=5000.0)
    assert ans == d.NO and det["reason_code"] == "beyond_straight_line"


def test_missing_straight_line_is_still_reported_as_that_not_as_scope():
    assert _step("Mosman", straight_m=None)[1]["reason_code"] == "no_straight_distance"


@pytest.mark.parametrize("content", ["{not json", "[]", "{}", '{"councils": []}', '{"councils": [1, 2]}', '{"councils": ["penrith", 5]}', '{"councils": "penrith"}', ""])
def test_a_bad_scope_file_makes_every_lot_cant_tell(tmp_path, monkeypatch, content):
    bad = tmp_path / "scope.json"
    bad.write_text(content, encoding="utf-8")
    assert d.walk_scope(bad) is None
    monkeypatch.setattr(d, "WALK_SCOPE_PATH", bad)
    monkeypatch.setattr(d, "walk_scope", lambda path=bad: d.__dict__["_orig_walk_scope"](path))  # noqa: placeholder replaced below


def test_the_council_name_variants_the_portal_uses_all_match():
    """The comparison is norm_lga, which drops City, Shire and Council, so the portal's own spellings are covered."""
    for name in ("Hornsby Shire", "HORNSBY", "Penrith City Council", "City of Wollongong", "Waverley Council", "Georges River Council",
                 "Northern Beaches Council", "Ku-ring-gai Council", "Inner West Council", "Blacktown City", "City of Parramatta"):
        step = d._distance_step({"straight_m": 300.0, "lga": name, "walk": {"valid": True, "m": 400.0, "anchor": "X", "entrance_id": "e"}}, FACTS)
        assert step[0] == "yes", name
    for name in ("Mosman Council", "City of Canterbury-Bankstown", "Woollahra Municipal Council", "Hawkesbury City Council"):
        step = d._distance_step({"straight_m": 300.0, "lga": name, "walk": {"valid": True, "m": 400.0, "anchor": "X", "entrance_id": "e"}}, FACTS)
        assert step[0] == "cant_tell" and step[1]["reason_code"] == "walk_not_checked_in_this_council", name
