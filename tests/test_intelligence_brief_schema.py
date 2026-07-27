"""
Intelligence Brief — Stage 1 Schema Tests.

Tests:
  1. Fixture validation — 4 hand-crafted briefs (house, apartment, townhouse, rural)
  2. DataField semantics — three-state distinction
  3. Strata classification — boundary values, spike edge cases
  4. Input validation — adversarial request payloads
  5. Confidence summary — tally correctness
  6. Gap collection — not_available fields surface as gaps
  7. Minimum viable brief — threshold enforcement
  8. _zone_prefix — empty/null/weird string handling
  9. _sanitise — HTML, null bytes, edge cases
  10. classify_strata — all four states, boundary lot areas
"""
import pytest
from pydantic import ValidationError

from services.intelligence_brief import (
    CONFIG,
    CompoundConstraint,
    CompoundSeverity,
    ConfidenceLevel,
    ConfidenceSummary,
    DCPControl,
    DCPControls,
    DataField,
    DevelopmentBrief,
    Economics,
    EnvironmentalConstraints,
    EnvironmentalOverlay,
    GapEntry,
    IntelligenceBriefRequest,
    LotDimensions,
    NearbyDA,
    Neighbourhood,
    PlanningControls,
    RenovationBrief,
    SEPPStandard,
    ShadowResult,
    ShadowScenario,
    StrataInfo,
    StrataType,
    ValuationHistory,
    _sanitise,
    _zone_prefix,
    check_minimum_viable,
    classify_strata,
    collect_gaps,
    compute_confidence_summary,
)


# ---------------------------------------------------------------------------
# Fixture builders — real data shapes from spike-results.json
# ---------------------------------------------------------------------------


def _auth(value, source="NSW Planning Portal"):
    return DataField(value=value, confidence=ConfidenceLevel.AUTHORITATIVE, source=source)


def _extracted(value, source="PlotDetect DCP extraction"):
    return DataField(value=value, confidence=ConfidenceLevel.EXTRACTED, source=source)


def _not_available(source, reason="API timeout"):
    return DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE, source=source, reason=reason)


def _make_planning_controls(**overrides):
    defaults = dict(
        zone=_auth("R2"),
        zone_full=_auth("Low Density Residential"),
        zone_epi=_auth("Inner West Local Environmental Plan 2022"),
        legislation_url=_auth("https://legislation.nsw.gov.au/..."),
        height=_auth("9.5"),
        fsr=_auth("0.6"),
        lot_size=_auth("450"),
        acid_sulfate_class=_auth(None),
        heritage_items=_auth([]),
        heritage_hca=_auth([]),
        sepp_overlays=_auth([]),
        housing_sepp=_auth(False),
        tod_area=_auth(False),
        lot_dimensions=_auth(LotDimensions(area_m2=467.0)),
        # Slice-1 land-use lists — populated on the fully-available fixture so
        # gap-collection tests keep meaning "this brief has zero gaps".
        permitted_uses=_auth(["dwelling_house", "dual_occupancy"]),
        prohibited_uses=_auth(["heavy_industry"]),
    )
    defaults.update(overrides)
    return PlanningControls(**defaults)


def _make_env_constraints(**overrides):
    defaults = dict(
        flood_epi=_auth(False),
        overlays=_auth([]),
        overlay_coverage=_auth(["flood", "bushfire", "biodiversity", "heritage"]),
        bushfire_designation=_auth(None),
        heritage_postgis=_auth(None),
        mine_subsidence=_auth(False),
        contaminated_land=_auth(False),
        drinking_water_catchment=_auth(False),
        terrestrial_biodiversity=_auth(False),
        riparian_land=_auth(False),
        wetlands=_auth(False),
        anef=_auth(None),
        coastal_hazards=_auth(None),
        # Slice-2 detail fields — populated on the fully-available fixture so
        # gap-collection tests keep meaning "this brief has zero gaps".
        anef_level=_auth(None),
        nearest_features=_auth({"flood": 830}),
        contaminated_detail=_auth(None),
        mine_subsidence_district=_auth(None),
        # Sydney Water servicing summary — 'empty' (not in a growth precinct) is a
        # real authoritative answer, so the fully-available fixture carries one.
        servicing=_auth("Not in a Sydney Water growth-servicing precinct."),
    )
    defaults.update(overrides)
    return EnvironmentalConstraints(**defaults)


