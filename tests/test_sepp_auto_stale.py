"""SEPP auto-stale (W3, founder decision 2026-07-29).

Contract:
  - a detected instrument version change stamps stale_since/stale_reason on
    dependent standards tables (first change wins; unmapped instruments no-op)
  - values KEEP SERVING — consumers render a notice, never a blank
  - re-verification clears the stamp (stale_since IS NULL = no notice)
"""

import datetime
import importlib.util
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ROOT = Path(__file__).resolve().parent.parent
MON_SRC = (ROOT / "scripts" / "legislation_monitor.py").read_text(encoding="utf-8")


def _load_mark():
    ns: dict = {}
    start = MON_SRC.index("STANDARDS_TABLES_BY_INSTRUMENT = {")
    end = MON_SRC.index("def send_telegram")
    exec(MON_SRC[start:end], ns)
    return ns["mark_dependent_standards_stale"], ns["STANDARDS_TABLES_BY_INSTRUMENT"]


mark_stale, TABLE_MAP = _load_mark()


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.rowcount = 3

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def close(self):
        pass


class FakeConn:
    def __init__(self):
        self._cur = FakeCursor()

    def cursor(self):
        return self._cur


class TestMonitorMarking:
    def test_codes_sepp_change_stamps_both_tables(self):
        """The E&C Codes SEPP feeds the CDC standards AND housing rows citing it."""
        conn = FakeConn()
        notes = mark_stale(conn, "sepp_exempt_complying_2008",
                           "SEPP (Exempt and Complying Development Codes) 2008",
                           "29 Aug 2025", "15 Jul 2026")
        sqls = [s for s, _ in conn._cur.executed]
        assert any("cdc_eligibility_standards" in s for s in sqls)
        assert any("housing_sepp_standards" in s for s in sqls)
        assert all("stale_since IS NULL" in s for s in sqls), "first change must win"
        assert len(notes) == 2 and all("STALE" in n for n in notes)

    def test_housing_sepp_change_stamps_housing_only(self):
        conn = FakeConn()
        mark_stale(conn, "sepp_housing_2021", "SEPP (Housing) 2021", "a", "b")
        sqls = [s for s, _ in conn._cur.executed]
        assert any("housing_sepp_standards" in s for s in sqls)
        assert not any("cdc_eligibility_standards" in s for s in sqls)

    def test_each_instrument_stamps_only_its_own_rows(self):
        """Sol #839: housing_sepp_standards holds rows from BOTH instruments —
        a Housing amendment must not stale the E&C-derived rows and vice versa."""
        conn = FakeConn()
        mark_stale(conn, "sepp_housing_2021", "SEPP (Housing) 2021", "a", "b")
        housing_sql = next(s for s, _ in conn._cur.executed if "housing_sepp_standards" in s)
        assert "ILIKE '%housing%'" in housing_sql
        conn2 = FakeConn()
        mark_stale(conn2, "sepp_exempt_complying_2008", "E&C Codes SEPP", "a", "b")
        ec_housing_sql = next(s for s, _ in conn2._cur.executed if "housing_sepp_standards" in s)
        assert "ILIKE '%exempt%'" in ec_housing_sql
        cdc_sql = next(s for s, _ in conn2._cur.executed if "cdc_eligibility_standards" in s)
        assert "ILIKE" not in cdc_sql   # whole table is E&C-derived

    def test_unmapped_instrument_is_noop(self):
        conn = FakeConn()
        notes = mark_stale(conn, "lep_inner_west_2022", "Inner West LEP 2022", "a", "b")
        assert notes == [] and conn._cur.executed == []

    def test_reason_names_instrument_and_versions(self):
        conn = FakeConn()
        mark_stale(conn, "sepp_housing_2021", "SEPP (Housing) 2021", "v1", "v2")
        _, params = conn._cur.executed[0]
        assert "SEPP (Housing) 2021" in params[0] and "v1" in params[0] and "v2" in params[0]

    def test_alert_includes_stale_notes(self):
        """Source pin: the change alert must carry the stale lines."""
        assert "r.stale_notes" in MON_SRC
        assert "stale_notes=tuple(stale_notes)" in MON_SRC


