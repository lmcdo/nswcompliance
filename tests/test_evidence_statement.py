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


def test_walk_figures_are_kept_and_margins_are_gone_when_the_answer_is_no_because_the_walk_is_too_long():
    w = es.walk(_walked(1500.0, 1600.0))  # noqa: regulatory-number -- test fixture
    assert w["answer"] == "no" and w["walk_low_m"] is not None
    assert "margin_low_m" not in w and "margin_high_m" not in w   # the fitted margins no longer exist
    assert w["walk_low_m"] == w["walk_high_m"] == w["walk_best_m"] == 1500   # mapped entrance: the walk is one number, even on a 'no'
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


def test_a_result_word_the_page_does_not_know_is_counted_unknown_and_also_listed_for_a_hand_check():
    rows = [{"result": "clear", "clause": "s164(1)(a)"}, {"result": "needs_review", "clause": "s164(1)(b)"}, {"result": "excludes", "clause": "s164(1)(c)"}]
    assert es.summary(rows)["counts"]["unknown"] == 1
    assert [m["clause"] for m in es.manual_checks(rows)] == ["s164(1)(b)"]   # the count and the list agree


def test_the_count_line_does_not_say_looked_at_and_not_checked_in_one_breath():
    line = es.summary([{"result": "clear"}, {"result": "not_checked"}])["line"]
    assert "looked at" not in line and "1 not checked by this tool" in line and "1 no exclusion found" in line


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


# --- road rules shown beside the crossings-only walk: word for word from the saved text, or unreadable ---

def _road_rules_doc():
    import json
    return json.loads(es.ROAD_RULES_PATH.read_text(encoding="utf-8"))


def test_road_rule_fingerprint_matches_the_repo_fingerprint_function_and_every_quote_is_word_for_word():
    import sys
    sys.path.insert(0, str(es.REPO_ROOT / "scripts"))
    import extract_lmr_law_facts as law
    doc = _road_rules_doc()
    text = (es.REPO_ROOT / doc["text_file"]).read_text(encoding="utf-8")
    assert doc["text_sha256"] == law.text_sha256(text)
    assert doc["text_sha256"] == law.text_sha256(text.replace("\n", "\r\n"))     # a Windows checkout does not change it
    for key, f in doc["facts"].items():
        assert f["quote"] in law.normalise(text), key
        assert f["source_url"].startswith("https://www5.austlii.edu.au/au/legis/nsw/consol_reg/rr2014104/s"), key


def test_road_rules_load_with_clause_heading_quote_and_source():
    out = es.road_rules()
    assert out["status"] == "ok" and [r["clause"] for r in out["rules"]] == ["reg 231(2)", "reg 232(2)", "reg 234(1)", "reg 234(4)"]
    r234 = {r["clause"]: r for r in out["rules"]}["reg 234(1)"]
    assert r234["quote"].startswith("(1) A pedestrian must not cross a road") and "\n(e) " in r234["quote"]   # the whole subrule, with its exceptions
    assert all(r["heading"] and r["source_url"] for r in out["rules"])


def test_an_altered_quote_is_unreadable_never_shown(tmp_path):
    import json
    doc = _road_rules_doc()
    doc["facts"]["reg_234_1"]["quote"] = doc["facts"]["reg_234_1"]["quote"].replace("must not cross", "may cross")
    p = tmp_path / "facts.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    out = es.road_rules(p)
    assert out["status"] == "unreadable" and "reg 234(1)" in out["reason"] and "rules" not in out


def test_changed_saved_text_no_longer_matches_its_fingerprint(tmp_path):
    import json
    doc = _road_rules_doc()
    text = (es.REPO_ROOT / doc["text_file"]).read_text(encoding="utf-8").replace("must not start to cross", "may start to cross")
    (tmp_path / "t.txt").write_text(text, encoding="utf-8")
    doc["text_file"] = "t.txt"
    p = tmp_path / "facts.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    out = es.road_rules(p, repo=tmp_path)
    assert out["status"] == "unreadable" and "fingerprint" in out["reason"]


def test_missing_or_broken_road_rules_file_is_unreadable_not_a_crash(tmp_path):
    assert es.road_rules(tmp_path / "nope.json")["status"] == "unreadable"
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert es.road_rules(bad)["status"] == "unreadable"


def test_build_carries_the_road_rules():
    out = es.build(d.decide(_lot(), FACTS), {"status": "none"}, {"status": "none"}, FACTS)
    assert out["road_rules"]["status"] == "ok" and len(out["road_rules"]["rules"]) == 4