def _make_economics(**overrides):
    defaults = dict(
        land_value=_auth(1330000),
        val_base_date=_auth("2025-07-01"),
        val_history=_auth([ValuationHistory(year="2025", value=1330000)]),
        lot_area_m2=_auth(467.0),
    )
    defaults.update(overrides)
    return Economics(**defaults)


def _make_neighbourhood(**overrides):
    defaults = dict(
        nearby_das=_auth([]),
        da_count=_auth(0),
        shadow=DataField(value=None, confidence=ConfidenceLevel.DERIVED, source="shadow_detector"),
        # DA outcomes wiring — populated on the fully-available fixture so
        # gap-collection tests keep meaning "this brief has zero gaps".
        da_outcomes=_auth({"outcomes": [], "radius_m": 200, "years_back": 8}),
        da_refusal_stats=_auth(None),
    )
    defaults.update(overrides)
    return Neighbourhood(**defaults)


def _make_dcp_controls(**overrides):
    defaults = dict(
        controls=_extracted([]),
        dcp_name=_extracted("Inner West DCP 2022"),
        dcp_url=_extracted(None),
        section_ref=_extracted(None),
    )
    defaults.update(overrides)
    return DCPControls(**defaults)


# ---------------------------------------------------------------------------
# Fixture 1: Inner West freestanding house (10 Hollands Ave, Marrickville)
# ---------------------------------------------------------------------------


def make_inner_west_house() -> DevelopmentBrief:
    return DevelopmentBrief(
        address="10 Hollands Avenue, Marrickville NSW 2204",
        lat=-33.911,
        lng=151.148,
        prop_id=1953939,
        run_date="2026-05-27",
        strata=_auth(StrataInfo(
            is_strata=False,
            strata_type=StrataType.NOT_STRATA,
            plan_label="DP387618",
            source="cadastre",
        )),
        planning_controls=_make_planning_controls(
            heritage_items=_auth(["Inter-War Group HCA — Hollands Avenue"]),
            heritage_hca=_auth(["Inter-War Group HCA — Hollands Avenue"]),
            lot_dimensions=_auth(LotDimensions(area_m2=202.3)),
        ),
        dcp_controls=_make_dcp_controls(
            controls=_extracted([
                DCPControl(control_type="front_setback", dev_type="dwelling_house",
                           value_min=4.5, unit="m", source_ref="IW DCP Part C 2.3"),
                DCPControl(control_type="rear_setback", dev_type="dwelling_house",
                           value_min=8.0, unit="m", source_ref="IW DCP Part C 2.3"),
            ]),
        ),
        sepp_housing=_auth([
            SEPPStandard(dev_type="secondary_dwelling", eligible=False,
                         min_lot_area_m2=450, reason_ineligible="Lot area 202m² < 450m² minimum"),
        ]),
        environmental_constraints=_make_env_constraints(
            heritage_postgis=_auth({"has_heritage": True, "hca_count": 1, "item_count": 0}),
        ),
        neighbourhood=_make_neighbourhood(
            da_count=_auth(4),
            nearby_das=_auth([NearbyDA(number="PAN-566269", distance_m=7, status="Determined")]),
        ),
        economics=_make_economics(land_value=_auth(1330000), lot_area_m2=_auth(202.3)),
        confidence_summary=ConfidenceSummary(),
    )


# ---------------------------------------------------------------------------
# Fixture 2: Strata apartment (5/1 Treacy St, Hurstville)
# ---------------------------------------------------------------------------


