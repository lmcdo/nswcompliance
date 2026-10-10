"""OC-17's council list: each way the published list can disagree with the computed one must FAIL.

The check reads the database, so these feed it a fake connection with fixed rows and stub the two
machines it calls (DQ-114's SQL, probe_115). Each test forces one failure on an otherwise-passing
fixture, so a check that quietly stopped comparing would turn a test red.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

import outreach_scoped_councils as osc  # noqa: E402

EXC = {"council": "cb", "field": "applicable_dev_types", "chapters": ["ch-schools"],
       "statement": "stated"}


class _Cur:
    def __init__(self, universe, split, total, no_config=(), declined=(), lep=()):
        self._answers = [universe, split, [(total,)], list(no_config), list(declined), list(lep)]
        self._last = None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self._last = self._answers.pop(0)

    def fetchall(self):
        return self._last

    def fetchone(self):
        return self._last[0]


class _Conn:
    def __init__(self, universe, split, total, no_config=(), declined=(), lep=()):
        self.cur = _Cur(universe, split, total, no_config, declined, lep)

    def cursor(self):
        return self.cur

    def close(self):
        pass


UNIVERSE = [("aa", "Aa"), ("bb", "Bb"), ("cb", "Cb")]
#: bb has one undecided key; cb has one, covered by the stated exception.
SPLIT = [("bb", "ch-x", "applicable_zones", 2), ("cb", "ch-schools", "applicable_dev_types", 7)]


@pytest.fixture
def world(monkeypatch, tmp_path):
    state = {"universe": UNIVERSE, "split": SPLIT, "total": 9, "dq115": {}, "orphans": [], "no_config": [],
             "declined": [], "lep": []}
    monkeypatch.setattr(osc, "_dq115_by_council",
                        lambda slugs: (state["dq115"], state["orphans"]))
    import dq_db
    monkeypatch.setattr(dq_db, "connect",
                        lambda: _Conn(state["universe"], state["split"], state["total"],
                                      state["no_config"], state["declined"], state["lep"]))
    pub = tmp_path / "pub.json"
    monkeypatch.setattr(osc, "PUBLISHED", pub)

    def publish(councils, exceptions=(EXC,)):
        pub.write_text(json.dumps({"councils": [{"slug": s, "name": n} for s, n in councils],
                                   "exceptions": list(exceptions)}), encoding="utf-8")
    state["publish"] = publish
    return state


def test_matching_list_passes_and_exception_excuses_its_rows(world):
    world["publish"]([("aa", "Aa"), ("cb", "Cb")])
    verdict, text = osc.check()
    assert verdict == osc.PASS, text
    assert "bb (DQ-114 2)" in text


def test_overclaim_fails(world):
    world["publish"]([("aa", "Aa"), ("bb", "Bb"), ("cb", "Cb")])
    verdict, text = osc.check()
    assert verdict == osc.FAIL and "published but fails: bb" in text


def test_underclaim_fails(world):
    world["publish"]([("aa", "Aa")])
    verdict, text = osc.check()
    assert verdict == osc.FAIL and "passes but not published: cb" in text


def test_without_the_exception_the_council_is_delisted(world):
    world["publish"]([("aa", "Aa"), ("cb", "Cb")], exceptions=())
    verdict, text = osc.check()
    assert verdict == osc.FAIL and "published but fails: cb (DQ-114 7)" in text


def test_stale_exception_fails(world):
    world["split"] = [("bb", "ch-x", "applicable_zones", 2)]
    world["total"] = 2
    world["publish"]([("aa", "Aa"), ("cb", "Cb")])
    verdict, text = osc.check()
    assert verdict == osc.FAIL and "is stale" in text


def test_exception_whose_rows_were_DECLINED_is_not_stale(world):
    """Recording the decision moves the rows out of DQ-114; the caveat stays true and must stay."""
    world["split"] = [("bb", "ch-x", "applicable_zones", 2)]
    world["total"] = 2
    world["declined"] = [("cb", "ch-schools", "applicable_dev_types")]
    world["publish"]([("aa", "Aa"), ("cb", "Cb")])
    verdict, text = osc.check()
    assert verdict == osc.PASS, text


def test_declined_row_for_another_key_does_not_rescue_a_stale_exception(world):
    world["split"] = [("bb", "ch-x", "applicable_zones", 2)]
    world["total"] = 2
    world["declined"] = [("cb", "ch-schools", "applicable_zones")]
    world["publish"]([("aa", "Aa"), ("cb", "Cb")])
    verdict, text = osc.check()
    assert verdict == osc.FAIL and "is stale" in text


def test_split_drifting_from_dq114_fails(world):
    world["total"] = 10
    world["publish"]([("aa", "Aa"), ("cb", "Cb")])
    verdict, text = osc.check()
    assert verdict == osc.FAIL and "drifted apart" in text


def test_dq115_hit_delists_and_orphan_hit_fails(world):
    world["dq115"] = {"aa": 2}
    world["publish"]([("aa", "Aa"), ("cb", "Cb")])
    verdict, text = osc.check()
    assert verdict == osc.FAIL and "published but fails: aa (DQ-115 2)" in text
    world["dq115"] = {}
    world["orphans"] = ["warringah/parts/X"]
    verdict, text = osc.check()
    assert verdict == osc.FAIL and "warringah/parts/X" in text


def test_no_config_rows_delist_and_no_exception_reaches_them(world):
    # DQ-33 is a fleet floor, so it passes while a council serves unscoped rows. The list must not.
    world["no_config"] = [("aa", 3), ("cb", 0)]
    world["publish"]([("aa", "Aa"), ("cb", "Cb")])
    verdict, text = osc.check()
    assert verdict == osc.FAIL and "published but fails: aa (no_config 3)" in text


def test_wrong_display_name_fails(world):
    world["publish"]([("aa", "AA Council"), ("cb", "Cb")])
    verdict, text = osc.check()
    assert verdict == osc.FAIL and "is not the registry's" in text


def test_unreachable_database_is_unknown_not_pass(world, monkeypatch):
    import dq_db

    def boom():
        raise OSError("no route")
    monkeypatch.setattr(dq_db, "connect", boom)
    world["publish"]([("aa", "Aa"), ("cb", "Cb")])
    assert osc.check()[0] == osc.UNKNOWN


def test_published_file_is_well_formed():
    data = osc.load_published()
    assert data["claim"].startswith("For the councils listed")
    slugs = [c["slug"] for c in data["councils"]]
    assert slugs == sorted(set(slugs))
    for exc in data["exceptions"]:
        assert exc["chapters"] and exc["statement"] and exc["field"] in (
            "applicable_dev_types", "applicable_zones")


def test_oc4_is_the_two_counts_only_and_oc17_runs_the_list():
    import outreach_claim_checks as occ
    assert len(occ.CLAIMS["OC-4"]) == 1
    assert osc.check in occ.CLAIMS["OC-17"]


def test_undecided_lep_scope_delists_a_council_whose_dcp_rows_are_clean(world):
    # DQ-114 (and the split) leave LEP rows to DQ-140; a council whose LEP scope is undecided
    # must still not be listed (2026-10-10: the split counted 240 LEP keys DQ-114 no longer did).
    world["lep"] = [("aa", 4)]
    world["publish"]([("aa", "Aa"), ("cb", "Cb")])
    verdict, text = osc.check()
    assert verdict == "FAIL" and "aa (DQ-140 4)" in text
    world["publish"]([("cb", "Cb")])
    assert osc.check()[0] == "PASS"