def test_a_quote_filed_under_the_wrong_regulation_is_unreadable(tmp_path):
    import json
    doc = _road_rules_doc()
    doc["facts"]["reg_231_2"]["quote"] = doc["facts"]["reg_232_2"]["quote"]     # the reg 232 words, labelled reg 231(2); the text and its fingerprint are unchanged
    p = tmp_path / "facts.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    out = es.road_rules(p)
    assert out["status"] == "unreadable" and "reg 231(2)" in out["reason"]


def test_a_clause_that_names_no_regulation_is_unreadable(tmp_path):
    import json
    doc = _road_rules_doc()
    doc["facts"]["reg_231_2"]["clause"] = "subrule (2)"
    p = tmp_path / "facts.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert es.road_rules(p)["status"] == "unreadable"


def test_valid_json_of_the_wrong_kind_is_unreadable_not_a_server_error(tmp_path):
    for body in ("[]", '{"facts": [1]}', '{"facts": {"a": 1}}', '"text"', "null", '{"facts": {"a": {"quote": 5}}}'):
        p = tmp_path / "facts.json"
        p.write_text(body, encoding="utf-8")
        assert es.road_rules(p)["status"] == "unreadable", body


def test_a_quote_filed_under_the_wrong_subrule_of_the_right_regulation_is_unreadable(tmp_path):
    import json
    doc = _road_rules_doc()
    doc["facts"]["reg_234_4"]["clause"] = "reg 234(1)"       # the definition of 'crossing', labelled as subrule (1); both are in reg 234
    p = tmp_path / "facts.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    out = es.road_rules(p)
    assert out["status"] == "unreadable" and "subrule" in out["reason"]


def test_a_source_address_for_another_regulation_is_unreadable(tmp_path):
    import json
    doc = _road_rules_doc()
    doc["facts"]["reg_231_2"]["source_url"] = doc["facts"]["reg_232_2"]["source_url"]       # the reg 232 page cited for reg 231(2)
    p = tmp_path / "facts.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    out = es.road_rules(p)
    assert out["status"] == "unreadable" and "source address" in out["reason"] and "reg 231(2)" in out["reason"]


def test_a_clause_without_its_subrule_is_unreadable(tmp_path):
    import json
    doc = _road_rules_doc()
    doc["facts"]["reg_234_1"]["clause"] = "reg 234"
    p = tmp_path / "facts.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert es.road_rules(p)["status"] == "unreadable"


# ---- flood-study and pipeline facts on the exclusion rows (distances for the page; nothing computed in evidence_statement)
def _flood_lot(inside=False, edge_m=9855.7, nearest_m=9855.7, **over):
    pmf = {"inside": inside, "edge_m": edge_m, "nearest_m": nearest_m, "within_box": True, "used_outline": True, "as_of": "2026-11-22", "polygons": 5}
    m = _lot(hn_catchment={"point": True, "lot": True}, flood_study={"pmf": pmf, "aep500": {**pmf, "nearest_m": 10217.7}, "aep100": {**pmf, "nearest_m": 10246.9}},
             pipeline={"hit": False, "names": [], "nearest_m": 23916, "nearest_name": "Sydney to Newcastle Pipeline"})
    m.update(over)
    return d.decide(m, FACTS)


def test_flood_row_carries_the_rules_figures_and_the_two_frequency_distances():
    rows = {r["para"]: r for r in es.exclusions(_flood_lot(), FACTS)}
    f = rows["f"]
    assert f["result"] == "clear" and f["facts"]["flood_state"] == "outside" and f["facts"]["nearest_m"] == 9855.7
    assert f["facts"]["margin_m"] == d.FLOOD_EDGE_M and f["facts"]["copy_as_of"] == "2026-11-22"
    assert f["facts"]["nearest_500_year_m"] == 10217.7 and f["facts"]["nearest_100_year_m"] == 10246.9


def test_flood_row_inside_is_a_warning_with_its_state_never_clear():
    f = {r["para"]: r for r in es.exclusions(_flood_lot(inside=True, edge_m=300.0, nearest_m=0.0), FACTS)}["f"]
    assert f["result"] == "warn" and f["facts"]["flood_state"] == "inside" and f["facts"]["inside"] is True


def test_flood_row_without_the_flood_copy_has_no_facts_and_the_older_rule_applies():
    m = _lot(hn_catchment={"point": True, "lot": True})
    f = {r["para"]: r for r in es.exclusions(d.decide(m, FACTS), FACTS)}["f"]
    assert f["result"] == "warn" and "facts" not in f