def make_strata_apartment() -> RenovationBrief:
    return RenovationBrief(
        address="5/1 Treacy Street, Hurstville NSW 2220",
        lat=-33.961,
        lng=151.102,
        prop_id=2001234,
        run_date="2026-05-27",
        strata=_auth(StrataInfo(
            is_strata=True,
            strata_type=StrataType.APARTMENT,
            strata_plan="SP12345",
            plan_label="SP12345",
            source="cadastre",
            lot_area_m2=1555.0,
        )),
        planning_controls=_make_planning_controls(
            zone=_auth("R4"),
            zone_full=_auth("High Density Residential"),
            zone_epi=_auth("Georges River Local Environmental Plan 2021"),
            height=_auth("21"),
            fsr=_auth("1.5:1"),
        ),
        environmental_constraints=_make_env_constraints(),
        economics=_make_economics(lot_area_m2=_auth(1555.0)),
        confidence_summary=ConfidenceSummary(),
    )


# ---------------------------------------------------------------------------
# Fixture 3: Strata townhouse (3/22 Carlton Cres, Summer Hill) — spike edge case
# ---------------------------------------------------------------------------


def make_strata_townhouse() -> DevelopmentBrief:
    return DevelopmentBrief(
        address="3/22 Carlton Crescent, Summer Hill NSW 2130",
        lat=-33.891,
        lng=151.130,
        prop_id=1999876,
        run_date="2026-05-27",
        strata=_auth(StrataInfo(
            is_strata=True,
            strata_type=StrataType.AMBIGUOUS,
            strata_plan="SP67890",
            plan_label="SP67890",
            source="cadastre",
            lot_area_m2=2140.0,
        )),
        planning_controls=_make_planning_controls(
            zone=_auth("R2"),
            zone_epi=_auth("Inner West Local Environmental Plan 2022"),
            lot_dimensions=_auth(LotDimensions(area_m2=2140.0)),
        ),
        dcp_controls=_make_dcp_controls(),
        sepp_housing=_auth([]),
        environmental_constraints=_make_env_constraints(),
        neighbourhood=_make_neighbourhood(),
        economics=_make_economics(lot_area_m2=_auth(2140.0)),
        confidence_summary=ConfidenceSummary(),
    )


# ---------------------------------------------------------------------------
# Fixture 4: Rural lot (123 Bells Line of Road, Kurrajong Heights)
# ---------------------------------------------------------------------------


def make_rural_lot() -> DevelopmentBrief:
    return DevelopmentBrief(
        address="123 Bells Line of Road, Kurrajong Heights NSW 2758",
        lat=-33.531,
        lng=150.627,
        prop_id=3001234,
        run_date="2026-05-27",
        strata=_auth(StrataInfo(
            is_strata=False,
            strata_type=StrataType.NOT_STRATA,
            source="cadastre",
        )),
        planning_controls=_make_planning_controls(
            zone=_auth("RU2"),
            zone_full=_auth("Rural Landscape"),
            zone_epi=_auth("Hawkesbury Local Environmental Plan 2012"),
            height=_not_available("NSW Planning Portal", "No height map for RU2"),
            fsr=_not_available("NSW Planning Portal", "No FSR map for RU2"),
            lot_size=_auth("40ha"),
            lot_size_units="ha",
        ),
        dcp_controls=_make_dcp_controls(
            controls=_not_available("PlotDetect DCP extraction", "Hawkesbury not onboarded"),
            dcp_name=_not_available("PlotDetect DCP extraction", "Hawkesbury not onboarded"),
            dcp_url=_not_available("PlotDetect DCP extraction", "Hawkesbury not onboarded"),
            section_ref=_not_available("PlotDetect DCP extraction", "Hawkesbury not onboarded"),
        ),
        sepp_housing=_auth([
            SEPPStandard(dev_type="secondary_dwelling", eligible=False,
                         reason_ineligible="Zone RU2 not in permitted zones"),
        ]),
        environmental_constraints=_make_env_constraints(
            overlays=_auth([
                EnvironmentalOverlay(layer_type="bushfire", value="Category 1"),
            ]),
            bushfire_designation=_auth("Category 1"),
            overlay_coverage=_not_available("PostGIS", "Hawkesbury overlays not ingested"),
        ),
        neighbourhood=_make_neighbourhood(
            da_count=_auth(0),
            nearby_das=_auth([]),
        ),
        economics=_make_economics(
            land_value=_not_available("NSW VG API", "No valuation for this propId"),
            lot_area_m2=_not_available("NSW VG API", "No valuation for this propId"),
        ),
        confidence_summary=ConfidenceSummary(),
    )


