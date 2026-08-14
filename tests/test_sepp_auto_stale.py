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
        self.commits = 0

    def cursor(self):
        return self._cur

    def commit(self):
        self.commits += 1


# ── "we checked it" must be recorded, and only when it is TRUE ───────────────
# The monitor reported "Checked: 26" on 2026-08-14 while instrument_registry
# last_checked sat frozen at 2026-06-08: check_instrument returned early on
# new_version is None and wrote nothing, and the PCO no-change path makes that
# the NORMAL case. So nothing could distinguish "monitor dead" from "monitor
# fine, nothing changed" — and no currency claim could be dated.
def _load_check_instrument():
    """check_instrument sits at ~L567, after send_telegram and the dataclass it
    returns, so the slice is (dataclass decorator .. def main) plus the two
    datetime names it closes over."""
    _dt = __import__("datetime")
    ns: dict = {
        "datetime": _dt.datetime,
        "timezone": _dt.timezone,
        "dataclass": __import__("dataclasses").dataclass,
        "Optional": __import__("typing").Optional,
    }
    head = MON_SRC.index("@dataclass")
    head_end = MON_SRC.index("def mark_dependent_standards_stale")
    body = MON_SRC.index("def check_instrument")
    body_end = MON_SRC.index("def main():")
    exec(MON_SRC[head:head_end] + "\n\n" + MON_SRC[body:body_end], ns)
    return ns["check_instrument"]


check_instrument = _load_check_instrument()


def _inst(pco_id):
    return {
        "instrument_key": "sepp_housing_2021",
        "instrument_label": "SEPP (Housing) 2021",
        "current_version": "1 Jan 2026",
        "legislation_url": "https://example.invalid",
        "pco_instrument_id": pco_id,
    }


class TestUncheckedIsRecorded:
    def test_pco_silence_on_a_covered_instrument_stamps_last_checked(self):
        """PCO lists every amended instrument, so absence IS a confirmation."""
        conn = FakeConn()
        check_instrument(_inst("epi-2021-0714"), None, "pco", False, conn)
        sqls = [s for s, _ in conn._cur.executed]
        assert any("last_checked" in s and "instrument_registry" in s for s in sqls), \
            "a confirmed-unchanged instrument must record that it was checked"
        assert conn.commits == 1

    def test_pco_silence_on_an_UNCOVERED_instrument_stamps_nothing(self):
        """No pco_instrument_id => it can never appear in the export, so silence
        about it means nothing. Stamping would fabricate a confirmation.
        Live case: wingecarribee_lep_2010."""
        conn = FakeConn()
        check_instrument(_inst(None), None, "pco", False, conn)
        assert conn._cur.executed == [], \
            "an instrument PCO does not cover must NOT be marked as checked"
        assert conn.commits == 0

    def test_other_sources_do_not_stamp_on_a_miss(self):
        """nsw_legislation/austlii fetch per instrument — a None there is a
        failed fetch, not a confirmation."""
        for src in ("nsw_legislation", "austlii"):
            conn = FakeConn()
            check_instrument(_inst("epi-2021-0714"), None, src, False, conn)
            assert conn._cur.executed == [], f"{src} must not stamp on a miss"

    def test_dry_run_writes_nothing(self):
        conn = FakeConn()
        check_instrument(_inst("epi-2021-0714"), None, "pco", True, conn)
        assert conn._cur.executed == [] and conn.commits == 0


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

    def test_predicates_match_representative_source_documents(self):
        """Sol #839 round 2: evaluate the predicates against every known
        source_document spelling (prod values verified 2026-07-29 plus the
        in-repo abbreviation), not just the SQL text."""
        housing_docs = [
            "SEPP (Housing) 2021 - LMR Amendment",
            "SEPP (Housing) 2021",
            "State Environmental Planning Policy (Housing) 2021",
        ]
        ec_docs = [
            "State Environmental Planning Policy (Exempt and Complying\r\n"
            "  Development Codes) 2008",
            "SEPP (E&C) 2008",   # abbreviation used by in-repo fixtures
        ]

        def matches(predicate: str, doc: str) -> bool:
            pats = re.findall(r"ILIKE '%(.+?)%'", predicate)
            return any(p.lower() in doc.lower() for p in pats)

        housing_pred = dict(TABLE_MAP["sepp_housing_2021"])["housing_sepp_standards"]
        ec_pred = dict(TABLE_MAP["sepp_exempt_complying_2008"])["housing_sepp_standards"]
        for doc in housing_docs:
            assert matches(housing_pred, doc) and not matches(ec_pred, doc), doc
        for doc in ec_docs:
            assert matches(ec_pred, doc) and not matches(housing_pred, doc), doc

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
