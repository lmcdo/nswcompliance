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


def _entry(**o):
    e = {"type": "Front setback", "semantic_type": "front_setback", "dev_type": "dwelling_house", "value_min": 4.5, "value_max": None, "unit": "m", "requirement": "4.5 m",  # noqa: regulatory-number -- test fixture
         "notes": "", "applicability": None, "source_text": "words", "clause": "", "clause_unchecked": "2.8", "clause_shown": False,
         "pdf_page": 32, "source_chapter_key": "ch", "dcp_version": "v1"}
    e.update(o)
    return e


def test_controls_unknown_council_is_unreadable_not_empty():
    assert ec.council_controls(None)["status"] == "unreadable"


def test_controls_db_down_is_unreadable_not_none():
    def boom():
        raise RuntimeError("down")
    assert ec.council_controls("Penrith", connect=boom)["status"] == "unreadable"
    assert ec.council_controls("Penrith", connect=lambda: None)["status"] == "unreadable"


def test_controls_producer_failure_is_unreadable():
    def bad(conn, key):
        raise RuntimeError("query failed")
    assert ec.council_controls("Penrith", connect=lambda: _Conn([]), fetch=bad)["status"] == "unreadable"


def test_controls_none_when_producer_finds_no_rows():
    assert ec.council_controls("Penrith", connect=lambda: _Conn([]), fetch=lambda c, k: None)["status"] == "none"


def test_controls_keep_dwelling_house_only_with_words_clause_page_and_proof_flag():
    data = {"setbacks": [_entry(), _entry(dev_type="dual_occupancy")], "as_at_line": "as at x"}
    out = ec.council_controls("PENRITH", connect=lambda: _Conn([]), fetch=lambda c, k: data)
    assert out["status"] == "ok" and out["council"] == "penrith" and len(out["controls"]) == 1
    c = out["controls"][0]
    assert c["label"] == "Front setback" and c["council_words"] == "words" and c["page"] == 32 and c["clause"] == "2.8" and c["clause_shown"] is False


def test_files_earlier_version_has_no_council_date():
    import datetime as dt
    t1, t2 = dt.datetime(2026, 10, 26), dt.datetime(2026, 4, 27)
    rows = [("c", "v1.2", t1, None, "Tue, 29 Sep 2026", "http://u"), ("c", "v1.1", t2, t1, "Tue, 29 Sep 2026", "http://u")]
    f = ec.council_files("Penrith", connect=lambda: _Conn(rows))["files"]
    assert f[0]["council_file_date"] == "Tue, 29 Sep 2026" and f[1]["council_file_date"] is None
    assert f[1]["council_file_date_note"] == "not kept for earlier versions"


def test_walk_heuristic_is_not_invented_when_absent():
    assert es.walk({})["heuristic"] is None


def _walked(walk_m, safe_m, **over):
    """A lot with a measured normal walk and a crossings-only walk, run through the real decision code."""
    return d.decide(_lot(walk={"m": walk_m, "valid": True, "anchor": "Test station", "entrance_id": "e1"},  # noqa: regulatory-number -- test fixture
                         walk_safe={"m": safe_m, "valid": True, "near_busy_road": True}, **over), FACTS)  # noqa: regulatory-number -- test fixture


def test_crossings_only_walk_and_its_busy_road_note_reach_the_page_data():
    w = es.walk(_walked(600.0, 700.0))  # noqa: regulatory-number -- test fixture
    assert w["crossings_only_walk_m"] == 700  # noqa: regulatory-number -- test fixture
    assert "+100 m compared with the normal walk" in w["crossings_only_note"]
    assert "next to a busy road" in w["crossings_only_note"]


def test_crossings_only_walk_absent_stays_none_never_filled_from_the_normal_walk():
    area = d.decide(_lot(walk={"m": 600.0, "valid": True, "anchor": "Test station", "entrance_id": "e1"}), FACTS)  # noqa: regulatory-number -- test fixture
    w = es.walk(area)
    assert w["crossings_only_walk_m"] is None and w["crossings_only_note"] is None
    assert w["walk_low_m"] is not None   # the normal walk is still there


def test_an_exclusion_decides_before_any_walk_so_no_walk_line_is_invented():
    area = _walked(600.0, 700.0, bushfire={"point": True, "lot": True})  # noqa: regulatory-number -- test fixture
    w = es.walk(area)
    assert area["lmr"]["answer"] == "no"
    assert w["walk_low_m"] is None and w["crossings_only_walk_m"] is None


