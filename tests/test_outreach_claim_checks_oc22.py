"""OC-22 (the housing reform area card): the claim holds only on a recorded, passing, current accuracy run, and it can fail.

prior-art-checked: tests for a sub-check added to scripts/outreach_claim_checks.py; the sibling files
(test_outreach_claim_checks_oc20.py, _plan_and_zone.py, _ranges_and_citations.py) cover other functions.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import outreach_claim_checks as occ  # noqa: E402

GOOD = {"lots": 100, "yes_no": 80, "yes_no_match": 77, "wrong_yes": 0, "wrong_no": 0, "borderline": 15, "cant_tell": 2,
        "range_checked": 98, "range_holds": 95, "passed": True, "data_fingerprint": "abc"}


def run(tmp_path, rec, fp="abc"):
    p = tmp_path / "acc.json"
    if rec is not None:
        p.write_text(json.dumps(rec), encoding="utf-8")
    return occ.area_check_accuracy_recorded(p, lambda: fp)


def test_a_passing_current_record_holds(tmp_path):
    assert run(tmp_path, GOOD)[0] == occ.PASS


def test_no_record_fails(tmp_path):
    verdict, why = run(tmp_path, None)
    assert verdict == occ.FAIL and "no recorded accuracy run" in why


def test_record_measured_on_other_data_fails(tmp_path):
    verdict, why = run(tmp_path, GOOD, fp="changed")
    assert verdict == occ.FAIL and "different data" in why


def test_too_few_lots_fails(tmp_path):
    assert run(tmp_path, {**GOOD, "lots": 99})[0] == occ.FAIL


def test_a_hand_edited_passed_flag_cannot_hide_bad_counts(tmp_path):
    for bad in ({"yes_no_match": 60}, {"wrong_yes": 1}, {"wrong_no": 1}, {"range_holds": 80}, {"cant_tell": 6}):
        assert run(tmp_path, {**GOOD, **bad})[0] == occ.FAIL, bad


def test_passed_false_fails_even_with_good_counts(tmp_path):
    assert run(tmp_path, {**GOOD, "passed": False})[0] == occ.FAIL


def test_unreadable_or_empty_record_fails_not_passes(tmp_path):
    p = tmp_path / "acc.json"
    p.write_text("{not json", encoding="utf-8")
    assert occ.area_check_accuracy_recorded(p, lambda: "abc")[0] == occ.FAIL
    assert run(tmp_path, {})[0] == occ.FAIL


def test_oc22_is_declared_false_until_a_record_exists():
    d = json.loads((ROOT / ".claude" / "dq_checks.json").read_text(encoding="utf-8"))["checks"]["OC-22"]
    assert d["blocks_outreach"] is True
    assert (ROOT / "data" / "lmr_area_accuracy.json").is_file() == (d["declared"] == "true")


def test_the_fingerprint_changes_when_a_walking_file_changes(tmp_path):
    sys.path.insert(0, str(ROOT))
    from services.lmr_walk_surface import data_fingerprint

    (tmp_path / "data" / "lmr_walk").mkdir(parents=True)
    (tmp_path / "data" / "law").mkdir(parents=True)
    (tmp_path / "data" / "lmr_walk" / "a.npz").write_bytes(b"one")
    (tmp_path / "data" / "law" / "lmr_station_entrances.json").write_text('{"a": 1}', encoding="utf-8")
    (tmp_path / "data" / "law" / "housing_sepp_lmr_facts.json").write_text('{"b": 2}', encoding="utf-8")
    before = data_fingerprint(tmp_path)
    assert before == data_fingerprint(tmp_path)
    (tmp_path / "data" / "lmr_walk" / "a.npz").write_bytes(b"two")
    assert data_fingerprint(tmp_path) != before
