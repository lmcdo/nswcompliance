"""Gate rules (scripts/gate_rules.py) and the Woollahra B2 keying rules (DQ-146)."""
import re

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import derive_precinct_keys as dpk  # noqa: E402
import dq_probe_live as probes  # noqa: E402
import gate_rules as g  # noqa: E402


class FakeCursor:
    """Returns `rows` for the SELECT and records every UPDATE."""

    def __init__(self, rows):
        self.rows, self.updates = rows, []

    def execute(self, sql, params=None):
        if sql.startswith("UPDATE"):
            self.updates.append((sql, params))

    def fetchall(self):
        return self.rows


def _only(name):
    return {name}


def test_every_rule_sets_only_gate_columns():
    for rule in g.GATE_RULES:
        assert set(rule["set"]) <= g._GATE_COLUMNS, rule["name"]
        assert rule["where"].strip(), rule["name"]


def test_apply_changes_only_rows_that_differ_and_backs_them_up():
    cur = FakeCursor([(1, None), (2, "heritage")])
    changes = g.apply_gate_rules(cur, "ashfield", apply=True, only=_only("ashfield_e1_heritage"))
    assert changes == [(1, "v2_marker", None, "heritage", "ashfield_e1_heritage")]
    assert len(cur.updates) == 1 and cur.updates[0][1] == ["heritage", 1]


def test_dry_run_writes_nothing():
    cur = FakeCursor([(1, None)])
    changes = g.apply_gate_rules(cur, "ashfield", apply=False, only=_only("ashfield_e1_heritage"))
    assert len(changes) == 1 and cur.updates == []


def test_unknown_column_is_refused(monkeypatch):
    monkeypatch.setattr(g, "GATE_RULES", [{"name": "bad", "council": "x", "where": "true",
                                           "set": {"provision_text": "no"}}])
    try:
        g.apply_gate_rules(FakeCursor([]), None, apply=False)
    except ValueError:
        return
    raise AssertionError("a rule touching a non-gate column must be refused")


def test_e2_flood_and_whole_council_rules_split_by_section():
    flood = next(r for r in g.GATE_RULES if r["name"] == "woollahra_e2_3_flood")
    whole = next(r for r in g.GATE_RULES if r["name"] == "woollahra_e2_whole_council")
    assert "~ '__E2_3'" in flood["where"] and "!~ '__E2_3'" in whole["where"]
    assert flood["set"] == {"v2_dcp_layer": "condition", "v2_site_condition_required": "flood"}


def test_b2_rules_send_each_section_to_one_area_and_b2_1_to_all_eleven():
    rules = {r["name"]: r for r in dpk.RULES if r["name"].startswith("woollahra_b2")}
    assert len(rules) == 12
    union = re.search(r"!~ '([^']+)'", rules["woollahra_b2_all_eleven"]["where"]).group(1)
    for ref, area in [("X__B2_2", "Etham Avenue HCA"), ("X__B2_12", "Bell Street HCA")]:
        assert re.search(union, ref), ref  # excluded from the union rule
        n = ref.rsplit("_", 1)[1]
        assert rules[f"woollahra_b2_{n}"]["strategy"]["precinct_id"] == area
    for ref in ("X__B2_1_7 C1", "X__B3", "X__B2_1_3 O1"):
        assert not re.search(union, ref), ref  # these go to the union


def test_all_heritage_pattern_reads_the_chapters_own_sentence():
    yes = probes._ALL_HERITAGE.search
    assert yes("Part E1 applies to sites which are listed as Heritage Items listed in the Inner West LEP 2022")
    assert yes("Part 19 applies to any development associated with a Heritage Item or within a Heritage "
               "Conservation Area (HCA) identified on the KLEP Heritage Map.")
    assert not yes("This chapter applies to the following neighbourhood HCAs:")
    assert not yes("This chapter applies to the Paddington HCA as identified in Map 1.")


def test_dq146_counts_exactly_what_no_route_query_returns():
    sql = probes.PROBES["DQ-146"][1]
    assert "v2_dcp_layer = 'condition'" in sql
    assert "NOT IN ('flood', 'bushfire', 'acid_sulfate', 'riparian', 'greenweb')" in sql
    assert "<> 'heritage'" in sql


