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
        """Source pin: load_cdc_standards selects and propagates the columns."""
        src = (ROOT / "services" / "cdc_screen.py").read_text(encoding="utf-8")
        assert "stale_since, stale_reason" in src
        assert '"stale_since": max(' in src


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
