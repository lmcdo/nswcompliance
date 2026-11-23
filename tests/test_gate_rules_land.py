"""scripts/gate_rules_land.py: zone / heritage / place limits, matched by council + chapter + text fingerprint."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import gate_rules_land as g  # noqa: E402
import never_serve  # noqa: E402

TEXT = "Development is limited to the Pound Road area."


class FakeCur:
    """SELECT returns the rows: (id, text, marker, zones, layer, precinct_id, hca). UPDATEs are recorded."""

    def __init__(self, rows):
        self.rows, self.updates = rows, []

    def execute(self, sql, params=None):
        if not sql.lstrip().upper().startswith("SELECT"):
            self.updates.append((sql, params))

    def fetchall(self):
        return self.rows


def entry(kind, zones=()):
    return {"council": "hornsby", "chapter_key": "", "kind": kind, "zones": list(zones), "expect": 1,
            "text_sha256_16": [never_serve.text_key(TEXT)]}


@pytest.fixture()
def use(monkeypatch):
    def _use(e, zones_ok=True):
        monkeypatch.setattr(g, "entries", lambda: (e,))
        monkeypatch.setattr(g, "_zones_ok", lambda cur, c, z: zones_ok)
        monkeypatch.setattr(never_serve, "ids", lambda: frozenset({999}))
    return _use


def row(i=1, text=TEXT, marker=None, zones=None, layer="generic", pid=None, hca=None):
    return (i, text, marker, zones, layer, pid, hca)


def test_precinct_kind_hides_an_unkeyed_row(use):
    use(entry("precinct"))
    cur = FakeCur([row()])
    assert g.apply_land_limits(cur, None, True) == [(1, "v2_dcp_layer", "generic", "precinct", "land_limits")]
    assert cur.updates[0][1] == ("precinct", 1)


def test_heritage_kind_sets_the_marker_only_when_empty(use):
    use(entry("heritage"))
    assert len(g.apply_land_limits(FakeCur([row()]), None, True)) == 1
    assert g.apply_land_limits(FakeCur([row(marker="flood")]), None, True) == []


@pytest.mark.parametrize("zones", [None, [], ["ALL"]])
def test_zones_kind_sets_zones_only_when_unrestricted(use, zones):
    use(entry("zones", ["R2", "R3"]))  # noqa: zone-codes  (test input, not taxonomy data)
    ch = g.apply_land_limits(FakeCur([row(zones=zones)]), None, True)
    assert ch == [(1, "v2_applicable_zones", zones, ["R2", "R3"], "land_limits")]  # noqa: zone-codes  (test input, not taxonomy data)


def test_zones_kind_narrows_a_wider_row_but_never_widens(use):
    use(entry("zones", ["R2"]))  # noqa: zone-codes  (test input, not taxonomy data)
    ch = g.apply_land_limits(FakeCur([row(zones=["R2", "R3", "R4"])]), None, True)  # noqa: zone-codes  (test input, not taxonomy data)
    assert ch == [(1, "v2_applicable_zones", ["R2", "R3", "R4"], ["R2"], "land_limits")]  # noqa: zone-codes  (test input, not taxonomy data)
    assert g.apply_land_limits(FakeCur([row(zones=["R2"])]), None, True) == []  # same set: nothing to do  # noqa: zone-codes  (test input, not taxonomy data)
    assert g.apply_land_limits(FakeCur([row(zones=["R3", "R4"])]), None, True) == []  # not a superset: leave  # noqa: zone-codes  (test input, not taxonomy data)


def test_zones_kind_leaves_an_already_restricted_row(use):
    use(entry("zones", ["R2"]))  # noqa: zone-codes  (test input, not taxonomy data)
    assert g.apply_land_limits(FakeCur([row(zones=["B1"])]), None, True) == []  # noqa: zone-codes  (test input, not taxonomy data)


def test_zones_not_in_the_councils_lep_raise_before_any_write(use):
    use(entry("zones", ["XX9"]), zones_ok=False)  # noqa: zone-codes  (test input, not taxonomy data)
    cur = FakeCur([row()])
    with pytest.raises(ValueError):
        g.apply_land_limits(cur, None, True)
    assert cur.updates == []


@pytest.mark.parametrize("r", [row(pid="Beecroft"), row(marker="heritage"), row(hca="Haberfield HCA"),
                               row(layer="precinct"), row(layer="condition")])
def test_precinct_kind_never_touches_keyed_heritage_or_withheld_rows(use, r):
    use(entry("precinct"))
    cur = FakeCur([r])
    assert g.apply_land_limits(cur, None, True) == [] and cur.updates == []


def test_skips_unlisted_text_and_never_serve_ids(use):
    use(entry("precinct"))
    cur = FakeCur([row(text=TEXT + " more"), row(i=999)])
    assert g.apply_land_limits(cur, None, True) == [] and cur.updates == []


def test_dry_run_writes_nothing_and_second_run_is_idempotent(use):
    use(entry("precinct"))
    first = FakeCur([row()])
    assert len(g.apply_land_limits(first, None, False)) == 1 and first.updates == []
    assert g.apply_land_limits(FakeCur([row(layer="precinct")]), None, True) == []


def test_council_and_only_filters(use):
    use(entry("precinct"))
    cur = FakeCur([row()])
    assert g.apply_land_limits(cur, "parramatta", True) == []
    assert g.apply_land_limits(cur, None, True, {"other_rule"}) == []


def test_the_real_file_is_consistent():
    g.entries.cache_clear()
    es = g.entries()                                   # raises on a malformed or miscounted entry
    assert len(es) > 100
    assert {e["kind"] for e in es} == {"zones", "heritage", "precinct", "key"}   # precinct = named place with no outline, owner ruling 2026-10-15
    assert sum(e["expect"] for e in es) == 1099
    assert all(set(e["zones"]) for e in es if e["kind"] == "zones")


def test_a_missing_file_raises(monkeypatch, tmp_path):
    g.entries.cache_clear()
    monkeypatch.setattr(g, "PATH", tmp_path / "nope.json")
    with pytest.raises(FileNotFoundError):
        g.entries()
    g.entries.cache_clear()


def test_key_kind_keys_an_unkeyed_row_to_the_named_precinct(use):
    e = entry("key"); e["precinct_id"] = "5.2"
    use(e)
    ch = g.apply_land_limits(FakeCur([row(layer="precinct")]), None, True)
    assert ch == [(1, "v2_precinct_id", None, "5.2", "land_limits")]              # layer already precinct: one change
    ch = g.apply_land_limits(FakeCur([row(layer="generic")]), None, True)
    assert [c[1] for c in ch] == ["v2_precinct_id", "v2_dcp_layer"]
    assert g.apply_land_limits(FakeCur([row(pid="5.1")]), None, True) == []        # already keyed: left alone
    assert g.apply_land_limits(FakeCur([row(marker="heritage")]), None, True) == []
