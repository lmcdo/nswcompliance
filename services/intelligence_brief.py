"""
Intelligence Brief — Contract + Schema (Stage 1).

Pydantic models defining the response contract for the intelligence brief.
Every downstream stage implements against this contract.

Key design decisions:
  - DataField wraps every value with confidence, source, as_at, reason
  - Three-state semantics: value present / queried-no-results / query-failed
  - Two brief templates: DevelopmentBrief (freestanding) / RenovationBrief (apartment)
  - Strata classification: four-state enum, not binary
  - Compound constraints: JSONB-compatible list of typed rules

POST /pipeline/intelligence-brief
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Generator, Generic, Literal, NamedTuple, Optional, TypeVar

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

try:
    from vg_comparables import (  # noqa: E402 — Railway runs from services/
        ComparableAnalysis,
        PropertySale,
        get_comparable_values,
        get_recent_sales,
    )
except ImportError:
    from services.vg_comparables import (  # noqa: E402
        ComparableAnalysis,
        PropertySale,
        get_comparable_values,
        get_recent_sales,
    )

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BriefConfig:
    """Centralised constants — no magic numbers in pipeline code."""

    # Timeouts (seconds)
    timeout_planning_portal: float = 8.0
    timeout_vg: float = 5.0
    timeout_postgis: float = 5.0
    timeout_eplanning: float = 10.0
    timeout_shadow: float = 15.0
    timeout_satellite: float = 45.0
    timeout_strata: float = 5.0
    timeout_terrain: float = 100.0  # covers GA(12+12 capped) + SIX Maps DEM (up to 65s, variable) + whitebox chain
    timeout_premium: float = 120.0  # pre-DA site history is a 30–90s pipeline — give it room to finish, not time out
    timeout_shadow_collect: float = 65.0  # the shadow endpoint's own POST timeout is 60s; the brief must wait longer, not cut it off at 50s

    # NSW bounding box (WGS84)
    nsw_lat_min: float = -37.5
    nsw_lat_max: float = -28.0
    nsw_lng_min: float = 140.9
    nsw_lng_max: float = 153.7

    # Search parameters
    da_radius_m: int = 500  # neighbourhood scope — 200m was too tight to be useful
    da_lookback_days: int = 365
    # Market context (VG comparables + sales). Same 500m scope as the DA radius —
    # the bounding box + zone + lot-area filters keep a neighbour's different
    # market segment from leaking into "comparable" statistics.
    market_radius_m: int = 500
    market_sales_years_back: int = 3
    timeout_market: float = 15.0  # two VG ArcGIS queries (~0.3s each live); headroom for a slow VG day
    timeout_land_use: float = 10.0  # one indexed lep_land_use_table query (~0.3s live)
    # DA outcomes (determined applications with results) — tighter radius than
    # the recent-DA feed: outcomes describe THIS street's determinations.
    da_outcomes_radius_m: int = 200
    # The tracking layer's outcome field is only backfilled up to ~2022
    # lodgements (verified live 2026-07-04) — a 3-year window held 4 records
    # for a whole LGA. 8 years gives a meaningful cohort; the period is always
    # displayed with the counts.
    da_outcomes_years_back: int = 8
    timeout_da_outcomes: float = 15.0

    # Concurrency — single pool runs all sources; dependents submitted after
    # their prerequisite completes, so effective parallelism is ~15-20.
    max_parallel_sources: int = 20

    # Minimum viable brief — refuse if too many fields failed
    min_available_ratio: float = 0.70


# Concurrency cap on the heavy brief stream. Each brief peaks at a few GB; two at
# once OOM-killed the 8GB Railway container. Default 1 (fully serialised) is safe on
# 8GB; raise BRIEF_MAX_CONCURRENCY when the container has more memory. A queued
# request waits up to BRIEF_ACQUIRE_TIMEOUT_S, then gets an honest "busy" event.
_BRIEF_MAX_CONCURRENCY = max(1, int(os.getenv("BRIEF_MAX_CONCURRENCY", "1")))
_BRIEF_ACQUIRE_TIMEOUT_S = float(os.getenv("BRIEF_ACQUIRE_TIMEOUT_S", "150"))
_BRIEF_SEMAPHORE = threading.BoundedSemaphore(_BRIEF_MAX_CONCURRENCY)


CONFIG = BriefConfig()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ConfidenceLevel(str, Enum):
    """Per-field confidence classification.

    authoritative  — live government API, current
    extracted      — manual DCP extraction, QA'd
    estimated      — model output (shadow geometry, satellite)
    derived        — computed from authoritative inputs
    not_available  — query failed or data not yet ingested
    stale          — data older than staleness threshold
    """

    AUTHORITATIVE = "authoritative"
    EXTRACTED = "extracted"
    ESTIMATED = "estimated"
    DERIVED = "derived"
    NOT_AVAILABLE = "not_available"
    STALE = "stale"


class StrataType(str, Enum):
    """Four-state strata classification.

    Spike finding: binary apartment/development is wrong for strata townhouses.
    """

    NOT_STRATA = "not_strata"
    APARTMENT = "apartment"
    DEVELOPMENT = "development"  # strata townhouse / strata house
    AMBIGUOUS = "ambiguous"  # strata but can't determine building type


class CompoundSeverity(str, Enum):
    WARNING = "warning"
    INFO = "info"


class BriefType(str, Enum):
    DEVELOPMENT = "development"
    RENOVATION = "renovation"


# ---------------------------------------------------------------------------
# DataField — the core wrapper
# ---------------------------------------------------------------------------


T = TypeVar("T")


class DataField(BaseModel, Generic[T]):
    """Wraps every value with provenance metadata.

    Three-state semantics:
      value=X,    confidence!=not_available  → data present
      value=None, confidence!=not_available  → queried, no results (legitimately empty)
      value=None, confidence=not_available   → query failed or not attempted
    """

    value: Optional[T] = None
    confidence: ConfidenceLevel
    source: str
    as_at: Optional[str] = None  # ISO date of data currency
    reason: Optional[str] = None  # populated when value is None due to error

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def _fail_closed_on_errored_authoritative(self) -> "DataField":
        """S1 fail-closed invariant, enforced at every construction site.

        A DataField with no value that carries an error ``reason`` is a FAILED
        fetch (per the field contract above) — it must never present
        AUTHORITATIVE confidence, or a failed lookup renders as a confident
        answer (the strata/overlay false-negative class). Coerce, don't raise:
        the brief must degrade to an honest NOT_AVAILABLE card, not 500.

        ``value=None, reason=None`` is deliberately untouched — that is the
        documented queried-and-legitimately-empty state (e.g. a zone with no
        height control), which must keep its AUTHORITATIVE badge.
        """
        if (
            self.confidence == ConfidenceLevel.AUTHORITATIVE
            and self.value is None
            and self.reason
        ):
            self.confidence = ConfidenceLevel.NOT_AVAILABLE
        return self


# ---------------------------------------------------------------------------
# _safe_call — error isolation for every external data source
# ---------------------------------------------------------------------------


def _safe_call(
    fn,
    source_name: str,
    confidence_on_success: ConfidenceLevel,
    as_at: Optional[str] = None,
) -> DataField:
    """Call fn(). On success → DataField(value, confidence).
    On failure → DataField(value=None, not_available, reason=error).
    Never raises."""
    start = time.monotonic()
    try:
        result = fn()
        return DataField(
            value=result,
            confidence=confidence_on_success,
            source=source_name,
            as_at=as_at or date.today().isoformat(),
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.warning(f"{source_name} failed after {elapsed:.1f}s: {e}")
        return DataField(
            value=None,
            confidence=ConfidenceLevel.NOT_AVAILABLE,
            source=source_name,
            reason=f"{type(e).__name__}: {str(e)[:200]}",
        )


# ---------------------------------------------------------------------------
# Request model — input validation
# ---------------------------------------------------------------------------


class IntelligenceBriefRequest(BaseModel):
    """Validated request for the intelligence brief endpoint."""

    address: str = Field(..., min_length=5, max_length=200)
    lat: Optional[float] = Field(None, ge=-37.5, le=-28.0)
    lng: Optional[float] = Field(None, ge=140.9, le=153.7)
    prop_id: Optional[str] = Field(None, pattern=r"^\d{1,12}$")
    include_satellite: bool = False
    include_premium: bool = False  # pre_da_history — slow (30-90s), user accepts latency

    @field_validator("address")
    @classmethod
    def clean_address(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Address too short after trimming")
        return v


# ---------------------------------------------------------------------------
# Section models — structured brief content
# ---------------------------------------------------------------------------


class ValuationHistory(BaseModel):
    year: str
    value: Optional[int] = None  # dollars


from services.constraint_models import (
    ConstraintArithmeticResult,
    ConstraintStep,
    ConstraintType,
    DCPControl,
    LotDimensions,
    SEPPStandard,
    SeppLepOverride,
    ShadowResult,
    ShadowScenario,
)


class PlanningControls(BaseModel):
    """LEP controls from Planning Portal + spatial overlays."""

    zone: DataField[Optional[str]]
    zone_full: DataField[Optional[str]]
    zone_epi: DataField[Optional[str]]
    legislation_url: DataField[Optional[str]]
    height: DataField[Optional[str]]
    height_units: str = "m"
    fsr: DataField[Optional[str]]
    lot_size: DataField[Optional[str]]
    lot_size_units: str = "m\u00b2"
    acid_sulfate_class: DataField[Optional[str]]
    heritage_items: DataField[list[str]]
    heritage_hca: DataField[list[str]]
    sepp_overlays: DataField[list[dict]]
    housing_sepp: DataField[bool]
    tod_area: DataField[bool]
    lot_dimensions: DataField[Optional[LotDimensions]]
    # LEP Land Use Table lists for this zone + LGA (lep_land_use_table, the
    # structured 25-LGA dataset). value=None + reason = not extracted for this
    # council yet / fetch failed \u2014 never a silent empty list.
    permitted_uses: DataField[Optional[list[str]]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="lep_land_use_table", reason="Land-use lists not queried",
    )
    prohibited_uses: DataField[Optional[list[str]]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="lep_land_use_table", reason="Land-use lists not queried",
    )


class MarketContext(BaseModel):
    """VG comparables + recent sales around the subject lot.

    Wording contract (liability): percentile_rank / assessment_signal are the
    subject's FACTUAL position within the comparable set \u2014 rendered as
    "sits at the Nth percentile of comparable lots within X m", never as an
    over/under-valuation opinion.
    """

    comparables: DataField[Optional[ComparableAnalysis]]
    recent_sales: DataField[Optional[list[PropertySale]]]
    radius_m: int = CONFIG.market_radius_m
    sales_years_back: int = CONFIG.market_sales_years_back


class DCPControls(BaseModel):
    """DCP setback and development controls."""

    controls: DataField[list[DCPControl]]
    dcp_name: DataField[Optional[str]]
    dcp_url: DataField[Optional[str]]
    section_ref: DataField[Optional[str]]
    # Plan-date provenance, typed (campaign item 3): 'resolved' (as_at set on
    # the fields), 'absent' (checked, no defensible date), 'unavailable' (the
    # lookup FAILED — as_at_note carries the disclosure so the failure is
    # never mistakable for a completed lookup that found nothing).
    as_at_status: Optional[str] = None
    as_at_note: Optional[str] = None


class ContributionPlan(BaseModel):
    """A single development contributions plan (s7.11 / s7.12)."""

    plan_name: str
    plan_url: Optional[str] = None


class HousingProductivityContribution(BaseModel):
    """Housing and Productivity Contribution (HPC) overlay."""

    name: Optional[str] = None
    component: Optional[str] = None  # "BHPC" etc
    commenced_date: Optional[str] = None
    ministerial_order_url: Optional[str] = None


class ContributionsResult(BaseModel):
    """Development contributions applicable to a property."""

    plans: list[ContributionPlan] = []
    hpc: Optional[HousingProductivityContribution] = None
    lga_name: Optional[str] = None


class StrataInfo(BaseModel):
    """Strata classification with four-state type."""

    is_strata: bool
    strata_type: StrataType
    strata_plan: Optional[str] = None
    plan_label: Optional[str] = None
    # Legal title identifiers from the NSW cadastre — "Lot 5 DP900454" is the
    # reference conveyancers and contracts use; the plan number alone is half an ID.
    lot_number: Optional[str] = None
    section_number: Optional[str] = None
    source: Optional[str] = None
    lot_area_m2: Optional[float] = None
    # StrataHub supplementary detail (display only — never drives the
    # development/renovation brief-type routing, which classify_strata owns).
    lot_total: Optional[int] = None
    dwelling_type: Optional[str] = None
    registration_date: Optional[str] = None


class NearbyDA(BaseModel):
    """Nearby development application summary."""

    number: str
    address: Optional[str] = None
    distance_m: Optional[int] = None
    status: Optional[str] = None
    dev_type: Optional[str] = None
    lodgement_date: Optional[str] = None
    cost: Optional[float] = None


class EnvironmentalOverlay(BaseModel):
    """Environmental constraint overlay."""

    layer_type: str  # flood, bushfire, biodiversity, etc.
    value: Optional[str] = None
    instrument: Optional[str] = None
    lga: Optional[str] = None


class EnvironmentalConstraints(BaseModel):
    """Environmental risk layers from PostGIS + portal + spatial queries."""

    flood_epi: DataField[bool]
    overlays: DataField[list[EnvironmentalOverlay]]
    overlay_coverage: DataField[list[str]]  # layer types ingested for this LGA
    bushfire_designation: DataField[Optional[str]]  # from portal SEPP overlay
    heritage_postgis: DataField[Optional[dict]]  # PostGIS heritage near lot

    # Typed constraint fields — extracted from overlays or portal queries
    # Default NOT_AVAILABLE until orchestrator wires each source
    mine_subsidence: DataField[Optional[bool]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="nsw_spatial_services", reason="Not yet wired in orchestrator",
    )
    contaminated_land: DataField[Optional[bool]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="epa_contaminated_sites", reason="Not yet wired in orchestrator",
    )
    drinking_water_catchment: DataField[Optional[bool]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="sepp_resilience_hazards", reason="Not yet wired in orchestrator",
    )
    terrestrial_biodiversity: DataField[Optional[bool]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="postgis_overlays", reason="Not yet extracted from overlays",
    )
    riparian_land: DataField[Optional[bool]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="postgis_overlays", reason="Not yet extracted from overlays",
    )
    wetlands: DataField[Optional[bool]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="postgis_overlays", reason="Not yet extracted from overlays",
    )
    anef: DataField[Optional[str]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="postgis_overlays", reason="Not yet extracted from overlays",
    )
    # Numeric ANEF contour value (when one applies) — the display string above
    # stays for the card; this carries the number for downstream consumers.
    anef_level: DataField[Optional[float]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="planning_portal_protection", reason="Not yet extracted from overlays",
    )
    coastal_hazards: DataField[Optional[dict]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="sepp_resilience_hazards", reason="Not yet extracted from overlays",
    )
    # Nearest-feature distances (metres) for mapped layers that are covered for
    # this LGA but do NOT intersect this lot — measured by PostGIS ST_Distance
    # in get_unique_overlays, never estimated. Decorates the "No" rows
    # ("Flood: No — nearest mapped flood polygon 830 m away").
    nearest_features: DataField[Optional[dict]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="postgis_overlays", reason="Not yet extracted from overlays",
    )
    # Detail behind the booleans above — already returned by their services.
    contaminated_detail: DataField[Optional[dict]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="epa_contaminated_sites", reason="Not yet wired in orchestrator",
    )
    mine_subsidence_district: DataField[Optional[str]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="nsw_spatial_services", reason="Not yet wired in orchestrator",
    )
    # Sydney Water Growth Servicing Plan status — one-line human summary from
    # gsp_servicing.summarize_servicing. Data is © Sydney Water ("guide only");
    # the summary carries the source attribution.
    servicing: DataField[Optional[str]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="sydney_water_gsp", reason="Not yet wired in orchestrator",
    )


class Neighbourhood(BaseModel):
    """Nearby DA activity and context."""

    nearby_das: DataField[list[NearbyDA]]
    da_count: DataField[Optional[int]]
    shadow: DataField[Optional[ShadowResult]]
    # Determined applications with OUTCOMES (DA tracking layer) + the LGA-wide
    # determination counts. value carries radius/period so the UI states them
    # from data. Defaults = not queried (legacy constructors).
    da_outcomes: DataField[Optional[dict]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="da_tracking_mapserver", reason="DA outcomes not queried",
    )
    da_refusal_stats: DataField[Optional[dict]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="da_tracking_mapserver", reason="Refusal counts not queried",
    )


class Economics(BaseModel):
    """Valuation and economic context."""

    land_value: DataField[Optional[int]]  # dollars
    val_base_date: DataField[Optional[str]]
    val_history: DataField[list[ValuationHistory]]
    lot_area_m2: DataField[Optional[float]]


# ---------------------------------------------------------------------------
# Satellite section models — Stage 4a
# ---------------------------------------------------------------------------


class BushfireDetail(BaseModel):
    """Bushfire pre-screen from RFS BFPL + PostGIS cross-overlays."""

    is_bushfire_prone: Optional[bool] = None
    category: Optional[str] = None  # Vegetation Category 1/2/3, buffer
    bal_estimate: Optional[str] = None
    vegetation_type: Optional[str] = None  # RFS designation guideline
    fire_signal: Optional[str] = None  # none/low/moderate/elevated/unavailable
    cross_overlays: Optional[list[dict]] = None  # flood, heritage, zone intersections
    rfs_referral_required: Optional[bool] = None
    rfs_referral_triggers: Optional[list[str]] = None
    rfs_referral_note: Optional[str] = None  # conditional wording alongside the triggers
    cdc_pathway_available: Optional[bool] = None
    # Pass-through parity (PR-B): guidance/context the service already emits.
    designation_source: Optional[str] = None
    bal_assessment_likely_required: Optional[bool] = None
    bal_formal_assessment_cost_range: Optional[str] = None  # guidance "typical range"
    bal_assessor_directory_url: Optional[str] = None
    clearing_10_50_entitled: Optional[bool] = None  # None on prone land = depends on RFS 10/50 map
    clearing_10_50_exceptions: Optional[str] = None
    estimated_consultant_costs: Optional[str] = None
    state_legislation: Optional[str] = None
    legislation_url: Optional[str] = None
    data_currency: Optional[str] = None
    confidence: Optional[str] = None


class _BushfireCompliance(BaseModel):
    model_config = ConfigDict(extra="ignore")
    # The service emits a LIST of {type, ...} overlay dicts (or null) — typing
    # this as dict crashed validation on every bushfire-prone lot with overlays.
    cross_overlays: Optional[list[dict]] = None
    rfs_referral_required: Optional[bool] = None
    rfs_referral_triggers: Optional[list[str]] = None
    rfs_referral_note: Optional[str] = None
    cdc_pathway_available: Optional[bool] = None
    clearing_10_50_entitled: Optional[bool] = None
    clearing_10_50_exceptions: Optional[str] = None
    estimated_consultant_costs: Optional[str] = None
    state_legislation: Optional[str] = None
    legislation_url: Optional[str] = None


class BushfireServiceOutput(BaseModel):
    """S2 typed contract for the bushfire service's ``outputs`` dict.

    Single source of truth for the bushfire output key names the brief consumes;
    a rename is a typed/test failure here, not a silent null in the card.
    """

    model_config = ConfigDict(extra="ignore")
    is_bushfire_prone: Optional[bool] = None
    designation_category: Optional[str] = None
    designation_source: Optional[str] = None
    estimated_bal_band: Optional[str] = None
    designation_guideline: Optional[str] = None
    fire_signal: Optional[str] = None
    bal_assessment_likely_required: Optional[bool] = None
    bal_formal_assessment_cost_range: Optional[str] = None
    bal_assessor_directory_url: Optional[str] = None
    data_currency: Optional[str] = None
    compliance: Optional[_BushfireCompliance] = None


class FloodDetail(BaseModel):
    """Multi-source flood analysis beyond statutory EPI flag."""

    # The engine's computed screening signal (validated enum in flood_truth) —
    # rendered as the card's headline line, never a bare verdict.
    flood_signal: Optional[str] = None  # none/low/moderate/elevated/unavailable
    epi_flood: Optional[bool] = None
    epi_flood_label: Optional[str] = None  # EPI flood class label (human-readable)
    # Copernicus EMS — PostGIS point-in-polygon vs ingested activation footprints.
    # Three-state: None = not checked / table unavailable; False = checked, no
    # mapped extent here; True = mapped flood extent intersected this location.
    ems_flood_detected: Optional[bool] = None
    ems_activations: Optional[list[dict]] = None  # {activation_id, event_name, event_date, flood_type}
    sar_flood_detected: Optional[bool] = None
    sar_confidence: Optional[str] = None
    sar_analysis_date: Optional[str] = None
    ses_in_flood_planning_area: Optional[bool] = None
    ses_flood_class: Optional[str] = None
    ses_study_name: Optional[str] = None
    jrc_occurrence_pct: Optional[float] = None  # JRC 1984-2021
    jrc_data_year: Optional[int] = None
    wofs_frequency_pct: Optional[float] = None  # DEA WOfS
    bom_gauge_name: Optional[str] = None
    bom_gauge_distance_km: Optional[float] = None
    bom_last_major_flood_date: Optional[str] = None
    bom_last_major_flood_peak_m: Optional[float] = None
    bom_flood_history: Optional[list[dict]] = None  # {date, peak_m, ari_category}
    in_100yr_flood_zone: Optional[bool] = None
    # Named studies (e.g. "Redbank Creek flood study") covering this address's
    # council whose rasters could not be consulted this run — only set when
    # in_100yr_flood_zone is None. See lib/not-assessed.ts on the frontend,
    # which already renders this same field for the standalone flood report.
    in_100yr_flood_zone_unconsulted: Optional[list[str]] = None
    ground_elevation_m_ahd: Optional[float] = None
    s1_gap_warning: Optional[str] = None
    flood_studies: Optional[list[dict]] = None
    confidence: Optional[str] = None


class FloodServiceOutput(BaseModel):
    """S2 typed contract for the flood service's ``outputs`` dict.

    This is the SINGLE SOURCE OF TRUTH for the flood output key names the brief
    consumes. _build_flood_detail reads typed attributes off it, so a typo or a
    renamed key is a static/type error here instead of a silent null in the card
    (the jrc_occurrence_pct vs jrc_water_occurrence_pct class). Extra keys the
    service emits (refused, hawkesbury_* backward-compat, etc.) are ignored;
    values stay nullable so a genuine empty reading is preserved.
    """

    model_config = ConfigDict(extra="ignore")
    flood_signal: Optional[str] = None
    epi_flood_class: Optional[str] = None
    epi_flood_label: Optional[str] = None
    ems_flood_detected: Optional[bool] = None
    ems_activations: Optional[list[dict]] = None
    sar_flood_detected: Optional[bool] = None
    sar_confidence: Optional[str] = None
    sar_analysis_date: Optional[str] = None
    ses_in_flood_planning_area: Optional[bool] = None
    ses_flood_class: Optional[str] = None
    ses_study_name: Optional[str] = None
    jrc_water_occurrence_pct: Optional[float] = None
    jrc_data_year: Optional[int] = None
    dea_wofs_frequency_pct: Optional[float] = None
    bom_gauge_name: Optional[str] = None
    bom_gauge_distance_km: Optional[float] = None
    bom_last_major_flood_date: Optional[str] = None
    bom_last_major_flood_peak_m: Optional[float] = None
    bom_flood_history: Optional[list[dict]] = None
    in_100yr_flood_zone: Optional[bool] = None
    in_100yr_flood_zone_unconsulted: Optional[list[str]] = None
    ground_elevation_m_ahd: Optional[float] = None
    s1_gap_warning: Optional[str] = None
    flood_studies: Optional[list[dict]] = None


class ShadowScenarioOutput(BaseModel):
    """S2 typed contract for one shadow service scenario dict."""

    model_config = ConfigDict(extra="ignore")
    label: Optional[str] = None
    time_local: Optional[str] = None
    shadow_length_m: Optional[float] = None
    shadow_overlap_fraction: Optional[float] = None  # 0-1; brief converts to percent
    shadow_direction_deg: Optional[float] = None
    overlaps_subject_lot: Optional[bool] = None
    status: Optional[str] = None       # "computed" | "unavailable"
    error_note: Optional[str] = None   # why the scenario has no measurements


class ShadowServiceOutput(BaseModel):
    """S2 typed contract for the shadow service's output dict (no ``outputs`` wrapper).

    Single source of truth for the shadow output + per-scenario key names the
    brief consumes; a rename is a typed/test failure, not a silent null.
    """

    model_config = ConfigDict(extra="ignore")
    height_m: Optional[float] = None
    height_source: Optional[str] = None
    adg_compliant: Optional[bool] = None
    worst_case_scenario: Optional[str] = None
    scenarios: list[ShadowScenarioOutput] = []
    # Run-level passthrough (PR-B): the envelope confidence is merged into the
    # outputs dict by get_shadow_risk.
    confidence: Optional[str] = None


class StrataCoreOutput(BaseModel):
    """Keys ``detect_strata`` (cadastre) emits on EVERY return path.

    The runtime drift tripwire checks against this class only — the StrataHub
    enrichment keys below are conditionally present by design, so their absence
    is not drift.
    """

    model_config = ConfigDict(extra="ignore")
    is_strata: bool = False
    strata_plan: Optional[str] = None
    plan_type: Optional[str] = None
    source: Optional[str] = None
    parent_has_strata: bool = False
    plan_label: Optional[str] = None


class StrataServiceOutput(StrataCoreOutput):
    """S2 typed contract for the cadastre strata dict (``detect_strata``,
    optionally enriched with StrataHub ``lot_total``/``dwelling_type`` by
    ``_fetch_strata``).

    Single source of truth for the strata key names the brief consumes
    (``classify_strata`` + the strata card); a renamed service key is a
    drift-warning + test failure, not a silent "not strata" routing.
    """

    # StrataHub enrichment — present only when the parcel is strata and the
    # StrataHub lookup succeeded (best-effort, see _fetch_strata).
    lot_total: Optional[int] = None
    dwelling_type: Optional[str] = None
    registration_date: Optional[str] = None


class ClimateHazardOutput(BaseModel):
    """S2 typed contract for one hazard entry in the climate risk output.

    Mirrors ``climate_risk_score.HazardScore.to_dict()`` — these dicts pass
    through to ``ClimateDisclosureProfile.per_hazard_detail`` and the UI reads
    them by key, so the key set is locked here and in the golden-fixture test.
    """

    model_config = ConfigDict(extra="ignore")
    hazard: Optional[str] = None
    present: Optional[bool] = None
    detail: Optional[str] = None
    confidence: Optional[str] = None
    confidence_reason: Optional[str] = None
    data_source: Optional[str] = None
    available: Optional[bool] = None
    # raw_score / weight / weighted_score are deliberately absent: they are the
    # composite model's arithmetic, no surface renders them, and weight plus
    # weighted_score make the composite reconstructible. climate_risk_score
    # .to_dict() no longer serialises them.


class ClimateRiskServiceOutput(BaseModel):
    """S2 typed contract for ``climate_risk_score(...).to_dict()`` at the brief seam.

    ``score``/``band``/``interaction_bonus`` are absent by design — the composite
    is unvalidatable and #699 bars it from customer surfaces. ``ClimateDisclosure
    Profile`` never carried them either (pinned by
    ``tests/test_satellite_integration.py``), so nothing downstream loses data.
    """

    model_config = ConfigDict(extra="ignore")
    hazards: list[ClimateHazardOutput] = []
    methodology_version: Optional[str] = None
    data_date: Optional[str] = None
    disclaimer: Optional[str] = None
    # NARCliM 2.0 projection summary attached by _fetch_climate_risk:
    # {} = queried, no grid coverage here; None/absent = lookup failed/not run.
    narclim: Optional[dict] = None


class HousingSeppFormOutput(BaseModel):
    """S2 typed contract mirroring ``housing_sepp_eligibility.FormEligibility``.

    ``evaluate_eligibility`` returns dataclasses (attribute access is already
    fail-loud), so this mirror exists to (a) lock the field names the brief's
    per-form wire-in (Phase 2) will consume — the lock test fails if the
    dataclass renames a field — and (b) give that wire-in a serialisable model.
    """

    model_config = ConfigDict(extra="ignore")
    development_type: Optional[str] = None
    eligible: Optional[bool] = None
    reason: Optional[str] = None
    requires_lmr_area: Optional[bool] = None
    unconfirmed: Optional[bool] = None
    applicable_zones: list = []
    min_lot_size_m2: Optional[float] = None
    min_lot_width_m: Optional[float] = None
    source_clause: Optional[str] = None
    source_document: Optional[str] = None
    legislation_url: Optional[str] = None
    effective_date: Optional[str] = None
    # DQ-96: mirrors FormEligibility.stale_since/stale_reason, added when the
    # dataclass gained the W3 (#839) auto-stale notice services/cdc_screen.py
    # already carried for its own standards table.
    stale_since: Optional[str] = None
    stale_reason: Optional[str] = None


class LepLandUseRow(BaseModel):
    """S2 typed contract for one ``lep_land_use_table`` row at the brief seam.

    Locks the column names the brief consumes (``_permitted_engine_forms`` now;
    the permitted/prohibited-uses wire-in in Phase 2). A renamed column is a
    fixture/test failure, not a silently empty permitted-forms set.
    """

    model_config = ConfigDict(extra="ignore")
    lga: Optional[str] = None
    zone: Optional[str] = None
    development_type: Optional[str] = None
    permissibility: Optional[str] = None


class GeometryRelationship(str, Enum):
    """How the property relates to a spatial designation."""

    INTERSECTS = "intersects"
    CONTAINS = "contains"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class FalsePositiveLikelihood(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ActionCategory(str, Enum):
    VERIFY = "verify"
    INVESTIGATE = "investigate"
    MONITOR = "monitor"


class StatutoryFinding(BaseModel):
    """Layer 1 — government-designated hazard constraint."""

    hazard: str
    designation: str
    source: str
    legislation_ref: Optional[str] = None
    as_at: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.AUTHORITATIVE
    geometry_relationship: GeometryRelationship = GeometryRelationship.UNKNOWN
    statutory_data_age_days: Optional[int] = None


class EmpiricalFinding(BaseModel):
    """Layer 2 — observed/measured data from authoritative datasets."""

    hazard: str
    value: Optional[float] = None
    unit: Optional[str] = None
    source: str
    data_date: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.ESTIMATED
    false_positive_likelihood: FalsePositiveLikelihood = FalsePositiveLikelihood.LOW


class ProjectedFinding(BaseModel):
    """Layer 3 — climate model output (scenario-dependent)."""

    hazard: str
    value: Optional[float] = None
    model: Optional[str] = None
    scenario: Optional[str] = None
    timeframe: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel.ESTIMATED


class UnavailableSource(BaseModel):
    """Source that could not be queried during assessment."""

    source: str
    reason: str


class AssessmentManifest(BaseModel):
    """Tracks what was assessed and what succeeded."""

    categories_assessed: int = 0
    sources_queried: int = 0
    sources_successful: int = 0
    sources_unavailable: list[UnavailableSource] = []
    coverage_pct: float = 0.0
    data_quality_notes: list[str] = []


class ActionItem(BaseModel):
    """Informational action derived from gap alerts, stale data, or unavailable sources."""

    description: str
    category: ActionCategory
    recommended_source: Optional[str] = None
    verify_url: Optional[str] = None


class ClimateDisclosureProfile(BaseModel):
    """Climate Disclosure Profile — replaces composite climate risk score.

    Three epistemological layers with cross-layer gap detection and action register.
    No composite score. Methodology: CLIMATE_METHODOLOGY_V2.md
    """

    assessment_date: Optional[str] = None
    methodology_version: str = "2.0"

    manifest: AssessmentManifest = AssessmentManifest()
    scope_limitations: list[str] = []

    statutory_findings: list[StatutoryFinding] = []
    statutory_count: int = 0

    empirical_findings: list[EmpiricalFinding] = []

    projected_findings: list[ProjectedFinding] = []

    gap_alerts: list[CompoundConstraint] = []
    gap_alert_count: int = 0

    action_register: list[ActionItem] = []

    per_hazard_detail: list[dict] = []


class GrannyFlatDetection(BaseModel):
    """Detection-only granny flat result (no confirmation step)."""

    structure_count: Optional[int] = None
    sepp_eligible: Optional[bool] = None
    sepp_ineligible_reason: Optional[str] = None
    lot_area_m2: Optional[float] = None
    confirmation_required: bool = True  # always true — user must confirm in standalone tool


class PreDAHistoryDetail(BaseModel):
    """Pre-DA site history timeline (premium tier)."""

    timeline: Optional[list[dict]] = None
    heritage_flag: Optional[bool] = None
    council: Optional[str] = None
    data_quality_note: Optional[str] = None


class SatelliteData(BaseModel):
    """Container for all satellite/paid-tier pipeline results."""

    bushfire: DataField[Optional[BushfireDetail]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="bushfire_prescreen", reason="Satellite data not requested",
    )
    flood: DataField[Optional[FloodDetail]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="flood_truth", reason="Satellite data not requested",
    )
    climate_disclosure: DataField[Optional[ClimateDisclosureProfile]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="climate_disclosure_profile", reason="Satellite data not requested",
    )
    granny_flat: DataField[Optional[GrannyFlatDetection]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="granny_flat_detect", reason="Satellite data not requested",
    )
    pre_da_history: DataField[Optional[PreDAHistoryDetail]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="pre_da_history", reason="Premium data not requested",
    )
    terrain: DataField[Optional[TerrainAnalysisDetail]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="terrain_analysis", reason="Satellite data not requested",
    )


class CompoundConstraint(BaseModel):
    """Cross-layer insight that only emerges from combining data."""

    id: str
    description: str
    caveat: str
    severity: CompoundSeverity
    data_sources_used: list[str] = []


class GapEntry(BaseModel):
    """Disclosed data gap — field that could not be populated."""

    field: str
    reason: str
    verify_url: Optional[str] = None


class ConfidenceSummary(BaseModel):
    """Aggregate confidence across all fields."""

    authoritative: int = 0
    extracted: int = 0
    estimated: int = 0
    derived: int = 0
    not_available: int = 0
    stale: int = 0
    total: int = 0


# ---------------------------------------------------------------------------
# Response models — the contract
# ---------------------------------------------------------------------------


class DevelopmentBrief(BaseModel):
    """Full intelligence brief for freestanding/development-capable lots."""

    brief_type: Literal["development"] = "development"
    address: str
    lat: float
    lng: float
    prop_id: Optional[int] = None
    run_date: str
    strata: DataField[StrataInfo]
    planning_controls: PlanningControls
    dcp_controls: DCPControls
    sepp_housing: DataField[list[SEPPStandard]]
    sepp_lep_overrides: list[SeppLepOverride] = []
    # Per-form Housing-SEPP eligibility with clause citations, from the SAME
    # evaluate_eligibility run the capacity ceiling uses (computed once).
    # value=None = engine errored; [] = ran, no applicable forms for this zone.
    sepp_eligibility: Optional[DataField[Optional[list[HousingSeppFormOutput]]]] = None
    environmental_constraints: EnvironmentalConstraints
    neighbourhood: Neighbourhood
    economics: Economics
    market_context: Optional[DataField[Optional[MarketContext]]] = None
    contributions: Optional[DataField[ContributionsResult]] = None
    satellite: Optional[SatelliteData] = None
    constraint_arithmetic: Optional[DataField[ConstraintArithmeticResult]] = None
    compound_constraints: list[CompoundConstraint] = []
    data_currency_warnings: list[str] = []
    gaps: list[GapEntry] = []
    scope_limitations: list[str] = []
    confidence_summary: ConfidenceSummary
    narrative: Optional[str] = None
    disclaimer: str = (
        "This site screening brief is for preliminary research purposes only. "
        "It does not constitute planning, legal, or financial advice. "
        "Data is sourced from NSW government and council sources — accuracy is "
        "not independently verified. Conditions may have changed since the data "
        "was last updated. Engage a qualified town planner for site-specific assessment."
    )

    model_config = ConfigDict(extra="forbid")


class RenovationBrief(BaseModel):
    """Reduced brief for apartment strata (no development analysis)."""

    brief_type: Literal["renovation"] = "renovation"
    address: str
    lat: float
    lng: float
    prop_id: Optional[int] = None
    run_date: str
    strata: DataField[StrataInfo]
    planning_controls: PlanningControls
    environmental_constraints: EnvironmentalConstraints
    economics: Economics
    satellite: Optional[SatelliteData] = None
    compound_constraints: list[CompoundConstraint] = []
    data_currency_warnings: list[str] = []
    gaps: list[GapEntry] = []
    scope_limitations: list[str] = []
    confidence_summary: ConfidenceSummary
    disclaimer: str = (
        "This site screening brief is for preliminary research purposes only. "
        "It does not constitute planning, legal, or financial advice. "
        "Data is sourced from NSW government and council sources — accuracy is "
        "not independently verified. Conditions may have changed since the data "
        "was last updated. Engage a qualified town planner for site-specific assessment."
    )

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def classify_strata(
    strata_info: dict,
    lot_area_m2: Optional[float],
) -> StrataType:
    """Classify strata type from cadastre data + StrataHub lot count + lot area.

    Prefers the StrataHub strata-plan lot count (authoritative; boundaries
    smoke-tested in ``strata_lookup.classify_dwelling_type``) when available,
    because lot count separates apartment vs townhouse far better than lot area.
    The lot-area heuristic is a weaker fallback — spike finding: the 1500m²
    heuristic misclassifies strata townhouses — used only when no count is
    available. Four-state enum; ambiguity is accepted for the residual cases.

    Args:
        strata_info: cadastre strata dict; may carry ``lot_total`` enriched from
            StrataHub by ``_fetch_strata``.
        lot_area_m2: parcel area, used only for the fallback heuristic.
    """
    if not strata_info.get("is_strata"):
        return StrataType.NOT_STRATA

    # Definitive signal
    plan_type = (strata_info.get("plan_type") or "").lower()
    if plan_type in ("community", "neighbourhood"):
        return StrataType.DEVELOPMENT  # community title = ground-level

    # Preferred signal: StrataHub lot count. Few lots = low-rise / ground-level
    # strata (development analysis can apply); many lots = apartment form (per-lot
    # development analysis does not apply). Boundary mirrors classify_dwelling_type
    # (<=2 duplex, 3-4 townhouse, 5-8 small apartment, 9+ apartment).
    lot_total = strata_info.get("lot_total")
    if isinstance(lot_total, int) and not isinstance(lot_total, bool) and lot_total > 0:
        if lot_total <= 4:
            return StrataType.DEVELOPMENT  # duplex / townhouse
        return StrataType.APARTMENT  # 5+ lots → (small) apartment

    # Fallback heuristic (weak): lot area, only when no lot count is available.
    if lot_area_m2 is not None:
        if lot_area_m2 > 2500:
            return StrataType.APARTMENT  # very large parent lot → high confidence
        if lot_area_m2 < 400:
            return StrataType.DEVELOPMENT  # tiny lot → strata subdivision of house
        # 400-2500m² → ambiguous without building footprint data
        return StrataType.AMBIGUOUS

    return StrataType.AMBIGUOUS


def _strata_scope_note(strata_type: StrataType) -> list[str]:
    """Honest scope note for the apartment/strata brief.

    The apartment brief intentionally omits development-capacity analysis; this
    states *why* in plain language so the absence reads as a defined scope, not a
    silent blank (Bug 4 Stage 2). Factual scope statement only — no advice and no
    computed yield. APARTMENT and AMBIGUOUS get distinct wording; other states
    return no note.
    """
    if strata_type == StrataType.APARTMENT:
        return [
            "This address is an individual lot within a strata scheme. "
            "Development-capacity analysis is not provided for individual strata "
            "lots — redevelopment of a strata scheme is a matter for the owners "
            "corporation and the whole site. Engage a qualified town planner for "
            "a site-specific assessment."
        ]
    if strata_type == StrataType.AMBIGUOUS:
        return [
            "Strata status could not be determined for this address from the "
            "available data, so development-capacity analysis is not provided. "
            "Whether this is an individual strata lot or a developable parcel can "
            "be resolved by checking the strata plan or the building footprint."
        ]
    return []


def _zone_prefix(zone: Optional[str]) -> str:
    """Extract zone prefix safely. Returns empty string on None/empty.

    Fixes the IndexError that occurs when splitting an empty zone string
    and accessing index zero of the resulting empty list.
    """
    if not zone or not zone.strip():
        return ""
    parts = zone.strip().split()
    return parts[0].upper() if parts else ""


def _sanitise(value: Optional[str]) -> Optional[str]:
    """Strip HTML tags and null bytes from external API strings."""
    if value is None:
        return None
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("\x00", "")
    return value.strip()


def compute_confidence_summary(brief) -> ConfidenceSummary:
    """Walk all DataField instances in a brief and tally confidence levels."""
    summary = ConfidenceSummary()

    def _walk(obj):
        if isinstance(obj, DataField):
            level = obj.confidence
            if level == ConfidenceLevel.AUTHORITATIVE:
                summary.authoritative += 1
            elif level == ConfidenceLevel.EXTRACTED:
                summary.extracted += 1
            elif level == ConfidenceLevel.ESTIMATED:
                summary.estimated += 1
            elif level == ConfidenceLevel.DERIVED:
                summary.derived += 1
            elif level == ConfidenceLevel.NOT_AVAILABLE:
                summary.not_available += 1
            elif level == ConfidenceLevel.STALE:
                summary.stale += 1
            summary.total += 1
        elif isinstance(obj, BaseModel):
            for field_name in obj.model_fields:
                _walk(getattr(obj, field_name, None))
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(brief)
    return summary


def check_minimum_viable(summary: ConfidenceSummary) -> bool:
    """Returns True if enough fields are available to serve the brief.

    Threshold: >=70% of fields must not be 'not_available'.
    """
    if summary.total == 0:
        return False
    available = summary.total - summary.not_available
    return (available / summary.total) >= CONFIG.min_available_ratio


def collect_gaps(brief) -> list[GapEntry]:
    """Walk all DataField instances and collect not_available ones as gaps."""
    gaps: list[GapEntry] = []

    def _walk(obj, prefix: str = ""):
        if isinstance(obj, DataField):
            if obj.confidence == ConfidenceLevel.NOT_AVAILABLE:
                gaps.append(GapEntry(
                    field=prefix,
                    reason=obj.reason or f"{obj.source} returned no data",
                ))
        elif isinstance(obj, BaseModel):
            for field_name in obj.model_fields:
                child = getattr(obj, field_name, None)
                path = f"{prefix}.{field_name}" if prefix else field_name
                _walk(child, path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _walk(item, f"{prefix}[{i}]")

    _walk(brief)
    return gaps


# ---------------------------------------------------------------------------
# Imports from existing conveyancing pipeline — same functions, different output
# ---------------------------------------------------------------------------

_project_root = Path(__file__).parent.parent
_scripts_dir = _project_root / "scripts"
_services_dir = Path(__file__).parent
sys.path.insert(0, str(_scripts_dir))
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_services_dir))

from generate_conveyancing_report import (  # noqa: E402
    resolve_address,
    resolve_propid_by_point,
    get_raw_controls,
    parse_controls,
    get_valuation,
    get_unique_overlays,
    detect_strata,
    detect_former_council,
    get_shadow_risk,
    _council_from_zone_epi,
)
from conveyancing_db import (  # noqa: E402
    fetch_dcp_setbacks,
    fetch_heritage_postgis,
    fetch_nearby_das as db_fetch_nearby_das,
    fetch_sepp_housing_standards,
)
from lga_lookup import lookup_lga  # noqa: E402
from compound_constraints import (  # noqa: E402
    evaluate_compound_constraints,
    evaluate_satellite_constraints,
    detect_staleness,
    enrich_gaps_with_verify_url,
)

# Satellite pipeline imports — each is optional; _safe_call handles ImportError at call time
try:
    from bushfire_prescreen import run_bushfire, BushfireRequest  # noqa: E402
except ImportError:
    from services.bushfire_prescreen import run_bushfire, BushfireRequest  # noqa: E402

try:
    from flood_truth import run_flood, FloodRequest  # noqa: E402
except ImportError:
    from services.flood_truth import run_flood, FloodRequest  # noqa: E402

try:
    from climate_risk_score import climate_risk_score as _climate_risk_score_fn  # noqa: E402
except ImportError:
    from services.climate_risk_score import climate_risk_score as _climate_risk_score_fn  # noqa: E402

try:
    from pre_da_history import run_pre_da_history, PreDAHistoryRequest  # noqa: E402
except ImportError:
    from services.pre_da_history import run_pre_da_history, PreDAHistoryRequest  # noqa: E402

try:
    from terrain_analysis import run_terrain_analysis, TerrainAnalysisDetail  # noqa: E402
except (ImportError, ModuleNotFoundError):
    try:
        from services.terrain_analysis import run_terrain_analysis, TerrainAnalysisDetail  # noqa: E402
    except (ImportError, ModuleNotFoundError):
        # rasterio/whitebox not installed — provide stubs for non-terrain callers
        from pydantic import BaseModel as _BM

        class TerrainAnalysisDetail(_BM):  # type: ignore[no-redef]
            """Stub when rasterio unavailable."""
            slope_mean_deg: Optional[float] = None
            hillshade_png_b64: Optional[str] = None

        def run_terrain_analysis(*args, **kwargs):  # type: ignore[no-redef]
            raise RuntimeError("terrain_analysis unavailable — rasterio not installed")


# ---------------------------------------------------------------------------
# DB connection helper — shared by all DB-dependent calls in this module
# ---------------------------------------------------------------------------


def _get_db_conn():
    """Get a psycopg2 connection. Raises if DATABASE_URL not set."""
    import psycopg2
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise EnvironmentError("DATABASE_URL not set")
    conn = psycopg2.connect(db_url, options="-c statement_timeout=5000")
    conn.autocommit = True
    return conn


# GATE-1 part 2: derive the development FORM from the LEP Land Use Table
# (lep_land_use_table — per-zone, per-LGA permitted/prohibited) so the engine
# computes yield for the densest PERMITTED form, not a hardcoded dwelling_house.
# Density order (densest first); each maps the table's snake_case form to the
# engine dev_type string.
_PERMITTED_FORM_DENSITY = (
    ("residential_flat_buildings", "residential_flat_building"),
    ("shop_top_housing", "shop_top_housing"),
    ("multi_dwelling_housing", "multi_dwelling_housing"),
    ("attached_dwellings", "attached_dwelling"),
    ("manor_houses", "manor_house"),
    ("dual_occupancies", "dual_occupancy"),
    ("semi_detached_dwellings", "dual_occupancy"),
    ("dwelling_houses", "dwelling_house"),
)


# Engine dev_type forms in density order (densest first), de-duplicated from the
# mapping above. Used to rank forms against the zone-tier ceiling.
_ENGINE_FORM_DENSITY: tuple[str, ...] = tuple(
    dict.fromkeys(engine for _, engine in _PERMITTED_FORM_DENSITY)
)

# Realism ceiling per residential zone — the densest built form that reflects the
# zone's *character*, independent of the LGA. This is Standard-Instrument structural
# metadata (the R1–R5 density hierarchy), universal across NSW and never amended
# per-LGA, so it is NOT hardcoded LEP regulatory data — it only ever CAPS the form
# downward. The permitted list (per-LGA) then filters further. Together they stop an
# outlier permitted-with-consent use (e.g. shop_top_housing in low-density R2) being
# read as the realistic yield. LMR/Housing-SEPP uplift of these ceilings is a later
# refinement; this is the conservative baseline.
_ZONE_TIER_CEILING: dict[str, str] = {
    "R1": "residential_flat_building",   # General Residential — full range
    "R2": "dual_occupancy",              # Low Density — house / dual-occ
    "R3": "multi_dwelling_housing",      # Medium Density — terraces / townhouses
    "R4": "residential_flat_building",   # High Density — apartments
    "R5": "dwelling_house",              # Large Lot — single dwellings
}


def _bare_lga_from_epi(zone_epi: Optional[str]) -> Optional[str]:
    """LGA name from a Standard Instrument EPI title, without instrument phrase/year.

    "Canada Bay Local Environmental Plan 2013" -> "Canada Bay". More reliable than
    _council_from_zone_epi for the LEP-table join (that helper appends council
    suffixes and returns None for some LGAs). Returns None if no instrument phrase.
    """
    s = (zone_epi or "").upper()
    cut = -1
    for marker in ("LOCAL ENVIRONMENTAL PLAN", " LEP"):
        idx = s.find(marker)
        if idx > 0:
            cut = idx
            break
    if cut < 0:
        return None
    name = (zone_epi or "")[:cut].strip()
    return name or None


def _norm_lga(name: Optional[str]) -> str:
    """Normalise an LGA / council name for matching across naming conventions.

    Drops council-type and connective words so "Council of the City of Sydney",
    "Strathfield Municipal Council" and the bare table values "Sydney"/"Strathfield"
    reduce to the same key. The 25 LEP-table LGAs reduce to distinct keys (verified
    2026-06-19), so this cannot cross-match.
    """
    if not name:
        return ""
    s = name.lower().replace("-", " ")
    drop = {"council", "city", "shire", "municipal", "municipality", "regional", "of", "the"}
    tokens = [t for t in re.split(r"[^a-z0-9]+", s) if t and t not in drop]
    return " ".join(tokens)


def _permitted_engine_forms(zone_code: Optional[str], lga_name: Optional[str]) -> set[str]:
    """Set of engine dev_type forms PERMITTED for this zone + LGA in the LEP Land
    Use Table. Empty set on missing inputs / no coverage (25 LGAs) / any error —
    the caller then fails safe to ``dwelling_house``. The LGA is matched via
    _norm_lga so a council-name suffix mismatch no longer silently empties the set.
    """
    if not zone_code or not lga_name:
        return set()
    target = _norm_lga(lga_name)
    if not target:
        return set()
    conn = None
    try:
        conn = _get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT lga, development_type FROM lep_land_use_table "
            "WHERE zone = %s AND permissibility = 'permitted'",
            (zone_code,),
        )
        table_forms = {dt for (lga, dt) in cur.fetchall() if _norm_lga(lga) == target}
        return {engine for (tbl, engine) in _PERMITTED_FORM_DENSITY if tbl in table_forms}
    except Exception as e:  # fail-safe: any error -> empty -> caller defaults
        logger.warning("permitted form lookup failed (%s/%s): %s", zone_code, lga_name, e)
        return set()
    finally:
        if conn:
            conn.close()


def _ceiling_within_tier(
    zone_code: Optional[str],
    permitted_engine_forms: set[str],
    excluded_forms: Optional[set[str]] = None,
) -> str:
    """Densest permitted form AT OR BELOW the zone-tier ceiling.

    Walks the density ladder from the zone's realism ceiling downward and returns the
    first form that is permitted — so an outlier permitted use *denser* than the zone
    tier (shop_top in R2) is never selected. ``excluded_forms`` (e.g. a form prohibited
    on this lot by a live SEPP exclusion gate) are skipped. Fail-safe to ``dwelling_house``.
    """
    excluded = excluded_forms or set()
    tier_form = _ZONE_TIER_CEILING.get((zone_code or "").strip().upper(), "dwelling_house")
    try:
        start = _ENGINE_FORM_DENSITY.index(tier_form)
    except ValueError:
        start = _ENGINE_FORM_DENSITY.index("dwelling_house")
    for form in _ENGINE_FORM_DENSITY[start:]:
        if form in permitted_engine_forms and form not in excluded:
            return form
    return "dwelling_house"


def _realistic_forms(
    zone_code: Optional[str],
    lga_name: Optional[str],
    excluded_forms: Optional[set[str]] = None,
    uplift_form: Optional[str] = None,
    return_source: bool = False,
):
    """Return (as_of_right_form, ceiling_form) for the capacity range.

    - as_of_right_form: the conservative, always-true baseline (``dwelling_house``).
    - ceiling_form: the densest of (a) the base form bounded by the zone tier ∩ the LGA's
      permitted list, minus ``excluded_forms``, and (b) ``uplift_form`` — the densest form
      the Housing-SEPP/LMR engine found ELIGIBLE for this lot (which can legitimately exceed
      the base zone tier, e.g. a residential flat in a TOD catchment). The realistic upside,
      subject to a DA. Fail-safe to ``dwelling_house``.
    """
    base = _ceiling_within_tier(
        zone_code, _permitted_engine_forms(zone_code, lga_name), excluded_forms
    )
    ceiling = base
    if uplift_form and uplift_form in _ENGINE_FORM_DENSITY and base in _ENGINE_FORM_DENSITY:
        # Lower index = denser; take the denser of the base and the eligible LMR uplift.
        if _ENGINE_FORM_DENSITY.index(uplift_form) < _ENGINE_FORM_DENSITY.index(base):
            ceiling = uplift_form
    if return_source:
        # The ceiling came from LMR only when the uplift strictly raised it above
        # the base zone-tier form (not when the base already reached that density).
        ceiling_from_lmr = bool(uplift_form) and ceiling == uplift_form and ceiling != base
        return "dwelling_house", ceiling, ceiling_from_lmr
    return "dwelling_house", ceiling


# housing_sepp_standards development_type -> engine ceiling form, for the LMR/SEPP uplift.
# (dwelling_houses / secondary_dwelling do not raise the ceiling FORM — they affect the floor.)
_SEPP_FORM_TO_ENGINE = {
    "residential_flat_r1r2": "residential_flat_building",
    "residential_flat_r3r4_inner": "residential_flat_building",
    "residential_flat_r3r4_outer": "residential_flat_building",
    "multi_dwelling": "multi_dwelling_housing",
    "terraces": "attached_dwelling",
    "manor_house": "manor_house",
    "dual_occupancy": "dual_occupancy",
}


def _sepp_eligibility_results(
    zone_code: Optional[str], lat: Optional[float], lng: Optional[float],
    lot_area_m2: Optional[float], lot_width_m: Optional[float], heritage: bool,
) -> Optional[list]:
    """Run the Housing-SEPP eligibility engine ONCE per brief, fail-safe.

    prior-art-checked: this is the extraction of the existing evaluate_eligibility
    call out of _lmr_uplift_form (below) so the SEPP card and the capacity ceiling
    SHARE one engine run — reuse of services/housing_sepp_eligibility.py, not a
    new eligibility implementation.

    Three states: a populated list = per-form outcomes with citations;
    [] = the engine ran and no forms apply (non-residential zone / no standards);
    None = the engine errored (callers surface NOT_AVAILABLE, never a silent
    "nothing applies").
    """
    try:
        from services.housing_sepp_eligibility import evaluate_eligibility
        return evaluate_eligibility(
            zone_code, lot_area_m2, lot_width_m, lat, lng, heritage=heritage
        )
    except Exception as e:  # fail-safe — never block the brief on the eligibility engine
        logger.warning("SEPP eligibility evaluation failed: %s", e)
        return None


def _build_sepp_eligibility_field(results: Optional[list]) -> "DataField":
    """Wrap per-form eligibility outcomes for the SEPP card (S2-typed rows).

    Serialises each FormEligibility dataclass through the HousingSeppFormOutput
    contract so a renamed engine field is a validation error here, not a silent
    null in the card.
    """
    today = date.today().isoformat()
    if results is None:
        return DataField(
            value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="housing_sepp_standards", as_at=today,
            reason="Eligibility assessment did not complete",
        )
    from dataclasses import asdict

    try:
        forms = [HousingSeppFormOutput.model_validate(asdict(r)) for r in results]
    except ValidationError as e:
        # A contract violation is a FAILED assessment, never a stream-killing
        # exception or silently-wrong rows.
        logger.warning("SEPP eligibility rows failed the S2 contract: %s", e)
        return DataField(
            value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="housing_sepp_standards", as_at=today,
            reason="Eligibility rows failed the typed contract",
        )
    return DataField(
        value=forms, confidence=ConfidenceLevel.AUTHORITATIVE,
        source="housing_sepp_standards", as_at=today,
    )


def _lmr_uplift_form(
    zone_code: Optional[str], lat: Optional[float], lng: Optional[float],
    lot_area_m2: Optional[float], lot_width_m: Optional[float], heritage: bool,
    results: Optional[list] = None,
) -> tuple[Optional[str], Optional[dict]]:
    """Densest engine form ELIGIBLE under the Housing-SEPP / LMR engine (the catchment/area
    uplift, subject to a DA), plus the CITATION of the standard that grants it, or (None, None).

    Delegates to the single-source-of-truth eligibility engine, which carries the clause /
    document / legislation URL / effective date from housing_sepp_standards — so any LMR claim
    the card makes is sourced. Fail-safe: any error -> (None, None) (no uplift; base tier stands).

    ``results``: a precomputed ``evaluate_eligibility`` list (from
    ``_sepp_eligibility_results``) — pass it when the brief already ran the
    engine for the SEPP card so it is never invoked twice per brief.
    """
    if results is None:
        results = _sepp_eligibility_results(
            zone_code, lat, lng, lot_area_m2, lot_width_m, heritage,
        )
    if results is None:  # engine errored — no uplift; base tier stands
        return None, None
    # Map each eligible SEPP form to its engine form, keeping the FormEligibility so the
    # winning form's citation can be attached.
    engine_to_result = {}
    for r in results:
        if r.eligible and r.development_type in _SEPP_FORM_TO_ENGINE:
            engine_to_result.setdefault(_SEPP_FORM_TO_ENGINE[r.development_type], r)
    for form in _ENGINE_FORM_DENSITY:  # densest first
        if form in engine_to_result:
            r = engine_to_result[form]
            citation = None
            if r.source_clause:  # only surface a citation when one genuinely exists
                citation = {
                    "source_clause": r.source_clause,
                    "source_document": r.source_document,
                    "legislation_url": r.legislation_url,
                    "effective_date": r.effective_date,
                }
            return form, citation
    return None, None


def _apply_lmr_attribution(result, ceiling_from_lmr: bool, citation: Optional[dict]) -> None:
    """Attribute the ceiling to LMR ONLY when it genuinely raised the limit AND a real clause
    can be cited. No citation -> no claim (the product never asserts a regulatory fact without
    a source). Sets the flag + the citation fields on the result in place."""
    if result is None:
        return
    if ceiling_from_lmr and citation and citation.get("source_clause"):
        result.ceiling_from_lmr = True
        result.lmr_source_clause = citation.get("source_clause")
        result.lmr_source_document = citation.get("source_document")
        result.lmr_legislation_url = citation.get("legislation_url")
        result.lmr_effective_date = citation.get("effective_date")
    else:
        result.ceiling_from_lmr = False


def _eligibility_excluded_forms(lat: Optional[float], lng: Optional[float]) -> set[str]:
    """Engine forms to EXCLUDE from the capacity ceiling, from live SEPP eligibility gates.

    Wires a previously fetched-but-unused exclusion layer into the capacity decision so the
    backend brief and the planning UI can no longer disagree:
    - **Dual occupancy prohibition** (ePlanning layer 452): where a lot is inside a
      dual-occupancy prohibition area, ``dual_occupancy`` is removed from the ceiling (an
      R2 lot then tops out at ``dwelling_house`` instead of a prohibited dual occ).

    Heritage is handled separately (GATE-2 suppresses SEPP overrides on heritage land). The
    776 low/mid-rise exclusion has no active ceiling effect yet — the ceiling reflects
    base-LEP permissions, and LMR *uplift* (which 776 would suppress) lands in P2.

    Fail-safe: missing coordinates or any query error -> empty set (ceiling unchanged, never
    over-restricted on a transient failure).
    """
    if lat is None or lng is None:
        return set()
    excluded: set[str] = set()
    try:
        dual = _fetch_dual_occ_prohibition(lat, lng)
        if dual and dual.get("prohibited"):
            excluded.add("dual_occupancy")
    except Exception as e:  # fail-safe — never block the brief on a gate query
        logger.warning("dual-occ prohibition gate query failed: %s", e)
    return excluded


# ---------------------------------------------------------------------------
# LGA validation — Fix A from IMPLEMENTATION.md
# ---------------------------------------------------------------------------


def _validate_former_council_postgis(
    text_slug: Optional[str],
    lat: float,
    lng: float,
    address: str,
) -> tuple[Optional[str], Optional[str]]:
    """Cross-check text-derived LGA slug against PostGIS boundary.

    Returns (validated_slug, advisory_message).
    advisory_message is populated when PostGIS corrected the text match.
    """
    conn = None
    try:
        conn = _get_db_conn()
        lga_result = lookup_lga(lat, lng, conn, address=address)
    except Exception as e:
        logger.warning("PostGIS LGA validation failed: %s — trusting text match", e)
        return text_slug, None
    finally:
        if conn:
            conn.close()

    postgis_lga = (lga_result.get("lga_name") or "").lower()
    postgis_slug = lga_result.get("lga_slug")

    # Inner West boundary suburbs: text match may resolve to wrong former council
    if text_slug and text_slug in ("marrickville", "leichhardt", "ashfield"):
        if postgis_lga and postgis_lga != "inner west":
            advisory = (
                f"LGA boundary verified by spatial lookup: text-based detection "
                f"returned '{text_slug}' but coordinates confirm '{postgis_lga}'. "
                f"DCP controls may not be available for this LGA."
            )
            logger.info("Fix A: %s → PostGIS overrode to %s", text_slug, postgis_lga)
            return None, advisory

    # Text match returned None but PostGIS says Inner West — resolve
    if text_slug is None and postgis_lga == "inner west" and postgis_slug:
        if postgis_slug not in ("inner_west",):
            advisory = (
                f"Former council resolved via spatial lookup: '{postgis_slug}' "
                f"(text-based detection could not determine former council)."
            )
            logger.info("Fix A: PostGIS resolved unmapped suburb → %s", postgis_slug)
            return postgis_slug, advisory

    return text_slug, None


# ---------------------------------------------------------------------------
# Address validation — NSW bbox check
# ---------------------------------------------------------------------------


def _validate_coordinates(lat: float, lng: float) -> Optional[str]:
    """Check coordinates are within NSW bounding box.

    Returns a warning message if outside, None if OK.
    """
    if not (CONFIG.nsw_lat_min <= lat <= CONFIG.nsw_lat_max):
        return f"Latitude {lat} is outside NSW bounds ({CONFIG.nsw_lat_min} to {CONFIG.nsw_lat_max})"
    if not (CONFIG.nsw_lng_min <= lng <= CONFIG.nsw_lng_max):
        return f"Longitude {lng} is outside NSW bounds ({CONFIG.nsw_lng_min} to {CONFIG.nsw_lng_max})"
    return None


# ---------------------------------------------------------------------------
# Data source fetchers — each returns the raw result, _safe_call wraps them
# ---------------------------------------------------------------------------


def _fetch_controls(prop_id: int) -> dict:
    """Planning Portal: zone, height, FSR, heritage, SEPP overlays."""
    return parse_controls(get_raw_controls(prop_id))


def _fetch_valuation(prop_id: int) -> dict:
    """VG API: lot area, land value, 5-year history."""
    return get_valuation(prop_id)


CP_API = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/cp"


def _fetch_contributions(prop_id: int) -> Optional[ContributionsResult]:
    """Planning Portal /cp: development contributions plans and HPC overlay."""
    import requests

    try:
        r = requests.get(CP_API, params={"id": prop_id, "type": "property"}, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None

    plans: list[ContributionPlan] = []
    lga_name: Optional[str] = None

    cp_results = (data.get("cp") or {}).get("results") or []
    for entry in cp_results:
        if not lga_name:
            lga_name = entry.get("lgaName")
        for cp in (entry.get("cpResults") or []):
            plans.append(ContributionPlan(
                plan_name=cp.get("planName", ""),
                plan_url=cp.get("planURL"),
            ))

    hpc: Optional[HousingProductivityContribution] = None
    icdp_results = (data.get("icdp") or {}).get("results") or []
    for entry in icdp_results:
        for res in (entry.get("results") or []):
            hpc = HousingProductivityContribution(
                name=res.get("Name"),
                component=res.get("Component"),
                commenced_date=res.get("Commenced Date"),
                ministerial_order_url=res.get("Ministerial Order"),
            )
            break
        if hpc:
            break

    if not plans and not hpc:
        return None

    return ContributionsResult(plans=plans, hpc=hpc, lga_name=lga_name)


def _fetch_overlays(lat: float, lng: float, lot_wkt: Optional[str]) -> dict:
    """PostGIS spatial_overlays: environmental constraints."""
    overlays, covered_layers, proximity_m = get_unique_overlays(lat, lng, lot_wkt)
    return {
        "overlays": overlays,
        "covered_layers": list(covered_layers),
        "proximity_m": proximity_m,
    }


def _fetch_strata(address: str, lat: float, lng: float) -> dict:
    """Cadastre strata detection, enriched with the StrataHub lot count.

    ``detect_strata`` (cadastre) decides *whether* a parcel is strata; StrataHub
    adds the *lot count*, the stronger signal for apartment-vs-townhouse
    classification in :func:`classify_strata`. Best-effort: a StrataHub failure
    never fails the brief — we just fall back to the lot-area heuristic.
    """
    result = detect_strata(address, lat, lng)
    if lat is not None and lng is not None and (
        result.get("is_strata") or result.get("parent_has_strata")
    ):
        try:
            from services.strata_lookup import query_strata_at_point

            sh = query_strata_at_point(lng, lat)
            if sh is not None and sh.lot_total:
                result["lot_total"] = sh.lot_total
                result["dwelling_type"] = sh.dwelling_type
                result["registration_date"] = sh.registration_date
        except Exception as e:  # best-effort enrichment only
            logger.warning("StrataHub lot-count enrichment failed: %s", e)
    return result


def _fetch_nearby_das(
    lat: float, lng: float, council_name: Optional[str],
    radius_m: int, days: int,
) -> list[dict]:
    """Nearby development applications from the consolidated ``development_applications``
    table — the SAME reliable source the PlotDetect map-viewer uses (not the
    flaky live ePlanning API, which timed out and returned 0).

    This is a PROXIMITY query: the lat/lng bounding box already constrains
    location, so the council filter is intentionally dropped (``council_name=None``).
    An exact ``council_name = 'X'`` match was returning 0 on any name-format
    mismatch; ``council_name`` is kept in the signature for compatibility but not
    used as a filter. A connection failure propagates so the brief reports
    NOT_AVAILABLE rather than a false "0 nearby DAs".
    """
    conn = None
    try:
        conn = _get_db_conn()
        return db_fetch_nearby_das(conn, lat, lng, council_name=None, radius_m=radius_m, days=days)
    finally:
        if conn:
            conn.close()


def _fetch_da_outcomes(lng: float, lat: float) -> dict:
    """Determined DAs with outcomes near the lot (DA tracking MapServer).

    prior-art-checked: wires the existing services/da_outcome.py (fixed in this
    PR — the TYPE_OF_DEVELOPMENT field rename made every query silently zero).
    Raises on a failed query so _safe_call stamps NOT_AVAILABLE; [] = genuinely
    no determined applications within the radius/window.
    """
    from services.da_outcome import get_data_currency, query_da_outcomes_near

    rows = query_da_outcomes_near(
        lng, lat,
        radius_m=CONFIG.da_outcomes_radius_m,
        years_back=CONFIG.da_outcomes_years_back,
    )
    # The tracking layer is a point-in-time extract (frozen at 2023-04 as of
    # 2026-07): the renderer must state the window the data actually covers,
    # never "last N years" arithmetic from years_back. Window ends come from
    # the rows themselves; data_currency is the layer-wide newest lodgement.
    # If the currency probe fails the whole field fails (raise -> _safe_call
    # stamps NOT_AVAILABLE) — a windowless outcome list would render as if
    # current, which is the defect this fixes.
    data_currency = get_data_currency()
    lodgements = sorted(
        r.lodgement_date for r in rows
        if r.lodgement_date and len(r.lodgement_date) == 10
    )
    return {
        "outcomes": [r.model_dump() for r in rows],
        "radius_m": CONFIG.da_outcomes_radius_m,
        "years_back": CONFIG.da_outcomes_years_back,
        "data_currency": data_currency,
        "window_start": lodgements[0] if lodgements else None,
        "window_end": lodgements[-1] if lodgements else None,
    }


def _fetch_refusal_stats(lga_name: str) -> Optional[dict]:
    """LGA-wide determination counts + refusal rate (DA tracking MapServer).

    Counts and rate only; the period rides along for display. None = the layer
    holds no determined applications for this LGA in the window (queried-empty);
    a failed count query raises (visible failure, never a silent zero).
    """
    from services.da_outcome import get_refusal_rate

    stats = get_refusal_rate(lga_name, years=CONFIG.da_outcomes_years_back)
    return stats.model_dump() if stats is not None else None


def _fetch_shadow(
    address: str, prop_id: int, lat: float, lng: float,
    height_m: Optional[float], report_id: Optional[str] = None,
) -> Optional[dict]:
    """Shadow pipeline via Railway."""
    return get_shadow_risk(
        address, prop_id, lat, lng, height_m=height_m, report_id=report_id,
    )


def _fetch_dcp_controls(
    lga_slug: Optional[str], zone_code: Optional[str],
) -> Optional[dict]:
    """PostGIS: DCP setback controls for former council."""
    if not lga_slug:
        return None
    conn = None
    try:
        conn = _get_db_conn()
        return fetch_dcp_setbacks(conn, lga_slug, zone_code)
    finally:
        if conn:
            conn.close()


def _fetch_heritage_postgis(
    lat: float, lng: float, lot_wkt: Optional[str],
) -> dict:
    """PostGIS: heritage overlays near lot."""
    conn = None
    try:
        conn = _get_db_conn()
        return fetch_heritage_postgis(conn, lat, lng, lot_wkt)
    finally:
        if conn:
            conn.close()


def _fetch_sepp_housing(zone_code: Optional[str]) -> list[dict]:
    """SEPP Housing standards for this zone."""
    conn = None
    try:
        conn = _get_db_conn()
        return fetch_sepp_housing_standards(conn, zone_code=zone_code)
    finally:
        if conn:
            conn.close()


def _fetch_market_context(
    lng: float, lat: float, zone_code: Optional[str],
    lot_area_m2: Optional[float], subject_propid: Optional[int],
) -> dict:
    """VG comparables + recent sales around the subject lot.

    prior-art-checked: this WIRES the existing services/vg_comparables.py
    (get_comparable_values / get_recent_sales) into the brief — the Tier-1
    wire-in the enrichment plan specifies; no new comparables implementation.

    The two halves are isolated: comparables need zone + lot area (same-zone,
    similar-size matching — the scope that keeps a neighbour's different market
    segment out), sales only need coordinates. One half failing must not blank
    the other; only if BOTH fail does this raise so _safe_call stamps the whole
    fetch NOT_AVAILABLE.
    """
    out: dict = {"comparables": None, "comparables_reason": None,
                 "sales": None, "sales_reason": None}
    if zone_code and lot_area_m2:
        try:
            out["comparables"] = get_comparable_values(
                lng, lat, zone_code, lot_area_m2=lot_area_m2,
                radius_m=CONFIG.market_radius_m, subject_propid=subject_propid,
            )
        except Exception as e:
            out["comparables_reason"] = f"{type(e).__name__}: {str(e)[:160]}"
            logger.warning("VG comparables query failed: %s", e)
    else:
        out["comparables_reason"] = "No zone or lot area resolved for comparable matching"
    try:
        out["sales"] = get_recent_sales(
            lng, lat, radius_m=CONFIG.market_radius_m,
            years_back=CONFIG.market_sales_years_back,
        )
    except Exception as e:
        out["sales_reason"] = f"{type(e).__name__}: {str(e)[:160]}"
        logger.warning("VG sales query failed: %s", e)
    if out["comparables"] is None and out["sales"] is None:  # noqa: bracket-access — local dict, keys set above
        raise RuntimeError(out["sales_reason"] or out["comparables_reason"] or "VG queries failed")  # noqa: bracket-access
    return out


def _build_market_context(market_raw: Optional[dict]) -> Optional[MarketContext]:
    """Assemble MarketContext with per-half three-state fields.

    comparables: DERIVED (median/percentile are statistics computed from
    authoritative VG valuations). recent_sales: AUTHORITATIVE records; an empty
    list is a genuine "no sales within the radius/window", kept distinct from a
    failed query (None + reason).
    """
    if not market_raw:
        return None
    today = date.today().isoformat()
    comps = market_raw.get("comparables")
    sales = market_raw.get("sales")
    return MarketContext(
        comparables=DataField(
            value=comps,
            confidence=ConfidenceLevel.DERIVED if comps is not None else ConfidenceLevel.NOT_AVAILABLE,
            source="nsw_valuer_general",
            as_at=today,
            reason=None if comps is not None else (market_raw.get("comparables_reason") or "Comparables query did not complete"),
        ),
        recent_sales=DataField(
            value=[s for s in sales] if sales is not None else None,
            confidence=ConfidenceLevel.AUTHORITATIVE if sales is not None else ConfidenceLevel.NOT_AVAILABLE,
            source="nsw_valuer_general_sales",
            as_at=today,
            reason=None if sales is not None else (market_raw.get("sales_reason") or "Sales query did not complete"),
        ),
    )


def _fetch_land_use_lists(zone_code: str, lga_name: str) -> dict:
    """Permitted/prohibited development types for this zone + LGA from the
    structured ``lep_land_use_table``.

    prior-art-checked: reads the SAME table `_permitted_engine_forms` already
    consumes (rows validated through the S2 ``LepLandUseRow`` contract) — this
    surfaces the full lists the plan's Tier-1 item specifies, not a new source.

    Returns {"permitted": [...], "prohibited": [...], "row_count": N}. Zero rows
    = this council/zone is not in the structured dataset (queried-empty — the
    caller renders "not extracted yet", distinct from a DB failure, which raises
    so _safe_call stamps NOT_AVAILABLE with the error).
    """
    target = _norm_lga(lga_name)
    conn = None
    try:
        conn = _get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT lga, zone, development_type, permissibility "
            "FROM lep_land_use_table "
            "WHERE zone = %s AND permissibility IN ('permitted', 'prohibited')",
            (zone_code,),
        )
        rows = [
            LepLandUseRow.model_validate(
                {"lga": r[0], "zone": r[1], "development_type": r[2], "permissibility": r[3]}
            )
            for r in cur.fetchall()
        ]
    finally:
        if conn:
            conn.close()
    matched = [r for r in rows if _norm_lga(r.lga) == target]
    permitted = sorted({r.development_type for r in matched if r.permissibility == "permitted" and r.development_type})
    prohibited = sorted({r.development_type for r in matched if r.permissibility == "prohibited" and r.development_type})
    return {"permitted": permitted, "prohibited": prohibited, "row_count": len(matched)}


def fetch_anef_zone(lat: float, lng: float) -> Optional[dict]:
    """Sydney ANEF from the curated ``anef_zones`` table — the SAME source the
    verify app's /api/environmental/anef route uses.

    QUARANTINED from the brief's ANEF field since 2026-07-07: the table's
    contours are 10-13-vertex digitisations (ANEF-20 polygon ~789 km²) that
    stamped false values on fringe lots — issue #686. Kept as the documented
    accessor for the verify-app parity and for a future properly re-digitised
    table; no brief or PDF surface calls it.

    prior-art-checked: reuses the existing anef_zones table (no new source); the
    query implementation lives in portal_constraints.fetch_anef_zone_exact —
    this wrapper preserves the fail-open contract. Returns
    ``{"anef_level": int, "airport": str, "anef_version": str}`` or None;
    None on any failure.
    """
    if lat is None or lng is None:
        return None
    try:
        from portal_constraints import fetch_anef_zone_exact
    except ImportError:
        from services.portal_constraints import fetch_anef_zone_exact
    try:
        return fetch_anef_zone_exact(lat, lng)
    except Exception:
        logger.warning("anef_zones point query failed")
        return None


# ---------------------------------------------------------------------------
# Portal constraint fetchers — shared module
# ---------------------------------------------------------------------------

from services.portal_constraints import (
    fetch_mine_subsidence as _fetch_mine_subsidence,
    fetch_contaminated_land as _fetch_contaminated_land,
    fetch_drinking_water_catchment as _fetch_drinking_water_catchment,
    fetch_uhi as _fetch_uhi,
    fetch_arr_ifd as _fetch_arr_ifd,
    fetch_firms_hotspots as _fetch_firms_hotspots,
    fetch_dual_occ_prohibition as _fetch_dual_occ_prohibition,
)
from services.lot_dimensions import (
    fetch_lot_geometry,
    calculate_lot_dimensions,
    eligibility_lot_width,
)


# ---------------------------------------------------------------------------
# Satellite fetchers — Stage 4a
# ---------------------------------------------------------------------------


def _derive_service_report_id(parent_report_id: str, product: str) -> str:
    """Deterministic per-product report id for satellite writes (issue #762).

    flood/bushfire/shadow each upsert into ``property_reports`` with
    ``ON CONFLICT (id) DO UPDATE SET outputs`` — handing every service the
    brief's single parent report_id let the last writer overwrite the first
    writer's ``outputs`` while the row kept the first writer's ``product``
    label (e.g. rows tagged ``product='bushfire'`` carrying flood or shadow
    fields, which then poisoned the bushfire cache read).

    ``uuid5(parent, product)`` keeps one stable row per product per brief run
    (re-runs of the same brief upsert the same derived id) while guaranteeing
    distinct rows across products. The parent report_id itself is unchanged —
    standalone tool flows still poll ``property_reports`` by the id the
    frontend allocated, and the services' own id handling is untouched.
    """
    return str(uuid.uuid5(uuid.UUID(parent_report_id), product))


def _fetch_bushfire(
    address: str, lat: float, lng: float,
    prop_id: Optional[str], report_id: str,
) -> dict:
    """Bushfire pre-screen via RFS BFPL + PostGIS."""
    import uuid
    req = BushfireRequest(
        address=address, lat=lat, lng=lng,
        prop_id=prop_id, report_id=report_id,
    )
    return run_bushfire(req)


def _fetch_flood(
    address: str, lat: float, lng: float,
    prop_id: Optional[str], report_id: str,
) -> dict:
    """Multi-source flood analysis.

    Raises RuntimeError if run_flood returns refused=True (too few sources).
    _safe_call catches this and wraps it as NOT_AVAILABLE DataField, which
    feeds into check_minimum_viable naturally.
    """
    req = FloodRequest(
        address=address, lat=lat, lng=lng,
        prop_id=prop_id, report_id=report_id,
    )
    result = run_flood(req)
    if result.get("refused"):
        raise RuntimeError(
            f"Flood screening refused: {result.get('reason', 'insufficient sources')}"
        )
    return result


def _fetch_climate_risk(lat: float, lng: float) -> dict:
    """Per-hazard climate scores (shim feeds into ClimateDisclosureProfile).

    Also attaches the NARCliM 2.0 projection summary for projected_findings:
    a dict of {prefix}_delta_2050/2090 changes ({} = queried, no grid coverage;
    None = the projection lookup failed — the card shows an honest gap, never
    fabricated projections).
    """
    result = _climate_risk_score_fn(lat, lng)
    out = result.to_dict()
    try:
        from services.climate_risk_raster import query_narclim_summary
        out["narclim"] = query_narclim_summary(lat, lng)
    except Exception as e:  # projection data missing must not blank the hazard card
        logger.warning("NARCLIM summary lookup failed: %s", e)
        out["narclim"] = None
    return out


def _fetch_solar_marker() -> dict:
    """Solar — DECOUPLED like granny flat. The brief never calls the paid Google
    Solar API inline; the frontend SolarBriefCard fires the existing rate-limited
    /api/satellite/solar-yield route (the same pipeline the standalone tool uses),
    so gating/billing stay in one place. This marker only reserves the card slot.
    """
    return {"decoupled": True}


def _fetch_granny_flat_detect(
    address: str, lat: float, lng: float,
    prop_id: str,
) -> dict:
    """Granny flat — DECOUPLED. The brief no longer runs the slow Modal structure
    detection inline (it timed out at 30s and would double-charge Modal now that the
    frontend GrannyFlatCard fires the gated /api/satellite/granny-flat route, which
    gates on SEPP cl 50/53 BEFORE the GPU scan). Emit a light marker so the section
    (and therefore the card slot) still appears; the real detection happens client-side.
    """
    return {"decoupled": True}


def _fetch_pre_da_history(
    address: str, lot_area_m2: Optional[float],
) -> dict:
    """Pre-DA site history (premium, 30-90s)."""
    req = PreDAHistoryRequest(
        address=address, lot_area_m2=lot_area_m2,
    )
    return run_pre_da_history(req)


def _warn_on_drift(contract_cls, raw: Optional[dict], service: str) -> None:
    """S3 inline drift tripwire: log a loud CONTRACT-DRIFT warning when a REAL
    service output is MISSING a contract key (a rename/drop -> the #589 silent-null
    class). Behaviour is unchanged — the card still fail-softs to None; this just
    makes the drift visible in prod logs on real traffic. Never raises.
    """
    try:
        from brief_contract_drift import check_drift
        missing = check_drift(contract_cls, raw or {}).get("missing")
        if missing:
            logger.warning(
                "CONTRACT-DRIFT %s: service output missing contract key(s) %s "
                "(rename/drop) — those card fields will be null", service, missing,
            )
    except Exception:  # drift-logging must never affect the brief
        pass


def _build_bushfire_detail(bushfire_raw: Optional[dict]) -> Optional[BushfireDetail]:
    """Extract BushfireDetail from raw bushfire prescreen output via the S2 contract.

    Reads typed attributes off BushfireServiceOutput so a renamed service key is
    a typed/test failure, not a silent null.
    """
    if not bushfire_raw:
        return None
    _warn_on_drift(BushfireServiceOutput, bushfire_raw.get("outputs"), "bushfire")
    out = BushfireServiceOutput.model_validate(bushfire_raw.get("outputs") or {})
    comp = out.compliance
    return BushfireDetail(
        is_bushfire_prone=out.is_bushfire_prone,
        category=out.designation_category,
        bal_estimate=out.estimated_bal_band,
        vegetation_type=out.designation_guideline,
        fire_signal=out.fire_signal,
        designation_source=out.designation_source,
        bal_assessment_likely_required=out.bal_assessment_likely_required,
        bal_formal_assessment_cost_range=out.bal_formal_assessment_cost_range,
        bal_assessor_directory_url=out.bal_assessor_directory_url,
        data_currency=out.data_currency,
        cross_overlays=(comp.cross_overlays if comp else None),
        rfs_referral_required=(comp.rfs_referral_required if comp else None),
        rfs_referral_triggers=(comp.rfs_referral_triggers if comp else None),
        rfs_referral_note=(comp.rfs_referral_note if comp else None),
        cdc_pathway_available=(comp.cdc_pathway_available if comp else None),
        clearing_10_50_entitled=(comp.clearing_10_50_entitled if comp else None),
        clearing_10_50_exceptions=(comp.clearing_10_50_exceptions if comp else None),
        estimated_consultant_costs=(comp.estimated_consultant_costs if comp else None),
        state_legislation=(comp.state_legislation if comp else None),
        legislation_url=(comp.legislation_url if comp else None),
        confidence=bushfire_raw.get("confidence"),
    )


def _build_flood_detail(flood_raw: Optional[dict]) -> Optional[FloodDetail]:
    """Extract FloodDetail from raw flood truth output via the S2 typed contract.

    Reading typed attributes off FloodServiceOutput (not loose .get on the raw
    dict) makes the flood output key names a single typed contract: a typo or a
    service rename is a static/type error, not a silent null in the card.
    """
    if not flood_raw:
        return None
    _warn_on_drift(FloodServiceOutput, flood_raw.get("outputs"), "flood")
    out = FloodServiceOutput.model_validate(flood_raw.get("outputs") or {})
    epi_class = out.epi_flood_class
    return FloodDetail(
        flood_signal=out.flood_signal,
        # None = not assessed; False = checked, not in a flood class; True = flood class present
        epi_flood=(None if epi_class is None else epi_class != "none"),
        epi_flood_label=out.epi_flood_label,
        ems_flood_detected=out.ems_flood_detected,
        ems_activations=out.ems_activations,
        sar_flood_detected=out.sar_flood_detected,
        sar_confidence=out.sar_confidence,
        sar_analysis_date=out.sar_analysis_date,
        ses_in_flood_planning_area=out.ses_in_flood_planning_area,
        ses_flood_class=out.ses_flood_class,
        ses_study_name=out.ses_study_name,
        jrc_occurrence_pct=out.jrc_water_occurrence_pct,
        jrc_data_year=out.jrc_data_year,
        wofs_frequency_pct=out.dea_wofs_frequency_pct,
        bom_gauge_name=out.bom_gauge_name,
        bom_gauge_distance_km=out.bom_gauge_distance_km,
        bom_last_major_flood_date=out.bom_last_major_flood_date,
        bom_last_major_flood_peak_m=out.bom_last_major_flood_peak_m,
        bom_flood_history=out.bom_flood_history,
        in_100yr_flood_zone=out.in_100yr_flood_zone,
        in_100yr_flood_zone_unconsulted=out.in_100yr_flood_zone_unconsulted,
        ground_elevation_m_ahd=out.ground_elevation_m_ahd,
        s1_gap_warning=out.s1_gap_warning,
        flood_studies=out.flood_studies,
        confidence=flood_raw.get("confidence"),
    )


def _build_shadow_result(shadow_result: Optional[dict]) -> Optional[ShadowResult]:
    """Map raw shadow_detector output into ShadowResult.

    Service scenario keys: label / time_local / shadow_overlap_fraction (0-1) /
    shadow_direction_deg / overlaps_subject_lot. Overlap fraction -> percent.
    """
    if not shadow_result:
        return None
    _warn_on_drift(ShadowServiceOutput, shadow_result, "shadow")
    out = ShadowServiceOutput.model_validate(shadow_result)
    scenarios = []
    for s in out.scenarios:
        frac = s.shadow_overlap_fraction
        scenarios.append(ShadowScenario(
            date_label=(s.label or ""),
            time_label=(s.time_local or ""),
            # WO-5: sun_altitude_deg/sun_azimuth_deg removed — the shadow service
            # never emits them (it emits shadow_direction_deg = opposite of sun
            # azimuth) and nothing renders them, so they were always-null dead fields.
            shadow_length_m=s.shadow_length_m,
            overlap_pct=(frac * 100 if frac is not None else None),
            shadow_direction_deg=s.shadow_direction_deg,
            overlaps_subject_lot=s.overlaps_subject_lot,
            status=s.status,
            error_note=s.error_note,
        ))
    return ShadowResult(
        height_m=out.height_m,
        height_source=out.height_source,
        adg_compliant=out.adg_compliant,
        scenarios=scenarios,
        worst_case_scenario=out.worst_case_scenario,
        confidence=out.confidence,
    )


def _build_climate_disclosure(
    climate_raw: Optional[dict],
    uhi_raw: Optional[dict] = None,
    arr_raw: Optional[dict] = None,
    firms_raw: Optional[dict] = None,
) -> Optional[ClimateDisclosureProfile]:
    """Build ClimateDisclosureProfile from Phase B data sources."""
    today = date.today().isoformat()
    if not (climate_raw or uhi_raw or arr_raw or firms_raw):
        return None

    # S2 boundary: tripwire-validate the climate output against the typed
    # contract. The hazard dicts pass through to per_hazard_detail RAW (no
    # re-shaping — a new service key must not be silently dropped here); the
    # contract catches type-level violations, which are treated as a FAILED
    # climate source rather than silently-wrong hazard rows.
    if climate_raw:
        _warn_on_drift(ClimateRiskServiceOutput, climate_raw, "climate")
        try:
            ClimateRiskServiceOutput.model_validate(climate_raw)
        except ValidationError as e:
            logger.warning("climate output failed the S2 contract — treating as unavailable: %s", e)
            climate_raw = None

    hazards_raw = (climate_raw.get("hazards") or []) if climate_raw else []
    empirical = []
    sources_queried = 0
    sources_successful = 0
    unavailable: list[UnavailableSource] = []
    quality_notes: list[str] = []

    sources_queried += 1
    if uhi_raw:
        sources_successful += 1
        empirical.append(EmpiricalFinding(
            hazard="urban_heat_island",
            value=uhi_raw.get("uhi_intensity"),
            unit="degrees_c_above_baseline",
            source="NSW UHGC (2016 meshblock data)",
            data_date="2016",
            confidence=ConfidenceLevel.ESTIMATED,
            false_positive_likelihood=FalsePositiveLikelihood.LOW,
        ))
        quality_notes.append("UHI data is 2016 vintage (most recent NSW-wide meshblock dataset)")
    else:
        unavailable.append(UnavailableSource(source="nsw_uhgc", reason="Outside UHGC coverage or query failed"))

    sources_queried += 1
    if arr_raw:
        sources_successful += 1
        ifd_val = arr_raw.get("ifd_1pct_60min_mm")
        if ifd_val is not None:
            empirical.append(EmpiricalFinding(
                hazard="extreme_rainfall",
                value=ifd_val,
                unit="mm_1pct_aep_60min",
                source="ARR Data Hub (BOM IFD)",
                data_date=today,
                confidence=ConfidenceLevel.ESTIMATED,
                false_positive_likelihood=FalsePositiveLikelihood.LOW,
            ))
    else:
        unavailable.append(UnavailableSource(source="arr_data_hub", reason="ARR Data Hub query failed"))

    sources_queried += 1
    if firms_raw is not None:
        sources_successful += 1
        if (firms_raw.get("hotspot_count") or 0) > 0:
            empirical.append(EmpiricalFinding(
                hazard="active_fire",
                value=float(firms_raw.get("hotspot_count", 0)),
                unit="detections",
                source=f"NASA FIRMS VIIRS ({firms_raw.get('search_days', 10)}d, {firms_raw.get('search_radius_km', 0.5)}km)",
                data_date=today,
                confidence=ConfidenceLevel.ESTIMATED,
                false_positive_likelihood=FalsePositiveLikelihood.MODERATE,
            ))
    else:
        unavailable.append(UnavailableSource(source="nasa_firms", reason="FIRMS API key missing or query failed"))

    if climate_raw:
        sources_queried += 1
        sources_successful += 1

    # NARCliM 2.0 projections -> Layer-3 projected findings. Three states:
    # populated dict = grid coverage with deltas; {} = queried, no coverage at
    # this location; None = the lookup failed. Values are model outputs — the
    # scenario/timeframe ride along so a number is never presented bare.
    projected: list[ProjectedFinding] = []
    narclim = climate_raw.get("narclim") if climate_raw else None
    _NARCLIM_HAZARDS = {
        "hot_days": ("extreme_heat_days", "additional days ≥35°C per year"),
        "temp": ("mean_temperature", "°C change in mean temperature"),
        "precip": ("daily_precipitation", "mm/day change in mean precipitation"),
    }
    if climate_raw is not None:
        sources_queried += 1
        if narclim is None:
            unavailable.append(UnavailableSource(
                source="narclim_projections",
                reason="NARCliM projection lookup failed or data not deployed",
            ))
        elif not narclim:
            unavailable.append(UnavailableSource(
                source="narclim_projections",
                reason="No NARCliM grid coverage at this location",
            ))
        else:
            sources_successful += 1
            for prefix, (hazard, _unit_note) in _NARCLIM_HAZARDS.items():
                for horizon in ("2050", "2090"):
                    val = narclim.get(f"{prefix}_delta_{horizon}")
                    if isinstance(val, (int, float)):
                        projected.append(ProjectedFinding(
                            hazard=hazard,
                            value=float(val),  # qa-ignore: guarded by the isinstance numeric check above
                            model="NARCliM 2.0 (AdaptNSW)",
                            scenario="worst available scenario vs 2015–2024 baseline",
                            timeframe=horizon,
                        ))

    coverage = (sources_successful / sources_queried * 100) if sources_queried > 0 else 0.0

    return ClimateDisclosureProfile(
        assessment_date=today,
        manifest=AssessmentManifest(
            categories_assessed=len(empirical) + len(hazards_raw),
            sources_queried=sources_queried,
            sources_successful=sources_successful,
            sources_unavailable=unavailable,
            coverage_pct=round(coverage, 1),
            data_quality_notes=quality_notes,
        ),
        per_hazard_detail=hazards_raw,
        empirical_findings=empirical,
        projected_findings=projected,
    )


def _build_granny_flat_detail(granny_flat_raw: Optional[dict]) -> Optional[GrannyFlatDetection]:
    """Extract GrannyFlatDetection from raw detection output."""
    if not granny_flat_raw:
        return None
    return GrannyFlatDetection(
        structure_count=granny_flat_raw.get("samgeo_structure_count"),
        sepp_eligible=granny_flat_raw.get("sepp_eligible"),
        sepp_ineligible_reason=granny_flat_raw.get("sepp_ineligible_reason"),
        lot_area_m2=granny_flat_raw.get("lot_area_m2"),
        confirmation_required=True,
    )


def _build_pre_da_detail(pre_da_raw: Optional[dict]) -> Optional[PreDAHistoryDetail]:
    """Extract PreDAHistoryDetail from raw pre-DA output.

    A refused run (fail-closed coverage/empty-timeline gate, issue #751) carries
    no timeline — treat it as no detail; the refusal reason is surfaced on the
    DataField by ``_pre_da_reason``.
    """
    if not pre_da_raw or pre_da_raw.get("refused"):
        return None
    return PreDAHistoryDetail(
        timeline=pre_da_raw.get("timeline"),
        heritage_flag=pre_da_raw.get("heritage_flag"),
        council=pre_da_raw.get("council"),
        data_quality_note=pre_da_raw.get("data_quality_note"),
    )


def _pre_da_reason(pre_da_raw: Optional[dict]) -> str:
    """Reason for an absent pre-DA detail: a refused run carries its own
    reason (legit-empty, e.g. no published satellite coverage); anything else
    is the generic not-requested/failed state."""
    if pre_da_raw and pre_da_raw.get("refused") and pre_da_raw.get("reason"):
        return str(pre_da_raw.get("reason"))
    return "Pre-DA history not requested or failed"


def _fetch_terrain(lat: float, lng: float) -> dict:
    """Run terrain analysis (slope, aspect, elevation, ruggedness)."""
    return run_terrain_analysis(lat, lng, include_flood=False)


def _build_terrain_detail(terrain_raw: Optional[dict]) -> Optional[TerrainAnalysisDetail]:
    """Extract TerrainAnalysisDetail from raw terrain output via the S2 contract.

    The contract IS the service's own ``TerrainAnalysisDetail`` (shared class —
    the strongest coupling: a service-side rename renames the brief side too).
    ``_run_terrain_chain`` emits every field on every run (values may be None),
    so a missing key in real output is genuine drift, not noise.
    """
    if not terrain_raw:
        return None
    terrain_fields = terrain_raw.get("terrain") or terrain_raw
    _warn_on_drift(TerrainAnalysisDetail, terrain_fields, "terrain")
    return TerrainAnalysisDetail(**{
        k: v for k, v in terrain_fields.items()
        if k in TerrainAnalysisDetail.model_fields
    })


def _build_satellite_data(
    bushfire_raw: Optional[dict],
    flood_raw: Optional[dict],
    climate_raw: Optional[dict],
    granny_flat_raw: Optional[dict],
    pre_da_raw: Optional[dict],
    uhi_raw: Optional[dict] = None,
    arr_raw: Optional[dict] = None,
    firms_raw: Optional[dict] = None,
    terrain_raw: Optional[dict] = None,
) -> SatelliteData:
    """Assemble satellite pipeline results into SatelliteData model."""
    today = date.today().isoformat()

    bushfire_detail = _build_bushfire_detail(bushfire_raw)
    flood_detail = _build_flood_detail(flood_raw)
    climate_profile = _build_climate_disclosure(climate_raw, uhi_raw, arr_raw, firms_raw)
    gf_detail = _build_granny_flat_detail(granny_flat_raw)
    pre_da_detail = _build_pre_da_detail(pre_da_raw)
    terrain_detail = _build_terrain_detail(terrain_raw)

    return SatelliteData(
        bushfire=DataField(
            value=bushfire_detail,
            confidence=ConfidenceLevel.AUTHORITATIVE if bushfire_detail and bushfire_detail.category else ConfidenceLevel.NOT_AVAILABLE,
            source="bushfire_prescreen",
            as_at=today,
            reason=None if bushfire_detail else "Bushfire pre-screen failed or not requested",
        ),
        flood=DataField(
            value=flood_detail,
            confidence=ConfidenceLevel.ESTIMATED if flood_detail else ConfidenceLevel.NOT_AVAILABLE,
            source="flood_truth",
            as_at=today,
            reason=None if flood_detail else "Flood analysis failed or not requested",
        ),
        climate_disclosure=DataField(
            value=climate_profile,
            confidence=ConfidenceLevel.ESTIMATED if climate_profile else ConfidenceLevel.NOT_AVAILABLE,
            source="climate_disclosure_profile",
            as_at=today,
            reason=None if climate_profile else "Climate disclosure profile failed or not requested",
        ),
        granny_flat=DataField(
            value=gf_detail,
            confidence=ConfidenceLevel.ESTIMATED if gf_detail else ConfidenceLevel.NOT_AVAILABLE,
            source="granny_flat_detect",
            as_at=today,
            reason=None if gf_detail else "Granny flat detection failed or not requested",
        ),
        pre_da_history=DataField(
            value=pre_da_detail,
            confidence=ConfidenceLevel.ESTIMATED if pre_da_detail else ConfidenceLevel.NOT_AVAILABLE,
            source="pre_da_history",
            as_at=today,
            reason=None if pre_da_detail else _pre_da_reason(pre_da_raw),
        ),
        terrain=DataField(
            value=terrain_detail,
            confidence=ConfidenceLevel.ESTIMATED if terrain_detail else ConfidenceLevel.NOT_AVAILABLE,
            source="terrain_analysis",
            as_at=today,
            reason=None if terrain_detail else "Terrain analysis failed or not requested",
        ),
    )


# ---------------------------------------------------------------------------
# Assembly — convert raw dicts to schema models
# ---------------------------------------------------------------------------


def _build_planning_controls(
    controls: dict,
    overlays_data: dict,
    lot_geometry: Optional[dict] = None,
    lot_area_m2: Optional[float] = None,
    controls_failed: bool = False,
    land_use_df: Optional["DataField"] = None,
) -> PlanningControls:
    """Map conveyancing parse_controls output to PlanningControls schema.

    prior-art-checked: extends THIS module's existing builder with the land-use
    lists from _fetch_land_use_lists (same lep_land_use_table the engine already
    reads) — no new source or parallel builder.

    Fail-closed: when the portal controls fetch FAILED (``controls_failed``), the
    portal-derived fields are emitted NOT_AVAILABLE — never blank@AUTHORITATIVE,
    which would read as a confident "no zone / no height control".

    ``land_use_df``: the _fetch_land_use_lists result (a DataField from
    _safe_call/_timed_result). Three states surface distinctly: rows →
    AUTHORITATIVE lists; zero rows → NOT_AVAILABLE "not extracted for this
    council yet"; fetch failure → NOT_AVAILABLE with the error reason.
    """
    today = date.today().isoformat()
    # A FAILED controls fetch must not produce confident blanks.
    auth = ConfidenceLevel.NOT_AVAILABLE if controls_failed else ConfidenceLevel.AUTHORITATIVE

    def _use_list_field(kind: str) -> DataField:
        if land_use_df is None:
            return DataField(
                value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                source="lep_land_use_table", as_at=today,
                reason="No zone resolved for a land-use lookup",
            )
        if land_use_df.confidence == ConfidenceLevel.NOT_AVAILABLE or land_use_df.value is None:
            return DataField(
                value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                source="lep_land_use_table", as_at=today,
                reason=land_use_df.reason or "Land-use table query did not complete",
            )
        lists = land_use_df.value
        if not lists.get("row_count"):
            return DataField(
                value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                source="lep_land_use_table", as_at=today,
                reason="Land-use table not yet extracted for this council",
            )
        return DataField(
            value=lists.get(kind) or [],
            confidence=ConfidenceLevel.AUTHORITATIVE,
            source="lep_land_use_table", as_at=today,
        )

    overlay_list = overlays_data.get("overlays", []) if overlays_data else []

    # Heritage from portal
    heritage_items_raw = controls.get("heritage_items") or []
    heritage_hca_raw = controls.get("heritage_hca") or []

    # SEPP overlays
    sepp_overlays_raw = controls.get("sepp_overlays") or []

    # Housing SEPP and TOD
    housing_sepp = controls.get("housing_sepp", False)
    tod_area = controls.get("tod_area", False)

    # Lot dimensions — frontage/depth from the polygon; area from the
    # authoritative cadastre/valuation lot_area_m2 passed in.
    # NB: controls["lot_size"] is the LEP minimum-lot-size standard (cl 4.1),
    # NOT this lot's area — never substitute it for the measured area.
    lot_dims = calculate_lot_dimensions(lot_geometry) if lot_geometry else None
    if lot_dims:
        if lot_area_m2:
            lot_dims.area_m2 = lot_area_m2
    elif lot_area_m2:
        # No polygon — area-only fallback
        lot_dims = LotDimensions(area_m2=lot_area_m2)

    return PlanningControls(
        zone=DataField(value=_sanitise(controls.get("zone")), confidence=auth, source="planning_portal", as_at=today),
        zone_full=DataField(value=_sanitise(controls.get("zone_full")), confidence=auth, source="planning_portal", as_at=today),
        zone_epi=DataField(value=_sanitise(controls.get("zone_epi")), confidence=auth, source="planning_portal", as_at=today),
        legislation_url=DataField(value=controls.get("legislation_url"), confidence=auth, source="planning_portal", as_at=today),
        height=DataField(value=controls.get("height"), confidence=auth, source="planning_portal", as_at=today),
        fsr=DataField(value=controls.get("fsr"), confidence=auth, source="planning_portal", as_at=today),
        lot_size=DataField(value=controls.get("lot_size"), confidence=auth, source="planning_portal", as_at=today),
        acid_sulfate_class=DataField(value=controls.get("ass_class"), confidence=auth, source="planning_portal", as_at=today),
        heritage_items=DataField(value=heritage_items_raw, confidence=auth, source="planning_portal", as_at=today),
        heritage_hca=DataField(value=heritage_hca_raw, confidence=auth, source="planning_portal", as_at=today),
        sepp_overlays=DataField(value=sepp_overlays_raw, confidence=auth, source="planning_portal", as_at=today),
        housing_sepp=DataField(value=housing_sepp, confidence=auth, source="planning_portal", as_at=today),
        tod_area=DataField(value=tod_area, confidence=auth, source="planning_portal", as_at=today),
        lot_dimensions=DataField(
            # lot_dims comes from geometry/cadastre, not the portal controls — a
            # controls failure must not downgrade it.
            value=lot_dims,
            confidence=ConfidenceLevel.AUTHORITATIVE if lot_dims else ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal",
            as_at=today,
        ),
        permitted_uses=_use_list_field("permitted"),
        prohibited_uses=_use_list_field("prohibited"),
    )


def _build_dcp_controls(
    dcp_data: Optional[dict],
    lga_slug: Optional[str],
) -> DCPControls:
    """Map fetch_dcp_setbacks output to DCPControls schema."""
    today = date.today().isoformat()

    if dcp_data is None:
        # No slug means the council is not in the DCP-onboarded set (the common
        # case — e.g. Wingecarribee), NOT that the address failed to resolve.
        # The wording matters: the frontend routes "not onboarded" to an honest
        # "Not assessed" card, while "could not ..." used to render as
        # "Address not matched — check the address", blaming the user's input
        # for our coverage gap.
        reason = (
            f"DCP controls not yet extracted for '{lga_slug}'"
            if lga_slug
            else "This council's DCP is not onboarded in our dataset yet"
        )
        return DCPControls(
            controls=DataField(value=[], confidence=ConfidenceLevel.NOT_AVAILABLE, source="plotdetect_dcp", reason=reason, as_at=today),
            dcp_name=DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE, source="plotdetect_dcp", reason=reason, as_at=today),
            dcp_url=DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE, source="plotdetect_dcp", reason=reason, as_at=today),
            section_ref=DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE, source="plotdetect_dcp", reason=reason, as_at=today),
        )

    extracted = ConfidenceLevel.EXTRACTED
    all_setbacks = (dcp_data.get("setbacks") or []) + (dcp_data.get("sd_setbacks") or [])

    from services.constraint_arithmetic import _parse_numeric

    controls_list = []
    for s in all_setbacks:
        # value_min is Optional[float]. The 'requirement' fallback can be free
        # text (e.g. "No maximum site coverage..."), which must NOT be forced into
        # the numeric field (it raises a Pydantic ValidationError → 500). Parse to
        # a number when possible; otherwise keep the descriptive text as condition.
        raw_min = s.get("value_min")
        if raw_min is None:
            raw_min = s.get("requirement")
        val_min = _parse_numeric(raw_min)
        condition = s.get("notes") or s.get("condition")
        if val_min is None and isinstance(raw_min, str) and raw_min.strip():
            condition = condition or raw_min.strip()
        controls_list.append(DCPControl(
            # semantic_type is the real control (front_setback, ...); control_type
            # from fetch_dcp_setbacks is only the 'prescribed'/'site_derived' kind.
            control_type=s.get("semantic_type") or s.get("control_type") or s.get("type", ""),
            dev_type=s.get("dev_type", "dwelling_house"),
            value_min=val_min,
            value_max=_parse_numeric(s.get("value_max")),
            unit=s.get("unit", "m"),
            condition=condition,
            source_ref=s.get("clause") or dcp_data.get("clause_ref"),
        ))

    # Data currency, not query date: as_at previously stamped date.today() on
    # every DCP field, presenting "we ran the query today" as "the data is
    # current today". fetch_dcp_setbacks now supplies the plan-level date with
    # a basis (portal record / plan's own statement / registry observation) —
    # campaign item 3. No defensible date → as_at=None and the provenance UI
    # shows no date, which is the honest state.
    plan_as_at = (dcp_data.get("as_at") or {}).get("date")
    as_at_status = dcp_data.get("as_at_status")
    return DCPControls(
        controls=DataField(value=controls_list, confidence=extracted, source="plotdetect_dcp", as_at=plan_as_at),
        dcp_name=DataField(value=dcp_data.get("dcp_name"), confidence=extracted, source="plotdetect_dcp", as_at=plan_as_at),
        dcp_url=DataField(value=dcp_data.get("dcp_url"), confidence=extracted, source="plotdetect_dcp", as_at=plan_as_at),
        section_ref=DataField(value=dcp_data.get("section"), confidence=extracted, source="plotdetect_dcp", as_at=plan_as_at),
        as_at_status=as_at_status,
        # Carry the disclosure only for a FAILED lookup — an undated brief
        # must stay distinguishable from one whose provenance query broke.
        as_at_note=(dcp_data.get("as_at_line")
                    if as_at_status == "unavailable" else None),
    )


def _select_lot_size_band(
    vals: dict[str, float],
    lot_area_m2: Optional[float],
    prefix: str,
) -> Optional[float]:
    """Select the correct lot-size-banded value for a property.

    Looks for keys like '{prefix}_lot_under_900', '{prefix}_lot_900_to_1500',
    '{prefix}_lot_over_1500' and returns the value matching lot_area_m2.
    Returns None if no banded keys exist or lot area is unknown.
    """
    banded = {k: v for k, v in vals.items() if k.startswith(prefix + "_lot_")}
    if not banded:
        return None
    if lot_area_m2 is None:
        return None
    for key, value in banded.items():
        suffix = key[len(prefix) + 1:]  # e.g. "lot_under_900"
        if "under" in suffix:
            threshold = float(suffix.split("_")[-1])  # qa-ignore: split on "_" always yields >=1 token; suffix is a band key
            if lot_area_m2 < threshold:
                return value
        elif "over" in suffix:
            threshold = float(suffix.split("_")[-1])  # qa-ignore: split on "_" always yields >=1 token; suffix is a band key
            if lot_area_m2 >= threshold:
                return value
        elif "to" in suffix:
            parts = suffix.replace("lot_", "").split("_to_")
            if len(parts) == 2:
                low, high = float(parts[0]), float(parts[1])
                if low <= lot_area_m2 < high:
                    return value
    return None


def _build_sepp_housing(
    standards_raw: list[dict],
    zone_code: Optional[str],
    lot_area_m2: Optional[float],
) -> list[SEPPStandard]:
    """Build SEPP Housing standards list from DB rows."""
    if not standards_raw:
        return []

    # Group by development_type — values AND the citation each standard row
    # carries (source_clause/source_document), so an override can cite it.
    by_dev_type: dict[str, dict[str, Any]] = {}
    citations: dict[str, dict[str, tuple]] = {}
    for s in standards_raw:
        dt = s["development_type"]
        st = s["standard_type"]
        if dt not in by_dev_type:
            by_dev_type[dt] = {}
            citations[dt] = {}
        by_dev_type[dt][st] = s["numeric_value"]
        if s.get("source_clause"):
            citations[dt][st] = (s.get("source_clause"), s.get("source_document"))

    results = []
    for dt, vals in by_dev_type.items():
        min_lot = vals.get("min_lot_size")
        eligible = True
        reason = None
        if min_lot and lot_area_m2 and lot_area_m2 < min_lot:
            eligible = False
            reason = f"Lot area {lot_area_m2:.0f}m² below minimum {min_lot:.0f}m²"

        # max_floor_area (migration 045) maps to max_gfa_m2 (absolute m²)
        max_gfa = vals.get("max_floor_area")
        # max_fsr (DB standard_type for LMR types) is an FSR ratio, not absolute area
        max_fsr = vals.get("max_fsr")

        # Lot-size-banded standards — resolve to the matching band
        site_coverage = _select_lot_size_band(vals, lot_area_m2, "max_site_coverage")
        total_floor_area = _select_lot_size_band(vals, lot_area_m2, "max_total_floor_area")

        # Collect non-standard fields into additional_standards
        known_keys = {
            "min_lot_size", "max_fsr", "max_floor_area", "max_height",
            "setback_front", "setback_rear", "setback_side",
            "min_lot_width", "parking_per_dwelling", "min_private_open_space",
        }
        banded_prefixes = ("max_site_coverage_lot_", "max_total_floor_area_lot_")
        additional = {
            k: v for k, v in vals.items()
            if k not in known_keys and not any(k.startswith(p) for p in banded_prefixes)
        }

        height_cit = citations.get(dt, {}).get("max_height")
        fsr_cit = citations.get(dt, {}).get("max_fsr")
        results.append(SEPPStandard(
            dev_type=dt,
            eligible=eligible,
            height_source_clause=height_cit[0] if height_cit else None,
            fsr_source_clause=fsr_cit[0] if fsr_cit else None,
            source_document=(height_cit or fsr_cit)[1] if (height_cit or fsr_cit) else None,
            min_lot_area_m2=min_lot,
            max_gfa_m2=max_gfa,
            max_fsr=max_fsr,
            max_height_m=vals.get("max_height"),
            setback_front_m=vals.get("setback_front"),
            setback_rear_m=vals.get("setback_rear"),
            setback_side_m=vals.get("setback_side"),
            reason_ineligible=reason,
            min_lot_width_m=vals.get("min_lot_width"),
            parking_spaces=vals.get("parking_per_dwelling"),
            min_private_open_space_m2=vals.get("min_private_open_space"),
            max_site_coverage_pct=site_coverage,
            max_total_floor_area_m2=total_floor_area,
            additional_standards=additional if additional else None,
        ))
    return results


def _is_heritage_land(controls: dict, heritage_postgis: Optional[dict]) -> bool:
    """Whether the parcel is a heritage item or in a Heritage Conservation Area.

    The NSW Low/Mid-Rise Housing reforms (the SEPP height/FSR bonuses) do NOT
    apply to heritage items or HCAs, so a SEPP override must be suppressed there
    (GATE-2). Checks both the Portal heritage_items and the PostGIS heritage layer.
    """
    if controls.get("heritage_items"):
        return True
    if heritage_postgis and heritage_postgis.get("has_heritage"):
        return True
    return False


def _detect_sepp_lep_overrides(
    sepp_standards: list[SEPPStandard],
    lep_height_m: Optional[float],
    lep_fsr: Optional[float],
    is_heritage: bool = False,
) -> list[SeppLepOverride]:
    """Detect cases where an ELIGIBLE SEPP standard exceeds (overrides) LEP control.

    SEPP prevails only when its value is MORE GENEROUS (strictly greater) than LEP.
    This is the server-side equivalent of the frontend override detection in PR #437.

    GATE-2: an override is created ONLY when the standard is eligible, and NEVER on
    heritage land — the Low/Mid-Rise Housing reforms exclude heritage items and
    Heritage Conservation Areas, so on heritage land the LEP control stands.
    """
    overrides: list[SeppLepOverride] = []
    # LMR height/FSR bonuses do not apply to heritage items / HCAs.
    if is_heritage:
        return overrides
    for std in sepp_standards:
        # Only an eligible standard can override the LEP (e.g. not lot-size-ineligible).
        if not std.eligible:
            continue
        if std.max_height_m and lep_height_m and std.max_height_m > lep_height_m:
            overrides.append(SeppLepOverride(
                dev_type=std.dev_type,
                control="height",
                lep_value=lep_height_m,
                sepp_value=std.max_height_m,
                source_clause=std.height_source_clause,
            ))
        if std.max_fsr and lep_fsr and std.max_fsr > lep_fsr:
            overrides.append(SeppLepOverride(
                dev_type=std.dev_type,
                control="fsr",
                lep_value=lep_fsr,
                sepp_value=std.max_fsr,
                source_clause=std.fsr_source_clause,
            ))
    return overrides


def _build_environmental(
    controls: dict,
    overlays_data: dict,
    heritage_postgis: Optional[dict],
    mine_subsidence_raw: Optional[dict] = None,
    contaminated_land_raw: Optional[dict] = None,
    drinking_water_raw: Optional[dict] = None,
    servicing_raw: Optional[dict] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    overlays_failed: bool = False,
    controls_failed: bool = False,
    mine_failed: bool = False,
    contam_failed: bool = False,
    drinking_failed: bool = False,
) -> EnvironmentalConstraints:
    """Map overlays + heritage to EnvironmentalConstraints.

    Fail-closed: when the overlay fetch FAILED (``overlays_failed``), the purely
    overlay-derived fields (the overlay list + coverage) are emitted NOT_AVAILABLE.
    flood_epi and bushfire_designation combine overlays WITH the portal controls,
    so they are only downgraded when BOTH sources failed — otherwise a single
    surviving source still gives a real answer.

    mine/contaminated/drinking return None BOTH when the lot is genuinely outside
    the layer AND when the fetch failed — the ``*_failed`` flags (from the fetch
    DataField) are the only way to keep those apart, so a failed fetch renders
    NOT_AVAILABLE, never a confident False (the WO-2 class).
    """
    today = date.today().isoformat()
    auth = ConfidenceLevel.AUTHORITATIVE
    na = ConfidenceLevel.NOT_AVAILABLE
    overlay_auth = na if overlays_failed else auth          # purely overlay-derived fields
    both_failed = overlays_failed and controls_failed       # overlay+controls hazard fields

    # Sydney Water servicing → one-line summary (None for failed/missing lookup).
    from services.gsp_servicing import summarize_servicing as _summarize_servicing
    _servicing_summary = _summarize_servicing(servicing_raw)

    overlay_list = (overlays_data.get("overlays") or []) if overlays_data else []
    covered = (overlays_data.get("covered_layers") or []) if overlays_data else []

    def _overlay_field(layer_key: str, db_present: bool, layer_id: int) -> DataField:
        """Prefer ingested DB coverage; otherwise live point-query the Protection
        layer so an un-ingested layer still reports the REAL fact for this lot
        (present + class, or a genuine "none here") rather than leaking an
        internal "not ingested" gap. Fail-safe: a failed/absent live query falls
        back to the conservative NOT_AVAILABLE state, never an over-statement.
        """
        if layer_key in covered:
            return DataField(value=db_present, confidence=auth, source="postgis_overlays", as_at=today)
        live = None
        if lat is not None and lng is not None:
            try:
                from services.portal_constraints import fetch_protection_overlay
                live = fetch_protection_overlay(lat, lng, layer_id)
            except Exception:
                live = None
        if live is not None:
            # The field is a boolean (present at this lot / not). True = the layer
            # applies here, False = a genuine "none at this property" (good news),
            # both real facts rather than an internal "not ingested" gap.
            return DataField(
                value=bool(live.get("present")),
                confidence=auth, source="live_protection_overlay", as_at=today,
            )
        return DataField(
            value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="postgis_overlays", as_at=today,
            reason="Layer not ingested for this LGA",
        )

    def _parse_anef_number(raw) -> Optional[float]:
        """Leading numeric part of an ANEF value ('25', 25, '20-25') — None when
        no clean number leads the value (never a guess)."""
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        m = re.match(r"\s*(\d+(?:\.\d+)?)", str(raw))
        return float(m.group(1)) if m else None

    def _anef_fields() -> tuple[DataField, DataField]:
        # prior-art-checked: reuses the existing portal_constraints.fetch_anef
        # (live LEP/SEPP-mapped contours). The curated anef_zones table (Sydney
        # KSA) is QUARANTINED from this field: its contours are 10-13-vertex
        # digitisations whose ANEF-20 polygon covers ~789 km² — far beyond the
        # published ANEF 2039 contour — so it stamped false values on fringe
        # lots (issue #686; same quarantine as the conveyancing PDF, #681).
        # Only trust the ingested overlay when it actually carries a value —
        # a null overlay must fall through to the live query, not
        # short-circuit to a blank.
        # Returns (display string field, numeric level field) from ONE lookup.
        def _level(num: Optional[float], src: str) -> DataField:
            if num is None:
                # Checked; no numeric contour applies (or the value isn't numeric).
                return DataField(value=None, confidence=auth, source=src, as_at=today)
            return DataField(value=num, confidence=auth, source=src, as_at=today)

        if "anef" in covered and anef_value is not None:
            return (
                DataField(value=anef_value, confidence=auth, source="postgis_overlays", as_at=today),
                _level(_parse_anef_number(anef_value), "postgis_overlays"),
            )
        if lat is None or lng is None:
            na_field = DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                                 source="planning_portal_protection", as_at=today,
                                 reason="Layer not ingested for this LGA")
            return na_field, na_field.model_copy()
        regional, regional_failed = None, False
        try:
            from services.portal_constraints import fetch_anef
            regional = fetch_anef(lat, lng)
        except Exception:
            regional_failed = True
        if regional:
            code = regional.get("anef_code") or regional.get("anef_level")
            return (
                DataField(value=f"ANEF contour {code}".strip(),
                          confidence=auth, source="planning_portal_protection", as_at=today),
                _level(_parse_anef_number(code), "planning_portal_protection"),
            )
        if regional_failed:
            # The lookup FAILED — "no contour" cannot be claimed off a failed check.
            na_field = DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                                 source="planning_portal_protection", as_at=today,
                                 reason="ANEF contour lookup did not complete")
            return na_field, na_field.model_copy()
        # The mapped government layer was genuinely checked — no contour here.
        return (
            DataField(value="No ANEF contour in the mapped planning layers at this property",
                      confidence=auth, source="planning_portal_protection", as_at=today),
            _level(None, "planning_portal_protection"),
        )

    flood_epi = any(
        o.get("layer_type") in ("flood", "flood_planning") for o in overlay_list
    ) or controls.get("flood_epi", False)

    bushfire_designation = None
    for o in overlay_list:
        if o.get("layer_type") == "bushfire":
            bushfire_designation = o.get("value")
            break
    # Portal SEPP overlay fallback
    for sepp in (controls.get("sepp_overlays") or []):
        if "bushfire" in (sepp.get("name") or "").lower():
            bushfire_designation = bushfire_designation or "Bushfire Prone Land"

    # #745 D7-4: principal planning-control layers (lot size, height, FSR,
    # zone) are Planning Controls, not environmental constraints — filter them
    # from the Environmental card's overlay list.
    _PLANNING_CONTROL_LAYERS = {"lot_size", "height", "fsr", "zone"}
    env_overlays = [
        EnvironmentalOverlay(
            layer_type=o.get("layer_type", ""),
            value=o.get("value"),
            instrument=o.get("instrument_key"),
            lga=o.get("lga"),
        )
        for o in overlay_list
        if o.get("layer_type") not in _PLANNING_CONTROL_LAYERS
    ]

    # Extract typed constraint fields from overlay list
    overlay_types = {o.get("layer_type") for o in overlay_list}
    has_biodiversity = "biodiversity" in overlay_types
    has_riparian = "riparian" in overlay_types
    has_wetlands = "wetlands" in overlay_types
    anef_value = next(
        (o.get("value") for o in overlay_list if o.get("layer_type") == "anef"),
        None,
    )
    coastal_layers = {
        o.get("layer_type"): o.get("value")
        for o in overlay_list
        if o.get("layer_type", "").startswith("coastal_") or o.get("layer_type") == "littoral_rainforest"
    }

    # Measured nearest-feature distances (metres) from get_unique_overlays —
    # only for covered layers with no intersection at this lot. Keys are layer
    # types (flood, biodiversity, riparian, wetlands, landslide). Values must be
    # numeric; anything else is dropped rather than rendered as a distance.
    proximity_raw = (overlays_data.get("proximity_m") or {}) if overlays_data else {}
    proximity = {
        k: round(float(v))
        for k, v in proximity_raw.items()
        if isinstance(v, (int, float))
    }

    anef_display_field, anef_level_field = _anef_fields()

    return EnvironmentalConstraints(
        flood_epi=DataField(
            value=None if both_failed else flood_epi,
            confidence=na if both_failed else auth,
            source="postgis_overlays", as_at=today,
            reason="Flood overlay and portal controls both unavailable" if both_failed else None,
        ),
        overlays=DataField(value=env_overlays, confidence=overlay_auth, source="postgis_overlays", as_at=today),
        overlay_coverage=DataField(value=covered, confidence=overlay_auth, source="postgis_overlays", as_at=today),
        bushfire_designation=DataField(
            value=None if both_failed else bushfire_designation,
            confidence=na if both_failed else auth,
            source="postgis_overlays", as_at=today,
        ),
        heritage_postgis=DataField(
            value=heritage_postgis if heritage_postgis and heritage_postgis.get("has_heritage") else None,
            confidence=auth if heritage_postgis else ConfidenceLevel.NOT_AVAILABLE,
            source="postgis_heritage",
            as_at=today,
        ),
        # Typed fields from spatial_overlays — DB coverage first, else a live
        # per-lot Protection-layer query (riparian=7, wetlands=11, biodiversity=10).
        terrestrial_biodiversity=_overlay_field("biodiversity", has_biodiversity, 10),
        riparian_land=_overlay_field("riparian", has_riparian, 7),
        wetlands=_overlay_field("wetlands", has_wetlands, 11),
        anef=anef_display_field,
        anef_level=anef_level_field,
        nearest_features=DataField(
            # Measured metres to the nearest mapped feature for covered layers
            # that do NOT intersect this lot. Legit-empty = value None with NO
            # reason (per the DataField contract, a reason on a null value means
            # the fetch FAILED and the S1 validator coerces to NOT_AVAILABLE);
            # the overlay failure case carries its reason via overlay_auth.
            value=proximity or None,
            confidence=overlay_auth,
            source="postgis_overlays",
            as_at=today,
            reason="Overlay query did not complete" if overlays_failed else None,
        ),
        coastal_hazards=DataField(
            # #745 D5: "queried, zero coastal layers" is a checked-CLEAR result,
            # not a data gap. Legit-empty = value None + NO reason, keeping the
            # overlay-auth badge (same contract as nearest_features above).
            # NOT_AVAILABLE + reason is reserved for an actual fetch failure.
            value=coastal_layers if coastal_layers else None,
            confidence=overlay_auth,
            source="sepp_resilience_hazards",
            as_at=today,
            reason="Overlay query did not complete" if overlays_failed else None,
        ),
        mine_subsidence=DataField(
            value=None if mine_failed else (mine_subsidence_raw.get("in_district", False) if mine_subsidence_raw else False),
            confidence=na if mine_failed else auth,
            source="nsw_spatial_services",
            as_at=today,
            reason="Mine subsidence lookup did not complete" if mine_failed else None,
        ),
        mine_subsidence_district=DataField(
            value=(mine_subsidence_raw or {}).get("district_name"),
            confidence=na if mine_failed else auth,
            source="nsw_spatial_services",
            as_at=today,
            reason="Mine subsidence lookup did not complete" if mine_failed else None,
        ),
        contaminated_land=DataField(
            value=None if contam_failed else (contaminated_land_raw.get("has_notified_sites", False) if contaminated_land_raw else False),
            confidence=na if contam_failed else auth,
            source="epa_contaminated_sites",
            as_at=today,
            reason="Contaminated land register lookup did not complete" if contam_failed else None,
        ),
        contaminated_detail=DataField(
            value=(
                {
                    "site_count": contaminated_land_raw.get("site_count"),
                    "nearest_site": contaminated_land_raw.get("nearest_site"),
                }
                if contaminated_land_raw and not contam_failed
                else None
            ),
            confidence=na if contam_failed else auth,
            source="epa_contaminated_sites",
            as_at=today,
            # Genuinely no sites = value None with NO reason (legit-empty per the
            # DataField contract — a reason would mark it failed and coerce to
            # NOT_AVAILABLE, surfacing a false gap). The boolean row answers.
            reason="Contaminated land register lookup did not complete" if contam_failed else None,
        ),
        drinking_water_catchment=DataField(
            value=None if drinking_failed else (drinking_water_raw.get("in_catchment", False) if drinking_water_raw else False),
            confidence=na if drinking_failed else auth,
            source="sepp_resilience_hazards",
            as_at=today,
            reason="Drinking water catchment lookup did not complete" if drinking_failed else None,
        ),
        # Sydney Water servicing — one-line summary via the shared summarizer.
        # 'empty' (not in a growth precinct) is a real answer (authoritative);
        # a failed/missing lookup summarizes to None -> NOT_AVAILABLE.
        servicing=DataField(
            value=_servicing_summary,
            confidence=na if _servicing_summary is None else auth,
            source="sydney_water_gsp",
            as_at=today,
            reason=("Sydney Water servicing lookup did not complete"
                    if _servicing_summary is None else None),
        ),
    )


def _build_neighbourhood(
    das_df: "DataField",
    shadow_result: Optional[dict],
    da_outcomes_df: Optional["DataField"] = None,
    refusal_df: Optional["DataField"] = None,
) -> Neighbourhood:
    """Map DA list + shadow to Neighbourhood schema.

    A failed/timed-out DA lookup (das_df.confidence == NOT_AVAILABLE) must NOT be
    served as an authoritative "0 nearby DAs" — that is a silent false negative.
    A genuine empty result (the query ran and found none) stays AUTHORITATIVE 0.
    """
    today = date.today().isoformat()
    da_failed = das_df.confidence == ConfidenceLevel.NOT_AVAILABLE
    das = das_df.value or []  # failsoft-ok: da_failed (above) re-stamps NOT_AVAILABLE so a failed lookup is never served as an authoritative 0 (the #582 guard)

    nearby = [
        NearbyDA(
            number=d.get("number", ""),
            address=d.get("address"),
            distance_m=d.get("distance_m"),
            status=d.get("status"),
            dev_type=d.get("description") or d.get("development_type"),
            lodgement_date=d.get("lodged") or (str(d.get("lodgement_date", ""))[:10] if d.get("lodgement_date") else None),  # qa-ignore: inner str() only runs when lodgement_date is truthy
            cost=d.get("cost_of_development"),
        )
        for d in das
    ]

    shadow_schema = _build_shadow_result(shadow_result)

    if da_failed:
        da_reason = das_df.reason or "Nearby-DA lookup did not complete"
        nearby_field = DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE, source="eplanning_da_api", as_at=today, reason=da_reason)
        count_field = DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE, source="eplanning_da_api", as_at=today, reason=da_reason)
    else:
        nearby_field = DataField(value=nearby, confidence=ConfidenceLevel.AUTHORITATIVE, source="eplanning_da_api", as_at=today)
        count_field = DataField(value=len(nearby), confidence=ConfidenceLevel.AUTHORITATIVE, source="eplanning_da_api", as_at=today)

    def _outcome_field(df: Optional["DataField"], label: str) -> DataField:
        """Three states: populated payload / queried-empty (None value from a
        successful run) / failed or not queried (NOT_AVAILABLE + reason)."""
        if df is None:
            return DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                             source="da_tracking_mapserver", as_at=today,
                             reason=f"{label} not queried for this brief")
        if df.confidence == ConfidenceLevel.NOT_AVAILABLE:
            return DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                             source="da_tracking_mapserver", as_at=today,
                             reason=df.reason or f"{label} lookup did not complete")
        return DataField(value=df.value, confidence=ConfidenceLevel.AUTHORITATIVE,
                         source="da_tracking_mapserver", as_at=today)

    return Neighbourhood(
        nearby_das=nearby_field,
        da_count=count_field,
        da_outcomes=_outcome_field(da_outcomes_df, "Determination outcomes"),
        da_refusal_stats=_outcome_field(refusal_df, "Determination counts"),
        shadow=DataField(
            value=shadow_schema,
            confidence=ConfidenceLevel.DERIVED if shadow_schema else ConfidenceLevel.NOT_AVAILABLE,
            source="shadow_detector",
            as_at=today,
            reason="Shadow pipeline unavailable" if not shadow_schema else None,
        ),
    )


class _LotAreaCheck(NamedTuple):
    """Outcome of cross-checking the VG valuation lot area vs the cadastral polygon."""

    area_m2: Optional[float]
    source: str  # "valuation" | "geometry" | "none"
    diverged: bool
    note: Optional[str]


def _reconcile_lot_area(
    vg_area: Optional[float],
    geom_area: Optional[float],
    tol_pct: float = 0.25,
) -> _LotAreaCheck:
    """Cross-check the VG valuation lot area against the cadastral lot polygon.

    The VG valuation parcel can aggregate several lots, or the address can
    resolve to the wrong parcel — either feeds a confident-but-wrong lot area
    into the whole brief (the 4,452 m2 suburban-lot failure). The Planning
    Portal lot polygon is the authoritative *single-lot* geometry, so when the
    two disagree by more than ``tol_pct`` we distrust the valuation and fall
    back to the geometry-derived area, flagging the discrepancy.

    Returns the area to use, which source it came from, whether the two sources
    materially diverged, and a note when they did. Pure function — unit-tested.
    """
    has_vg = vg_area is not None and vg_area > 0
    has_geom = geom_area is not None and geom_area > 0

    if has_vg and has_geom:
        rel_diff = abs(vg_area - geom_area) / geom_area
        if rel_diff <= tol_pct:
            return _LotAreaCheck(vg_area, "valuation", False, None)
        note = (
            f"Lot area mismatch: valuation parcel {vg_area:.0f} m2 vs cadastral "
            f"lot geometry {geom_area:.0f} m2 ({rel_diff * 100:.0f}% apart). The "
            f"valuation may cover an aggregated parcel; using the lot geometry and "
            f"flagging the area for manual check."
        )
        return _LotAreaCheck(geom_area, "geometry", True, note)

    if has_vg:
        return _LotAreaCheck(vg_area, "valuation", False, None)
    if has_geom:
        return _LotAreaCheck(geom_area, "geometry", False, None)
    return _LotAreaCheck(None, "none", False, None)


def _apply_lot_area_reconciliation(
    valuation: dict, lot_geometry_raw: Optional[dict],
) -> Optional[str]:
    """Cross-check valuation lot area vs portal geometry; update ``valuation`` in place.

    Recomputes the lot polygon area from the Planning Portal geometry and
    reconciles it with the valuation area. Writes the trusted value back to
    ``valuation['lot_area_m2']`` and, on divergence, records
    ``valuation['lot_area_caveat']`` (read by :func:`_build_economics` to
    downgrade the field to DERIVED). Returns a warning string for the brief's
    ``data_currency_warnings`` when the sources diverged, else ``None``.
    """
    geom_area: Optional[float] = None
    if lot_geometry_raw:
        dims = calculate_lot_dimensions(lot_geometry_raw)
        if dims is not None:
            geom_area = dims.area_m2

    check = _reconcile_lot_area(valuation.get("lot_area_m2"), geom_area)
    valuation["lot_area_m2"] = check.area_m2
    if check.diverged and check.note:
        valuation["lot_area_caveat"] = check.note
        return check.note
    return None


def _build_economics(valuation: dict) -> Economics:
    """Map VG valuation to Economics schema."""
    today = date.today().isoformat()

    history = [
        ValuationHistory(year=h.get("year") or "", value=int(h.get("value")) if h.get("value") else None)
        for h in (valuation.get("val_history") or [])
    ]

    lv = valuation.get("land_value")

    # Lot area: AUTHORITATIVE from the valuation, unless the cross-check against
    # the cadastral polygon flagged a mismatch — then it's geometry-DERIVED and
    # carries the caveat (see _apply_lot_area_reconciliation).
    area_val = valuation.get("lot_area_m2")
    area_caveat = valuation.get("lot_area_caveat")
    if area_val is None:
        area_conf = ConfidenceLevel.NOT_AVAILABLE
    elif area_caveat:
        area_conf = ConfidenceLevel.DERIVED
    else:
        area_conf = ConfidenceLevel.AUTHORITATIVE

    return Economics(
        land_value=DataField(
            value=int(lv) if lv else None,
            confidence=ConfidenceLevel.AUTHORITATIVE if lv else ConfidenceLevel.NOT_AVAILABLE,
            source="nsw_valuation_service",
            as_at=valuation.get("val_base_date") or today,
        ),
        val_base_date=DataField(
            value=valuation.get("val_base_date"),
            confidence=ConfidenceLevel.AUTHORITATIVE if valuation.get("val_base_date") else ConfidenceLevel.NOT_AVAILABLE,
            source="nsw_valuation_service",
            as_at=today,
        ),
        val_history=DataField(value=history, confidence=ConfidenceLevel.AUTHORITATIVE, source="nsw_valuation_service", as_at=today),
        lot_area_m2=DataField(
            value=area_val,
            confidence=area_conf,
            source="planning_portal_lot" if area_caveat else "nsw_valuation_service",
            as_at=today,
            reason=area_caveat,
        ),
    )


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def _sse_event(event: str, data: dict) -> str:
    """Format a single SSE event with JSON data."""
    payload = json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _resolve_address(req: IntelligenceBriefRequest) -> tuple:
    """Resolve address to (prop_id, lat, lng, lot_wkt). Raises HTTPException on failure."""
    if req.lat and req.lng and req.prop_id:
        return int(req.prop_id), req.lat, req.lng, None

    # Coordinate-first: a trusted pin (Google Places autocomplete) resolves the
    # parcel by point-in-cadastre + the SAME parcel-identity cross-check, which is
    # authoritative and avoids the fuzzy text geocode that false-closes valid
    # addresses. Any miss/ambiguity/error -> fall through to the text resolver.
    if req.lat and req.lng:
        try:
            hit = resolve_propid_by_point(req.lat, req.lng, req.address)
        except Exception as e:
            logger.warning("point->propid resolution failed: %s", e)
            hit = None
        if hit and hit[0] and hit[1] and hit[2] and not _validate_coordinates(hit[1], hit[2]):
            return hit

    try:
        resolved_prop_id, lat, lng, lot_wkt = resolve_address(req.address)
    except Exception as e:
        logger.error("Address resolution failed: %s", e)
        raise HTTPException(status_code=422, detail=f"Could not resolve address: {req.address}")

    if not lat or not lng:
        raise HTTPException(status_code=422, detail=f"Could not determine coordinates for: {req.address}")

    coord_warning = _validate_coordinates(lat, lng)
    if coord_warning:
        raise HTTPException(status_code=422, detail=coord_warning)

    return resolved_prop_id, lat, lng, lot_wkt


# ---------------------------------------------------------------------------
# Router + endpoint — Stage 2 orchestrator
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/pipeline", tags=["intelligence"])


def _timed_result(future, timeout: float, label: str, timings: list) -> "DataField":
    """Collect a future's result with timing and graceful timeout handling."""
    t0 = time.monotonic()
    try:
        result = future.result(timeout=timeout)
    except Exception as e:
        elapsed = time.monotonic() - t0
        timings.append((label, elapsed, "TIMEOUT" if "TimeoutError" in type(e).__name__ else "ERROR"))
        logger.warning("intelligence_brief: %s failed after %.1fs: %s", label, elapsed, e)
        return DataField(
            value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
            source=label, reason=f"Timeout after {elapsed:.1f}s",
        )
    elapsed = time.monotonic() - t0
    timings.append((label, elapsed, "OK"))
    return result


def _unwrap_or_default(df: "DataField", default):
    """Unwrap a DataField, preserving the FAILURE signal that ``df.value or X`` throws away.

    Returns ``(value, failed)`` where ``failed`` is True only when the upstream
    fetch did not succeed (``confidence == NOT_AVAILABLE``). Callers MUST use
    ``failed`` to decide the emitted section's confidence — a failed fetch must
    surface as NOT_AVAILABLE, never as a confident AUTHORITATIVE negative
    (the strata/overlay false-negative class). This is the sanctioned
    replacement for the ``df.value or <default>`` anti-pattern that the
    failsoft lint blocks.
    """
    failed = df.confidence == ConfidenceLevel.NOT_AVAILABLE
    value = df.value if df.value is not None else default
    return value, failed


# ---------------------------------------------------------------------------
# SSE streaming endpoint — progressive rendering
# ---------------------------------------------------------------------------


def _generate_brief_sse(
    req: IntelligenceBriefRequest,
    resolved_prop_id: Optional[int],
    lat: float,
    lng: float,
    lot_wkt: Optional[str],
) -> Generator[str, None, None]:
    """Yield SSE events as intelligence brief sections complete.

    The single brief assembly path: yields each section as soon as its source
    dependencies are satisfied.

    Events:
      event: metadata   — address, coordinates, run config
      event: section     — one assembled brief section (economics, strata, etc.)
      event: complete    — compound constraints, gaps, confidence summary
      event: error       — unrecoverable error mid-stream
    """
    start_time = time.monotonic()
    today = date.today().isoformat()
    timings: list[tuple] = []
    sections_yielded = 0

    # Count expected sections for progress tracking
    base_sections = 5  # economics, strata, environmental, planning_controls, brief_type
    dependent_sections = 0  # dcp, sepp, neighbourhood — only for development briefs (unknown until strata)
    satellite_sections = 7 if req.include_satellite else 0  # incl. the solar marker slot
    total_sections = base_sections + satellite_sections + 5  # +5 for dependent (max estimate)

    import uuid
    report_id = str(uuid.uuid4())

    yield _sse_event("metadata", {
        "address": req.address, "lat": lat, "lng": lng,
        "prop_id": resolved_prop_id, "run_date": today,
        "include_satellite": req.include_satellite,
        "include_premium": req.include_premium,
    })

    # ── Submit all independent sources ───────────────────────────────────
    f_controls = None
    f_valuation = None
    f_lot_geometry = None

    with ThreadPoolExecutor(max_workers=CONFIG.max_parallel_sources) as pool:

        if resolved_prop_id:
            f_controls = pool.submit(
                _safe_call, lambda: _fetch_controls(resolved_prop_id),
                "planning_portal", ConfidenceLevel.AUTHORITATIVE,
            )
            f_valuation = pool.submit(
                _safe_call, lambda: _fetch_valuation(resolved_prop_id),
                "nsw_valuation_service", ConfidenceLevel.AUTHORITATIVE,
            )
            f_lot_geometry = pool.submit(
                _safe_call, lambda: fetch_lot_geometry(str(resolved_prop_id)),
                "planning_portal_lot", ConfidenceLevel.AUTHORITATIVE,
            )
            f_contributions = pool.submit(
                _safe_call, lambda: _fetch_contributions(resolved_prop_id),
                "planning_portal_cp", ConfidenceLevel.AUTHORITATIVE,
            )

        f_overlays = pool.submit(
            _safe_call, lambda: _fetch_overlays(lat, lng, lot_wkt),
            "postgis_overlays", ConfidenceLevel.AUTHORITATIVE,
        )
        f_strata = pool.submit(
            _safe_call, lambda: _fetch_strata(req.address, lat, lng),
            "cadastre_strata", ConfidenceLevel.AUTHORITATIVE,
        )
        f_heritage = pool.submit(
            _safe_call, lambda: _fetch_heritage_postgis(lat, lng, lot_wkt),
            "postgis_heritage", ConfidenceLevel.AUTHORITATIVE,
        )
        f_mine_sub = pool.submit(
            _safe_call, lambda: _fetch_mine_subsidence(lat, lng),
            "nsw_spatial_services", ConfidenceLevel.AUTHORITATIVE,
        )
        f_contam = pool.submit(
            _safe_call, lambda: _fetch_contaminated_land(lat, lng),
            "epa_contaminated_sites", ConfidenceLevel.AUTHORITATIVE,
        )
        f_drinking = pool.submit(
            _safe_call, lambda: _fetch_drinking_water_catchment(lat, lng),
            "sepp_resilience_hazards", ConfidenceLevel.AUTHORITATIVE,
        )
        from services.gsp_servicing import fetch_gsp_servicing as _fetch_gsp_servicing
        f_servicing = pool.submit(
            _safe_call, lambda: _fetch_gsp_servicing(lat, lng),
            "sydney_water_gsp", ConfidenceLevel.AUTHORITATIVE,
        )

        # Satellite — fire immediately if requested
        f_bushfire = f_flood_sat = f_climate = f_granny = None
        f_uhi = f_arr = f_firms = f_terrain = None

        if req.include_satellite:
            f_bushfire = pool.submit(
                _safe_call,
                lambda: _fetch_bushfire(req.address, lat, lng, str(resolved_prop_id) if resolved_prop_id else None, _derive_service_report_id(report_id, "bushfire")),
                "bushfire_prescreen", ConfidenceLevel.AUTHORITATIVE,
            )
            f_flood_sat = pool.submit(
                _safe_call,
                lambda: _fetch_flood(req.address, lat, lng, str(resolved_prop_id) if resolved_prop_id else None, _derive_service_report_id(report_id, "flood")),
                "flood_truth", ConfidenceLevel.ESTIMATED,
            )
            f_climate = pool.submit(
                _safe_call,
                lambda: _fetch_climate_risk(lat, lng),
                "climate_risk_score", ConfidenceLevel.ESTIMATED,
            )
            f_granny = pool.submit(
                _safe_call,
                lambda: _fetch_granny_flat_detect(req.address, lat, lng, str(resolved_prop_id or 0)),
                "granny_flat_detect", ConfidenceLevel.ESTIMATED,
            )
            f_uhi = pool.submit(
                _safe_call, lambda: _fetch_uhi(lat, lng),
                "nsw_uhgc", ConfidenceLevel.ESTIMATED,
            )
            f_arr = pool.submit(
                _safe_call, lambda: _fetch_arr_ifd(lat, lng),
                "arr_data_hub", ConfidenceLevel.ESTIMATED,
            )
            f_firms = pool.submit(
                _safe_call, lambda: _fetch_firms_hotspots(lat, lng),
                "nasa_firms", ConfidenceLevel.ESTIMATED,
            )
            f_terrain = pool.submit(
                _safe_call, lambda: _fetch_terrain(lat, lng),
                "terrain_analysis", ConfidenceLevel.ESTIMATED,
            )

        # ── Yield economics first (fast, independent) ────────────────────
        valuation_df = _timed_result(f_valuation, 15, "nsw_valuation_service", timings) if f_valuation else DataField(
            value={"lot_area_m2": None, "land_value": None, "val_base_date": None, "val_history": []},
            confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="nsw_valuation_service", reason="No prop_id resolved",
        )
        valuation = valuation_df.value or {"lot_area_m2": None, "land_value": None, "val_base_date": None, "val_history": []}  # failsoft-ok: _build_economics maps each None field to NOT_AVAILABLE (audit 2026-06-22)

        # Await lot geometry up-front: economics is emitted first here, so the
        # valuation lot area must be sanity-checked against the cadastral polygon
        # BEFORE it goes out (avoids a confident wrong area on an aggregated
        # parcel — the 4,452 m2 case). Reused below instead of re-awaiting.
        lot_geometry_df = _timed_result(f_lot_geometry, 15, "planning_portal_lot", timings) if f_lot_geometry else DataField(
            value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal_lot", reason="No prop_id resolved",
        )
        lot_geometry_raw = lot_geometry_df.value
        lot_area_warning = _apply_lot_area_reconciliation(valuation, lot_geometry_raw)
        lot_area_m2 = valuation.get("lot_area_m2")

        economics = _build_economics(valuation)
        sections_yielded += 1
        yield _sse_event("section", {
            "section": "economics", "data": economics.model_dump(),
            "progress": int(sections_yielded / total_sections * 100),
        })

        # Submit pre_da now that we have lot_area_m2
        f_pre_da = None
        if req.include_satellite and req.include_premium:
            f_pre_da = pool.submit(
                _safe_call,
                lambda: _fetch_pre_da_history(req.address, lot_area_m2),
                "pre_da_history", ConfidenceLevel.ESTIMATED,
            )

        # ── Yield strata (depends on cadastre + lot_area_m2) ─────────────
        strata_df = _timed_result(f_strata, 10, "cadastre_strata", timings)
        strata_raw, strata_failed = _unwrap_or_default(strata_df, {"is_strata": False})  # failsoft-ok: strata_failed branch below restamps NOT_AVAILABLE + AMBIGUOUS routing
        if not strata_failed:
            # S2 boundary: tripwire-validate the cadastre dict against the typed
            # contract (drift check against the always-emitted core keys only —
            # StrataHub enrichment keys are conditionally present by design).
            # A type-level contract violation is a FAILED lookup: it takes the
            # fail-closed AMBIGUOUS route below, never a silent "not strata".
            _warn_on_drift(StrataCoreOutput, strata_raw, "strata")
            try:
                StrataServiceOutput.model_validate(strata_raw or {})
            except ValidationError as e:
                logger.warning("strata output failed the S2 contract — routing fail-closed: %s", e)
                strata_raw, strata_failed = {"is_strata": False}, True
        # Fail-closed: a FAILED strata lookup must NOT be served as a confident
        # "not strata" — that would silently route a possible apartment into a full
        # DevelopmentBrief (capacity claims it can't support). Treat unknown strata
        # as AMBIGUOUS → renovation path (no dev-capacity claims) + NOT_AVAILABLE card.
        strata_type = StrataType.AMBIGUOUS if strata_failed else classify_strata(strata_raw, lot_area_m2)
        strata_info = StrataInfo(
            is_strata=strata_raw.get("is_strata", False),
            strata_type=strata_type,
            strata_plan=strata_raw.get("strata_plan"),
            plan_label=strata_raw.get("plan_label"),
            lot_number=(str(strata_raw.get("lot_number"))
                        if strata_raw.get("lot_number") is not None else None),
            section_number=(str(strata_raw.get("section_number"))
                            if strata_raw.get("section_number") is not None else None),
            source=strata_raw.get("source"),
            lot_area_m2=lot_area_m2,
            lot_total=strata_raw.get("lot_total"),
            dwelling_type=strata_raw.get("dwelling_type"),
            registration_date=strata_raw.get("registration_date"),
        )
        is_apartment = strata_type == StrataType.APARTMENT or strata_type == StrataType.AMBIGUOUS

        # Update total_sections now we know brief type
        if is_apartment:
            total_sections = base_sections + satellite_sections  # no dcp/sepp/neighbourhood
        else:
            total_sections = base_sections + 5 + satellite_sections  # +dcp, sepp, neighbourhood, constraint_arithmetic, market_context

        sections_yielded += 1
        yield _sse_event("section", {
            "section": "strata", "data": DataField(
                value=strata_info,
                confidence=ConfidenceLevel.NOT_AVAILABLE if strata_failed else ConfidenceLevel.AUTHORITATIVE,
                source="cadastre_strata", as_at=today,
                reason=(strata_df.reason or "Strata lookup did not complete") if strata_failed else None,
            ).model_dump(),
            "progress": int(sections_yielded / total_sections * 100),
            "brief_type": "renovation" if is_apartment else "development",
        })

        # ── Await portal → submit dependents ─────────────────────────────
        controls_df = _timed_result(f_controls, 15, "planning_portal", timings) if f_controls else DataField(
            value=parse_controls([]), confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal", reason="No prop_id resolved",
        )
        controls, controls_failed = _unwrap_or_default(controls_df, parse_controls([]))  # WO-3: controls_failed -> _build_planning_controls stamps NOT_AVAILABLE instead of blank@AUTHORITATIVE

        zone_epi = controls.get("zone_epi", "")
        zone_code = controls.get("zone")
        council_name = _council_from_zone_epi(zone_epi)
        dcp_former_council = detect_former_council(req.address, zone_epi)
        dcp_former_council, lga_advisory = _validate_former_council_postgis(
            dcp_former_council, lat, lng, req.address,
        )
        height_str = controls.get("height")
        height_m = None
        if height_str:
            try:
                height_m = float(str(height_str).replace("m", "").strip())
            except (ValueError, TypeError):
                pass

        # Submit dependent sources
        f_das = pool.submit(
            _safe_call,
            lambda: _fetch_nearby_das(lat, lng, council_name, CONFIG.da_radius_m, CONFIG.da_lookback_days),
            "eplanning_da_api", ConfidenceLevel.AUTHORITATIVE,
        )
        f_shadow = pool.submit(
            _safe_call,
            lambda: _fetch_shadow(req.address, resolved_prop_id or 0, lat, lng, height_m, _derive_service_report_id(report_id, "shadow")),
            "shadow_detector", ConfidenceLevel.DERIVED,
        )
        f_dcp = pool.submit(
            _safe_call,
            lambda: _fetch_dcp_controls(dcp_former_council, zone_code),
            "plotdetect_dcp", ConfidenceLevel.EXTRACTED,
        )
        f_sepp = pool.submit(
            _safe_call,
            lambda: _fetch_sepp_housing(zone_code),
            "housing_sepp_standards", ConfidenceLevel.AUTHORITATIVE,
        )
        # Land-use lists need the zone; without one there is nothing to query
        # (the builder emits an honest "no zone resolved" state instead).
        land_use_lga = _bare_lga_from_epi(zone_epi) or council_name
        f_land_use = None
        if zone_code and land_use_lga:
            f_land_use = pool.submit(
                _safe_call,
                lambda: _fetch_land_use_lists(zone_code, land_use_lga),
                "lep_land_use_table", ConfidenceLevel.AUTHORITATIVE,
            )
        # DA outcomes need the LGA for the refusal counts; development path only
        # (a strata unit's street-level determination history reads as noise).
        f_da_outcomes = f_refusal = None
        if not is_apartment:
            f_da_outcomes = pool.submit(
                _safe_call, lambda: _fetch_da_outcomes(lng, lat),
                "da_tracking_mapserver", ConfidenceLevel.AUTHORITATIVE,
            )
            if land_use_lga:
                f_refusal = pool.submit(
                    _safe_call, lambda: _fetch_refusal_stats(land_use_lga),
                    "da_tracking_mapserver", ConfidenceLevel.AUTHORITATIVE,
                )
        # Market context is development-lot analysis (same-zone, similar-size
        # comparables) — meaningless for an individual strata lot, so it is
        # only fetched on the development path.
        f_market = None
        if not is_apartment:
            f_market = pool.submit(
                _safe_call,
                lambda: _fetch_market_context(lng, lat, zone_code, lot_area_m2, resolved_prop_id),
                "nsw_valuer_general", ConfidenceLevel.DERIVED,
            )

        # ── Yield environmental (overlays + heritage + env sources) ──────
        overlays_df = _timed_result(f_overlays, 10, "postgis_overlays", timings)
        heritage_df = _timed_result(f_heritage, 10, "postgis_heritage", timings)
        mine_sub_df = _timed_result(f_mine_sub, 10, "nsw_spatial_services", timings)
        contam_df = _timed_result(f_contam, 10, "epa_contaminated_sites", timings)
        drinking_df = _timed_result(f_drinking, 10, "sepp_resilience_hazards", timings)
        servicing_df = _timed_result(f_servicing, 10, "sydney_water_gsp", timings)

        overlays_data, overlays_failed = _unwrap_or_default(overlays_df, {"overlays": [], "covered_layers": [], "proximity_m": {}})  # WO-2: overlays_failed -> _build_environmental stamps overlay-derived fields NOT_AVAILABLE instead of False@AUTHORITATIVE
        heritage_postgis = heritage_df.value
        # These services return None BOTH for "genuinely outside the layer" and
        # (via _safe_call) for a failed fetch — the confidence flag is the only
        # way to keep the two apart downstream (WO-2 class).
        mine_subsidence_raw, mine_failed = _unwrap_or_default(mine_sub_df, None)
        contaminated_land_raw, contam_failed = _unwrap_or_default(contam_df, None)
        drinking_water_raw, drinking_failed = _unwrap_or_default(drinking_df, None)
        # fetch_gsp_servicing returns its own three-state dict (never raises); a
        # timeout/_safe_call failure yields None -> _build_environmental marks it
        # NOT_AVAILABLE. The dict's own 'failed' status is handled there too.
        servicing_raw, _servicing_failed = _unwrap_or_default(servicing_df, None)
        # lot_geometry already awaited + reconciled before economics (above).
        contributions_df = _timed_result(f_contributions, 15, "planning_portal_cp", timings) if f_contributions else DataField(
            value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal_cp", reason="No prop_id resolved",
        )

        environmental = _build_environmental(
            controls, overlays_data, heritage_postgis,
            mine_subsidence_raw=mine_subsidence_raw,
            contaminated_land_raw=contaminated_land_raw,
            drinking_water_raw=drinking_water_raw,
            servicing_raw=servicing_raw,
            lat=lat, lng=lng,
            overlays_failed=overlays_failed, controls_failed=controls_failed,
            mine_failed=mine_failed, contam_failed=contam_failed,
            drinking_failed=drinking_failed,
        )
        sections_yielded += 1
        yield _sse_event("section", {
            "section": "environmental_constraints",
            "data": environmental.model_dump(),
            "progress": int(sections_yielded / total_sections * 100),
        })

        # ── Yield planning_controls (portal + overlays for fallbacks) ────
        # PostGIS fallbacks
        ov_by_type = {o.get("layer_type"): o for o in (overlays_data.get("overlays") or [])}
        if not controls.get("ass_class") and "acid_sulfate" in ov_by_type:
            controls["ass_class"] = ov_by_type["acid_sulfate"].get("value") or "Present"
        if not controls.get("lot_size") and "lot_size" in ov_by_type:
            controls["lot_size"] = ov_by_type["lot_size"].get("value")

        land_use_df = _timed_result(f_land_use, CONFIG.timeout_land_use, "lep_land_use_table", timings) if f_land_use else None
        planning_controls = _build_planning_controls(controls, overlays_data, lot_geometry_raw, lot_area_m2=lot_area_m2, controls_failed=controls_failed, land_use_df=land_use_df)
        sections_yielded += 1
        yield _sse_event("section", {
            "section": "planning_controls",
            "data": planning_controls.model_dump(),
            "progress": int(sections_yielded / total_sections * 100),
        })

        # ── Yield development-only sections ──────────────────────────────
        dcp_df = _timed_result(f_dcp, 10, "plotdetect_dcp", timings)
        sepp_df = _timed_result(f_sepp, 10, "housing_sepp_standards", timings)
        das_df = _timed_result(f_das, 15, "eplanning_da_api", timings)
        # 30s: the shadow endpoint's Sentinel-2 fetch step alone can take ~25s;
        # the prior 20s budget guaranteed a timeout before it could return.
        shadow_df = _timed_result(f_shadow, CONFIG.timeout_shadow_collect, "shadow_detector", timings)

        dcp_raw = dcp_df.value
        sepp_raw = sepp_df.value or []  # failsoft-ok: empty list = no standards; SEPP is a fast DB lookup, _build_sepp_housing handles empty gracefully
        shadow_raw = shadow_df.value

        if not is_apartment:
            dcp_controls = _build_dcp_controls(dcp_raw, dcp_former_council)
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "dcp_controls",
                "data": dcp_controls.model_dump(),
                "progress": int(sections_yielded / total_sections * 100),
            })

            sepp_housing = _build_sepp_housing(sepp_raw, zone_code, lot_area_m2)

            # SEPP-LEP override detection (SSE path)
            sse_lep_fsr = None
            fsr_str_sse = controls.get("fsr")
            if fsr_str_sse:
                try:
                    sse_lep_fsr = float(str(fsr_str_sse).replace(":1", "").strip())
                except (ValueError, TypeError):
                    pass
            _heritage_lmr = _is_heritage_land(controls, heritage_postgis)
            sepp_lep_overrides = _detect_sepp_lep_overrides(
                sepp_housing, height_m, sse_lep_fsr,
                is_heritage=_heritage_lmr,
            )

            # Per-form eligibility with citations — the ONE engine run this
            # brief makes; the capacity ceiling below reuses the same results.
            # Width is battleaxe-aware: on a flag lot the SEPP width tests need
            # the developable HEAD width, not the access-handle frontage.
            lot_dims_for_ca = planning_controls.lot_dimensions.value if planning_controls.lot_dimensions else None
            _lot_width = eligibility_lot_width(lot_dims_for_ca)
            eligibility_results = _sepp_eligibility_results(
                zone_code, lat, lng, lot_area_m2, _lot_width, _heritage_lmr,
            )
            sepp_eligibility_field = _build_sepp_eligibility_field(eligibility_results)

            sections_yielded += 1
            yield _sse_event("section", {
                "section": "sepp_housing",
                "data": DataField(
                    value=sepp_housing, confidence=ConfidenceLevel.AUTHORITATIVE,
                    source="housing_sepp_standards", as_at=today,
                ).model_dump(),
                "sepp_lep_overrides": [o.model_dump() for o in sepp_lep_overrides],
                "eligibility_forms": sepp_eligibility_field.model_dump(),
                "lot_area_m2": lot_area_m2,
                "lot_width_m": _lot_width,
                "progress": int(sections_yielded / total_sections * 100),
            })

            # ── Constraint arithmetic — binding constraint + realistic yield ──
            # Drives the capacity headline in the live UI.
            constraint_field = None
            if lot_area_m2 and lot_area_m2 > 0:
                try:
                    from services.constraint_arithmetic import compute_constraint_arithmetic

                    _excluded_forms = _eligibility_excluded_forms(lat, lng)
                    # Reuse the eligibility run from the SEPP card above — the
                    # engine is never invoked twice per brief.
                    _uplift_form, _uplift_citation = _lmr_uplift_form(
                        controls.get("zone"), lat, lng, lot_area_m2, _lot_width,
                        _heritage_lmr, results=eligibility_results,
                    )
                    _floor_form, _ceiling_form, _ceiling_from_lmr = _realistic_forms(
                        controls.get("zone"), _bare_lga_from_epi(zone_epi) or council_name,
                        excluded_forms=_excluded_forms, uplift_form=_uplift_form, return_source=True,
                    )
                    constraint_result = compute_constraint_arithmetic(
                        lot_area_m2=lot_area_m2,
                        dev_type=_floor_form,
                        ceiling_dev_type=_ceiling_form,
                        lep_height_str=controls.get("height"),
                        lep_fsr_str=controls.get("fsr"),
                        lot_dimensions=lot_dims_for_ca,
                        dcp_controls=dcp_controls.controls.value if dcp_controls.controls.value else [],
                        sepp_standards=sepp_housing,
                        sepp_lep_overrides=sepp_lep_overrides,
                    )
                    if constraint_result is not None:
                        _apply_lmr_attribution(constraint_result, _ceiling_from_lmr, _uplift_citation)
                        constraint_field = DataField(
                            value=constraint_result,
                            confidence=ConfidenceLevel.DERIVED,
                            source="constraint_arithmetic_engine",
                            as_at=today,
                        )
                        sections_yielded += 1
                        yield _sse_event("section", {
                            "section": "constraint_arithmetic",
                            "data": constraint_field.model_dump(),
                            "progress": int(sections_yielded / total_sections * 100),
                        })
                except Exception as e:
                    logger.warning("Constraint arithmetic (SSE) failed: %s", e)

            da_outcomes_df = _timed_result(f_da_outcomes, CONFIG.timeout_da_outcomes, "da_tracking_mapserver", timings) if f_da_outcomes else None
            refusal_df = _timed_result(f_refusal, CONFIG.timeout_da_outcomes, "da_tracking_refusal", timings) if f_refusal else None
            neighbourhood = _build_neighbourhood(das_df, shadow_raw, da_outcomes_df=da_outcomes_df, refusal_df=refusal_df)
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "neighbourhood",
                "data": neighbourhood.model_dump(),
                "progress": int(sections_yielded / total_sections * 100),
            })

            # ── Market context: VG comparables + recent sales (dev path only) ──
            market_df = _timed_result(f_market, CONFIG.timeout_market, "nsw_valuer_general", timings) if f_market else DataField(
                value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                source="nsw_valuer_general", reason="Market context not fetched",
            )
            market_context = _build_market_context(market_df.value)
            market_field = DataField(
                value=market_context,
                confidence=ConfidenceLevel.DERIVED if market_context else ConfidenceLevel.NOT_AVAILABLE,
                source="nsw_valuer_general", as_at=today,
                reason=None if market_context else (market_df.reason or "Valuer-General queries did not complete"),
            )
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "market_context",
                "data": market_field.model_dump(),
                "progress": int(sections_yielded / total_sections * 100),
            })

        # ── Yield satellite sections individually ────────────────────────
        bushfire_raw = flood_raw_sat = climate_raw = granny_flat_raw = pre_da_raw = None
        uhi_raw = arr_raw = firms_raw = None

        if req.include_satellite:
            bushfire_df = _timed_result(f_bushfire, 30, "bushfire_prescreen", timings)
            bushfire_raw = bushfire_df.value
            bushfire_detail = _build_bushfire_detail(bushfire_raw)
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "satellite.bushfire",
                "data": DataField(
                    value=bushfire_detail,
                    confidence=ConfidenceLevel.AUTHORITATIVE if bushfire_detail and bushfire_detail.category else ConfidenceLevel.NOT_AVAILABLE,
                    source="bushfire_prescreen", as_at=today,
                ).model_dump(),
                "progress": int(sections_yielded / total_sections * 100),
            })

            flood_sat_df = _timed_result(f_flood_sat, 70, "flood_truth", timings)  # > the concurrent JRC/WOfS inner budgets (60s) so a slow raster read isn't cut off
            flood_raw_sat = flood_sat_df.value
            flood_detail = _build_flood_detail(flood_raw_sat)
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "satellite.flood",
                "data": DataField(
                    value=flood_detail,
                    confidence=ConfidenceLevel.ESTIMATED if flood_detail else ConfidenceLevel.NOT_AVAILABLE,
                    source="flood_truth", as_at=today,
                ).model_dump(),
                "progress": int(sections_yielded / total_sections * 100),
            })

            climate_df = _timed_result(f_climate, 25, "climate_risk_score", timings)
            uhi_df = _timed_result(f_uhi, 10, "nsw_uhgc", timings)
            arr_df = _timed_result(f_arr, 18, "arr_data_hub", timings)
            firms_df = _timed_result(f_firms, 18, "nasa_firms", timings)
            climate_raw = climate_df.value
            uhi_raw = uhi_df.value
            arr_raw = arr_df.value
            firms_raw = firms_df.value
            climate_disclosure = _build_climate_disclosure(climate_raw, uhi_raw, arr_raw, firms_raw)
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "satellite.climate_disclosure",
                "data": DataField(
                    value=climate_disclosure,
                    confidence=ConfidenceLevel.ESTIMATED if climate_disclosure else ConfidenceLevel.NOT_AVAILABLE,
                    source="climate_disclosure_profile", as_at=today,
                ).model_dump(),
                "progress": int(sections_yielded / total_sections * 100),
            })

            granny_df = _timed_result(f_granny, 30, "granny_flat_detect", timings)
            granny_flat_raw = granny_df.value
            granny_detail = _build_granny_flat_detail(granny_flat_raw)
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "satellite.granny_flat",
                "data": DataField(
                    value=granny_detail,
                    confidence=ConfidenceLevel.ESTIMATED if granny_detail else ConfidenceLevel.NOT_AVAILABLE,
                    source="granny_flat_detect", as_at=today,
                ).model_dump(),
                "progress": int(sections_yielded / total_sections * 100),
            })

            # Solar — marker slot only; the card fires the gated route client-side.
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "satellite.solar",
                "data": DataField(
                    value=_fetch_solar_marker(), confidence=ConfidenceLevel.ESTIMATED,
                    source="google_solar_api", as_at=today,
                ).model_dump(),
                "progress": int(sections_yielded / total_sections * 100),
            })

            pre_da_requested = f_pre_da is not None
            pre_da_df = _timed_result(f_pre_da, CONFIG.timeout_premium, "pre_da_history", timings) if f_pre_da else DataField(
                value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                source="pre_da_history", reason="Site history not requested",
            )
            pre_da_raw = pre_da_df.value
            pre_da_detail = _build_pre_da_detail(pre_da_raw)
            # Distinguish "not requested" (tick the box) from "requested but didn't
            # complete" (it ran and failed/timed out) so the UI message is honest.
            if pre_da_detail:
                pre_da_reason = None
            elif pre_da_requested:
                pre_da_reason = pre_da_df.reason or "Site-history analysis did not complete"
            else:
                pre_da_reason = "Site history not requested"
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "satellite.pre_da_history",
                "data": DataField(
                    value=pre_da_detail,
                    confidence=ConfidenceLevel.ESTIMATED if pre_da_detail else ConfidenceLevel.NOT_AVAILABLE,
                    source="pre_da_history", as_at=today,
                    reason=pre_da_reason,
                ).model_dump(),
                "progress": int(sections_yielded / total_sections * 100),
            })

            terrain_df = _timed_result(f_terrain, CONFIG.timeout_terrain, "terrain_analysis", timings) if f_terrain else DataField(
                value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                source="terrain_analysis", reason="Terrain analysis not requested",
            )
            terrain_raw = terrain_df.value
            terrain_detail = _build_terrain_detail(terrain_raw)
            # Surface the real failure reason (e.g. a DEM-fetch or whitebox error)
            # instead of a generic message, so the cause is diagnosable from the UI.
            if terrain_detail:
                terrain_reason = None
            elif f_terrain is not None:
                terrain_reason = terrain_df.reason or "Terrain analysis did not complete"
            else:
                terrain_reason = "Terrain analysis not requested"
            # Structured interpretation (findings with narratives) computed by
            # the terrain service itself — passthrough, only when it is a dict.
            terrain_interp = terrain_raw.get("interpretation") if isinstance(terrain_raw, dict) else None
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "satellite.terrain",
                "data": DataField(
                    value=terrain_detail,
                    confidence=ConfidenceLevel.ESTIMATED if terrain_detail else ConfidenceLevel.NOT_AVAILABLE,
                    source="terrain_analysis", as_at=today,
                    reason=terrain_reason,
                ).model_dump(),
                "interpretation": terrain_interp if isinstance(terrain_interp, dict) else None,
                "progress": int(sections_yielded / total_sections * 100),
            })

    # ── Final assembly: compound constraints, gaps, confidence ───────────
    # Build satellite_data for compound constraint evaluation
    satellite_data = None
    if req.include_satellite:
        satellite_data = _build_satellite_data(
            bushfire_raw, flood_raw_sat, climate_raw, granny_flat_raw, pre_da_raw,
            uhi_raw=uhi_raw, arr_raw=arr_raw, firms_raw=firms_raw,
            terrain_raw=terrain_raw,
        )

    # Assemble the full brief for confidence/gaps computation
    if is_apartment:
        brief = RenovationBrief(
            address=req.address, lat=lat, lng=lng,
            prop_id=resolved_prop_id, run_date=today,
            strata=DataField(value=strata_info, confidence=ConfidenceLevel.AUTHORITATIVE, source="cadastre_strata", as_at=today),
            planning_controls=planning_controls,
            environmental_constraints=environmental,
            economics=economics,
            satellite=satellite_data,
            scope_limitations=_strata_scope_note(strata_type),
            confidence_summary=ConfidenceSummary(),
        )
    else:
        contributions_raw = contributions_df.value
        # #745 D5: propagate the fetch's OWN confidence/reason. A successful
        # query with zero contributions plans is legit-empty (authoritative,
        # no reason) — only a genuine fetch failure is NOT_AVAILABLE+reason.
        contributions_failed = (
            contributions_df.confidence == ConfidenceLevel.NOT_AVAILABLE
        )
        contributions_field = DataField(
            value=contributions_raw,
            confidence=ConfidenceLevel.NOT_AVAILABLE if contributions_failed
            else ConfidenceLevel.AUTHORITATIVE,
            source="planning_portal_cp",
            as_at=today,
            reason=contributions_df.reason if contributions_failed else None,
        )
        brief = DevelopmentBrief(
            address=req.address, lat=lat, lng=lng,
            prop_id=resolved_prop_id, run_date=today,
            strata=DataField(value=strata_info, confidence=ConfidenceLevel.AUTHORITATIVE, source="cadastre_strata", as_at=today),
            planning_controls=planning_controls,
            dcp_controls=dcp_controls,
            sepp_housing=DataField(value=sepp_housing, confidence=ConfidenceLevel.AUTHORITATIVE, source="housing_sepp_standards", as_at=today),
            sepp_lep_overrides=sepp_lep_overrides if not is_apartment else [],
            sepp_eligibility=sepp_eligibility_field,
            environmental_constraints=environmental,
            neighbourhood=neighbourhood,
            economics=economics,
            market_context=market_field,
            contributions=contributions_field,
            constraint_arithmetic=constraint_field,
            satellite=satellite_data,
            confidence_summary=ConfidenceSummary(),
        )

    # Compound constraints
    min_lot_size_m2 = None
    lot_size_str = controls.get("lot_size")
    if lot_size_str:
        try:
            min_lot_size_m2 = float(str(lot_size_str).replace(",", "").replace("m\u00b2", "").strip())
        except (ValueError, TypeError):
            pass

    das_for_compounds = [
        {"number": d.number, "distance_m": d.distance_m, "status": d.status,
         "description": d.dev_type, "dev_type": d.dev_type}
        for d in (neighbourhood.nearby_das.value or [])
    ] if not is_apartment else []

    compound_constraints = evaluate_compound_constraints(
        heritage_items=planning_controls.heritage_items.value or [],
        heritage_hca=planning_controls.heritage_hca.value or [],
        heritage_postgis=heritage_postgis,
        bushfire_designation=environmental.bushfire_designation.value,
        flood_epi=environmental.flood_epi.value or False,
        tod_area=planning_controls.tod_area.value or False,
        lot_area_m2=lot_area_m2,
        min_lot_size_m2=min_lot_size_m2,
        zone_code=zone_code,
        nearby_das=das_for_compounds,
        overlays=[
            {"layer_type": o.layer_type, "value": o.value}
            for o in (environmental.overlays.value or [])
        ],
    )
    if satellite_data:
        flood_detail = satellite_data.flood.value if satellite_data.flood.value else None
        gf_detail = satellite_data.granny_flat.value if satellite_data.granny_flat.value else None
        sat_constraints = evaluate_satellite_constraints(
            granny_flat_structures=gf_detail.structure_count if gf_detail else None,
            nearby_das=das_for_compounds,
            flood_epi=environmental.flood_epi.value or False,
            flood_jrc_pct=flood_detail.jrc_occurrence_pct if flood_detail else None,
            flood_wofs_pct=flood_detail.wofs_frequency_pct if flood_detail else None,
        )
        compound_constraints.extend(sat_constraints)

    brief.compound_constraints = compound_constraints

    # Staleness, confidence, gaps
    staleness_warnings = detect_staleness(brief)
    if lot_area_warning:
        staleness_warnings = [lot_area_warning, *staleness_warnings]
    summary = compute_confidence_summary(brief)
    gaps = collect_gaps(brief)
    gaps = enrich_gaps_with_verify_url(gaps, dcp_former_council)

    if lga_advisory:
        gaps.append(GapEntry(field="lga_validation", reason=lga_advisory))

    elapsed = time.monotonic() - start_time
    timing_summary = " | ".join(f"{label}={t:.1f}s/{status}" for label, t, status in timings)
    logger.info(
        "Intelligence brief SSE for %s completed in %.1fs — %d/%d fields available, brief_type=%s | %s",
        req.address, elapsed, summary.total - summary.not_available, summary.total,
        brief.brief_type, timing_summary,
    )

    yield _sse_event("complete", {
        "compound_constraints": [c.model_dump() for c in compound_constraints],
        "data_currency_warnings": staleness_warnings,
        "gaps": [g.model_dump() for g in gaps],
        "confidence_summary": summary.model_dump(),
        "brief_type": brief.brief_type,
        "elapsed_seconds": round(elapsed, 1),
        "progress": 100,
    })


