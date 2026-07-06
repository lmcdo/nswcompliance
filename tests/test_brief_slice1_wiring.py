"""Slice 1 wiring tests — market context, land-use lists, per-form SEPP eligibility.

Break-it scenarios covered (silent wrong results, not crashes):
  1. A failed VG ArcGIS query returns {} — pre-fix that rendered as a confident
     "0 comparable lots nearby" (the da_outcome silent-zero class). It must
     RAISE; only a genuine {"features": []} is an empty result.
  2. One VG half down must not blank the other (comparables failed, sales fine).
  3. Another council's land-use rows must never leak into this council's lists
     (the #585 council-name-mismatch class, inverted).
  4. "LGA not extracted yet" / "DB query failed" / "no zone resolved" are three
     different land-use states and must render distinctly.
  5. The SEPP card must reuse the ONE eligibility engine run — never re-invoke.
  6. An errored eligibility engine must surface NOT_AVAILABLE, never a silent
     "no forms apply".
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import services.intelligence_brief as ib
from services.intelligence_brief import (
    ConfidenceLevel,
    DataField,
    HousingSeppFormOutput,
    _build_market_context,
    _build_planning_controls,
    _build_sepp_eligibility_field,
    _fetch_market_context,
    _lmr_uplift_form,
)
from services.vg_comparables import ComparableAnalysis, get_comparable_values, get_recent_sales

GOLDEN = Path(__file__).parent / "fixtures" / "brief_golden"
NA = ConfidenceLevel.NOT_AVAILABLE
AUTH = ConfidenceLevel.AUTHORITATIVE

_CONTROLS = {"zone": "R3", "height": "9", "fsr": "0.5:1"}
_OVERLAYS = {"overlays": [], "covered_layers": [], "proximity_m": {}}


def _golden(name: str):
    with open(GOLDEN / f"{name}.json", encoding="utf-8") as fh:
        return json.load(fh)["output"]


# ── 1. VG failed query must not look like zero comparables ──────────────────

@patch("services.vg_comparables.arcgis_get_with_retry", return_value={})
def test_vg_transport_failure_raises_instead_of_zero_comparables(mock_get):
    with pytest.raises(RuntimeError, match="failed"):
        get_comparable_values(151.1, -33.86, "R3", lot_area_m2=550.0)


@patch("services.vg_comparables.arcgis_get_with_retry", return_value={"features": []})
def test_vg_genuine_empty_is_zero_comparables_not_error(mock_get):
    result = get_comparable_values(151.1, -33.86, "R3", lot_area_m2=550.0)
    assert result.comparable_count == 0
    assert result.comparables == []


@patch("services.vg_comparables.arcgis_get_with_retry", return_value={})
def test_vg_sales_transport_failure_raises(mock_get):
    with pytest.raises(RuntimeError, match="failed"):
        get_recent_sales(151.1, -33.86)


@patch("services.vg_comparables.arcgis_get_with_retry", return_value={"features": []})
def test_vg_sales_genuine_empty_is_empty_list(mock_get):
    assert get_recent_sales(151.1, -33.86) == []


# ── 2. Half-isolation in the market fetch ────────────────────────────────────

def test_comparables_failure_does_not_blank_sales(monkeypatch):
    def comps_boom(*a, **k):
        raise RuntimeError("VG valuation query failed")
    monkeypatch.setattr(ib, "get_comparable_values", comps_boom)
    monkeypatch.setattr(ib, "get_recent_sales", lambda *a, **k: [])
    out = _fetch_market_context(151.1, -33.86, "R3", 550.0, 1456609)
    assert out["comparables"] is None
    assert "failed" in out["comparables_reason"]
    assert out["sales"] == []  # sales half survived — genuine empty preserved


def test_both_vg_halves_failing_raises_for_safe_call(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("VG down")
    monkeypatch.setattr(ib, "get_comparable_values", boom)
    monkeypatch.setattr(ib, "get_recent_sales", boom)
    with pytest.raises(RuntimeError):
        _fetch_market_context(151.1, -33.86, "R3", 550.0, None)


def test_missing_zone_still_fetches_sales(monkeypatch):
    monkeypatch.setattr(ib, "get_recent_sales", lambda *a, **k: [])
    out = _fetch_market_context(151.1, -33.86, None, 550.0, None)
    assert out["comparables"] is None
    assert "resolved" in out["comparables_reason"]  # frontend renders the honest neutral state
    assert out["sales"] == []


def test_build_market_context_three_states():
    # comparables failed + sales genuinely empty — the two must be DISTINCT
    mc = _build_market_context({
        "comparables": None, "comparables_reason": "RuntimeError: VG valuation query failed",
        "sales": [], "sales_reason": None,
    })
    assert mc.comparables.confidence == NA
    assert "failed" in mc.comparables.reason
    assert mc.recent_sales.confidence == AUTH
    assert mc.recent_sales.value == []
    # whole fetch failed upstream -> no MarketContext at all (card NOT_AVAILABLE)
    assert _build_market_context(None) is None


def test_build_market_context_populated_from_real_capture():
    comps = ComparableAnalysis.model_validate(_golden("vg_comparables"))
    from services.vg_comparables import PropertySale
    sales = [PropertySale.model_validate(r) for r in _golden("vg_sales")]
    mc = _build_market_context({
        "comparables": comps, "comparables_reason": None,
        "sales": sales, "sales_reason": None,
    })
    assert mc.comparables.confidence == ConfidenceLevel.DERIVED
    assert mc.comparables.value.comparable_count > 50  # real Concord capture: 117
    assert mc.comparables.value.median_value > 100_000
    assert mc.recent_sales.confidence == AUTH
    assert len(mc.recent_sales.value) > 10
    assert mc.radius_m == 500


# ── 3. LGA scoping — another council's rows must not leak in ────────────────

def _mock_conn_with_rows(rows):
    cur = MagicMock()
    cur.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn


def test_other_council_rows_do_not_leak_into_this_lga(monkeypatch):
    # Real-shaped rows from the golden capture: Bayside R3 rows. Target council
    # is Burwood — the lists must come back EMPTY (not-extracted state), never
    # Bayside's uses presented as Burwood's.
    bayside_rows = [
        ("Bayside", "R3", r["development_type"], r["permissibility"])
        for r in _golden("lep_land_use_rows")["rows"][:10]
    ]
    monkeypatch.setattr(ib, "_get_db_conn", lambda: _mock_conn_with_rows(bayside_rows))
    out = ib._fetch_land_use_lists("R3", "Burwood")
    assert out["row_count"] == 0
    assert out["permitted"] == [] and out["prohibited"] == []


def test_matching_lga_rows_are_grouped(monkeypatch):
    rows = [
        ("Bayside", "R3", "dwelling_house", "permitted"),
        ("Bayside", "R3", "heavy_industry", "prohibited"),
        ("Bayside", "R3", "dual_occupancy", "permitted"),
        ("Canada Bay", "R3", "sex_services_premises", "prohibited"),  # other LGA — excluded
    ]
    monkeypatch.setattr(ib, "_get_db_conn", lambda: _mock_conn_with_rows(rows))
    out = ib._fetch_land_use_lists("R3", "Bayside Council")
    assert out["permitted"] == ["dual_occupancy", "dwelling_house"]
    assert out["prohibited"] == ["heavy_industry"]
    assert out["row_count"] == 3


# ── 4. Land-use three states render distinctly on the card ──────────────────

def _pc_with_land_use(land_use_df):
    return _build_planning_controls(_CONTROLS, _OVERLAYS, land_use_df=land_use_df)


def test_land_use_no_zone_state():
    pc = _pc_with_land_use(None)
    assert pc.permitted_uses.confidence == NA
    assert "zone" in pc.permitted_uses.reason.lower()


def test_land_use_db_failure_state_keeps_error_reason():
    failed = DataField(value=None, confidence=NA, source="lep_land_use_table",
                       reason="OperationalError: connection refused")
    pc = _pc_with_land_use(failed)
    assert pc.permitted_uses.confidence == NA
    assert "OperationalError" in pc.permitted_uses.reason  # error tone, retryable


def test_land_use_council_not_extracted_state():
    empty = DataField(value={"permitted": [], "prohibited": [], "row_count": 0},
                      confidence=AUTH, source="lep_land_use_table")
    pc = _pc_with_land_use(empty)
    assert pc.permitted_uses.confidence == NA
    assert "not yet extracted" in pc.permitted_uses.reason  # 'Not assessed' tone, not an error


def test_land_use_populated_lists_are_authoritative():
    lists = DataField(
        value={"permitted": ["dwelling_house"], "prohibited": ["heavy_industry"], "row_count": 2},
        confidence=AUTH, source="lep_land_use_table",
    )
    pc = _pc_with_land_use(lists)
    assert pc.permitted_uses.confidence == AUTH
    assert pc.permitted_uses.value == ["dwelling_house"]
    assert pc.prohibited_uses.value == ["heavy_industry"]


def test_land_use_one_sided_zone_is_empty_list_not_not_extracted():
    # A covered LGA where the zone only lists prohibited uses: permitted must be
    # an AUTHORITATIVE [] ("none listed"), not the "not extracted" state.
    lists = DataField(
        value={"permitted": [], "prohibited": ["heavy_industry"], "row_count": 1},
        confidence=AUTH, source="lep_land_use_table",
    )
    pc = _pc_with_land_use(lists)
    assert pc.permitted_uses.confidence == AUTH
    assert pc.permitted_uses.value == []


# ── 5/6. SEPP eligibility: one engine run, honest failure ────────────────────

def test_eligibility_engine_error_is_not_available_never_empty():
    field = _build_sepp_eligibility_field(None)
    assert field.confidence == NA
    assert field.value is None
    assert field.reason


def test_eligibility_no_applicable_forms_is_authoritative_empty():
    field = _build_sepp_eligibility_field([])
    assert field.confidence == AUTH
    assert field.value == []
    assert field.reason is None


def test_eligibility_rows_carry_citations_from_real_capture():
    from services.housing_sepp_eligibility import FormEligibility

    rows = [FormEligibility(**r) for r in _golden("housing_sepp_eligibility")]
    field = _build_sepp_eligibility_field(rows)
    assert field.confidence == AUTH
    assert len(field.value) == len(rows)
    assert all(isinstance(f, HousingSeppFormOutput) for f in field.value)
    # the product's point — at least one outcome cites its clause
    assert any(f.source_clause for f in field.value)
    assert any(f.min_lot_size_m2 for f in field.value)  # drives the lot-vs-min line


def test_lmr_uplift_reuses_precomputed_results_never_reinvokes(monkeypatch):
    """The capacity ceiling must consume the SEPP card's engine run. If it
    re-invoked evaluate_eligibility, this patch would explode."""
    import services.housing_sepp_eligibility as hse

    def boom(*a, **k):
        raise AssertionError("evaluate_eligibility re-invoked — must reuse the precomputed run")
    monkeypatch.setattr(hse, "evaluate_eligibility", boom)

    from services.housing_sepp_eligibility import FormEligibility

    # Real Concord capture: all 7 forms ineligible → correctly no uplift, and
    # crucially the boom patch above never fired (no re-invocation).
    precomputed = [FormEligibility(**r) for r in _golden("housing_sepp_eligibility")]
    form, citation = _lmr_uplift_form("R3", -33.86, 151.1, 4096.0, 20.0, False,
                                      results=precomputed)
    assert form is None and citation is None

    # Flip one real row to eligible: selection must run off the precomputed
    # list (still no engine call) and carry that row's clause.
    import dataclasses
    eligible = [
        dataclasses.replace(r, eligible=True) if r.development_type == "dual_occupancy" else r
        for r in precomputed
    ]
    form, citation = _lmr_uplift_form("R3", -33.86, 151.1, 4096.0, 20.0, False,
                                      results=eligible)
    assert form == "dual_occupancy"
    assert citation and citation.get("source_clause") == "169(3)(d)"


# ── generator-level: new section obeys the fail-closed invariant ─────────────

def test_development_route_emits_market_context_and_eligibility(monkeypatch):
    from tests.test_brief_slice0_failclosed import _TORRENS, _run_generator

    events = _run_generator(monkeypatch, lambda *a, **k: dict(_TORRENS))
    sections = {d.get("section") for n, d in events if n == "section"}
    assert "market_context" in sections
    mkt = next(d for n, d in events if n == "section" and d.get("section") == "market_context")
    # all sources failed -> the card must be honestly unavailable, never a
    # fabricated "0 comparables"
    assert mkt["data"]["confidence"] == "not_available"
    assert mkt["data"]["value"] is None
    sepp = next(d for n, d in events if n == "section" and d.get("section") == "sepp_housing")
    assert "eligibility_forms" in sepp