class TestCdcEngineNotice:
    def _standards(self, stale=None):
        base = {
            "eligible_zones": {"R1", "R2"}, "min_lot_size": 200.0,
            "min_lot_conditionality": None, "acid_sulfate_max_class": None,
            "refs": {},
        }
        if stale:
            base["stale_since"] = stale
            base["stale_reason"] = "SEPP (E&C) 2008 version changed (a -> b)"
        return base

    def test_stale_standards_still_screen_with_notice(self):
        """Founder-specified: values keep serving; the notice rides along."""
        from services.cdc_screen import CdcScreenInputs, run_cdc_screen
        result = run_cdc_screen(
            self._standards(stale=datetime.datetime(2026, 7, 29, tzinfo=datetime.timezone.utc)),
            CdcScreenInputs(zone_code="R2", lot_area_m2=500.0),
        )
        assert result.eligible in ("no", "maybe")   # screen RAN — not blanked
        assert any("version changed" in w and "re-check" in w for w in result.warnings)
        assert any("2026-07-29" in w for w in result.warnings)

    def test_fresh_standards_carry_no_notice(self):
        from services.cdc_screen import CdcScreenInputs, run_cdc_screen
        result = run_cdc_screen(self._standards(), CdcScreenInputs(zone_code="R2"))
        assert not any("re-check" in w for w in result.warnings)

    def test_loader_aggregates_stale_from_rows(self):
        """Source pin: load_cdc_standards selects the columns and takes the
        date and reason from the SAME (latest) row — never mixed pairs."""
        src = (ROOT / "services" / "cdc_screen.py").read_text(encoding="utf-8")
        assert "stale_since, stale_reason" in src
        assert '"stale_since": _latest[0]' in src
        assert '"stale_reason": _latest[1]' in src

    def test_loader_pairs_date_with_its_own_reason(self):
        """Sol #839: two amendments on different rows — the notice must carry
        the LATER amendment's date AND its reason, not a mixed pair."""
        from services.cdc_screen import load_cdc_standards
        d1 = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        d2 = datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)
        rows = [
            ("eligible_zones", None, ["R1", "R2"], None, "cl 3.1", d1, "amendment A"),
            ("min_lot_size", 200.0, None, None, "cl 3.1(3)(b)", d2, "amendment B"),
        ]

        class Cur:
            def execute(self, *a): pass
            def fetchall(self): return rows
            def close(self): pass

        class Conn:
            def cursor(self): return Cur()

        out = load_cdc_standards(Conn())
        assert out["stale_since"] == d2
        assert out["stale_reason"] == "amendment B"


class TestSecondaryDwellingNotice:
    def _run(self, sepp):
        spec = importlib.util.spec_from_file_location(
            "gcr_stale_test", ROOT / "scripts" / "generate_conveyancing_report.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rows = mod.calc_feasibility(
            {"zone": "R2"}, {"lot_area_m2": 500, "land_value": 900_000}, [],
            is_strata=False, sepp_standards=sepp, tax_config=None,
        )
        return next(r for r in rows if "granny flat" in r["question"].lower())

    def test_stale_config_renders_value_with_note(self):
        sd = self._run({
            "sd_min_lot": 450.0, "sd_zones": {"R1", "R2"},
            "stale_since": datetime.datetime(2026, 7, 29, tzinfo=datetime.timezone.utc),
            "stale_reason": "SEPP (Housing) 2021 version changed (a -> b)",
        })
        assert sd["answer"] == "Likely permissible"   # value still served
        assert "version changed" in sd["basis"] and "re-check" in sd["basis"]

    def test_fresh_config_has_no_note(self):
        sd = self._run({"sd_min_lot": 450.0, "sd_zones": {"R1", "R2"}})
        assert "re-check" not in sd["basis"]


def test_migration_061_exists_and_is_additive():
    sql = (ROOT / "migrations" / "061_sepp_standards_stale_since.sql").read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS stale_since" in sql
    assert "cdc_eligibility_standards" in sql and "housing_sepp_standards" in sql
    assert not re.search(r"\bDROP\b|\bDELETE\b|\bTRUNCATE\b", sql, re.IGNORECASE)