def test_cb_4_3_section_21_goes_to_ashbury_and_the_rest_to_all_seven():
    rules = {r["name"]: r for r in g.EXTRA_KEY_RULES}
    ash = re.search(r"~ '([^']+)'", rules["cb_4_3_ashbury"]["where"]).group(1)
    for ref in ("X__21", "X__21_4", "X__21_16"):
        assert re.search(ash, ref)
    for ref in ("X__2_1", "X__1", "X__12_5", "X__Objectives O1"):
        assert not re.search(ash, ref)  # these go to the union rule
    assert rules["cb_4_3_all_seven"]["strategy"]["precinct_id"] == "C-B 4.3 heritage conservation areas"
    assert all(r["name"] in {x["name"] for x in dpk.RULES} for r in g.EXTRA_KEY_RULES)


def test_dq146_counts_rows_in_a_layer_the_route_never_reads():
    sql = probes.PROBES["DQ-146"][1]
    assert "NOT IN ('generic', 'use_specific', 'condition', 'precinct')" in sql


def test_b2_area_rules_take_the_whole_sub_section_tree():
    # cross-review 2026-10-12: a B2.2 sub-section ref must go to Etham Avenue, not to all eleven
    rules = {r["name"]: r for r in dpk.RULES if r["name"].startswith("woollahra_b2")}
    etham = re.search(r"~ '([^']+)'", rules["woollahra_b2_2"]["where"]).group(1)
    union_not = re.search(r"!~ '([^']+)'", rules["woollahra_b2_all_eleven"]["where"]).group(1)
    for ref in ("X__B2_2", "X__B2_2_1 C1", "X__B2_2 Note"):
        assert re.search(etham, ref) and re.search(union_not, ref)
    assert not re.search(etham, "X__B2_21")  # no such section, but 2 must not match 21


def test_marrickville_part8_reaches_heritage_houses_only():
    # Address audit 2026-10-15: Part 8 was recorded whole-council, so 913 of its rules reached
    # non-heritage houses. Its own sentence (p15) names heritage items and every HCA.
    assert probes._ALL_HERITAGE.search(
        "Part 8 applies to heritage items, heritage conservation areas (HCAs), archaeological "
        "sites and Aboriginal heritage.")
    keys, kinds = probes.PROBES["DQ-143"][2]
    assert dict(zip(keys, kinds))["marrickville__part8-heritage"] == "heritage_general"
    rule = next(r for r in g.GATE_RULES if r["name"] == "marrickville_part8_heritage")
    assert rule["set"] == {"v2_marker": "heritage"} and "'part8-heritage'" in rule["where"]


def test_a_precinct_rule_with_no_precinct_reaches_nobody():
    # Mirrors for-property/route.ts since 2026-10-15: the precinct layer returns nothing for an
    # address without a precinct, so an unkeyed precinct rule is shown to no house (DQ-146),
    # never to every house (it was: 2,827 rules, 24 of 49 audit errors).
    assert "(rp.v2_dcp_layer = 'precinct' AND rp.v2_precinct_id IS NULL)" in probes._REACHES_NOBODY
    assert "COALESCE(v2_dcp_layer, '') <> 'precinct'" in probes._REACHES_EVERY_HOUSE


def test_krg_14b_pages_cover_the_chapter_once_and_use_ids_precinct_service_attributes():
    # Address audit 2026-10-15: 184 Turramurra rules had no key. Ranges must tile p1-38 with no gap or
    # overlap, and every id must match precinct-service.ts's Ku-ring-gai pattern (its outline rows carry
    # no former_council, so an id outside ^14[A-O](_T\d)?$ would be attributed to another council).
    import import_woollahra_b2_union as u
    rule = next(r for r in g.EXTRA_KEY_RULES if r["name"] == "krg_14b_turramurra_by_page")
    ranges = rule["strategy"]["ranges"]
    pages = [p for _, lo, hi in ranges for p in range(lo, hi + 1)]
    assert pages == list(range(1, 39)) and rule["fingerprint"]["max_page"] == 38
    assert all(re.fullmatch(r"14[A-O](_T\d)?", pid, re.I) for pid, _, _ in ranges)
    assert {pid for pid, _, _ in ranges} == {u.UNIONS["krg_14b"]["id"], *u.UNIONS["krg_14b"]["members"]}


