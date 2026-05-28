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

import logging
import re
import time
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Generic, Literal, Optional, TypeVar

from fastapi import APIRouter, HTTPException
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

    # NSW bounding box (WGS84)
    nsw_lat_min: float = -37.5
    nsw_lat_max: float = -28.0
    nsw_lng_min: float = 140.9
    nsw_lng_max: float = 153.7

    # Search parameters
    da_radius_m: int = 200
    da_lookback_days: int = 365

    # Concurrency
    max_parallel_sources: int = 6

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


class LotDimensions(BaseModel):
    area_m2: Optional[float] = None
    frontage_m: Optional[float] = None
    depth_m: Optional[float] = None
    is_corner: Optional[bool] = None


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


class DCPControl(BaseModel):
    """Single DCP control value."""

    control_type: str  # front_setback, rear_setback, etc.
    dev_type: str  # dwelling_house, secondary_dwelling, etc.
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    unit: Optional[str] = None
    condition: Optional[str] = None
    source_ref: Optional[str] = None


class DCPControls(BaseModel):
    """DCP setback and development controls."""

    controls: DataField[list[DCPControl]]
    dcp_name: DataField[Optional[str]]
    dcp_url: DataField[Optional[str]]
    section_ref: DataField[Optional[str]]


class SEPPStandard(BaseModel):
    """SEPP Housing standard for a development type."""

    dev_type: str
    eligible: bool
    min_lot_area_m2: Optional[float] = None
    max_gfa_m2: Optional[float] = None
    max_height_m: Optional[float] = None
    setback_front_m: Optional[float] = None
    setback_rear_m: Optional[float] = None
    setback_side_m: Optional[float] = None
    reason_ineligible: Optional[str] = None


class ShadowScenario(BaseModel):
    """Shadow analysis for a single sun position."""

    date_label: str  # "Jun 21 (winter solstice)"
    time_label: str  # "9:00 AM", "12:00 PM", "3:00 PM"
    sun_altitude_deg: Optional[float] = None
    sun_azimuth_deg: Optional[float] = None
    shadow_length_m: Optional[float] = None
    overlap_pct: Optional[float] = None


class ShadowResult(BaseModel):
    """Geometric shadow analysis result."""

    height_m: Optional[float] = None
    height_source: Optional[str] = None
    adg_compliant: Optional[bool] = None
    scenarios: list[ShadowScenario] = []
    worst_case_scenario: Optional[str] = None
    temporal_caveat: str = (
        "Shadow analysis reflects current height controls only. "
        "Does not account for approved or pending development applications "
        "on adjacent lots."
    )


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
    """Environmental risk layers from PostGIS + portal."""

    flood_epi: DataField[bool]
    overlays: DataField[list[EnvironmentalOverlay]]
    overlay_coverage: DataField[list[str]]  # layer types ingested for this LGA
    bushfire_designation: DataField[Optional[str]]  # from portal SEPP overlay
    heritage_postgis: DataField[Optional[dict]]  # PostGIS heritage near lot


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
    environmental_constraints: EnvironmentalConstraints
    neighbourhood: Neighbourhood
    economics: Economics
    compound_constraints: list[CompoundConstraint] = []
    gaps: list[GapEntry] = []
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
    compound_constraints: list[CompoundConstraint] = []
    gaps: list[GapEntry] = []
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
# Router placeholder — Stage 2 will fill this in
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/pipeline", tags=["intelligence"])