def test_margins_are_kept_when_the_answer_is_no_because_the_walk_is_too_long():
    w = es.walk(_walked(1500.0, 1600.0))  # noqa: regulatory-number -- test fixture
    assert w["answer"] == "no" and w["walk_low_m"] is not None
    assert w["margin_low_m"] is not None and w["margin_high_m"] is not None   # why the walk is a range, even on a 'no'
    assert w["crossings_only_walk_m"] == 1600  # noqa: regulatory-number -- test fixture


def test_summary_counts_add_up_and_the_line_names_each_result():
    rows = [{"result": "clear"}, {"result": "clear"}, {"result": "excludes"}, {"result": "not_checked"}, {"result": "something_new"}]
    s = es.summary(rows)
    assert s["total"] == 5 and sum(s["counts"].values()) == 5
    assert s["counts"]["unknown"] == 1      # an unrecognised result is never counted as clear
    assert "1 excluded" in s["line"] and "2 no exclusion found" in s["line"] and "1 not checked by this tool" in s["line"]


def test_summary_of_no_rows_has_no_line():
    assert es.summary([]) == {"total": 0, "counts": {k: 0 for k, _ in es.SUMMARY_WORDS}, "line": ""}


def test_manual_checks_are_the_rows_that_were_not_cleared():
    rows = es.exclusions(d.decide(_lot(), FACTS), FACTS)
    manual = es.manual_checks(rows)
    assert {m["clause"] for m in manual} >= {r["clause"] for r in rows if r["para"] in ("h", "i")}
    assert all(m["law_words"] for m in manual)
    assert not any(r["result"] == "clear" and r["clause"] in {m["clause"] for m in manual} for r in rows)


def test_build_carries_the_summary_and_the_manual_checks():
    out = es.build(_walked(600.0, 700.0), {"status": "none"}, {"status": "none"}, FACTS)  # noqa: regulatory-number -- test fixture
    assert out["summary"]["total"] == 13 and out["summary"]["line"]
    assert out["manual_checks"] == es.manual_checks(out["exclusions"])
    assert out["walk"]["crossings_only_walk_m"] == 700  # noqa: regulatory-number -- test fixture


def test_version_checks_are_shown_and_a_changed_quote_marks_them_stale():
    import hashlib
    sha = hashlib.sha256(b"words").hexdigest()
    data = {"setbacks": [_entry(control_id=7)]}
    rows = [(7, "v1.1", "wrong_page", sha, 32), (7, "v1.2", "verbatim", "oldhash", 32)]
    out = ec.council_controls("PENRITH", connect=lambda: _Conn([]), fetch=lambda c, k: data, version_rows=lambda ids: rows)
    v = out["controls"][0]["version_checks"]
    assert v["status"] == "ok" and [x["verdict"] for x in v["versions"]] == ["wrong_page", "verbatim"]
    assert v["versions"][0]["stale"] is False and v["versions"][1]["stale"] is True
    assert v["versions"][0]["result_words"].startswith("Same words, on a different page")


def test_a_check_for_a_different_page_than_the_control_cites_now_is_stale():
    import hashlib
    sha = hashlib.sha256(b"words").hexdigest()
    data = {"setbacks": [_entry(control_id=7, pdf_page=33)]}
    out = ec.council_controls("PENRITH", connect=lambda: _Conn([]), fetch=lambda c, k: data, version_rows=lambda ids: [(7, "v1.2", "verbatim", sha, 32)])
    assert out["controls"][0]["version_checks"]["versions"][0]["stale"] is True


def test_version_checks_unreadable_is_not_none():
    data = {"setbacks": [_entry(control_id=7)]}
    out = ec.council_controls("PENRITH", connect=lambda: _Conn([]), fetch=lambda c, k: data, version_rows=lambda ids: None)
    assert out["controls"][0]["version_checks"]["status"] == "unreadable"


def test_control_without_checks_says_none():
    data = {"setbacks": [_entry(control_id=7)]}
    out = ec.council_controls("PENRITH", connect=lambda: _Conn([]), fetch=lambda c, k: data, version_rows=lambda ids: [])
    assert out["controls"][0]["version_checks"] == {"status": "none", "versions": []}