def test_cb_7_2_pages_tile_the_chapter_and_match_the_outline_ids():
    # Address audit 2026-10-15: 339 C-B 7.2 rules had no key. Pages 1-108 tiled once; every id is one the
    # raster fit writes (7.2.2-7.2.13 + union 7.2) and the importer accepts.
    import import_cb_centre_boundaries as imp
    rule = next(r for r in g.EXTRA_KEY_RULES if r["name"] == "cb_7_2_city_west_by_page")
    ranges = rule["strategy"]["ranges"]
    pages = sorted(p for _, lo, hi in ranges for p in range(lo, hi + 1))
    assert pages == list(range(1, 109))
    assert {pid for pid, _, _ in ranges} == imp.RASTER_IDS["centres_7_2.geojson"]


@pytest.mark.parametrize("name,last,ids", [
    ("krg_14a_st_ives_by_page", 22, {"14A", "14A_S1", "14A_S2", "14A_S3"}),
    ("krg_14d_gordon_by_page", 36, {"14D", *(f"14D_G{i}" for i in range(1, 6))}),
    ("krg_14e_lindfield_by_page", 70, {"14E", *(f"14E_L{i}" for i in range(1, 9))}),
])
def test_krg_centre_pages_tile_the_chapter(name, last, ids):
    # Address audit 2026-10-15. Pages 1..last tiled once; ids are those fit_vector_centres.py writes, which
    # import_vector_centres.py loads WITH former_council (they miss the ^14[A-O](_T\d)?$ fallback).
    rule = next(r for r in g.EXTRA_KEY_RULES if r["name"] == name)
    ranges = rule["strategy"]["ranges"]
    assert sorted(p for _, lo, hi in ranges for p in range(lo, hi + 1)) == list(range(1, last + 1))
    assert {pid for pid, _, _ in ranges} == ids


def test_marrickville_part8_sections_go_to_their_own_hca():
    rules = [r for r in g.GATE_RULES if "v2_heritage_hca" in r["set"]]
    pat = lambda w: re.search(r"ref_number ~ '([^']+)'", w).group(1)  # noqa: E731
    cases = [("X__8_2_4_1 9", "hca_2"), ("X__8_2_31_1~2", "south_dulwich_hill_heritage_conservation_area"),
             ("X__8_2_12", "hca_10"), ("X__8_2_1", "__any_hca__"), ("X__8_5_2 C1", "__any_hca__"),
             ("X__8_3_2~3", "__any_hca__"), ("X__8_1_7 C2", None)]
    for ref, want in cases:
        hits = [r["set"]["v2_heritage_hca"] for r in rules if re.search(pat(r["where"]), ref)]
        assert hits == ([want] if want else []), ref


def test_marrickville_2_22_flood_goes_to_the_flood_condition_layer():
    rule = next(r for r in g.GATE_RULES if r["name"] == "marrickville_2_22_flood")
    assert rule["council"] == "marrickville"
    assert rule["where"] == "source_chapter_key = 'part2-s22-flood-management'"
    assert rule["set"] == {"v2_dcp_layer": "condition", "v2_site_condition_required": "flood"}


def test_cb_11_14_riverwood_keyed_to_its_lep_outline():
    import json
    from pathlib import Path
    rule = next(r for r in dpk.RULES if r["name"] == "cb_11_14_riverwood_stage1")
    assert rule["where"] == "source_chapter_key = 'chapter-11-14-riverwood-estate'"
    assert rule["strategy"] == {"type": "constant", "precinct_id": "11.14"}
    src = Path(__file__).resolve().parent.parent / "data" / "canterbury_bankstown_precincts" / "lep_riverwood_11_14.geojson"
    ids = {f["properties"]["precinct_id"] for f in json.loads(src.read_text(encoding="utf-8"))["features"]}
    assert ids == {"11.14"}
