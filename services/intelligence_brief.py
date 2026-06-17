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
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Generator, Generic, Literal, Optional, TypeVar

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    timeout_terrain: float = 30.0

    # NSW bounding box (WGS84)
    nsw_lat_min: float = -37.5
    nsw_lat_max: float = -28.0
    nsw_lng_min: float = 140.9
    nsw_lng_max: float = 153.7

    # Search parameters
    da_radius_m: int = 200
    da_lookback_days: int = 365

    # Concurrency — single pool runs all sources; dependents submitted after
    # their prerequisite completes, so effective parallelism is ~15-20.
    max_parallel_sources: int = 20

    # Minimum viable brief — refuse if too many fields failed
    min_available_ratio: float = 0.70


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


class DCPControls(BaseModel):
    """DCP setback and development controls."""

    controls: DataField[list[DCPControl]]
    dcp_name: DataField[Optional[str]]
    dcp_url: DataField[Optional[str]]
    section_ref: DataField[Optional[str]]


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
    source: Optional[str] = None
    lot_area_m2: Optional[float] = None


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
    coastal_hazards: DataField[Optional[dict]] = DataField(
        value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
        source="sepp_resilience_hazards", reason="Not yet extracted from overlays",
    )


class Neighbourhood(BaseModel):
    """Nearby DA activity and context."""

    nearby_das: DataField[list[NearbyDA]]
    da_count: DataField[Optional[int]]
    shadow: DataField[Optional[ShadowResult]]


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

    category: Optional[str] = None  # Vegetation Category 1/2/3, buffer
    bal_estimate: Optional[str] = None
    vegetation_type: Optional[str] = None
    cross_overlays: Optional[dict] = None  # flood, heritage, zone intersections
    confidence: Optional[str] = None


class FloodDetail(BaseModel):
    """Multi-source flood analysis beyond statutory EPI flag."""

    epi_flood: Optional[bool] = None
    jrc_occurrence_pct: Optional[float] = None  # JRC 1984-2021
    wofs_frequency_pct: Optional[float] = None  # DEA WOfS
    bom_gauge_distance_km: Optional[float] = None
    flood_studies: Optional[list[dict]] = None
    confidence: Optional[str] = None


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
    environmental_constraints: EnvironmentalConstraints
    neighbourhood: Neighbourhood
    economics: Economics
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
    """Classify strata type from cadastre data + lot area.

    Spike finding: 1500m² heuristic misclassifies strata townhouses.
    v1: use four-state enum, accept ambiguity for edge cases.
    """
    if not strata_info.get("is_strata"):
        return StrataType.NOT_STRATA

    # Definitive signals
    plan_type = (strata_info.get("plan_type") or "").lower()
    if plan_type in ("community", "neighbourhood"):
        return StrataType.DEVELOPMENT  # community title = ground-level

    # Heuristic: large lot + strata = likely apartment, small = likely townhouse
    # But this fails for strata townhouse complexes on large lots (spike: 2140m²)
    if lot_area_m2 is not None:
        if lot_area_m2 > 2500:
            return StrataType.APARTMENT  # very large parent lot → high confidence
        if lot_area_m2 < 400:
            return StrataType.DEVELOPMENT  # tiny lot → strata subdivision of house
        # 400-2500m² → ambiguous without building footprint data
        return StrataType.AMBIGUOUS

    return StrataType.AMBIGUOUS


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
    get_raw_controls,
    parse_controls,
    get_valuation,
    get_unique_overlays,
    detect_strata,
    detect_former_council,
    get_shadow_risk,
    _council_from_zone_epi,
    get_nearby_das,
)
from conveyancing_db import (  # noqa: E402
    fetch_dcp_setbacks,
    fetch_heritage_postgis,
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
    from granny_flat import detect_structures, GrannyFlatDetectRequest  # noqa: E402
except ImportError:
    from services.granny_flat import detect_structures, GrannyFlatDetectRequest  # noqa: E402

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
    """Cadastre strata detection."""
    return detect_strata(address, lat, lng)


def _fetch_nearby_das(
    lat: float, lng: float, council_name: Optional[str],
    radius_m: int, days: int,
) -> list[dict]:
    """ePlanning DA API: nearby development applications."""
    if not council_name:
        return []
    return get_nearby_das(lat, lng, council_name, radius_m=radius_m, days=days)


def _fetch_shadow(
    address: str, prop_id: int, lat: float, lng: float,
    height_m: Optional[float],
) -> Optional[dict]:
    """Shadow pipeline via Railway."""
    return get_shadow_risk(address, prop_id, lat, lng, height_m=height_m)


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
)
from services.lot_dimensions import (
    fetch_lot_geometry,
    calculate_lot_dimensions,
)


# ---------------------------------------------------------------------------
# Satellite fetchers — Stage 4a
# ---------------------------------------------------------------------------


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
    """Per-hazard climate scores (shim feeds into ClimateDisclosureProfile)."""
    result = _climate_risk_score_fn(lat, lng)
    return result.to_dict()


def _fetch_granny_flat_detect(
    address: str, lat: float, lng: float,
    prop_id: str,
) -> dict:
    """Granny flat structure detection (step 1 only — no confirmation)."""
    req = GrannyFlatDetectRequest(
        address=address, lat=lat, lng=lng,
        prop_id=prop_id,
    )
    result = detect_structures(req)
    # Return the Pydantic model as dict
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


def _fetch_pre_da_history(
    address: str, lot_area_m2: Optional[float],
) -> dict:
    """Pre-DA site history (premium, 30-90s)."""
    req = PreDAHistoryRequest(
        address=address, lot_area_m2=lot_area_m2,
    )
    return run_pre_da_history(req)