# ===================================================================
# Tests
# ===================================================================


class TestFixtureValidation:
    """All 4 fixtures must serialise/deserialise without error."""

    def test_inner_west_house_round_trips(self):
        brief = make_inner_west_house()
        data = brief.model_dump()
        restored = DevelopmentBrief.model_validate(data)
        assert restored.address == brief.address
        assert restored.brief_type == "development"

    def test_strata_apartment_round_trips(self):
        brief = make_strata_apartment()
        data = brief.model_dump()
        restored = RenovationBrief.model_validate(data)
        assert restored.brief_type == "renovation"
        assert restored.strata.value.strata_type == StrataType.APARTMENT

    def test_strata_townhouse_round_trips(self):
        brief = make_strata_townhouse()
        data = brief.model_dump()
        restored = DevelopmentBrief.model_validate(data)
        assert restored.strata.value.strata_type == StrataType.AMBIGUOUS

    def test_rural_lot_round_trips(self):
        brief = make_rural_lot()
        data = brief.model_dump()
        restored = DevelopmentBrief.model_validate(data)
        assert restored.planning_controls.height.confidence == ConfidenceLevel.NOT_AVAILABLE

    def test_development_brief_forbids_extra_fields(self):
        brief = make_inner_west_house()
        data = brief.model_dump()
        data["rogue_field"] = "injected"
        with pytest.raises(ValidationError, match="rogue_field"):
            DevelopmentBrief.model_validate(data)

    def test_renovation_brief_forbids_extra_fields(self):
        brief = make_strata_apartment()
        data = brief.model_dump()
        data["rogue_field"] = "injected"
        with pytest.raises(ValidationError, match="rogue_field"):
            RenovationBrief.model_validate(data)

    def test_inner_west_house_has_heritage(self):
        brief = make_inner_west_house()
        assert len(brief.planning_controls.heritage_items.value) == 1
        assert len(brief.planning_controls.heritage_hca.value) == 1

    def test_rural_lot_has_gaps(self):
        brief = make_rural_lot()
        gaps = collect_gaps(brief)
        gap_fields = [g.field for g in gaps]
        assert any("height" in f for f in gap_fields)
        assert any("fsr" in f for f in gap_fields)
        assert any("dcp" in f.lower() for f in gap_fields)


class TestDataFieldSemantics:
    """Three-state semantics must be distinguishable."""

    def test_present_value(self):
        f = DataField(value="R2", confidence=ConfidenceLevel.AUTHORITATIVE, source="portal")
        assert f.value == "R2"
        assert f.confidence != ConfidenceLevel.NOT_AVAILABLE

    def test_queried_no_results(self):
        """Queried successfully, but nothing found (e.g. no heritage)."""
        f = DataField(value=None, confidence=ConfidenceLevel.AUTHORITATIVE, source="portal")
        assert f.value is None
        assert f.confidence == ConfidenceLevel.AUTHORITATIVE  # query worked, just empty

    def test_query_failed(self):
        f = DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                      source="portal", reason="ConnectionError: timeout")
        assert f.value is None
        assert f.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert f.reason is not None

    def test_empty_list_is_not_unavailable(self):
        """Empty list with authoritative confidence = no items found (valid)."""
        f = DataField(value=[], confidence=ConfidenceLevel.AUTHORITATIVE, source="portal")
        assert f.value == []
        assert f.confidence == ConfidenceLevel.AUTHORITATIVE

    def test_stale_confidence(self):
        f = DataField(value="8m", confidence=ConfidenceLevel.STALE, source="DCP",
                      as_at="2024-11-01", reason="Last verified > 6 months ago")
        assert f.confidence == ConfidenceLevel.STALE