def _safe_brief_sse(
    req: IntelligenceBriefRequest,
    resolved_prop_id: Optional[int],
    lat: float,
    lng: float,
    lot_wkt: Optional[str],
) -> Generator[str, None, None]:
    """Wrap the brief generator so a mid-stream exception surfaces as an
    ``error`` SSE event instead of silently terminating the stream. Without
    this, an exception after streaming started just closed the connection and
    the UI hung at the last progress percentage with no indication of failure.
    """
    # Concurrency cap: each brief peaks at a few GB (Sentinel-2 + pre-DA embeddings
    # + terrain arrays). Two at once OOM-killed the 8GB container, which severs every
    # in-flight stream (and drops the 'complete' event). Serialise heavy briefs; a
    # queued request waits up to the timeout, then gets an honest 'busy' event rather
    # than a crash. Tune via BRIEF_MAX_CONCURRENCY once the container has more memory.
    acquired = _BRIEF_SEMAPHORE.acquire(timeout=_BRIEF_ACQUIRE_TIMEOUT_S)
    if not acquired:
        yield _sse_event("error", {
            "error": "server_busy",
            "message": "The service is finishing other briefs right now — please try again in a minute.",
        })
        return
    try:
        yield from _generate_brief_sse(req, resolved_prop_id, lat, lng, lot_wkt)
    except Exception as e:  # convert ANY mid-stream failure into a visible event
        logger.exception("intelligence brief stream failed mid-generation")
        yield _sse_event("error", {
            "error": f"{type(e).__name__}: {str(e)[:300]}",
            "message": "The brief could not be completed. Please try again.",
        })
    finally:
        _BRIEF_SEMAPHORE.release()


@router.post("/intelligence-brief/stream")
def stream_intelligence_brief(req: IntelligenceBriefRequest):
    """SSE streaming variant — yields brief sections as data sources complete.

    Same sources and assembly logic as /intelligence-brief, but returns a
    text/event-stream where each section is emitted as soon as its
    dependencies are satisfied. Designed for Trigger.dev relay to frontend.

    Events:
      metadata  — address, coordinates, run config (immediate)
      section   — one assembled section with progress percentage
      complete  — compound constraints, gaps, confidence summary (final)
      error     — unrecoverable error mid-stream
    """
    resolved_prop_id, lat, lng, lot_wkt = _resolve_address(req)
    return StreamingResponse(
        _safe_brief_sse(req, resolved_prop_id, lat, lng, lot_wkt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
