"""Follow-up wiring tests — SEPP-override clause citations, solar marker slot,
drift-cron scope.

Break-it scenarios:
  1. An override claim without its clause is an uncited regulatory claim — the
     citation must ride from the standards ROW that grants the overriding value.
  2. A dev type whose height row has no citation must yield an override with
     source_clause None (no fabricated citation).
  3. The solar marker slot must appear on satellite runs WITHOUT the brief ever
     invoking the paid Google Solar API inline.
  4. The drift cron must stay read-only (no report-writing services).
"""
from services.constraint_models import SEPPStandard
from services.intelligence_brief import _build_sepp_housing, _detect_sepp_lep_overrides


def _row(dev, st, val, clause=None, doc=None):
    return {"development_type": dev, "standard_type": st, "numeric_value": val,
            "unit": "m", "applicable_zones": ["R3"],
            "source_clause": clause, "source_document": doc, "effective_date": "2025-02-28"}


def test_override_carries_the_granting_rows_clause():
    rows = [
        _row("terraces", "max_height", 12.5, clause="172(3)(b)", doc="SEPP (Housing) 2021"),
        _row("terraces", "max_fsr", 0.8, clause="172(3)(c)", doc="SEPP (Housing) 2021"),
        _row("terraces", "min_lot_size", 250.0, clause="172(1)", doc="SEPP (Housing) 2021"),
    ]
    stds = _build_sepp_housing(rows, "R3", lot_area_m2=500.0)
    assert stds[0].height_source_clause == "172(3)(b)"
    assert stds[0].fsr_source_clause == "172(3)(c)"

    overrides = _detect_sepp_lep_overrides(stds, lep_height_m=8.5, lep_fsr=0.5)
    by_control = {o.control: o for o in overrides}
    assert by_control["height"].source_clause == "172(3)(b)"  # the granting row's clause
    assert by_control["fsr"].source_clause == "172(3)(c)"


def test_override_without_a_row_citation_has_no_fabricated_clause():
    rows = [_row("terraces", "max_height", 12.5, clause=None)]
    stds = _build_sepp_housing(rows, "R3", lot_area_m2=500.0)
    overrides = _detect_sepp_lep_overrides(stds, lep_height_m=8.5, lep_fsr=None)
    assert overrides[0].source_clause is None  # no citation, no claim


def test_ineligible_standard_still_never_overrides():
    rows = [
        _row("terraces", "max_height", 12.5, clause="172(3)(b)"),
        _row("terraces", "min_lot_size", 800.0, clause="172(1)"),
    ]
    stds = _build_sepp_housing(rows, "R3", lot_area_m2=500.0)  # 500 < 800 min
    assert stds[0].eligible is False
    assert _detect_sepp_lep_overrides(stds, lep_height_m=8.5, lep_fsr=None) == []


def test_solar_marker_never_calls_the_paid_api():
    """The marker reserves the card slot; the frontend fires the gated route.
    _fetch_solar_marker must be a pure constant — no requests, no key use."""
    import services.intelligence_brief as ib

    assert ib._fetch_solar_marker() == {"decoupled": True}
    import inspect
    src = inspect.getsource(ib._fetch_solar_marker)
    assert "requests" not in src and "GOOGLE" not in src


def test_solar_marker_section_emitted_on_satellite_runs(monkeypatch):
    from tests.test_brief_slice0_failclosed import _TORRENS, _run_generator
    import tests.test_brief_slice0_failclosed as harness
    import services.intelligence_brief as ib

    # extend the all-failed harness to a satellite run
    orig = ib.IntelligenceBriefRequest
    events = None

    def strata(*a, **k):
        return dict(_TORRENS)

    # patch the satellite fetches to fail like everything else
    for fetch in ["_fetch_bushfire", "_fetch_flood", "_fetch_climate_risk",
                  "_fetch_granny_flat_detect", "_fetch_uhi", "_fetch_arr_ifd",
                  "_fetch_firms_hotspots", "_fetch_terrain"]:
        monkeypatch.setattr(ib, fetch, harness._boom)

    import json as _json
    for name in ["_fetch_controls", "_fetch_valuation", "_fetch_contributions",
                 "_fetch_overlays", "_fetch_heritage_postgis", "_fetch_mine_subsidence",
                 "_fetch_contaminated_land", "_fetch_drinking_water_catchment",
                 "_fetch_nearby_das", "_fetch_shadow", "_fetch_dcp_controls",
                 "_fetch_sepp_housing", "_fetch_market_context", "_fetch_land_use_lists",
                 "_fetch_da_outcomes", "_fetch_refusal_stats"]:
        monkeypatch.setattr(ib, name, harness._boom)
    monkeypatch.setattr(ib, "fetch_lot_geometry", harness._boom)
    monkeypatch.setattr(ib, "_fetch_strata", strata)
    monkeypatch.setattr(ib, "fetch_anef_zone", harness._boom)
    import services.portal_constraints as pc
    monkeypatch.setattr(pc, "fetch_anef", harness._boom)
    monkeypatch.setattr(ib, "_sepp_eligibility_results", lambda *a, **k: None)
    monkeypatch.setattr(ib, "detect_former_council", lambda addr, epi: None)
    monkeypatch.setattr(ib, "_validate_former_council_postgis", lambda s, la, ln, a: (s, None))
    monkeypatch.setattr(ib, "_eligibility_excluded_forms", lambda lat, lng: set())
    monkeypatch.setattr(ib, "enrich_gaps_with_verify_url", lambda gaps, slug: gaps)

    req = ib.IntelligenceBriefRequest(address="14 Stanley Street, Concord", include_satellite=True)
    names = []
    solar_payload = None
    for chunk in ib._generate_brief_sse(req, 1456609, -33.86382, 151.10586, None):
        lines = [l for l in chunk.strip().splitlines() if l]
        name = lines[0].removeprefix("event: ")
        data = _json.loads(lines[1].removeprefix("data: "))
        if name == "section" and data.get("section") == "satellite.solar":
            solar_payload = data["data"]
        names.append(data.get("section") or name)
    assert "satellite.solar" in names
    assert solar_payload["value"] == {"decoupled": True}


def test_drift_cron_scope_is_read_only():
    """run_bushfire writes a property_reports row; the cron must never include
    report-writing services (junk rows in production data)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "drift_runner", "scripts/run_brief_drift_check.py")
    src = open("scripts/run_brief_drift_check.py", encoding="utf-8").read()
    assert "_fetch_bushfire" not in src
    assert "run_flood" not in src and "run_terrain" not in src