class TestStrataClassification:
    """Strata classification boundary values from spike findings."""

    def test_not_strata(self):
        assert classify_strata({"is_strata": False}, 500) == StrataType.NOT_STRATA

    def test_apartment_large_lot(self):
        assert classify_strata({"is_strata": True}, 3000) == StrataType.APARTMENT

    def test_development_tiny_lot(self):
        assert classify_strata({"is_strata": True}, 300) == StrataType.DEVELOPMENT

    def test_ambiguous_mid_range(self):
        """Spike edge case: 2140m² strata lot (Carlton Cres Summer Hill)."""
        assert classify_strata({"is_strata": True}, 2140) == StrataType.AMBIGUOUS

    def test_ambiguous_no_lot_area(self):
        assert classify_strata({"is_strata": True}, None) == StrataType.AMBIGUOUS

    def test_community_title_is_development(self):
        assert classify_strata({"is_strata": True, "plan_type": "community"}, 5000) == StrataType.DEVELOPMENT

    def test_boundary_400m2(self):
        assert classify_strata({"is_strata": True}, 400) == StrataType.AMBIGUOUS

    def test_boundary_399m2(self):
        assert classify_strata({"is_strata": True}, 399) == StrataType.DEVELOPMENT

    def test_boundary_2500m2(self):
        assert classify_strata({"is_strata": True}, 2500) == StrataType.AMBIGUOUS

    def test_boundary_2501m2(self):
        assert classify_strata({"is_strata": True}, 2501) == StrataType.APARTMENT

    def test_not_strata_ignores_lot_area(self):
        assert classify_strata({"is_strata": False}, 5000) == StrataType.NOT_STRATA

    def test_empty_dict(self):
        assert classify_strata({}, 500) == StrataType.NOT_STRATA

    def test_neighbourhood_plan_type(self):
        assert classify_strata({"is_strata": True, "plan_type": "neighbourhood"}, 5000) == StrataType.DEVELOPMENT


class TestInputValidation:
    """Adversarial request payloads."""

    def test_valid_request(self):
        req = IntelligenceBriefRequest(address="42 Smith St, Marrickville NSW 2204")
        assert req.address == "42 Smith St, Marrickville NSW 2204"

    def test_address_too_short(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="abc")

    def test_address_empty(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="")

    def test_address_whitespace_only(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="     ")

    def test_address_stripped(self):
        req = IntelligenceBriefRequest(address="  42 Smith St, Marrickville  ")
        assert req.address == "42 Smith St, Marrickville"

    def test_address_max_length(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="A" * 201)

    def test_address_at_max_length(self):
        req = IntelligenceBriefRequest(address="A" * 200)
        assert len(req.address) == 200

    def test_lat_outside_nsw_north(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="42 Smith St", lat=-27.0, lng=151.0)

    def test_lat_outside_nsw_south(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="42 Smith St", lat=-38.0, lng=151.0)

    def test_lng_outside_nsw_west(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="42 Smith St", lat=-33.0, lng=140.0)

    def test_lng_outside_nsw_east(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="42 Smith St", lat=-33.0, lng=154.0)

    def test_lat_at_nsw_boundary(self):
        req = IntelligenceBriefRequest(address="42 Smith St", lat=-28.0, lng=153.7)
        assert req.lat == -28.0

    def test_prop_id_numeric(self):
        req = IntelligenceBriefRequest(address="42 Smith St", prop_id="12345")
        assert req.prop_id == "12345"

    def test_prop_id_non_numeric(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="42 Smith St", prop_id="abc")

    def test_prop_id_empty_string(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="42 Smith St", prop_id="")

    def test_prop_id_sql_injection(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="42 Smith St", prop_id="1; DROP TABLE")

    def test_prop_id_negative(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="42 Smith St", prop_id="-1")

    def test_prop_id_too_long(self):
        with pytest.raises(ValidationError):
            IntelligenceBriefRequest(address="42 Smith St", prop_id="1234567890123")

    def test_lat_without_lng(self):
        """Should accept — lat/lng are independently optional."""
        req = IntelligenceBriefRequest(address="42 Smith St", lat=-33.9)
        assert req.lat == -33.9
        assert req.lng is None

    def test_include_satellite_default_false(self):
        req = IntelligenceBriefRequest(address="42 Smith St")
        assert req.include_satellite is False


