"""Gate rules (scripts/gate_rules.py) and the Woollahra B2 keying rules (DQ-146)."""
import re
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
    assert "NOT IN ('flood', 'bushfire')" in sql
    assert "<> 'heritage'" in sql