def _build_bushfire_detail(bushfire_raw: Optional[dict]) -> Optional[BushfireDetail]:
    """Extract BushfireDetail from raw bushfire prescreen output."""
    if not bushfire_raw:
        return None
    outputs = bushfire_raw.get("outputs") or {}
    rfs = outputs.get("rfs") or {}
    return BushfireDetail(
        category=rfs.get("category"),
        bal_estimate=rfs.get("bal_estimate"),
        vegetation_type=rfs.get("vegetation_type"),
        cross_overlays=outputs.get("cross_overlays"),
        confidence=bushfire_raw.get("confidence"),
    )


def _build_flood_detail(flood_raw: Optional[dict]) -> Optional[FloodDetail]:
    """Extract FloodDetail from raw flood truth output."""
    if not flood_raw:
        return None
    outputs = flood_raw.get("outputs") or {}
    return FloodDetail(
        epi_flood=outputs.get("epi_flood"),
        jrc_occurrence_pct=outputs.get("jrc_occurrence_pct"),
        wofs_frequency_pct=outputs.get("wofs_frequency_pct"),
        bom_gauge_distance_km=outputs.get("bom_gauge_distance_km"),
        flood_studies=outputs.get("flood_studies"),
        confidence=flood_raw.get("confidence"),
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
        if firms_raw.get("hotspot_count", 0) > 0:
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
    """Extract PreDAHistoryDetail from raw pre-DA output."""
    if not pre_da_raw:
        return None
    return PreDAHistoryDetail(
        timeline=pre_da_raw.get("timeline"),
        heritage_flag=pre_da_raw.get("heritage_flag"),
        council=pre_da_raw.get("council"),
        data_quality_note=pre_da_raw.get("data_quality_note"),
    )


def _fetch_terrain(lat: float, lng: float) -> dict:
    """Run terrain analysis (slope, aspect, elevation, ruggedness)."""
    return run_terrain_analysis(lat, lng, include_flood=False)


def _build_terrain_detail(terrain_raw: Optional[dict]) -> Optional[TerrainAnalysisDetail]:
    """Extract TerrainAnalysisDetail from raw terrain output."""
    if not terrain_raw:
        return None
    terrain_fields = terrain_raw.get("terrain") or terrain_raw
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
            reason=None if pre_da_detail else "Pre-DA history not requested or failed",
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
) -> PlanningControls:
    """Map conveyancing parse_controls output to PlanningControls schema."""
    today = date.today().isoformat()
    auth = ConfidenceLevel.AUTHORITATIVE

    overlay_list = overlays_data.get("overlays", []) if overlays_data else []

    # Heritage from portal
    heritage_items_raw = controls.get("heritage_items") or []
    heritage_hca_raw = controls.get("heritage_hca") or []

    # SEPP overlays
    sepp_overlays_raw = controls.get("sepp_overlays") or []

    # Housing SEPP and TOD
    housing_sepp = controls.get("housing_sepp", False)
    tod_area = controls.get("tod_area", False)

    # Lot dimensions — compute from polygon geometry if available, fall back
    # to scalar lot_size string from planning portal
    lot_size_str = controls.get("lot_size")
    lot_area = None
    if lot_size_str:
        try:
            lot_area = float(str(lot_size_str).replace(",", "").replace("m²", "").strip())
        except (ValueError, TypeError):
            pass

    lot_dims = calculate_lot_dimensions(lot_geometry) if lot_geometry else None
    if lot_dims:
        # Polygon-derived dimensions — authoritative for frontage/depth.
        # Prefer portal lot_size for area if available (it's from the valuer).
        if lot_area and lot_dims.area_m2:
            lot_dims.area_m2 = lot_area
        elif lot_area and not lot_dims.area_m2:
            lot_dims.area_m2 = lot_area
    elif lot_area:
        # No polygon — area-only fallback (original behaviour)
        lot_dims = LotDimensions(area_m2=lot_area)

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
            value=lot_dims,
            confidence=auth if lot_dims else ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal",
            as_at=today,
        ),
    )


