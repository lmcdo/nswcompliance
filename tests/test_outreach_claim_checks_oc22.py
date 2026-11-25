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


def test_oc22_is_declared_true_only_when_a_record_exists():
    """A claim declared true needs a record. The reverse is NOT required: a record can sit in the repo and the claim still be declared false when
    the record is stale (its data fingerprint no longer matches, 2026-11-22) or a fresh run failed. The ledger (scripts/dq_check.py) enforces the other
    direction: a row declared false whose check passes reads contradicted, so a forgotten flip back to true is caught there."""
    d = json.loads((ROOT / ".claude" / "dq_checks.json").read_text(encoding="utf-8"))["checks"]["OC-22"]
    assert d["blocks_outreach"] is True
    if d["declared"] == "true":
        assert (ROOT / "data" / "lmr_area_accuracy.json").is_file()


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


# ---- OC-22 rewritten 2026-11-24: the claim is the scope (10 pilot councils answer, others say not checked), checked by walk_scope_is_the_pilot.
PILOT_KEYS = ["penrith", "wollongong", "waverley", "ku_ring_gai", "inner_west", "blacktown", "northern_beaches", "georges_river", "parramatta", "hornsby"]
PILOT_BRIEF = ["penrith", "wollongong", "waverley", "ku_ring_gai", "ashfield", "blacktown", "northern_beaches", "georges_river", "parramatta", "hornsby"]


def scope_run(tmp_path, scope=PILOT_KEYS, brief=PILOT_BRIEF, image="COPY data/lmr_walk_scope.json ./data/lmr_walk_scope.json\n", scope_text=None):
    sp, bp, dp = tmp_path / "scope.json", tmp_path / "brief.json", tmp_path / "Dockerfile.python"
    sp.write_text(scope_text if scope_text is not None else json.dumps({"councils": scope}), encoding="utf-8")
    bp.write_text(json.dumps({"councils": brief}), encoding="utf-8")
    if image is not None:
        dp.write_text(image, encoding="utf-8")
    return occ.walk_scope_is_the_pilot(sp, bp, dp)


def test_scope_equal_to_the_pilot_list_with_the_image_line_holds(tmp_path):
    assert scope_run(tmp_path)[0] == occ.PASS


def test_a_council_in_scope_but_not_in_the_pilot_fails_and_is_named(tmp_path):
    r = scope_run(tmp_path, scope=PILOT_KEYS + ["mosman"])
    assert r[0] == occ.FAIL and "mosman" in r[1]


def test_a_pilot_council_missing_from_scope_fails_and_is_named(tmp_path):
    r = scope_run(tmp_path, scope=PILOT_KEYS[:-1])
    assert r[0] == occ.FAIL and "hornsby" in r[1]


def test_ashfield_in_the_pilot_list_is_matched_by_inner_west_in_scope(tmp_path):
    assert scope_run(tmp_path, scope=[k for k in PILOT_KEYS if k != "inner_west"] + ["ashfield"])[0] == occ.FAIL


def test_the_image_must_copy_the_scope_file(tmp_path):
    r = scope_run(tmp_path, image="COPY data/lmr_walk/ ./data/lmr_walk/\n")
    assert r[0] == occ.FAIL and "Dockerfile.python" in r[1]


def test_unreadable_missing_or_empty_inputs_fail_never_pass(tmp_path):
    assert scope_run(tmp_path, scope_text="{not json")[0] == occ.FAIL
    assert scope_run(tmp_path, scope=[])[0] == occ.FAIL
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    assert scope_run(fresh, image=None)[0] == occ.FAIL   # no Dockerfile in this folder


def test_the_real_files_hold_today():
    assert occ.walk_scope_is_the_pilot()[0] == occ.PASS
