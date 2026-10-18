"""The rules-per-address alarm must go red on each way an answer can go wrong, and stay green when nothing moved."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "rules_per_address", Path(__file__).resolve().parents[1] / "scripts" / "address_audit" / "rules_per_address.py")
rpa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rpa)


def _row(layer_council="parramatta", chapter="ch1", precinct="p1"):
    return {"source_council": layer_council, "source_chapter_key": chapter, "v2_precinct_id": precinct}


def _response(generic=100, precinct=0, chapter="ch1", council="parramatta", precinct_key="p1"):
    return {"data": {"by_layer": [
        {"layer": "generic", "provisions": [_row(council, chapter) for _ in range(generic)]},
        {"layer": "precinct", "provisions": [_row(council, chapter, precinct_key) for _ in range(precinct)]},
    ]}}


def _entry(**kw):
    return {"key": "x", "baseline": rpa.shape(_response(**kw))}


def test_unchanged_answer_is_inside_the_box():
    assert rpa.judge(_entry(), rpa.shape(_response())) == []


def test_small_drift_is_tolerated():
    assert rpa.judge(_entry(generic=100), rpa.shape(_response(generic=104))) == []


def test_widening_is_red():
    found = rpa.judge(_entry(generic=100), rpa.shape(_response(generic=130)))
    assert any("widened 100 -> 130" in f for f in found)


def test_shrinking_is_red():
    found = rpa.judge(_entry(generic=100), rpa.shape(_response(generic=40)))
    assert any("shrank" in f for f in found)


def test_zero_rules_is_red_without_a_stated_reason():
    found = rpa.judge({"key": "x", "baseline": None}, rpa.shape(_response(generic=0)))
    assert any("served 0 rules" in f for f in found)


def test_zero_rules_with_a_stated_reason_is_not_red_for_being_empty():
    entry = {"key": "x", "expected_empty": "page says why", "baseline": rpa.shape(_response(generic=0))}
    assert rpa.judge(entry, rpa.shape(_response(generic=0))) == []


def test_precinct_rule_without_a_key_is_red():
    found = rpa.judge(_entry(precinct=3), rpa.shape(_response(precinct=3, precinct_key=None)))
    assert any("no precinct key" in f for f in found)


def test_new_council_is_red():
    entry = _entry()
    now = rpa.shape(_response())
    now["councils"].append("woollahra")
    assert any("council it never had: woollahra" in f for f in rpa.judge(entry, now))


def test_new_chapter_is_red_even_when_the_count_holds():
    found = rpa.judge(_entry(chapter="ch1"), rpa.shape(_response(chapter="local-centres")))
    assert any("chapter(s) it never had: local-centres" in f for f in found)


def test_missing_baseline_is_red():
    assert any("no accepted baseline" in f for f in rpa.judge({"key": "x"}, rpa.shape(_response())))


def test_committed_panel_has_a_baseline_for_every_address():
    import json
    panel = json.loads(rpa.PANEL.read_text(encoding="utf-8"))
    assert len(panel["addresses"]) >= 20
    assert all(e.get("baseline") for e in panel["addresses"])
    assert panel["history"][-1]["reason"]