def test_pipeline_row_carries_the_nearest_distance_the_law_distance_and_the_named_gap_but_is_never_cleared():
    i = {r["para"]: r for r in es.exclusions(_flood_lot(), FACTS)}["i"]
    assert i["result"] == "not_checked"          # a gas map miss clears nothing: fuel pipelines and the law's licence list are not on it
    assert i["facts"]["nearest_m"] == 23916 and i["facts"]["nearest_name"] == "Sydney to Newcastle Pipeline"
    assert i["facts"]["limit_m"] == FACTS.number("s164_i_distance") and i["facts"]["hit"] is False
    gap = i["facts"]["gap"]
    assert gap["named_in_law"] == 33 and gap["no_route_count"] == 13 and gap["verified"] is False and 42 in gap["licences"] and gap["other"] == "Clyde to Gore Bay"


def test_pipeline_row_has_no_facts_when_the_pipeline_was_not_measured():
    m = _lot()
    assert "facts" not in {r["para"]: r for r in es.exclusions(d.decide(m, FACTS), FACTS)}["i"]


def _cov(tmp_path, doc):
    import json
    p = tmp_path / "cov.json"
    p.write_text(json.dumps(doc) if not isinstance(doc, str) else doc, encoding="utf-8")
    return p


_GOOD_COV = {"checked_on": "2026-11-22", "named_in_law": 33, "licences_with_no_published_route": [1, 3], "other_named_pipeline_with_no_published_route": "Clyde to Gore Bay"}


def test_pipeline_coverage_reads_a_good_file(tmp_path):
    got = es.pipeline_coverage(_cov(tmp_path, _GOOD_COV))
    assert got == {"licences": [1, 3], "other": "Clyde to Gore Bay", "named_in_law": 33, "no_route_count": 3, "checked_on": "2026-11-22", "verified": False}


@pytest.mark.parametrize("bad", [
    "not json", "[]", {}, {**_GOOD_COV, "licences_with_no_published_route": []}, {**_GOOD_COV, "licences_with_no_published_route": ["1"]},
    {**_GOOD_COV, "licences_with_no_published_route": [True]}, {**_GOOD_COV, "licences_with_no_published_route": [0]},
    {**_GOOD_COV, "licences_with_no_published_route": None}, {**_GOOD_COV, "named_in_law": "33"}, {**_GOOD_COV, "checked_on": 20261122},
    {**_GOOD_COV, "named_in_law": True}, {**_GOOD_COV, "named_in_law": 0}, {**_GOOD_COV, "named_in_law": -3},
    {**_GOOD_COV, "licences_with_no_published_route": [1, 1, 3]},                                   # a licence listed twice
    {**_GOOD_COV, "named_in_law": 2},                                                              # three pipelines without a route, but the law names only two
])
def test_pipeline_coverage_is_none_for_a_malformed_file_never_all_covered(tmp_path, bad):
    assert es.pipeline_coverage(_cov(tmp_path, bad)) is None


def test_pipeline_coverage_missing_file_is_none(tmp_path):
    assert es.pipeline_coverage(tmp_path / "nope.json") is None


def test_the_committed_coverage_file_is_readable_and_counts_thirteen_of_thirty_three():
    got = es.pipeline_coverage()
    assert got is not None and got["no_route_count"] == 13 and got["named_in_law"] == 33


def test_every_live_paragraph_has_a_plain_title_and_it_reaches_the_hand_check_list():
    rows = es.exclusions(d.decide(_lot(), FACTS), FACTS)
    assert all(r["title"] for r in rows)
    assert {r["para"] for r in rows} == set(es.PLAIN_TITLES)
    by_clause = {r["clause"]: r["title"] for r in rows}
    manual = es.manual_checks(rows)
    assert manual and all(m["title"] == by_clause[m["clause"]] for m in manual)


def test_a_paragraph_without_a_listed_title_carries_none_never_a_guess(monkeypatch):
    monkeypatch.setattr(es, "PLAIN_TITLES", {})
    rows = es.exclusions(d.decide(_lot(), FACTS), FACTS)
    assert all(r["title"] is None for r in rows)


def test_law_instrument_is_the_saved_facts_title_and_none_when_the_file_has_none():
    area = d.decide(_lot(), FACTS)
    assert es.build(area, {"status": "none", "controls": []}, {"status": "none", "files": []}, FACTS)["law_instrument"] == FACTS.instrument
    assert FACTS.instrument and "Housing" in FACTS.instrument
    doc = {"law_version_date": "2026-01-01", "facts": {}, "instrument": 7}
    assert d.LawFacts(doc).instrument is None
