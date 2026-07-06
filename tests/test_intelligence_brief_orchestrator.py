"""
Intelligence Brief — Stage 2 Orchestrator Tests.

Tests:
  1. Assembly — raw dicts correctly map to DataField-wrapped schema models
  2. Strata routing — apartment → RenovationBrief, house → DevelopmentBrief, ambiguous → RenovationBrief
  3. Fix A — LGA PostGIS validation corrects text-based former council detection
  4. Minimum viable check — >30% not_available → 503
  5. DCP controls — populated when lga_slug found, gap disclosed when missing
  6. SEPP Housing — standards grouped by dev_type, eligibility by lot area
  7. Environmental — overlays mapped, flood_epi derived, bushfire from overlays
  8. Neighbourhood — DAs mapped, shadow result assembled
  9. Economics — valuation mapped, history preserved
  10. Gap collection — not_available fields appear in gaps list
  11. Coordinate validation — outside NSW → 422
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from services.intelligence_brief import (
    CONFIG,
    ConfidenceLevel,
    DataField,
    DevelopmentBrief,
    RenovationBrief,
    StrataType,
    _build_planning_controls,
    _build_dcp_controls,
    _build_sepp_housing,
    _build_environmental,
    _build_neighbourhood,
    _build_economics,
    _validate_coordinates,
    _validate_former_council_postgis,
    _detect_sepp_lep_overrides,
    _select_lot_size_band,
    classify_strata,
    compute_confidence_summary,
    collect_gaps,
    check_minimum_viable,
    SEPPStandard,
    SeppLepOverride,
)
from services.portal_constraints import (
    fetch_mine_subsidence,
    fetch_contaminated_land,
    fetch_drinking_water_catchment,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CONTROLS = {
    "zone": "R2",
    "zone_full": "R2 Low Density Residential",
    "zone_epi": "Inner West Local Environmental Plan 2022",
    "legislation_url": "https://legislation.nsw.gov.au/...",
    "height": "9",
    "fsr": "0.5:1",
    "lot_size": "450",
    "ass_class": "Class 3",
    "heritage_items": [],
    "heritage_hca": ["Heritage Conservation Area (Petersham South)"],
    "sepp_overlays": [{"name": "SEPP Housing 2021"}],
    "housing_sepp": True,
    "tod_area": False,
    "flood_epi": False,
}

SAMPLE_OVERLAYS_DATA = {
    "overlays": [
        {"layer_type": "heritage", "value": "Conservation Area - General", "instrument_key": "IW LEP 2022", "lga": "inner_west"},
        {"layer_type": "flood", "value": "Flood Planning", "instrument_key": "IW LEP 2022", "lga": "inner_west"},
    ],
    "covered_layers": ["heritage", "flood", "bushfire", "biodiversity"],
    "proximity_m": {},
}

SAMPLE_VALUATION = {
    "lot_area_m2": 520.0,
    "land_value": 1450000.0,
    "val_base_date": "2025-07-01",
    "val_history": [
        {"year": "2021-07-01", "value": 950000},
        {"year": "2022-07-01", "value": 1100000},
        {"year": "2023-07-01", "value": 1200000},
        {"year": "2024-07-01", "value": 1350000},
        {"year": "2025-07-01", "value": 1450000},
    ],
}

SAMPLE_DCP = {
    "dcp_name": "Marrickville DCP 2011",
    "section": "Part 2.3",
    "clause_ref": "C1",
    "dcp_url": "https://www.innerwest.nsw.gov.au/...",
    "setbacks": [
        {"control_type": "front_setback", "dev_type": "dwelling_house", "value_min": 5.5, "unit": "m", "clause": "C1"},
        {"control_type": "rear_setback", "dev_type": "dwelling_house", "value_min": 6.0, "unit": "m", "clause": "C2"},
    ],
    "sd_setbacks": [
        {"control_type": "rear_setback", "dev_type": "secondary_dwelling", "value_min": 3.0, "unit": "m", "clause": "C5"},
    ],
}

SAMPLE_DAS = [
    {"number": "DA/2025/0001", "address": "10 Smith St", "distance_m": 50, "status": "Under Assessment", "description": "New dwelling", "lodged": "2025-06-01"},
    {"number": "DA/2025/0002", "address": "22 Smith St", "distance_m": 150, "status": "Approved", "description": "Alterations", "lodged": "2025-03-15"},
]

SAMPLE_SHADOW = {
    "height_m": 9.0,
    "height_source": "LEP height control",
    "adg_compliant": True,
    "scenarios": [
        {"date_label": "Jun 21 (winter solstice)", "time_label": "9:00 AM", "sun_altitude_deg": 22.5, "sun_azimuth_deg": 42.0, "shadow_length_m": 21.7, "overlap_pct": 15.3},
    ],
    "worst_case_scenario": "Jun 21 9:00 AM",
}


# ---------------------------------------------------------------------------
# 1. Planning controls assembly
# ---------------------------------------------------------------------------

class TestBuildPlanningControls:
    def test_maps_all_fields(self):
        pc = _build_planning_controls(SAMPLE_CONTROLS, SAMPLE_OVERLAYS_DATA)
        assert pc.zone.value == "R2"
        assert pc.zone.confidence == ConfidenceLevel.AUTHORITATIVE
        assert pc.zone.source == "planning_portal"
        assert pc.height.value == "9"
        assert pc.fsr.value == "0.5:1"
        assert pc.housing_sepp.value is True
        assert pc.tod_area.value is False

    def test_empty_controls(self):
        pc = _build_planning_controls({}, {})
        assert pc.zone.value is None
        assert pc.zone.confidence == ConfidenceLevel.AUTHORITATIVE  # still authoritative (portal returned nothing)

    def test_lot_dimensions_uses_real_area_not_min_lot_size(self):
        # Regression: area must come from the authoritative lot_area_m2, NOT
        # controls['lot_size'] (the LEP minimum-lot-size standard). The old code
        # displayed the min-lot-size as the lot's area.
        pc = _build_planning_controls(
            SAMPLE_CONTROLS, SAMPLE_OVERLAYS_DATA, lot_area_m2=612.0
        )
        assert pc.lot_dimensions.value is not None
        assert pc.lot_dimensions.value.area_m2 == 612.0
        assert pc.lot_dimensions.value.area_m2 != 450.0  # not the min-lot-size

    def test_lot_dimensions_none_without_area_or_geometry(self):
        # No geometry and no real area → no fabricated area from min-lot-size.
        pc = _build_planning_controls(SAMPLE_CONTROLS, SAMPLE_OVERLAYS_DATA)
        assert pc.lot_dimensions.value is None


# ---------------------------------------------------------------------------
# 2. DCP controls assembly
# ---------------------------------------------------------------------------

class TestBuildDCPControls:
    def test_populated_dcp(self):
        dcp = _build_dcp_controls(SAMPLE_DCP, "marrickville")
        assert dcp.dcp_name.value == "Marrickville DCP 2011"
        assert dcp.dcp_url.value is not None
        assert len(dcp.controls.value) == 3  # 2 DH + 1 SD
        assert dcp.controls.confidence == ConfidenceLevel.EXTRACTED

    def test_none_dcp_with_lga(self):
        dcp = _build_dcp_controls(None, "canterbury")
        assert dcp.controls.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert "canterbury" in dcp.controls.reason

    def test_none_dcp_no_lga(self):
        # No slug = council not in the DCP-onboarded set. The reason must say
        # "not onboarded" (frontend routes it to an honest "Not assessed" card)
        # and must NOT say "could not" (which used to render as "Address not
        # matched — check the address", blaming the user for a coverage gap).
        dcp = _build_dcp_controls(None, None)
        assert "not onboarded" in dcp.controls.reason
        assert "could not" not in dcp.controls.reason

    def test_nonnumeric_requirement_does_not_crash(self):
        # Regression: some councils (e.g. Penrith, Inner West) store a free-text
        # 'requirement' like "No maximum site coverage...". The old code forced it
        # into the numeric value_min field, raising a Pydantic ValidationError that
        # 500'd the whole brief. It must coerce to None and keep the text as a note.
        dcp = _build_dcp_controls(
            {
                "dcp_name": "Test DCP",
                "setbacks": [
                    {
                        "control_type": "site_coverage",
                        "dev_type": "dwelling_house",
                        "requirement": "No maximum site coverage; refer to height limits in the LEP.",
                        "unit": "%",
                    },
                    {
                        "control_type": "front_setback",
                        "dev_type": "dwelling_house",
                        "value_min": "6.5",
                        "unit": "m",
                    },
                ],
            },
            "penrith",
        )
        ctrls = dcp.controls.value
        assert len(ctrls) == 2
        # Non-numeric requirement: coerced to None, text preserved as condition
        assert ctrls[0].value_min is None
        assert "No maximum site coverage" in (ctrls[0].condition or "")
        # Numeric value still parses correctly
        assert ctrls[1].value_min == 6.5


def test_safe_brief_sse_emits_error_event_on_exception(monkeypatch):
    # Regression: a mid-stream exception must surface as an `error` SSE event,
    # not silently terminate the stream (which left the UI hanging at last %).
    from services import intelligence_brief as ib

    def boom(*args, **kwargs):
        yield ib._sse_event("metadata", {"ok": True})
        raise RuntimeError("kaboom mid stream")

    monkeypatch.setattr(ib, "_generate_brief_sse", boom)
    events = list(ib._safe_brief_sse(MagicMock(), None, -33.8, 151.1, None))
    # The metadata event still passes through, then an error event is appended.
    assert any("event: metadata" in e for e in events)
    assert any("event: error" in e for e in events)
    assert any("kaboom mid stream" in e for e in events)


# ---------------------------------------------------------------------------
# 3. SEPP Housing standards
# ---------------------------------------------------------------------------

class TestBuildSEPPHousing:
    def test_eligible_lot(self):
        raw = [
            {"development_type": "secondary_dwelling", "standard_type": "min_lot_size", "numeric_value": 450.0},
            {"development_type": "secondary_dwelling", "standard_type": "max_floor_area", "numeric_value": 60.0},
        ]
        result = _build_sepp_housing(raw, "R2", 520.0)
        assert len(result) == 1
        assert result[0].dev_type == "secondary_dwelling"
        assert result[0].eligible is True
        assert result[0].min_lot_area_m2 == 450.0

    def test_ineligible_lot(self):
        raw = [
            {"development_type": "secondary_dwelling", "standard_type": "min_lot_size", "numeric_value": 450.0},
        ]
        result = _build_sepp_housing(raw, "R2", 400.0)
        assert result[0].eligible is False
        assert "400" in result[0].reason_ineligible

    def test_empty_standards(self):
        result = _build_sepp_housing([], "R2", 520.0)
        assert result == []


# ---------------------------------------------------------------------------
# 4. Environmental constraints
# ---------------------------------------------------------------------------

class TestBuildEnvironmental:
    def test_flood_from_overlays(self):
        env = _build_environmental({}, SAMPLE_OVERLAYS_DATA, None)
        assert env.flood_epi.value is True

    def test_no_flood(self):
        env = _build_environmental({}, {"overlays": [], "covered_layers": []}, None)
        assert env.flood_epi.value is False

    def test_heritage_postgis_populated(self):
        heritage = {"hca": ["HCA 1"], "items": [], "has_heritage": True, "raw": []}
        env = _build_environmental({}, SAMPLE_OVERLAYS_DATA, heritage)
        assert env.heritage_postgis.value is not None
        assert env.heritage_postgis.confidence == ConfidenceLevel.AUTHORITATIVE

    def test_heritage_postgis_empty(self):
        heritage = {"hca": [], "items": [], "has_heritage": False, "raw": []}
        env = _build_environmental({}, SAMPLE_OVERLAYS_DATA, heritage)
        assert env.heritage_postgis.value is None

    def test_mine_subsidence_populated(self):
        mine_data = {"in_district": True, "district_name": "Newcastle", "last_update": "2024-01-01"}
        env = _build_environmental({}, SAMPLE_OVERLAYS_DATA, None, mine_subsidence_raw=mine_data)
        assert env.mine_subsidence.value is True
        assert env.mine_subsidence.confidence == ConfidenceLevel.AUTHORITATIVE

    def test_mine_subsidence_absent(self):
        env = _build_environmental({}, SAMPLE_OVERLAYS_DATA, None, mine_subsidence_raw=None)
        assert env.mine_subsidence.value is False  # not in district
        assert env.mine_subsidence.confidence == ConfidenceLevel.AUTHORITATIVE

    def test_contaminated_land_populated(self):
        contam_data = {"has_notified_sites": True, "site_count": 2, "nearest_site": {"name": "Test", "distance_m": 150}}
        env = _build_environmental({}, SAMPLE_OVERLAYS_DATA, None, contaminated_land_raw=contam_data)
        assert env.contaminated_land.value is True
        assert env.contaminated_land.confidence == ConfidenceLevel.AUTHORITATIVE

    def test_contaminated_land_absent(self):
        env = _build_environmental({}, SAMPLE_OVERLAYS_DATA, None, contaminated_land_raw=None)
        assert env.contaminated_land.value is False

    def test_drinking_water_populated(self):
        dw_data = {"in_catchment": True, "epi_name": "Sydney DWC"}
        env = _build_environmental({}, SAMPLE_OVERLAYS_DATA, None, drinking_water_raw=dw_data)
        assert env.drinking_water_catchment.value is True
        assert env.drinking_water_catchment.confidence == ConfidenceLevel.AUTHORITATIVE

    def test_drinking_water_absent(self):
        env = _build_environmental({}, SAMPLE_OVERLAYS_DATA, None, drinking_water_raw=None)
        assert env.drinking_water_catchment.value is False

    def test_biodiversity_from_overlays(self):
        data = {
            "overlays": [
                {"layer_type": "biodiversity", "value": "Terrestrial Biodiversity"},
            ],
            "covered_layers": ["biodiversity"],
        }
        env = _build_environmental({}, data, None)
        assert env.terrestrial_biodiversity.value is True
        assert env.terrestrial_biodiversity.confidence == ConfidenceLevel.AUTHORITATIVE

    def test_biodiversity_absent_but_covered(self):
        data = {
            "overlays": [],
            "covered_layers": ["biodiversity"],
        }
        env = _build_environmental({}, data, None)
        assert env.terrestrial_biodiversity.value is False

    def test_biodiversity_not_covered(self):
        data = {"overlays": [], "covered_layers": []}
        env = _build_environmental({}, data, None)
        assert env.terrestrial_biodiversity.value is None
        assert env.terrestrial_biodiversity.confidence == ConfidenceLevel.NOT_AVAILABLE


# ---------------------------------------------------------------------------
# 4b. Portal constraint fetcher tests (HTTP-mocked)
# ---------------------------------------------------------------------------

class TestFetchMineSubsidence:
    @patch("services.portal_constraints.requests.get")
    def test_in_district(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"features": [{"attributes": {"districtname": "Newcastle", "lastupdate": "2024-06-01"}}]},
        )
        result = fetch_mine_subsidence(-32.92, 151.78)
        assert result["in_district"] is True
        assert result["district_name"] == "Newcastle"
        assert result["last_update"] == "2024-06-01"

    @patch("services.portal_constraints.requests.get")
    def test_outside_district(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"features": []},
        )
        result = fetch_mine_subsidence(-33.87, 151.21)
        assert result is None

    @patch("services.portal_constraints.requests.get")
    def test_http_error_propagates(self, mock_get):
        mock_get.return_value = MagicMock(status_code=500)
        mock_get.return_value.raise_for_status.side_effect = Exception("500 Server Error")
        with pytest.raises(Exception, match="500"):
            fetch_mine_subsidence(-33.87, 151.21)


class TestFetchContaminatedLand:
    @patch("services.portal_constraints.requests.get")
    def test_sites_found(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"features": [
                {
                    "attributes": {
                        "SiteName": "Former Gas Works",
                        "SiteStreet": "123 Main St",
                        "Suburb": "Testville",
                        "ManagementClass": "Remediation",
                        "ContaminationActivityType": "Gasworks",
                    },
                    "geometry": {"x": 151.21, "y": -33.87},
                },
                {
                    "attributes": {"SiteName": "Old Depot"},
                    "geometry": {"x": 151.215, "y": -33.875},
                },
            ]},
        )
        result = fetch_contaminated_land(-33.88, 151.20)
        assert result["has_notified_sites"] is True
        assert result["site_count"] == 2
        assert result["nearest_site"]["name"] == "Former Gas Works"
        assert result["nearest_site"]["distance_m"] is not None

    @patch("services.portal_constraints.requests.get")
    def test_no_sites(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"features": []},
        )
        result = fetch_contaminated_land(-33.88, 151.20)
        assert result is None

    @patch("services.portal_constraints.requests.get")
    def test_missing_geometry_still_works(self, mock_get):
        """Site returned but no geometry → distance_m is None, not a crash."""
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"features": [{"attributes": {"SiteName": "Test"}, "geometry": {}}]},
        )
        result = fetch_contaminated_land(-33.88, 151.20)
        assert result["has_notified_sites"] is True
        assert result["nearest_site"]["distance_m"] is None


class TestFetchDrinkingWaterCatchment:
    @patch("services.portal_constraints.requests.get")
    def test_in_catchment(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"features": [{"attributes": {"EPI_NAME": "Sydney Drinking Water Catchment", "LGA_NAME": "Wollondilly"}}]},
        )
        result = fetch_drinking_water_catchment(-34.30, 150.50)
        assert result["in_catchment"] is True
        assert result["epi_name"] == "Sydney Drinking Water Catchment"
        assert result["lga_name"] == "Wollondilly"

    @patch("services.portal_constraints.requests.get")
    def test_outside_catchment(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"features": []},
        )
        result = fetch_drinking_water_catchment(-33.87, 151.21)
        assert result is None


# ---------------------------------------------------------------------------
# 5. Neighbourhood assembly
# ---------------------------------------------------------------------------

def _da_ok(das: list) -> DataField:
    """A successful DA lookup (the query ran) — wraps the list AUTHORITATIVE."""
    return DataField(value=das, confidence=ConfidenceLevel.AUTHORITATIVE, source="eplanning_da_api")


def _da_failed() -> DataField:
    """A failed/timed-out DA lookup — value None, NOT_AVAILABLE, with a reason."""
    return DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                     source="eplanning_da_api", reason="Timeout after 15.0s")


class TestBuildNeighbourhood:
    def test_das_mapped(self):
        nb = _build_neighbourhood(_da_ok(SAMPLE_DAS), SAMPLE_SHADOW)
        assert len(nb.nearby_das.value) == 2
        assert nb.nearby_das.value[0].number == "DA/2025/0001"
        assert nb.nearby_das.value[0].distance_m == 50
        assert nb.da_count.value == 2

    def test_genuine_empty_stays_authoritative_zero(self):
        # The query RAN and found none → 0 is a real, authoritative answer.
        nb = _build_neighbourhood(_da_ok([]), SAMPLE_SHADOW)
        assert nb.da_count.value == 0
        assert nb.da_count.confidence == ConfidenceLevel.AUTHORITATIVE
        assert nb.nearby_das.confidence == ConfidenceLevel.AUTHORITATIVE

    def test_failed_lookup_is_not_authoritative_zero(self):
        # REGRESSION GUARD: a failed lookup must NOT be served as "0 DAs, authoritative".
        nb = _build_neighbourhood(_da_failed(), SAMPLE_SHADOW)
        assert nb.da_count.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert nb.da_count.value is None
        assert nb.nearby_das.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert nb.nearby_das.value is None
        assert nb.da_count.reason  # carries the failure reason, not a silent 0

    def test_shadow_mapped(self):
        nb = _build_neighbourhood(_da_ok([]), SAMPLE_SHADOW)
        assert nb.shadow.value is not None
        assert nb.shadow.value.height_m == 9.0
        assert len(nb.shadow.value.scenarios) == 1
        assert nb.shadow.confidence == ConfidenceLevel.DERIVED

    def test_shadow_unavailable(self):
        nb = _build_neighbourhood(_da_ok([]), None)
        assert nb.shadow.value is None
        assert nb.shadow.confidence == ConfidenceLevel.NOT_AVAILABLE


# ---------------------------------------------------------------------------
# 6. Economics assembly
# ---------------------------------------------------------------------------

class TestBuildEconomics:
    def test_full_valuation(self):
        econ = _build_economics(SAMPLE_VALUATION)
        assert econ.land_value.value == 1450000
        assert econ.lot_area_m2.value == 520.0
        assert len(econ.val_history.value) == 5

    def test_empty_valuation(self):
        econ = _build_economics({"lot_area_m2": None, "land_value": None, "val_base_date": None, "val_history": []})
        assert econ.land_value.value is None
        assert econ.land_value.confidence == ConfidenceLevel.NOT_AVAILABLE


# ---------------------------------------------------------------------------
# 7. Strata routing
# ---------------------------------------------------------------------------

class TestStrataRouting:
    def test_apartment_strata(self):
        st = classify_strata({"is_strata": True}, 3000.0)
        assert st == StrataType.APARTMENT

    def test_strata_house_small_lot(self):
        st = classify_strata({"is_strata": True}, 350.0)
        assert st == StrataType.DEVELOPMENT

    def test_ambiguous_strata(self):
        st = classify_strata({"is_strata": True}, 600.0)
        assert st == StrataType.AMBIGUOUS

    def test_not_strata(self):
        st = classify_strata({"is_strata": False}, 520.0)
        assert st == StrataType.NOT_STRATA

    def test_community_title(self):
        st = classify_strata({"is_strata": True, "plan_type": "Community"}, 2000.0)
        assert st == StrataType.DEVELOPMENT


# ---------------------------------------------------------------------------
# 8. Coordinate validation
# ---------------------------------------------------------------------------

class TestCoordinateValidation:
    def test_valid_sydney(self):
        assert _validate_coordinates(-33.87, 151.21) is None

    def test_outside_lat(self):
        result = _validate_coordinates(-40.0, 151.0)
        assert result is not None
        assert "Latitude" in result

    def test_outside_lng(self):
        result = _validate_coordinates(-33.0, 160.0)
        assert result is not None
        assert "Longitude" in result


# ---------------------------------------------------------------------------
# 9. Fix A — LGA PostGIS validation
# ---------------------------------------------------------------------------

class TestFixA:
    @patch("services.intelligence_brief._get_db_conn")
    @patch("services.intelligence_brief.lookup_lga")
    def test_postgis_corrects_inner_west_boundary(self, mock_lookup, mock_conn):
        """Stanmore property in City of Sydney should NOT get Inner West DCP."""
        mock_conn.return_value = MagicMock()
        mock_lookup.return_value = {"lga_name": "City of Sydney", "lga_slug": "city_of_sydney"}

        slug, advisory = _validate_former_council_postgis(
            "marrickville", -33.89, 151.17, "1 Stanmore Rd",
        )
        assert slug is None  # PostGIS says not Inner West
        assert advisory is not None
        assert "city of sydney" in advisory.lower()

    @patch("services.intelligence_brief._get_db_conn")
    @patch("services.intelligence_brief.lookup_lga")
    def test_postgis_confirms_inner_west(self, mock_lookup, mock_conn):
        """Property genuinely in Inner West keeps text slug."""
        mock_conn.return_value = MagicMock()
        mock_lookup.return_value = {"lga_name": "Inner West", "lga_slug": "marrickville"}

        slug, advisory = _validate_former_council_postgis(
            "marrickville", -33.90, 151.16, "10 Petersham St",
        )
        assert slug == "marrickville"
        assert advisory is None

    @patch("services.intelligence_brief._get_db_conn")
    @patch("services.intelligence_brief.lookup_lga")
    def test_postgis_resolves_unmapped(self, mock_lookup, mock_conn):
        """Text match returned None but PostGIS finds the former council."""
        mock_conn.return_value = MagicMock()
        mock_lookup.return_value = {"lga_name": "Inner West", "lga_slug": "leichhardt"}

        slug, advisory = _validate_former_council_postgis(
            None, -33.88, 151.15, "5 Norton St Leichhardt",
        )
        assert slug == "leichhardt"
        assert advisory is not None

    @patch("services.intelligence_brief._get_db_conn")
    def test_db_failure_trusts_text(self, mock_conn):
        """If PostGIS is down, fall back to text match."""
        mock_conn.side_effect = Exception("connection refused")

        slug, advisory = _validate_former_council_postgis(
            "marrickville", -33.90, 151.16, "10 Petersham St",
        )
        assert slug == "marrickville"
        assert advisory is None


# ---------------------------------------------------------------------------
# 10. Minimum viable brief
# ---------------------------------------------------------------------------

class TestMinimumViable:
    def test_all_available(self):
        summary = compute_confidence_summary(_make_brief_with_n_available(20, 0))
        assert check_minimum_viable(summary) is True

    def test_30pct_failed(self):
        """Exactly 30% not_available → should still pass (>=70% available)."""
        summary = compute_confidence_summary(_make_brief_with_n_available(7, 3))
        assert check_minimum_viable(summary) is True

    def test_over_30pct_failed(self):
        """More than 30% of total fields not_available → should fail.
        Brief has ~32 DataFields total, so 11+ must fail."""
        summary = compute_confidence_summary(_make_brief_with_n_available(0, 11))
        assert check_minimum_viable(summary) is False


def _make_brief_with_n_available(n_ok: int, n_fail: int) -> DevelopmentBrief:
    """Helper: create a brief with a controlled number of not_available fields.

    The brief has ~32 DataFields total. n_fail controls how many are NOT_AVAILABLE,
    spread across all sections.
    """
    today = date.today().isoformat()
    ok = ConfidenceLevel.AUTHORITATIVE
    fail = ConfidenceLevel.NOT_AVAILABLE

    # Track which index to fail at
    fail_idx = 0

    def _conf():
        nonlocal fail_idx
        if fail_idx < n_fail:
            fail_idx += 1
            return fail
        return ok

    from services.intelligence_brief import (
        DCPControls, EnvironmentalConstraints, Neighbourhood,
        Economics, StrataInfo, ValuationHistory,
    )

    pc = PlanningControls(
        zone=DataField(value="R2", confidence=_conf(), source="test", as_at=today),
        zone_full=DataField(value="R2 Low Density", confidence=_conf(), source="test", as_at=today),
        zone_epi=DataField(value="Test LEP", confidence=_conf(), source="test", as_at=today),
        legislation_url=DataField(value=None, confidence=_conf(), source="test", as_at=today),
        height=DataField(value="9", confidence=_conf(), source="test", as_at=today),
        fsr=DataField(value="0.5:1", confidence=_conf(), source="test", as_at=today),
        lot_size=DataField(value="450", confidence=_conf(), source="test", as_at=today),
        acid_sulfate_class=DataField(value=None, confidence=_conf(), source="test", as_at=today),
        heritage_items=DataField(value=[], confidence=_conf(), source="test", as_at=today),
        heritage_hca=DataField(value=[], confidence=_conf(), source="test", as_at=today),
        sepp_overlays=DataField(value=[], confidence=_conf(), source="test", as_at=today),
        housing_sepp=DataField(value=False, confidence=_conf(), source="test", as_at=today),
        tod_area=DataField(value=False, confidence=_conf(), source="test", as_at=today),
        lot_dimensions=DataField(value=None, confidence=_conf(), source="test", as_at=today),
        # Slice-1 land-use lists — participate in the controlled ok/fail spread
        # like every other DataField so the viability ratios stay exact.
        permitted_uses=DataField(value=["dwelling_house"], confidence=_conf(), source="test", as_at=today),
        prohibited_uses=DataField(value=["heavy_industry"], confidence=_conf(), source="test", as_at=today),
    )

    return DevelopmentBrief(
        address="Test",
        lat=-33.9,
        lng=151.2,
        run_date=today,
        strata=DataField(value=StrataInfo(is_strata=False, strata_type=StrataType.NOT_STRATA), confidence=_conf(), source="test", as_at=today),
        planning_controls=pc,
        dcp_controls=DCPControls(
            controls=DataField(value=[], confidence=_conf(), source="test", as_at=today),
            dcp_name=DataField(value=None, confidence=_conf(), source="test", as_at=today),
            dcp_url=DataField(value=None, confidence=_conf(), source="test", as_at=today),
            section_ref=DataField(value=None, confidence=_conf(), source="test", as_at=today),
        ),
        sepp_housing=DataField(value=[], confidence=_conf(), source="test", as_at=today),
        environmental_constraints=EnvironmentalConstraints(
            flood_epi=DataField(value=False, confidence=_conf(), source="test", as_at=today),
            overlays=DataField(value=[], confidence=_conf(), source="test", as_at=today),
            overlay_coverage=DataField(value=[], confidence=_conf(), source="test", as_at=today),
            bushfire_designation=DataField(value=None, confidence=_conf(), source="test", as_at=today),
            heritage_postgis=DataField(value=None, confidence=_conf(), source="test", as_at=today),
            # Slice-2 detail fields — inside the controlled ok/fail spread so
            # the viability-ratio tests stay exact.
            anef_level=DataField(value=None, confidence=_conf(), source="test", as_at=today),
            nearest_features=DataField(value={"flood": 830}, confidence=_conf(), source="test", as_at=today),
            contaminated_detail=DataField(value=None, confidence=_conf(), source="test", as_at=today),
            mine_subsidence_district=DataField(value=None, confidence=_conf(), source="test", as_at=today),
        ),
        neighbourhood=Neighbourhood(
            nearby_das=DataField(value=[], confidence=_conf(), source="test", as_at=today),
            da_count=DataField(value=0, confidence=_conf(), source="test", as_at=today),
            shadow=DataField(value=None, confidence=_conf(), source="test", as_at=today),
        ),
        economics=Economics(
            land_value=DataField(value=None, confidence=_conf(), source="test", as_at=today),
            val_base_date=DataField(value=None, confidence=_conf(), source="test", as_at=today),
            val_history=DataField(value=[], confidence=_conf(), source="test", as_at=today),
            lot_area_m2=DataField(value=None, confidence=_conf(), source="test", as_at=today),
        ),
        confidence_summary=ConfidenceSummary(),
    )


# Need explicit import for the helper
from services.intelligence_brief import (
    PlanningControls, ConfidenceSummary, DCPControls,
    EnvironmentalConstraints, Neighbourhood, Economics,
    StrataInfo, ValuationHistory,
)


# ---------------------------------------------------------------------------
# Lot-size band selection tests
# ---------------------------------------------------------------------------

class TestSelectLotSizeBand:
    """Test _select_lot_size_band for lot-size-banded SEPP standards."""

    def test_under_band(self):
        vals = {
            "max_site_coverage_lot_under_900": 50.0,
            "max_site_coverage_lot_900_to_1500": 40.0,
            "max_site_coverage_lot_over_1500": 30.0,
        }
        assert _select_lot_size_band(vals, 500.0, "max_site_coverage") == 50.0

    def test_mid_band(self):
        vals = {
            "max_site_coverage_lot_under_900": 50.0,
            "max_site_coverage_lot_900_to_1500": 40.0,
            "max_site_coverage_lot_over_1500": 30.0,
        }
        assert _select_lot_size_band(vals, 1000.0, "max_site_coverage") == 40.0

    def test_over_band(self):
        vals = {
            "max_site_coverage_lot_under_900": 50.0,
            "max_site_coverage_lot_900_to_1500": 40.0,
            "max_site_coverage_lot_over_1500": 30.0,
        }
        assert _select_lot_size_band(vals, 2000.0, "max_site_coverage") == 30.0

    def test_no_lot_area(self):
        vals = {"max_site_coverage_lot_under_900": 50.0}
        assert _select_lot_size_band(vals, None, "max_site_coverage") is None

    def test_no_banded_keys(self):
        vals = {"max_height": 3.8}
        assert _select_lot_size_band(vals, 500.0, "max_site_coverage") is None

    def test_boundary_at_900(self):
        vals = {
            "max_site_coverage_lot_under_900": 50.0,
            "max_site_coverage_lot_900_to_1500": 40.0,
        }
        # 900m² should hit the 900_to_1500 band (under uses < threshold)
        assert _select_lot_size_band(vals, 900.0, "max_site_coverage") == 40.0

    def test_floor_area_bands(self):
        vals = {
            "max_total_floor_area_lot_under_600": 330.0,
            "max_total_floor_area_lot_600_to_900": 380.0,
            "max_total_floor_area_lot_over_900": 430.0,
        }
        assert _select_lot_size_band(vals, 450.0, "max_total_floor_area") == 330.0
        assert _select_lot_size_band(vals, 700.0, "max_total_floor_area") == 380.0
        assert _select_lot_size_band(vals, 1200.0, "max_total_floor_area") == 430.0


# ---------------------------------------------------------------------------
# Secondary dwelling standard mapping tests
# ---------------------------------------------------------------------------

class TestBuildSEPPHousingSecondaryDwelling:
    """Test _build_sepp_housing with secondary_dwelling standards."""

    def test_max_floor_area_maps_to_max_gfa(self):
        """Migration 045 uses 'max_floor_area', model field is 'max_gfa_m2'."""
        raw = [
            {"development_type": "secondary_dwelling", "standard_type": "min_lot_size", "numeric_value": 450},
            {"development_type": "secondary_dwelling", "standard_type": "max_floor_area", "numeric_value": 60},
        ]
        result = _build_sepp_housing(raw, "R2", 500.0)
        assert len(result) == 1
        assert result[0].dev_type == "secondary_dwelling"
        assert result[0].max_gfa_m2 == 60.0
        assert result[0].max_fsr is None  # secondary_dwelling has no FSR ratio
        assert result[0].eligible is True

    def test_max_fsr_maps_for_lmr(self):
        """LMR types use 'max_fsr' standard_type — must map to max_fsr field, not max_gfa_m2."""
        raw = [
            {"development_type": "low_rise_medium_density", "standard_type": "min_lot_size", "numeric_value": 600},
            {"development_type": "low_rise_medium_density", "standard_type": "max_fsr", "numeric_value": 0.65},
            {"development_type": "low_rise_medium_density", "standard_type": "max_height", "numeric_value": 9.0},
        ]
        result = _build_sepp_housing(raw, "R2", 700.0)
        assert len(result) == 1
        assert result[0].max_fsr == 0.65
        assert result[0].max_gfa_m2 is None  # max_fsr is not absolute floor area
        assert result[0].max_height_m == 9.0

    def test_extended_fields_populated(self):
        """Migration 047 standards map to new SEPPStandard fields."""
        raw = [
            {"development_type": "secondary_dwelling", "standard_type": "min_lot_size", "numeric_value": 450},
            {"development_type": "secondary_dwelling", "standard_type": "min_lot_width", "numeric_value": 12},
            {"development_type": "secondary_dwelling", "standard_type": "parking_per_dwelling", "numeric_value": 0},
            {"development_type": "secondary_dwelling", "standard_type": "max_height", "numeric_value": 3.8},
            {"development_type": "secondary_dwelling", "standard_type": "min_private_open_space", "numeric_value": 24},
            {"development_type": "secondary_dwelling", "standard_type": "max_site_coverage_lot_under_900", "numeric_value": 50},
            {"development_type": "secondary_dwelling", "standard_type": "max_site_coverage_lot_900_to_1500", "numeric_value": 40},
        ]
        result = _build_sepp_housing(raw, "R2", 500.0)
        sd = result[0]
        assert sd.min_lot_width_m == 12.0
        assert sd.parking_spaces == 0.0
        assert sd.max_height_m == 3.8
        assert sd.min_private_open_space_m2 == 24.0
        assert sd.max_site_coverage_pct == 50.0  # 500m² < 900 → under band

    def test_ineligible_lot(self):
        raw = [
            {"development_type": "secondary_dwelling", "standard_type": "min_lot_size", "numeric_value": 450},
        ]
        result = _build_sepp_housing(raw, "R2", 400.0)
        assert result[0].eligible is False
        assert "400" in result[0].reason_ineligible
        assert "450" in result[0].reason_ineligible


# ---------------------------------------------------------------------------
# SEPP-LEP override detection tests
# ---------------------------------------------------------------------------

class TestSeppLepOverrides:
    """Test _detect_sepp_lep_overrides — SEPP overrides LEP where more generous."""

    def test_height_override_detected(self):
        standards = [SEPPStandard(dev_type="low_rise", eligible=True, max_height_m=12.0)]
        overrides = _detect_sepp_lep_overrides(standards, lep_height_m=9.0, lep_fsr=None)
        assert len(overrides) == 1
        assert overrides[0].control == "height"
        assert overrides[0].lep_value == 9.0
        assert overrides[0].sepp_value == 12.0

    def test_no_override_when_lep_higher(self):
        standards = [SEPPStandard(dev_type="low_rise", eligible=True, max_height_m=9.0)]
        overrides = _detect_sepp_lep_overrides(standards, lep_height_m=12.0, lep_fsr=None)
        assert len(overrides) == 0

    def test_no_override_when_equal(self):
        standards = [SEPPStandard(dev_type="low_rise", eligible=True, max_height_m=9.0)]
        overrides = _detect_sepp_lep_overrides(standards, lep_height_m=9.0, lep_fsr=None)
        assert len(overrides) == 0

    def test_no_override_when_lep_missing(self):
        standards = [SEPPStandard(dev_type="low_rise", eligible=True, max_height_m=12.0)]
        overrides = _detect_sepp_lep_overrides(standards, lep_height_m=None, lep_fsr=None)
        assert len(overrides) == 0

    def test_secondary_dwelling_skips_fsr(self):
        """Secondary dwelling has max_gfa_m2 (absolute 60m²), not max_fsr — no FSR override."""
        standards = [SEPPStandard(dev_type="secondary_dwelling", eligible=True, max_gfa_m2=60.0)]
        overrides = _detect_sepp_lep_overrides(standards, lep_height_m=None, lep_fsr=0.5)
        assert len(overrides) == 0

    def test_lmr_fsr_override_detected(self):
        standards = [SEPPStandard(dev_type="low_rise", eligible=True, max_fsr=0.8)]
        overrides = _detect_sepp_lep_overrides(standards, lep_height_m=None, lep_fsr=0.5)
        assert len(overrides) == 1
        assert overrides[0].control == "fsr"

    def test_multiple_dev_types(self):
        standards = [
            SEPPStandard(dev_type="low_rise", eligible=True, max_height_m=12.0),
            SEPPStandard(dev_type="secondary_dwelling", eligible=True, max_height_m=3.8),
        ]
        overrides = _detect_sepp_lep_overrides(standards, lep_height_m=9.0, lep_fsr=None)
        # Only low_rise should override (12 > 9), not secondary_dwelling (3.8 < 9)
        assert len(overrides) == 1
        assert overrides[0].dev_type == "low_rise"
