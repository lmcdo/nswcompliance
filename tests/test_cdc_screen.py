"""CDC screen engine truth tests (#820 PR-1).

Contract under test:
  - standards come only from verified cdc_eligibility_standards rows; anything
    missing or invalid fails closed to None (loader) / ValueError (engine)
  - the screen never answers "yes"
  - unknown inputs surface as unchecked warnings, never silent passes
  - contamination: lot-on-register = exclusion; nearby = warning only
  - mine subsidence: always a warning, never an exclusion
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.cdc_screen import (
    CdcScreenInputs,
    _validate_standards,
    load_cdc_standards,
    run_cdc_screen,
)


def _standards(**overrides) -> dict:
    base = {
        "eligible_zones": {"R1", "R2", "R3", "R4", "RU5"},
        "min_lot_size": 200.0,
        "min_lot_conditionality": "applies if no minimum size is specified for the lot",
        "acid_sulfate_max_class": 3,
        "refs": {"eligible_zones": "cl 3.1", "min_lot_size": "cl 6.4(1)(d)(ii)"},
    }
    base.update(overrides)
    return base


def _clear_inputs(**overrides) -> CdcScreenInputs:
    base = dict(
        zone_code="R2", lot_area_m2=550.0, heritage_item=False,
        heritage_conservation_area=False, flood_prone=False,
        bushfire_prone=False, acid_sulfate_class=None, complying_excluded=False,
        dual_occ_prohibited=False, contaminated_lot_on_register=False,
        contamination_within_500m=False, mine_subsidence_district=False,
    )
    base.update(overrides)
    return CdcScreenInputs(**base)


class FakeCursor:
    def __init__(self, rows=None, raise_on_execute=False):
        self._rows = rows or []
        self._raise = raise_on_execute
        self.executed_sql = None

    def execute(self, sql, params=None):
        if self._raise:
            raise Exception("DB error")
        self.executed_sql = sql

    def fetchall(self):
        return self._rows

    def close(self):
        pass


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def _std_rows(min_lot=200.0, zones=("R1", "R2", "R3", "R4", "RU5"), ass=3, stale=None):
    rows = [
        ("eligible_zones", None, list(zones), None, "cl 3.1", stale, "instrument amended" if stale else None),
        ("min_lot_size", min_lot, None, "if no minimum size is specified", "cl 6.4(1)(d)(ii)", stale, "instrument amended" if stale else None),
    ]
    if ass is not None:
        rows.append(("acid_sulfate_max_class", ass, None, None, "cl 1.19", None, None))
    return rows


# ---------------------------------------------------------------------------
# _validate_standards — shared boundary validation
# ---------------------------------------------------------------------------

class TestValidateStandards:
    def test_valid_normalises(self):
        out = _validate_standards(_standards(eligible_zones=[" R1 ", "R2"]))
        assert out["eligible_zones"] == {"R1", "R2"}
        assert out["min_lot_size"] == 200.0

    def test_rejects_zero_negative_nonfinite_minimum(self):
        for bad in (0, -200, float("nan"), float("inf"), None, "abc"):
            assert _validate_standards(_standards(min_lot_size=bad)) is None, bad

    def test_rejects_bad_zone_collections(self):
        for bad in (["R1", None], ["R1", ""], [], None, "R1"):
            assert _validate_standards(_standards(eligible_zones=bad)) is None, bad

    def test_rejects_empty(self):
        assert _validate_standards(None) is None
        assert _validate_standards({}) is None


# ---------------------------------------------------------------------------
# load_cdc_standards — verified rows only, fail closed
# ---------------------------------------------------------------------------

class TestLoadCdcStandards:
    def test_no_conn_returns_none(self):
        assert load_cdc_standards(None) is None

    def test_query_filters_to_verified_active_rows(self):
        cur = FakeCursor(rows=_std_rows())
        load_cdc_standards(FakeConn(cur))
        assert "manual_verified = TRUE" in cur.executed_sql
        assert "is_active = TRUE" in cur.executed_sql

    def test_duplicate_active_rows_fail_closed(self):
        """Two active rows for one standard type would be a nondeterministic
        pick — the loader must refuse, not choose."""
        rows = _std_rows() + [("min_lot_size", 300.0, None, None, "cl 3.x", None, None)]
        assert load_cdc_standards(FakeConn(FakeCursor(rows=rows))) is None

    def test_invalid_present_acid_sulfate_fails_whole_load(self):
        """A PRESENT but invalid threshold must not silently vanish and let
        the screen run with incomplete standards."""
        for bad in ("bad", 3.9, 0, 9, None):
            rows = _std_rows(ass=None) + [("acid_sulfate_max_class", bad, None, None, "cl 1.19", None, None)]
            assert load_cdc_standards(FakeConn(FakeCursor(rows=rows))) is None, bad

    def test_loads_valid_standards(self):
        out = load_cdc_standards(FakeConn(FakeCursor(rows=_std_rows(min_lot=200.0))))
        assert out["min_lot_size"] == 200.0
        assert out["eligible_zones"] == {"R1", "R2", "R3", "R4", "RU5"}
        assert out["acid_sulfate_max_class"] == 3
        assert out["refs"]["min_lot_size"] == "cl 6.4(1)(d)(ii)"

    def test_missing_required_rows_returns_none(self):
        only_zones = [("eligible_zones", None, ["R2"], None, "cl 3.1", None, None)]
        assert load_cdc_standards(FakeConn(FakeCursor(rows=only_zones))) is None
        assert load_cdc_standards(FakeConn(FakeCursor(rows=[]))) is None

    def test_query_failure_returns_none(self):
        assert load_cdc_standards(FakeConn(FakeCursor(raise_on_execute=True))) is None

    def test_corrupt_values_return_none(self):
        """Mutation check: a zero minimum or null zone entry must not load."""
        assert load_cdc_standards(FakeConn(FakeCursor(rows=_std_rows(min_lot=0)))) is None
        rows = _std_rows()
        rows[0] = ("eligible_zones", None, ["R2", None], None, "cl 3.1", None, None)
        assert load_cdc_standards(FakeConn(FakeCursor(rows=rows))) is None

    def test_missing_acid_sulfate_row_is_allowed(self):
        out = load_cdc_standards(FakeConn(FakeCursor(rows=_std_rows(ass=None))))
        assert out is not None
        assert out["acid_sulfate_max_class"] is None


# ---------------------------------------------------------------------------
# run_cdc_screen — verdicts
# ---------------------------------------------------------------------------

class TestRunCdcScreen:
    def test_never_yes(self):
        result = run_cdc_screen(_standards(), _clear_inputs())
        assert result.eligible == "maybe"
        assert result.exclusions == []

    def test_garbage_standards_raise(self):
        with pytest.raises(ValueError):
            run_cdc_screen({"min_lot_size": 0, "eligible_zones": {"R2"}}, _clear_inputs())

    def test_zone_outside_set_is_definite_no(self):
        result = run_cdc_screen(_standards(), _clear_inputs(zone_code="E2"))
        assert result.eligible == "no"
        assert any(e.constraint == "zone" and e.severity == "definite" for e in result.exclusions)
        assert "SEPP (Exempt and Complying Development Codes) 2008" in result.exclusions[0].source

    def test_lot_below_minimum_uses_injected_figure(self):
        """Mutation check: the figure comes from standards, not a constant.
        Condition asserted met → definite exclusion."""
        result = run_cdc_screen(
            _standards(min_lot_size=600.0),
            _clear_inputs(lot_area_m2=550.0, min_lot_condition_met=True))
        assert result.eligible == "no"
        exc = next(e for e in result.exclusions if e.constraint == "lot_size")
        assert exc.severity == "definite"
        assert "600" in exc.reason
        assert "200" not in exc.reason

    def test_lot_condition_unknown_is_likely_not_definite(self):
        """The stored conditionality is EVALUATED: with the condition unknown
        the threshold may not govern, so below-threshold is not a definite no."""
        result = run_cdc_screen(_standards(), _clear_inputs(lot_area_m2=150.0))
        exc = next(e for e in result.exclusions if e.constraint == "lot_size")
        assert exc.severity == "likely"
        assert "if no minimum size is specified" in exc.reason
        assert result.eligible == "maybe"

    def test_lot_condition_not_met_is_unchecked(self):
        """A specified minimum governs instead → this standard's figure does
        not apply; no exclusion, surfaced as unchecked."""
        result = run_cdc_screen(
            _standards(), _clear_inputs(lot_area_m2=150.0, min_lot_condition_met=False))
        assert not any(e.constraint == "lot_size" for e in result.exclusions)
        assert any("lot size" in u for u in result.unchecked)

    def test_nan_lot_area_surfaces_as_unchecked(self):
        """NaN < min is False — without coercion a NaN area would silently
        pass the minimum check as if screened."""
        result = run_cdc_screen(_standards(), _clear_inputs(lot_area_m2=float("nan")))
        assert not any(e.constraint == "lot_size" for e in result.exclusions)
        assert "lot size" in result.unchecked

    def test_nonpositive_lot_area_is_error_sentinel_not_exclusion(self):
        """-1 or 0 from an upstream failure must read as unknown, never as a
        tiny lot that fails the minimum."""
        for bad in (-1.0, 0.0):
            result = run_cdc_screen(_standards(), _clear_inputs(lot_area_m2=bad))
            assert not any(e.constraint == "lot_size" for e in result.exclusions), bad
            assert "lot size" in result.unchecked, bad

    def test_lot_reason_never_contradicts_comparison(self):
        """199.6 m² vs a 200 m² minimum must not render as '200 below 200'."""
        result = run_cdc_screen(
            _standards(), _clear_inputs(lot_area_m2=199.6, min_lot_condition_met=True))
        reason = next(e for e in result.exclusions if e.constraint == "lot_size").reason
        assert "199.6" in reason

    def test_unknown_heritage_item_not_cleared_by_known_hca(self):
        """heritage_item=None with heritage_conservation_area=False must
        surface the item status as unchecked, not read as clear."""
        result = run_cdc_screen(_standards(), _clear_inputs(
            heritage_item=None, heritage_conservation_area=False))
        assert any("heritage item" in u for u in result.unchecked)

    def test_unknown_lot_register_not_cleared_by_known_proximity(self):
        result = run_cdc_screen(_standards(), _clear_inputs(
            contaminated_lot_on_register=None, contamination_within_500m=False))
        assert any("subject-lot register" in u for u in result.unchecked)

    def test_out_of_range_acid_class_reads_as_unknown(self):
        """Class 6 does not exist on the maps — corrupt data must surface as
        unchecked, not as screened-and-clear."""
        result = run_cdc_screen(_standards(), _clear_inputs(acid_sulfate_class=6))
        assert not any(e.constraint == "acid_sulfate" for e in result.exclusions)
        assert "acid sulfate soils" in result.unchecked

    def test_heritage_item_is_definite_no(self):
        result = run_cdc_screen(_standards(), _clear_inputs(heritage_item=True))
        assert result.eligible == "no"
        exc = next(e for e in result.exclusions if e.constraint == "heritage")
        assert exc.severity == "definite"

    def test_heritage_conservation_area_is_likely_not_definite(self):
        result = run_cdc_screen(_standards(), _clear_inputs(heritage_conservation_area=True))
        assert result.eligible == "maybe"
        exc = next(e for e in result.exclusions if e.constraint == "heritage")
        assert exc.severity == "likely"

    def test_flood_bushfire_are_likely_not_blanket_definite(self):
        """Broad overlay booleans alone do not establish a Codes SEPP
        exclusion — they must never produce a definite 'no'."""
        for field, constraint in (("flood_prone", "flood"), ("bushfire_prone", "bushfire")):
            result = run_cdc_screen(_standards(), _clear_inputs(**{field: True}))
            assert result.eligible == "maybe", field
            exc = next(e for e in result.exclusions if e.constraint == constraint)
            assert exc.severity == "likely"
            assert "certifier" in exc.reason

    def test_unknown_inputs_surface_as_unchecked_not_silent_pass(self):
        result = run_cdc_screen(_standards(), CdcScreenInputs())
        assert result.eligible == "maybe"
        assert result.exclusions == []
        assert "zone" in result.unchecked
        assert "lot size" in result.unchecked
        assert any("Not screened" in w for w in result.warnings)

    def test_exclusion_area_layer_is_definite(self):
        result = run_cdc_screen(_standards(), _clear_inputs(complying_excluded=True))
        assert result.eligible == "no"
        assert any(e.constraint == "complying_exclusion" for e in result.exclusions)

    def test_acid_sulfate_check_only_when_standard_present(self):
        no_ass = _standards(acid_sulfate_max_class=None)
        result = run_cdc_screen(no_ass, _clear_inputs(acid_sulfate_class=2))
        assert "Acid sulfate soils" not in result.checks_performed
        with_ass = run_cdc_screen(_standards(), _clear_inputs(acid_sulfate_class=2))
        assert any(e.constraint == "acid_sulfate" and e.severity == "likely"
                   for e in with_ass.exclusions)
        # 'likely' severity alone must not produce a definite 'no'
        assert with_ass.eligible == "maybe"

    def test_contamination_on_register_is_exclusion(self):
        result = run_cdc_screen(_standards(), _clear_inputs(contaminated_lot_on_register=True))
        assert result.eligible == "no"
        assert any(e.constraint == "contamination" for e in result.exclusions)

    def test_contamination_nearby_is_warning_only(self):
        result = run_cdc_screen(_standards(), _clear_inputs(contamination_within_500m=True))
        assert result.eligible == "maybe"
        assert not any(e.constraint == "contamination" for e in result.exclusions)
        assert any("500 m" in w for w in result.warnings)

    def test_mine_subsidence_is_warning_never_exclusion(self):
        result = run_cdc_screen(_standards(), _clear_inputs(mine_subsidence_district=True))
        assert result.eligible == "maybe"
        assert not any(e.constraint.startswith("mine") for e in result.exclusions)
        assert any("Subsidence Advisory" in w for w in result.warnings)

    def test_dual_occ_prohibition_excludes_only_dual_occ_proposals(self):
        result = run_cdc_screen(_standards(), _clear_inputs(
            dual_occ_prohibited=True, dual_occ_epi_name="Ryde LEP 2014",
            development_type="dual_occupancy"))
        assert result.eligible == "no"
        exc = next(e for e in result.exclusions if e.constraint == "dual_occ_prohibition")
        assert exc.source == "Ryde LEP 2014"

    def test_dual_occ_prohibition_is_warning_for_other_proposals(self):
        """A dwelling-house (or unknown) proposal must not be rejected by a
        dual-occ-specific prohibition."""
        for dev_type in ("dwelling_house", None):
            result = run_cdc_screen(_standards(), _clear_inputs(
                dual_occ_prohibited=True, development_type=dev_type))
            assert result.eligible == "maybe", dev_type
            assert not any(e.constraint == "dual_occ_prohibition" for e in result.exclusions)
            assert any("dual-occupancy prohibition" in w for w in result.warnings)

    def test_dual_occ_prohibition_with_unknown_proposal_surfaces_unchecked(self):
        """Unknown proposal type on prohibited land is a gap in the screen,
        not a quiet downgrade — it must appear in unchecked."""
        result = run_cdc_screen(_standards(), _clear_inputs(
            dual_occ_prohibited=True, development_type=None))
        assert any("development type" in u for u in result.unchecked)
        known = run_cdc_screen(_standards(), _clear_inputs(
            dual_occ_prohibited=True, development_type="dwelling_house"))
        assert not any("development type" in u for u in known.unchecked)


# ---------------------------------------------------------------------------
# Source guard — the engine must stay hardcode-free
# ---------------------------------------------------------------------------

def test_engine_source_contains_no_regulatory_constants():
    """The zone lists and thresholds the TS route hardcodes must never appear
    here — every figure flows from cdc_eligibility_standards."""
    import pathlib
    src = (pathlib.Path(__file__).resolve().parent.parent
           / "services" / "cdc_screen.py").read_text(encoding="utf-8")
    for phrase in ("'R1', 'R2'", '"R1", "R2"', "200m", "= 200", "8.5", "< 0.3",
                   "CDC_ELIGIBLE_ZONES"):
        assert phrase not in src, f"regulatory constant hardcoded in cdc_screen.py: {phrase!r}"


# ---------------------------------------------------------------------------
# build_cdc_inputs — report-shaped data → three-state engine inputs
# ---------------------------------------------------------------------------

class TestBuildCdcInputs:
    def test_overlay_absent_is_false_only_when_layer_covered(self):
        """Absence of a flood overlay means 'clear' only if the flood layer was
        actually queried; otherwise it must read unknown."""
        from services.cdc_screen import build_cdc_inputs
        covered = build_cdc_inputs("R2 Low Density", 500.0, [], [], [], {"flood"})
        assert covered.flood_prone is False
        uncovered = build_cdc_inputs("R2 Low Density", 500.0, [], [], [], set())
        assert uncovered.flood_prone is None

    def test_overlay_present_is_true_regardless_of_coverage(self):
        from services.cdc_screen import build_cdc_inputs
        inputs = build_cdc_inputs("R2", 500.0, [], [], [{"layer_type": "flood", "value": "x"}], set())
        assert inputs.flood_prone is True

    def test_zone_token_extracted_and_uppercased(self):
        from services.cdc_screen import build_cdc_inputs
        assert build_cdc_inputs("r2 Low Density Residential", None, None, None, [], set()).zone_code == "R2"
        assert build_cdc_inputs("", None, None, None, [], set()).zone_code is None
        assert build_cdc_inputs(None, None, None, None, [], set()).zone_code is None

    def test_heritage_lists_are_three_state(self):
        from services.cdc_screen import build_cdc_inputs
        known_clear = build_cdc_inputs("R2", None, [], [], [], set())
        assert known_clear.heritage_item is False
        assert known_clear.heritage_conservation_area is False
        listed = build_cdc_inputs("R2", None, ["Item 123"], None, [], set())
        assert listed.heritage_item is True
        assert listed.heritage_conservation_area is None

    def test_acid_class_parsed_from_overlay_value(self):
        from services.cdc_screen import build_cdc_inputs
        inputs = build_cdc_inputs("R2", None, [], [], [
            {"layer_type": "acid_sulfate", "value": "Class 2"}], {"acid_sulfate"})
        assert inputs.acid_sulfate_class == 2
        junk = build_cdc_inputs("R2", None, [], [], [
            {"layer_type": "acid_sulfate", "value": "Present"}], {"acid_sulfate"})
        assert junk.acid_sulfate_class is None


class TestRunCdcScreenForReport:
    def test_fails_closed_without_db(self, monkeypatch):
        """No DATABASE_URL / unloadable standards → None, never an exception."""
        from services.cdc_screen import run_cdc_screen_for_report
        assert run_cdc_screen_for_report(None, "R2", 500.0, [], [], [], set()) is None

    def test_engine_crash_degrades_to_none(self, monkeypatch):
        import services.cdc_screen as cs
        monkeypatch.setattr(cs, "load_cdc_standards_from_url", lambda *a, **k: _standards())
        monkeypatch.setattr(cs, "run_cdc_screen", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        assert cs.run_cdc_screen_for_report("postgres://x", "R2", 500.0, [], [], [], set()) is None

    def test_runs_screen_when_standards_load(self, monkeypatch):
        import services.cdc_screen as cs
        monkeypatch.setattr(cs, "load_cdc_standards_from_url", lambda *a, **k: _standards())
        result = cs.run_cdc_screen_for_report("postgres://x", "E2 Environmental", 500.0, [], [], [], set())
        assert result.eligible == "no"
        assert any(e.constraint == "zone" for e in result.exclusions)