class TestZonePrefix:
    """_zone_prefix edge cases from adversarial QA."""

    def test_normal(self):
        assert _zone_prefix("R2 Low Density Residential") == "R2"

    def test_zone_only(self):
        assert _zone_prefix("R2") == "R2"

    def test_none(self):
        assert _zone_prefix(None) == ""

    def test_empty_string(self):
        assert _zone_prefix("") == ""

    def test_whitespace_only(self):
        assert _zone_prefix("   ") == ""

    def test_lowercase(self):
        assert _zone_prefix("r2 low density") == "R2"

    def test_e1_mixed_use(self):
        assert _zone_prefix("E1 Local Centre") == "E1"

    def test_ru2(self):
        assert _zone_prefix("RU2 Rural Landscape") == "RU2"

    def test_sp2(self):
        assert _zone_prefix("SP2 Infrastructure") == "SP2"

    def test_with_prefix_dash(self):
        assert _zone_prefix("B2 - Local Centre") == "B2"


class TestSanitise:
    """_sanitise HTML/XSS prevention."""

    def test_normal_string(self):
        assert _sanitise("42 Smith St") == "42 Smith St"

    def test_none(self):
        assert _sanitise(None) is None

    def test_html_tags_stripped(self):
        assert _sanitise("<script>alert('xss')</script>Hello") == "alert('xss')Hello"

    def test_nested_tags(self):
        assert _sanitise("<b><i>Bold Italic</i></b>") == "Bold Italic"

    def test_null_bytes_removed(self):
        assert _sanitise("test\x00value") == "testvalue"

    def test_strips_whitespace(self):
        assert _sanitise("  hello  ") == "hello"

    def test_empty_string(self):
        assert _sanitise("") == ""

    def test_only_tags(self):
        assert _sanitise("<br/><hr/>") == ""


class TestConfidenceSummary:
    """compute_confidence_summary tallies correctly."""

    def test_counts_all_levels(self):
        brief = make_inner_west_house()
        summary = compute_confidence_summary(brief)
        assert summary.total > 0
        assert summary.authoritative > 0

    def test_rural_lot_has_not_available(self):
        brief = make_rural_lot()
        summary = compute_confidence_summary(brief)
        assert summary.not_available > 0

    def test_empty_brief_is_zero(self):
        summary = ConfidenceSummary()
        assert summary.total == 0


class TestMinimumViableBrief:
    """Minimum viable threshold enforcement."""

    def test_all_available(self):
        summary = ConfidenceSummary(authoritative=10, total=10)
        assert check_minimum_viable(summary) is True

    def test_below_threshold(self):
        summary = ConfidenceSummary(authoritative=2, not_available=8, total=10)
        assert check_minimum_viable(summary) is False

    def test_at_threshold(self):
        summary = ConfidenceSummary(authoritative=7, not_available=3, total=10)
        assert check_minimum_viable(summary) is True

    def test_just_below_threshold(self):
        summary = ConfidenceSummary(authoritative=6, not_available=4, total=10)
        assert check_minimum_viable(summary) is False

    def test_zero_total(self):
        summary = ConfidenceSummary(total=0)
        assert check_minimum_viable(summary) is False

    def test_stale_counts_as_available(self):
        summary = ConfidenceSummary(stale=10, total=10)
        assert check_minimum_viable(summary) is True

    def test_mixed_confidence(self):
        summary = ConfidenceSummary(
            authoritative=5, extracted=2, estimated=1, not_available=2, total=10
        )
        assert check_minimum_viable(summary) is True


