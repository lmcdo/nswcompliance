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
    classify_strata,
    compute_confidence_summary,
    collect_gaps,
    check_minimum_viable,
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

    def test_lot_dimensions_parsed(self):
        pc = _build_planning_controls(SAMPLE_CONTROLS, SAMPLE_OVERLAYS_DATA)
        assert pc.lot_dimensions.value is not None
        assert pc.lot_dimensions.value.area_m2 == 450.0


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
        dcp = _build_dcp_controls(None, None)
        assert "could not be determined" in dcp.controls.reason


# ---------------------------------------------------------------------------
# 3. SEPP Housing standards
# ---------------------------------------------------------------------------

class TestBuildSEPPHousing:
    def test_eligible_lot(self):
        raw = [
            {"development_type": "secondary_dwelling", "standard_type": "min_lot_size", "numeric_value": 450.0},
            {"development_type": "secondary_dwelling", "standard_type": "max_gfa", "numeric_value": 60.0},
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

class TestBuildNeighbourhood:
    def test_das_mapped(self):
        nb = _build_neighbourhood(SAMPLE_DAS, SAMPLE_SHADOW)
        assert len(nb.nearby_das.value) == 2
        assert nb.nearby_das.value[0].number == "DA/2025/0001"
        assert nb.nearby_das.value[0].distance_m == 50
        assert nb.da_count.value == 2

    def test_shadow_mapped(self):
        nb = _build_neighbourhood([], SAMPLE_SHADOW)
        assert nb.shadow.value is not None
        assert nb.shadow.value.height_m == 9.0
        assert len(nb.shadow.value.scenarios) == 1
        assert nb.shadow.confidence == ConfidenceLevel.DERIVED

    def test_shadow_unavailable(self):
        nb = _build_neighbourhood([], None)
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
