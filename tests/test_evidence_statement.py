"""Evidence statement: shaping of the area check into the evidence structure. Fake area-check dicts, no network."""
from __future__ import annotations

import pytest

from services import evidence_council as ec
from services import evidence_statement as es
from services import lmr_area_decision as d

FACTS = d.LawFacts.load()
LIVE_PARAS = ["a", "b", "c", "d", "e", "f", "f1", "g", "h", "i", "k", "l", "m"]


def _lot(**over):
    m = {"lga": "Penrith", "tod_map": {"point": False, "lot": False}, "accelerated": {"point": False, "lot": False},
         "exclusion": {"point": False, "lot": False}, "bushfire": {"point": False, "lot": False},
         "heritage": {"item": False}, "sched12_straight_m": 99999.0, "straight_m": 300.0}  # noqa: regulatory-number -- test fixture
    m.update(over)
    return m


def test_thirteen_live_paragraphs_in_law_order_j_absent():
    rows = es.exclusions(d.decide(_lot(), FACTS), FACTS)
    assert [r["para"] for r in rows] == LIVE_PARAS
    assert all(r["law_words"] and r["clause"] and r["page"] for r in rows)


def test_results_come_from_the_rules_and_unchecked_paragraphs_say_so():
    rows = {r["para"]: r for r in es.exclusions(d.decide(_lot(), FACTS), FACTS)}
    assert rows["a"]["result"] == "clear" and rows["a"]["source_checked"]
    assert rows["i"]["result"] == "not_checked"
    assert rows["h"]["result"] == "not_checked"


def test_exclusion_is_shown_not_hidden():
    rows = {r["para"]: r for r in es.exclusions(d.decide(_lot(bushfire={"point": True, "lot": True}), FACTS), FACTS)}
    assert rows["a"]["result"] == "excludes"


def test_unanswered_layer_is_unknown_never_clear():
    m = _lot()
    del m["bushfire"]["point"]
    m["bushfire"] = {"point": None, "lot": None}
    rows = {r["para"]: r for r in es.exclusions(d.decide(m, FACTS), FACTS)}
    assert rows["a"]["result"] == "unknown"


def test_failed_area_check_gives_rows_not_a_crash():
    rows = es.exclusions(d._failed("x"), FACTS)
    assert [r["para"] for r in rows] == LIVE_PARAS
    assert all(r["result"] == "not_checked" for r in rows)


def test_walk_missing_stays_none():
    w = es.walk({})
    assert w["walk_low_m"] is None and w["limit_m"] is None


def test_build_carries_sources_with_status():
    out = es.build(d.decide(_lot(), FACTS), {"status": "none"}, {"status": "unreadable"}, FACTS)
    assert out["council_controls"]["status"] == "none" and out["council_files"]["status"] == "unreadable"
    assert out["lga"] == "Penrith" and len(out["exclusions"]) == 13


class _Conn:
    def __init__(self, rows):
        self.rows = rows
    def cursor(self):
        return self
    def execute(self, *a):
        pass
    def fetchall(self):
        return self.rows
    def close(self):
        pass


def test_controls_unknown_council_is_unreadable_not_empty():
    assert ec.council_controls(None)["status"] == "unreadable"


def test_controls_db_down_is_unreadable_not_none():
    def boom():
        raise RuntimeError("down")
    assert ec.council_controls("Penrith", connect=boom)["status"] == "unreadable"
    assert ec.council_controls("Penrith", connect=lambda: None)["status"] == "unreadable"


def test_controls_rows_shaped_with_words_clause_page():
    from decimal import Decimal
    row = ("landscaping_min", "dwelling_house", Decimal("40"), None, "%", None, None, "words", "2.8", 32, "ch", "v1", None)
    out = ec.council_controls("Penrith", connect=lambda: _Conn([row]))
    assert out["status"] == "ok" and out["controls"][0]["council_words"] == "words" and out["controls"][0]["page"] == 32


def test_files_earlier_version_has_no_council_date():
    import datetime as dt
    t1, t2 = dt.datetime(2026, 10, 26), dt.datetime(2026, 4, 27)
    rows = [("c", "v1.2", t1, None, "Tue, 29 Sep 2026", "http://u"), ("c", "v1.1", t2, t1, "Tue, 29 Sep 2026", "http://u")]
    f = ec.council_files("Penrith", connect=lambda: _Conn(rows))["files"]
    assert f[0]["council_file_date"] == "Tue, 29 Sep 2026" and f[1]["council_file_date"] is None
    assert f[1]["council_file_date_note"] == "not kept for earlier versions"


@pytest.mark.database
def test_penrith_two_hand_avenue_real_db_controls_and_files():
    c = ec.council_controls("Penrith")
    f = ec.council_files("Penrith")
    assert c["status"] in ("ok", "none", "unreadable") and f["status"] in ("ok", "none", "unreadable")