class TestGapCollection:
    """collect_gaps finds all not_available DataFields."""

    def test_inner_west_house_no_gaps(self):
        brief = make_inner_west_house()
        gaps = collect_gaps(brief)
        assert len(gaps) == 0

    def test_rural_lot_has_gaps(self):
        brief = make_rural_lot()
        gaps = collect_gaps(brief)
        assert len(gaps) > 0
        reasons = [g.reason for g in gaps]
        assert any("timeout" in r.lower() or "not onboarded" in r.lower() or "no valuation" in r.lower()
                    for r in reasons)

    def test_gap_has_field_path(self):
        brief = make_rural_lot()
        gaps = collect_gaps(brief)
        fields = [g.field for g in gaps]
        assert all(f != "" for f in fields)


class TestSafeCall:
    """_safe_call error isolation."""

    def test_success(self):
        result = _safe_call_test(lambda: "ok", "test_source", ConfidenceLevel.AUTHORITATIVE)
        assert result.value == "ok"
        assert result.confidence == ConfidenceLevel.AUTHORITATIVE

    def test_exception_caught(self):
        result = _safe_call_test(
            lambda: (_ for _ in ()).throw(ConnectionError("timeout")),
            "test_source",
            ConfidenceLevel.AUTHORITATIVE,
        )
        assert result.value is None
        assert result.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert "ConnectionError" in result.reason

    def test_value_error_caught(self):
        result = _safe_call_test(
            lambda: int("abc"),
            "test_source",
            ConfidenceLevel.AUTHORITATIVE,
        )
        assert result.value is None
        assert result.confidence == ConfidenceLevel.NOT_AVAILABLE

    def test_none_return_is_not_failure(self):
        """fn() returning None is valid (e.g. no heritage). NOT a failure."""
        result = _safe_call_test(lambda: None, "test_source", ConfidenceLevel.AUTHORITATIVE)
        assert result.value is None
        assert result.confidence == ConfidenceLevel.AUTHORITATIVE  # success, just empty


def _safe_call_test(fn, source, confidence):
    """Import-safe wrapper for _safe_call."""
    from services.intelligence_brief import _safe_call
    return _safe_call(fn, source, confidence)


class TestCompoundConstraint:
    """CompoundConstraint model validation."""

    def test_valid_constraint(self):
        c = CompoundConstraint(
            id="heritage_hca_flood",
            description="Heritage conservation area AND flood planning area",
            caveat="Flood mitigation may require Heritage NSW concurrence",
            severity=CompoundSeverity.WARNING,
            data_sources_used=["Planning Portal", "PostGIS spatial_overlays"],
        )
        assert c.severity == CompoundSeverity.WARNING

    def test_info_severity(self):
        c = CompoundConstraint(
            id="zone_permits_higher_density",
            description="Zone R3 permits multi-dwelling housing",
            caveat="Check LEP land use table",
            severity=CompoundSeverity.INFO,
        )
        assert c.severity == CompoundSeverity.INFO


class TestConfig:
    """BriefConfig values are reasonable."""

    def test_nsw_bbox_valid(self):
        assert CONFIG.nsw_lat_min < CONFIG.nsw_lat_max
        assert CONFIG.nsw_lng_min < CONFIG.nsw_lng_max

    def test_timeouts_positive(self):
        assert CONFIG.timeout_planning_portal > 0
        assert CONFIG.timeout_vg > 0
        assert CONFIG.timeout_postgis > 0

    def test_min_available_ratio_between_0_and_1(self):
        assert 0 < CONFIG.min_available_ratio < 1