def _build_dcp_controls(
    dcp_data: Optional[dict],
    lga_slug: Optional[str],
) -> DCPControls:
    """Map fetch_dcp_setbacks output to DCPControls schema."""
    today = date.today().isoformat()

    if dcp_data is None:
        reason = f"DCP controls not yet extracted for '{lga_slug}'" if lga_slug else "Former council could not be determined"
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
            control_type=s.get("control_type", s.get("type", "")),
            dev_type=s.get("dev_type", "dwelling_house"),
            value_min=val_min,
            value_max=_parse_numeric(s.get("value_max")),
            unit=s.get("unit", "m"),
            condition=condition,
            source_ref=s.get("clause") or dcp_data.get("clause_ref"),
        ))

    return DCPControls(
        controls=DataField(value=controls_list, confidence=extracted, source="plotdetect_dcp", as_at=today),
        dcp_name=DataField(value=dcp_data.get("dcp_name"), confidence=extracted, source="plotdetect_dcp", as_at=today),
        dcp_url=DataField(value=dcp_data.get("dcp_url"), confidence=extracted, source="plotdetect_dcp", as_at=today),
        section_ref=DataField(value=dcp_data.get("section"), confidence=extracted, source="plotdetect_dcp", as_at=today),
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
            threshold = float(suffix.split("_")[-1])
            if lot_area_m2 < threshold:
                return value
        elif "over" in suffix:
            threshold = float(suffix.split("_")[-1])
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

    # Group by development_type
    by_dev_type: dict[str, dict[str, Any]] = {}
    for s in standards_raw:
        dt = s["development_type"]
        st = s["standard_type"]
        if dt not in by_dev_type:
            by_dev_type[dt] = {}
        by_dev_type[dt][st] = s["numeric_value"]

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

        results.append(SEPPStandard(
            dev_type=dt,
            eligible=eligible,
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


def _detect_sepp_lep_overrides(
    sepp_standards: list[SEPPStandard],
    lep_height_m: Optional[float],
    lep_fsr: Optional[float],
) -> list[SeppLepOverride]:
    """Detect cases where SEPP standard exceeds (overrides) LEP control.

    SEPP prevails only when its value is MORE GENEROUS (strictly greater) than LEP.
    This is the server-side equivalent of the frontend override detection in PR #437.
    """
    overrides: list[SeppLepOverride] = []
    for std in sepp_standards:
        if std.max_height_m and lep_height_m and std.max_height_m > lep_height_m:
            overrides.append(SeppLepOverride(
                dev_type=std.dev_type,
                control="height",
                lep_value=lep_height_m,
                sepp_value=std.max_height_m,
            ))
        if std.max_fsr and lep_fsr and std.max_fsr > lep_fsr:
            overrides.append(SeppLepOverride(
                dev_type=std.dev_type,
                control="fsr",
                lep_value=lep_fsr,
                sepp_value=std.max_fsr,
            ))
    return overrides


def _build_environmental(
    controls: dict,
    overlays_data: dict,
    heritage_postgis: Optional[dict],
    mine_subsidence_raw: Optional[dict] = None,
    contaminated_land_raw: Optional[dict] = None,
    drinking_water_raw: Optional[dict] = None,
) -> EnvironmentalConstraints:
    """Map overlays + heritage to EnvironmentalConstraints."""
    today = date.today().isoformat()
    auth = ConfidenceLevel.AUTHORITATIVE

    overlay_list = overlays_data.get("overlays", []) if overlays_data else []
    covered = overlays_data.get("covered_layers", []) if overlays_data else []

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

    env_overlays = [
        EnvironmentalOverlay(
            layer_type=o.get("layer_type", ""),
            value=o.get("value"),
            instrument=o.get("instrument_key"),
            lga=o.get("lga"),
        )
        for o in overlay_list
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

    return EnvironmentalConstraints(
        flood_epi=DataField(value=flood_epi, confidence=auth, source="postgis_overlays", as_at=today),
        overlays=DataField(value=env_overlays, confidence=auth, source="postgis_overlays", as_at=today),
        overlay_coverage=DataField(value=covered, confidence=auth, source="postgis_overlays", as_at=today),
        bushfire_designation=DataField(value=bushfire_designation, confidence=auth, source="postgis_overlays", as_at=today),
        heritage_postgis=DataField(
            value=heritage_postgis if heritage_postgis and heritage_postgis.get("has_heritage") else None,
            confidence=auth if heritage_postgis else ConfidenceLevel.NOT_AVAILABLE,
            source="postgis_heritage",
            as_at=today,
        ),
        # Typed fields from spatial_overlays — present if layer is in covered list
        terrestrial_biodiversity=DataField(
            value=has_biodiversity if "biodiversity" in covered else None,
            confidence=auth if "biodiversity" in covered else ConfidenceLevel.NOT_AVAILABLE,
            source="postgis_overlays",
            as_at=today,
            reason=None if "biodiversity" in covered else "Layer not ingested for this LGA",
        ),
        riparian_land=DataField(
            value=has_riparian if "riparian" in covered else None,
            confidence=auth if "riparian" in covered else ConfidenceLevel.NOT_AVAILABLE,
            source="postgis_overlays",
            as_at=today,
            reason=None if "riparian" in covered else "Layer not ingested for this LGA",
        ),
        wetlands=DataField(
            value=has_wetlands if "wetlands" in covered else None,
            confidence=auth if "wetlands" in covered else ConfidenceLevel.NOT_AVAILABLE,
            source="postgis_overlays",
            as_at=today,
            reason=None if "wetlands" in covered else "Layer not ingested for this LGA",
        ),
        anef=DataField(
            value=anef_value if "anef" in covered else None,
            confidence=auth if "anef" in covered else ConfidenceLevel.NOT_AVAILABLE,
            source="postgis_overlays",
            as_at=today,
            reason=None if "anef" in covered else "Layer not ingested for this LGA",
        ),
        coastal_hazards=DataField(
            value=coastal_layers if coastal_layers else None,
            confidence=auth if coastal_layers else ConfidenceLevel.NOT_AVAILABLE,
            source="sepp_resilience_hazards",
            as_at=today,
            reason=None if coastal_layers else "No coastal hazard overlays at this location",
        ),
        mine_subsidence=DataField(
            value=mine_subsidence_raw.get("in_district", False) if mine_subsidence_raw else False,
            confidence=auth,
            source="nsw_spatial_services",
            as_at=today,
        ),
        contaminated_land=DataField(
            value=contaminated_land_raw.get("has_notified_sites", False) if contaminated_land_raw else False,
            confidence=auth,
            source="epa_contaminated_sites",
            as_at=today,
        ),
        drinking_water_catchment=DataField(
            value=drinking_water_raw.get("in_catchment", False) if drinking_water_raw else False,
            confidence=auth,
            source="sepp_resilience_hazards",
            as_at=today,
        ),
    )


def _build_neighbourhood(
    das: list[dict],
    shadow_result: Optional[dict],
) -> Neighbourhood:
    """Map DA list + shadow to Neighbourhood schema."""
    today = date.today().isoformat()

    nearby = [
        NearbyDA(
            number=d.get("number", ""),
            address=d.get("address"),
            distance_m=d.get("distance_m"),
            status=d.get("status"),
            dev_type=d.get("description") or d.get("development_type"),
            lodgement_date=d.get("lodged") or (str(d.get("lodgement_date", ""))[:10] if d.get("lodgement_date") else None),
            cost=d.get("cost_of_development"),
        )
        for d in das
    ]

    shadow_schema = None
    if shadow_result:
        scenarios = []
        for s in shadow_result.get("scenarios", []):
            scenarios.append(ShadowScenario(
                date_label=s.get("date_label", ""),
                time_label=s.get("time_label", ""),
                sun_altitude_deg=s.get("sun_altitude_deg"),
                sun_azimuth_deg=s.get("sun_azimuth_deg"),
                shadow_length_m=s.get("shadow_length_m"),
                overlap_pct=s.get("overlap_pct"),
            ))
        shadow_schema = ShadowResult(
            height_m=shadow_result.get("height_m"),
            height_source=shadow_result.get("height_source"),
            adg_compliant=shadow_result.get("adg_compliant"),
            scenarios=scenarios,
            worst_case_scenario=shadow_result.get("worst_case_scenario"),
        )

    return Neighbourhood(
        nearby_das=DataField(value=nearby, confidence=ConfidenceLevel.AUTHORITATIVE, source="eplanning_da_api", as_at=today),
        da_count=DataField(value=len(nearby), confidence=ConfidenceLevel.AUTHORITATIVE, source="eplanning_da_api", as_at=today),
        shadow=DataField(
            value=shadow_schema,
            confidence=ConfidenceLevel.DERIVED if shadow_schema else ConfidenceLevel.NOT_AVAILABLE,
            source="shadow_detector",
            as_at=today,
            reason="Shadow pipeline unavailable" if not shadow_schema else None,
        ),
    )


def _build_economics(valuation: dict) -> Economics:
    """Map VG valuation to Economics schema."""
    today = date.today().isoformat()

    history = [
        ValuationHistory(year=h.get("year", ""), value=int(h.get("value")) if h.get("value") else None)
        for h in (valuation.get("val_history") or [])
    ]

    lv = valuation.get("land_value")

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
            value=valuation.get("lot_area_m2"),
            confidence=ConfidenceLevel.AUTHORITATIVE if valuation.get("lot_area_m2") else ConfidenceLevel.NOT_AVAILABLE,
            source="nsw_valuation_service",
            as_at=today,
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


@router.post("/intelligence-brief")
def run_intelligence_brief(req: IntelligenceBriefRequest):
    """
    Intelligence Brief — on-demand property screening.

    Calls the same data sources as the conveyancing pipeline, restructured
    into the DataField[T] contract with confidence, source, and as_at on
    every field. No satellite, no LLM — those are Stages 4 and 5.
    """
    start_time = time.monotonic()
    today = date.today().isoformat()
    timings: list[tuple] = []

    # ── 1–2. Address resolution + coordinate validation ──────────────────
    resolved_prop_id, lat, lng, lot_wkt = _resolve_address(req)

    # ── 3. Flattened parallel fetch — single ThreadPoolExecutor ──────────
    #
    # Dependency graph:
    #   15 sources need only lat/lng/prop_id → fire immediately
    #   4 sources need zone_code/zone_epi from planning_portal → wait for portal
    #   1 source needs lot_area_m2 from valuation → wait for valuation
    #
    # All sources run in ONE pool. Dependents are submitted as soon as their
    # prerequisite completes — not after all independent sources finish.
    # This cuts worst-case from 85s (3 sequential pools) to ~30s (one pool,
    # total time ≈ max(portal + slowest_dependent, slowest_independent)).

    import uuid

    f_controls = None
    f_valuation = None
    satellite_data = None
    bushfire_raw = None
    flood_raw_sat = None
    climate_raw = None
    granny_flat_raw = None
    pre_da_raw = None
    uhi_raw = None
    arr_raw = None
    firms_raw = None
    report_id = str(uuid.uuid4())

    with ThreadPoolExecutor(max_workers=CONFIG.max_parallel_sources) as pool:

        # ── 3a. Submit all independent sources (only need lat/lng/prop_id) ──

        f_lot_geometry = None
        f_contributions = None
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

        # Satellite sources — fire immediately if requested (only need lat/lng)
        f_bushfire = None
        f_flood_sat = None
        f_climate = None
        f_granny = None
        f_uhi = None
        f_arr = None
        f_firms = None
        f_terrain = None

        if req.include_satellite:
            f_bushfire = pool.submit(
                _safe_call,
                lambda: _fetch_bushfire(req.address, lat, lng, str(resolved_prop_id) if resolved_prop_id else None, report_id),
                "bushfire_prescreen", ConfidenceLevel.AUTHORITATIVE,
            )
            f_flood_sat = pool.submit(
                _safe_call,
                lambda: _fetch_flood(req.address, lat, lng, str(resolved_prop_id) if resolved_prop_id else None, report_id),
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

        # ── 3b. Await planning_portal → derive dependents → submit them ────
        #
        # Only blocks on the ONE source these 4 dependents need.
        # Meanwhile, all other independent sources continue running in the pool.

        controls_df = _timed_result(f_controls, 15, "planning_portal", timings) if f_controls else DataField(
            value=parse_controls([]), confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal", reason="No prop_id resolved",
        )
        controls = controls_df.value or parse_controls([])

        # Derive parameters for dependent sources
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

        # Submit the 4 sources that depend on planning_portal results
        f_das = pool.submit(
            _safe_call,
            lambda: _fetch_nearby_das(lat, lng, council_name, CONFIG.da_radius_m, CONFIG.da_lookback_days),
            "eplanning_da_api", ConfidenceLevel.AUTHORITATIVE,
        )
        f_shadow = pool.submit(
            _safe_call,
            lambda: _fetch_shadow(req.address, resolved_prop_id or 0, lat, lng, height_m),
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

        # ── 3c. Await valuation → submit pre_da if premium ────────────────

        valuation_df = _timed_result(f_valuation, 15, "nsw_valuation_service", timings) if f_valuation else DataField(
            value={"lot_area_m2": None, "land_value": None, "val_base_date": None, "val_history": []},
            confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="nsw_valuation_service", reason="No prop_id resolved",
        )
        valuation = valuation_df.value or {"lot_area_m2": None, "land_value": None, "val_base_date": None, "val_history": []}
        lot_area_m2 = valuation.get("lot_area_m2")

        f_pre_da = None
        if req.include_satellite and req.include_premium:
            f_pre_da = pool.submit(
                _safe_call,
                lambda: _fetch_pre_da_history(req.address, lot_area_m2),
                "pre_da_history", ConfidenceLevel.ESTIMATED,
            )

        # ── 3d. Collect all remaining results ──────────────────────────────
        #
        # Most independent sources finished while we waited for controls/valuation.
        # These _timed_result calls return near-instantly for already-complete futures.

        overlays_df = _timed_result(f_overlays, 10, "postgis_overlays", timings)
        strata_df = _timed_result(f_strata, 10, "cadastre_strata", timings)
        heritage_df = _timed_result(f_heritage, 10, "postgis_heritage", timings)
        mine_sub_df = _timed_result(f_mine_sub, 10, "nsw_spatial_services", timings)
        contam_df = _timed_result(f_contam, 10, "epa_contaminated_sites", timings)
        drinking_df = _timed_result(f_drinking, 10, "sepp_resilience_hazards", timings)
        lot_geometry_df = _timed_result(f_lot_geometry, 15, "planning_portal_lot", timings) if f_lot_geometry else DataField(
            value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal_lot", reason="No prop_id resolved",
        )
        contributions_df = _timed_result(f_contributions, 15, "planning_portal_cp", timings) if f_contributions else DataField(
            value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal_cp", reason="No prop_id resolved",
        )

        # Dependent sources (submitted after controls)
        das_df = _timed_result(f_das, 15, "eplanning_da_api", timings)
        shadow_df = _timed_result(f_shadow, 20, "shadow_detector", timings)
        dcp_df = _timed_result(f_dcp, 10, "plotdetect_dcp", timings)
        sepp_df = _timed_result(f_sepp, 10, "housing_sepp_standards", timings)

        # Satellite results
        if req.include_satellite:
            bushfire_df = _timed_result(f_bushfire, CONFIG.timeout_postgis + 5, "bushfire_prescreen", timings)
            flood_sat_df = _timed_result(f_flood_sat, 20, "flood_truth", timings)
            climate_df = _timed_result(f_climate, 10, "climate_risk_score", timings)
            granny_df = _timed_result(f_granny, 30, "granny_flat_detect", timings)
            uhi_df = _timed_result(f_uhi, 10, "nsw_uhgc", timings)
            arr_df = _timed_result(f_arr, 18, "arr_data_hub", timings)
            firms_df = _timed_result(f_firms, 18, "nasa_firms", timings)
            terrain_df = _timed_result(f_terrain, CONFIG.timeout_terrain, "terrain_analysis", timings) if f_terrain else DataField(
                value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                source="terrain_analysis", reason="Terrain analysis not requested",
            )
            pre_da_df = _timed_result(f_pre_da, CONFIG.timeout_satellite + 5, "pre_da_history", timings) if f_pre_da else DataField(
                value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                source="pre_da_history", reason="Premium data not requested",
            )

            bushfire_raw = bushfire_df.value
            flood_raw_sat = flood_sat_df.value
            climate_raw = climate_df.value
            granny_flat_raw = granny_df.value
            pre_da_raw = pre_da_df.value
            uhi_raw = uhi_df.value
            arr_raw = arr_df.value
            firms_raw = firms_df.value
            terrain_raw = terrain_df.value

    # ── 4. Extract remaining results ────────────────────────────────────
    overlays_data = overlays_df.value or {"overlays": [], "covered_layers": [], "proximity_m": {}}
    strata_raw = strata_df.value or {"is_strata": False}
    heritage_postgis = heritage_df.value
    mine_subsidence_raw = mine_sub_df.value
    contaminated_land_raw = contam_df.value
    drinking_water_raw = drinking_df.value
    das_raw = das_df.value or []
    shadow_raw = shadow_df.value
    dcp_raw = dcp_df.value
    sepp_raw = sepp_df.value or []
    lot_geometry_raw = lot_geometry_df.value  # Portal lot polygon (EPSG:3857)

    # ── 5. PostGIS fallbacks (same as conveyancing.py) ───────────────────
    ov_by_type = {o.get("layer_type"): o for o in overlays_data.get("overlays", [])}
    if not controls.get("ass_class") and "acid_sulfate" in ov_by_type:
        controls["ass_class"] = ov_by_type["acid_sulfate"].get("value") or "Present"
    if not controls.get("lot_size") and "lot_size" in ov_by_type:
        controls["lot_size"] = ov_by_type["lot_size"].get("value")

    # Build satellite data if requested
    if req.include_satellite:
        satellite_data = _build_satellite_data(
            bushfire_raw, flood_raw_sat, climate_raw, granny_flat_raw, pre_da_raw,
            uhi_raw=uhi_raw, arr_raw=arr_raw, firms_raw=firms_raw,
            terrain_raw=terrain_raw,
        )

    # ── 6. Strata classification ─────────────────────────────────────────
    strata_type = classify_strata(strata_raw, lot_area_m2)

    strata_info = StrataInfo(
        is_strata=strata_raw.get("is_strata", False),
        strata_type=strata_type,
        strata_plan=strata_raw.get("strata_plan"),
        plan_label=strata_raw.get("plan_label"),
        source=strata_raw.get("source"),
        lot_area_m2=lot_area_m2,
    )

    # ── 7. Assemble brief ────────────────────────────────────────────────
    planning_controls = _build_planning_controls(controls, overlays_data, lot_geometry_raw)
    dcp_controls = _build_dcp_controls(dcp_raw, dcp_former_council)
    sepp_housing = _build_sepp_housing(sepp_raw, zone_code, lot_area_m2)

    # ── 7b. SEPP-LEP override detection ────────────────────────────────
    lep_height_m = None
    lep_fsr_val = None
    if height_m:
        lep_height_m = height_m
    fsr_str = controls.get("fsr")
    if fsr_str:
        try:
            lep_fsr_val = float(str(fsr_str).replace(":1", "").strip())
        except (ValueError, TypeError):
            pass
    sepp_lep_overrides = _detect_sepp_lep_overrides(sepp_housing, lep_height_m, lep_fsr_val)

    # ── 7c. Constraint arithmetic — binding constraint + realistic yield ──
    constraint_result = None
    if lot_area_m2 and lot_area_m2 > 0:
        try:
            from services.constraint_arithmetic import compute_constraint_arithmetic

            lot_dims_for_ca = planning_controls.lot_dimensions.value if planning_controls.lot_dimensions else None
            constraint_result = compute_constraint_arithmetic(
                lot_area_m2=lot_area_m2,
                dev_type="dwelling_house",
                lep_height_str=controls.get("max_height"),
                lep_fsr_str=fsr_str,
                lot_dimensions=lot_dims_for_ca,
                dcp_controls=dcp_controls.controls.value if dcp_controls.controls.value else [],
                sepp_standards=sepp_housing,
                sepp_lep_overrides=sepp_lep_overrides,
            )
        except Exception as e:
            logger.warning("Constraint arithmetic computation failed: %s", e)

    environmental = _build_environmental(
        controls, overlays_data, heritage_postgis,
        mine_subsidence_raw=mine_subsidence_raw,
        contaminated_land_raw=contaminated_land_raw,
        drinking_water_raw=drinking_water_raw,
    )
    neighbourhood = _build_neighbourhood(das_raw, shadow_raw)
    economics = _build_economics(valuation)

    # ── 8. Choose brief type based on strata classification ──────────────
    is_apartment = strata_type == StrataType.APARTMENT or strata_type == StrataType.AMBIGUOUS

    if is_apartment:
        brief = RenovationBrief(
            address=req.address,
            lat=lat,
            lng=lng,
            prop_id=resolved_prop_id,
            run_date=today,
            strata=DataField(value=strata_info, confidence=ConfidenceLevel.AUTHORITATIVE, source="cadastre_strata", as_at=today),
            planning_controls=planning_controls,
            environmental_constraints=environmental,
            economics=economics,
            satellite=satellite_data,
            confidence_summary=ConfidenceSummary(),  # placeholder, recomputed below
        )
    else:
        contributions_raw = contributions_df.value
        contributions_field = DataField(
            value=contributions_raw,
            confidence=ConfidenceLevel.AUTHORITATIVE if contributions_raw else ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal_cp",
            as_at=today,
            reason=None if contributions_raw else "No contributions plans found for this property",
        )

        constraint_arithmetic_field = None
        if constraint_result is not None:
            constraint_arithmetic_field = DataField(
                value=constraint_result,
                confidence=ConfidenceLevel.DERIVED,
                source="constraint_arithmetic_engine",
                as_at=today,
            )

        brief = DevelopmentBrief(
            address=req.address,
            lat=lat,
            lng=lng,
            prop_id=resolved_prop_id,
            run_date=today,
            strata=DataField(value=strata_info, confidence=ConfidenceLevel.AUTHORITATIVE, source="cadastre_strata", as_at=today),
            planning_controls=planning_controls,
            dcp_controls=dcp_controls,
            sepp_housing=DataField(value=sepp_housing, confidence=ConfidenceLevel.AUTHORITATIVE, source="housing_sepp_standards", as_at=today),
            sepp_lep_overrides=sepp_lep_overrides,
            environmental_constraints=environmental,
            neighbourhood=neighbourhood,
            economics=economics,
            contributions=contributions_field,
            constraint_arithmetic=constraint_arithmetic_field,
            satellite=satellite_data,
            confidence_summary=ConfidenceSummary(),  # placeholder
        )

    # ── 9. Compound constraints (Stage 3) ──────────────────────────────
    # Parse min lot size for marginal lot check
    min_lot_size_m2 = None
    lot_size_str = controls.get("lot_size")
    if lot_size_str:
        try:
            min_lot_size_m2 = float(str(lot_size_str).replace(",", "").replace("m²", "").strip())
        except (ValueError, TypeError):
            pass

    # Nearby DAs as dicts for compound constraint evaluation
    das_for_compounds = [
        {"number": d.number, "distance_m": d.distance_m, "status": d.status,
         "description": d.dev_type, "dev_type": d.dev_type}
        for d in (neighbourhood.nearby_das.value or [])
    ]

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
    # Satellite compound constraints (only when satellite data present)
    if satellite_data:
        flood_detail = (satellite_data.flood.value if satellite_data.flood.value else None)
        gf_detail = (satellite_data.granny_flat.value if satellite_data.granny_flat.value else None)
        sat_constraints = evaluate_satellite_constraints(
            granny_flat_structures=gf_detail.structure_count if gf_detail else None,
            nearby_das=das_for_compounds,
            flood_epi=environmental.flood_epi.value or False,
            flood_jrc_pct=flood_detail.jrc_occurrence_pct if flood_detail else None,
            flood_wofs_pct=flood_detail.wofs_frequency_pct if flood_detail else None,
        )
        compound_constraints.extend(sat_constraints)

    brief.compound_constraints = compound_constraints

    # ── 10. Staleness detection ─────────────────────────────────────────
    staleness_warnings = detect_staleness(brief)
    if staleness_warnings:
        logger.info("Staleness warnings for %s: %s", req.address, staleness_warnings)

    # ── 11. Confidence summary + gaps + minimum viable check ────────────
    summary = compute_confidence_summary(brief)
    gaps = collect_gaps(brief)

    # Enrich gaps with verify_url and add LGA advisory
    gaps = enrich_gaps_with_verify_url(gaps, dcp_former_council)

    if lga_advisory:
        gaps.append(GapEntry(
            field="lga_validation",
            reason=lga_advisory,
        ))

    if not check_minimum_viable(summary):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Insufficient data available for this address",
                "fields_available": summary.total - summary.not_available,
                "fields_total": summary.total,
                "fields_failed": summary.not_available,
                "gaps": [g.model_dump() for g in gaps],
            },
        )

    # Update brief with computed summary, gaps, and staleness warnings
    brief.confidence_summary = summary
    brief.gaps = gaps
    brief.data_currency_warnings = staleness_warnings

    elapsed = time.monotonic() - start_time
    timing_summary = " | ".join(f"{label}={t:.1f}s/{status}" for label, t, status in timings)
    logger.info(
        "Intelligence brief for %s completed in %.1fs — %d/%d fields available, brief_type=%s | %s",
        req.address, elapsed, summary.total - summary.not_available, summary.total,
        brief.brief_type, timing_summary,
    )

    return brief.model_dump()


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

    Same data sources and assembly logic as run_intelligence_brief, but yields
    each section as soon as its source dependencies are satisfied.

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
    satellite_sections = 6 if req.include_satellite else 0
    total_sections = base_sections + satellite_sections + 3  # +3 for dependent (max estimate)

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

        # Satellite — fire immediately if requested
        f_bushfire = f_flood_sat = f_climate = f_granny = None
        f_uhi = f_arr = f_firms = f_terrain = None

        if req.include_satellite:
            f_bushfire = pool.submit(
                _safe_call,
                lambda: _fetch_bushfire(req.address, lat, lng, str(resolved_prop_id) if resolved_prop_id else None, report_id),
                "bushfire_prescreen", ConfidenceLevel.AUTHORITATIVE,
            )
            f_flood_sat = pool.submit(
                _safe_call,
                lambda: _fetch_flood(req.address, lat, lng, str(resolved_prop_id) if resolved_prop_id else None, report_id),
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
        valuation = valuation_df.value or {"lot_area_m2": None, "land_value": None, "val_base_date": None, "val_history": []}
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
        strata_raw = strata_df.value or {"is_strata": False}
        strata_type = classify_strata(strata_raw, lot_area_m2)
        strata_info = StrataInfo(
            is_strata=strata_raw.get("is_strata", False),
            strata_type=strata_type,
            strata_plan=strata_raw.get("strata_plan"),
            plan_label=strata_raw.get("plan_label"),
            source=strata_raw.get("source"),
            lot_area_m2=lot_area_m2,
        )
        is_apartment = strata_type == StrataType.APARTMENT or strata_type == StrataType.AMBIGUOUS

        # Update total_sections now we know brief type
        if is_apartment:
            total_sections = base_sections + satellite_sections  # no dcp/sepp/neighbourhood
        else:
            total_sections = base_sections + 3 + satellite_sections  # +dcp, sepp, neighbourhood

        sections_yielded += 1
        yield _sse_event("section", {
            "section": "strata", "data": DataField(
                value=strata_info, confidence=ConfidenceLevel.AUTHORITATIVE,
                source="cadastre_strata", as_at=today,
            ).model_dump(),
            "progress": int(sections_yielded / total_sections * 100),
            "brief_type": "renovation" if is_apartment else "development",
        })

        # ── Await portal → submit dependents ─────────────────────────────
        controls_df = _timed_result(f_controls, 15, "planning_portal", timings) if f_controls else DataField(
            value=parse_controls([]), confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal", reason="No prop_id resolved",
        )
        controls = controls_df.value or parse_controls([])

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
            lambda: _fetch_shadow(req.address, resolved_prop_id or 0, lat, lng, height_m),
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

        # ── Yield environmental (overlays + heritage + env sources) ──────
        overlays_df = _timed_result(f_overlays, 10, "postgis_overlays", timings)
        heritage_df = _timed_result(f_heritage, 10, "postgis_heritage", timings)
        mine_sub_df = _timed_result(f_mine_sub, 10, "nsw_spatial_services", timings)
        contam_df = _timed_result(f_contam, 10, "epa_contaminated_sites", timings)
        drinking_df = _timed_result(f_drinking, 10, "sepp_resilience_hazards", timings)

        overlays_data = overlays_df.value or {"overlays": [], "covered_layers": [], "proximity_m": {}}
        heritage_postgis = heritage_df.value
        mine_subsidence_raw = mine_sub_df.value
        contaminated_land_raw = contam_df.value
        drinking_water_raw = drinking_df.value
        lot_geometry_df = _timed_result(f_lot_geometry, 15, "planning_portal_lot", timings) if f_lot_geometry else DataField(
            value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal_lot", reason="No prop_id resolved",
        )
        lot_geometry_raw = lot_geometry_df.value
        contributions_df = _timed_result(f_contributions, 15, "planning_portal_cp", timings) if f_contributions else DataField(
            value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal_cp", reason="No prop_id resolved",
        )

        environmental = _build_environmental(
            controls, overlays_data, heritage_postgis,
            mine_subsidence_raw=mine_subsidence_raw,
            contaminated_land_raw=contaminated_land_raw,
            drinking_water_raw=drinking_water_raw,
        )
        sections_yielded += 1
        yield _sse_event("section", {
            "section": "environmental_constraints",
            "data": environmental.model_dump(),
            "progress": int(sections_yielded / total_sections * 100),
        })

        # ── Yield planning_controls (portal + overlays for fallbacks) ────
        # PostGIS fallbacks
        ov_by_type = {o.get("layer_type"): o for o in overlays_data.get("overlays", [])}
        if not controls.get("ass_class") and "acid_sulfate" in ov_by_type:
            controls["ass_class"] = ov_by_type["acid_sulfate"].get("value") or "Present"
        if not controls.get("lot_size") and "lot_size" in ov_by_type:
            controls["lot_size"] = ov_by_type["lot_size"].get("value")

        planning_controls = _build_planning_controls(controls, overlays_data, lot_geometry_raw)
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
        shadow_df = _timed_result(f_shadow, 20, "shadow_detector", timings)

        dcp_raw = dcp_df.value
        sepp_raw = sepp_df.value or []
        das_raw = das_df.value or []
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
            sepp_lep_overrides = _detect_sepp_lep_overrides(sepp_housing, height_m, sse_lep_fsr)

            sections_yielded += 1
            yield _sse_event("section", {
                "section": "sepp_housing",
                "data": DataField(
                    value=sepp_housing, confidence=ConfidenceLevel.AUTHORITATIVE,
                    source="housing_sepp_standards", as_at=today,
                ).model_dump(),
                "sepp_lep_overrides": [o.model_dump() for o in sepp_lep_overrides],
                "progress": int(sections_yielded / total_sections * 100),
            })

            neighbourhood = _build_neighbourhood(das_raw, shadow_raw)
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "neighbourhood",
                "data": neighbourhood.model_dump(),
                "progress": int(sections_yielded / total_sections * 100),
            })

        # ── Yield satellite sections individually ────────────────────────
        bushfire_raw = flood_raw_sat = climate_raw = granny_flat_raw = pre_da_raw = None
        uhi_raw = arr_raw = firms_raw = None

        if req.include_satellite:
            bushfire_df = _timed_result(f_bushfire, CONFIG.timeout_postgis + 5, "bushfire_prescreen", timings)
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

            flood_sat_df = _timed_result(f_flood_sat, 20, "flood_truth", timings)
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

            climate_df = _timed_result(f_climate, 10, "climate_risk_score", timings)
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

            pre_da_df = _timed_result(f_pre_da, CONFIG.timeout_satellite + 5, "pre_da_history", timings) if f_pre_da else DataField(
                value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                source="pre_da_history", reason="Pre-DA history not requested or not available",
            )
            pre_da_raw = pre_da_df.value
            pre_da_detail = _build_pre_da_detail(pre_da_raw)
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "satellite.pre_da_history",
                "data": DataField(
                    value=pre_da_detail,
                    confidence=ConfidenceLevel.ESTIMATED if pre_da_detail else ConfidenceLevel.NOT_AVAILABLE,
                    source="pre_da_history", as_at=today,
                    reason=None if pre_da_detail else "Pre-DA history not requested or not available",
                ).model_dump(),
                "progress": int(sections_yielded / total_sections * 100),
            })

            terrain_df = _timed_result(f_terrain, CONFIG.timeout_terrain, "terrain_analysis", timings) if f_terrain else DataField(
                value=None, confidence=ConfidenceLevel.NOT_AVAILABLE,
                source="terrain_analysis", reason="Terrain analysis not requested",
            )
            terrain_raw = terrain_df.value
            terrain_detail = _build_terrain_detail(terrain_raw)
            sections_yielded += 1
            yield _sse_event("section", {
                "section": "satellite.terrain",
                "data": DataField(
                    value=terrain_detail,
                    confidence=ConfidenceLevel.ESTIMATED if terrain_detail else ConfidenceLevel.NOT_AVAILABLE,
                    source="terrain_analysis", as_at=today,
                    reason=None if terrain_detail else "Terrain analysis failed or not requested",
                ).model_dump(),
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
            confidence_summary=ConfidenceSummary(),
        )
    else:
        contributions_raw = contributions_df.value
        contributions_field = DataField(
            value=contributions_raw,
            confidence=ConfidenceLevel.AUTHORITATIVE if contributions_raw else ConfidenceLevel.NOT_AVAILABLE,
            source="planning_portal_cp",
            as_at=today,
            reason=None if contributions_raw else "No contributions plans found for this property",
        )
        brief = DevelopmentBrief(
            address=req.address, lat=lat, lng=lng,
            prop_id=resolved_prop_id, run_date=today,
            strata=DataField(value=strata_info, confidence=ConfidenceLevel.AUTHORITATIVE, source="cadastre_strata", as_at=today),
            planning_controls=planning_controls,
            dcp_controls=dcp_controls,
            sepp_housing=DataField(value=sepp_housing, confidence=ConfidenceLevel.AUTHORITATIVE, source="housing_sepp_standards", as_at=today),
            sepp_lep_overrides=sepp_lep_overrides if not is_apartment else [],
            environmental_constraints=environmental,
            neighbourhood=neighbourhood,
            economics=economics,
            contributions=contributions_field,
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
        _generate_brief_sse(req, resolved_prop_id, lat, lng, lot_wkt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
