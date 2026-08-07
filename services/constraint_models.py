"""
Shared Pydantic models used by both constraint_arithmetic and intelligence_brief.

Extracted to break the circular import: constraint_arithmetic imports models that
were defined in intelligence_brief, but intelligence_brief needs to call
compute_constraint_arithmetic and use its result type.

These models are pure data containers — no DB queries, no API calls.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Lot and DCP models (originally in intelligence_brief.py)
# ---------------------------------------------------------------------------


class LotDimensions(BaseModel):
    area_m2: Optional[float] = None
    frontage_m: Optional[float] = None
    depth_m: Optional[float] = None
    is_corner: Optional[bool] = None
    # True when the polygon is too irregular for frontage/depth to be measured
    # (fills <60% of its oriented bounding box) — so a null frontage renders as
    # "can't be measured", not as a broken lookup. None = shape not assessed.
    irregular: Optional[bool] = None
    # Shape classification: 'rectangular' | 'battleaxe' | 'irregular'.
    # None = not assessed (older payloads). Battleaxe (flag) lots carry the
    # handle/head breakdown below — width-based eligibility tests must use the
    # developable HEAD width, not the handle (lot_dimensions.eligibility_lot_width).
    lot_type: Optional[str] = None
    battleaxe_access_way_width_m: Optional[float] = None
    battleaxe_access_way_length_m: Optional[float] = None
    battleaxe_main_lot_width_m: Optional[float] = None
    battleaxe_main_lot_area_m2: Optional[float] = None


class DCPControl(BaseModel):
    """Single DCP control value."""

    control_type: str  # front_setback, rear_setback, etc.
    dev_type: str  # dwelling_house, secondary_dwelling, etc.
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    unit: Optional[str] = None
    condition: Optional[str] = None
    source_ref: Optional[str] = None


class SEPPStandard(BaseModel):
    """SEPP Housing standard for a development type."""

    dev_type: str
    eligible: bool
    min_lot_area_m2: Optional[float] = None
    max_gfa_m2: Optional[float] = None  # Absolute floor area (m²) — secondary_dwelling only
    max_fsr: Optional[float] = None  # FSR ratio — LMR types only (DB: standard_type='max_fsr')
    max_height_m: Optional[float] = None
    setback_front_m: Optional[float] = None
    setback_rear_m: Optional[float] = None
    setback_side_m: Optional[float] = None
    reason_ineligible: Optional[str] = None
    # Secondary dwelling extended standards (migration 047)
    min_lot_width_m: Optional[float] = None
    parking_spaces: Optional[float] = None
    min_private_open_space_m2: Optional[float] = None
    max_site_coverage_pct: Optional[float] = None
    max_total_floor_area_m2: Optional[float] = None
    # All raw standards for dev types with non-standard fields
    additional_standards: Optional[dict[str, float]] = None
    # Citations of the rows granting the height/FSR standards — carried so a
    # SEPP-over-LEP override can cite the clause it rests on (no citation, no claim).
    height_source_clause: Optional[str] = None
    fsr_source_clause: Optional[str] = None
    source_document: Optional[str] = None


class SeppLepOverride(BaseModel):
    """Case where SEPP standard exceeds (overrides) the LEP control."""

    dev_type: str
    control: str  # "height" or "fsr"
    lep_value: float
    sepp_value: float
    source_clause: Optional[str] = None
    note: str = "SEPP standard exceeds LEP control — SEPP prevails where more generous"


class ShadowScenario(BaseModel):
    """Shadow analysis for a single sun position."""

    date_label: str  # "Jun 21 (winter solstice)"
    time_label: str  # "9:00 AM", "12:00 PM", "3:00 PM"
    shadow_length_m: Optional[float] = None
    overlap_pct: Optional[float] = None
    shadow_direction_deg: Optional[float] = None  # compass bearing the shadow falls toward (opposite of sun azimuth)
    overlaps_subject_lot: Optional[bool] = None
    # "computed" | "unavailable". Absent on rows written before the typed-absence
    # fix, which were all computed. Carried to the surface DELIBERATELY: without
    # it every measurement field is simply null and the page renders three em
    # dashes, which a reader skims as "nothing to worry about" rather than "we
    # have no answer".
    status: Optional[str] = None
    error_note: Optional[str] = None


class ShadowResult(BaseModel):
    """Geometric shadow analysis result."""

    height_m: Optional[float] = None
    height_source: Optional[str] = None
    adg_compliant: Optional[bool] = None
    scenarios: list[ShadowScenario] = []
    worst_case_scenario: Optional[str] = None
    # Run-level confidence from the shadow service ("low" when the height fell
    # back to the two-storey default).
    confidence: Optional[str] = None
    temporal_caveat: str = (
        "Shadow analysis reflects the height control mapped at this property "
        "only. The modelled building north of the lot is an offset rectangle, "
        "not the neighbouring parcel, and approved or pending development "
        "applications are not accounted for."
    )


# ---------------------------------------------------------------------------
# Constraint arithmetic result models (originally in constraint_arithmetic.py)
# ---------------------------------------------------------------------------


class ConstraintType(str, Enum):
    """The types of constraint that can be binding."""

    LEP_HEIGHT = "lep_height"
    LEP_FSR = "lep_fsr"
    DCP_SETBACKS = "dcp_setbacks"
    DCP_SITE_COVERAGE = "dcp_site_coverage"
    DCP_LANDSCAPING = "dcp_landscaping"
    DCP_DEEP_SOIL = "dcp_deep_soil"
    SHADOW_ACCESS = "shadow_access"
    PARKING = "parking"
    LOT_SIZE = "lot_size"
    SEPP_OVERRIDE = "sepp_override"


class ConstraintStep(BaseModel):
    """One step in the constraint arithmetic chain."""

    constraint: ConstraintType
    label: str
    # "lep"  — establishes the maximum envelope (FSR vs height ALTERNATIVES, not a
    #          subtraction); the headline is min(FSR cap, height cap).
    # "dcp"  — the indicative after-council erosion (a reconciling GFA/footprint chain).
    # Phases are displayed as two separate ledgers, never summed together.
    phase: Optional[str] = None
    input_gfa_m2: Optional[float] = None
    reduction_m2: Optional[float] = None
    output_gfa_m2: Optional[float] = None
    footprint_m2: Optional[float] = None
    note: str = ""


class ConstraintArithmeticResult(BaseModel):
    """Full result of constraint arithmetic computation."""

    # Inputs echoed back
    lot_area_m2: float
    dev_type: str
    lep_height_m: Optional[float] = None
    lep_fsr: Optional[float] = None

    # LEP envelope
    lep_max_gfa_from_fsr_m2: Optional[float] = None
    lep_max_storeys: Optional[int] = None
    lep_max_gfa_from_height_m2: Optional[float] = None
    lep_envelope_gfa_m2: Optional[float] = None  # min of FSR and height paths

    # DCP erosion
    buildable_footprint_m2: Optional[float] = None
    setback_front_m: Optional[float] = None
    setback_rear_m: Optional[float] = None
    setback_side_m: Optional[float] = None
    site_coverage_cap_m2: Optional[float] = None
    landscaping_reduction_m2: Optional[float] = None

    # SEPP override
    sepp_overrides_applied: list[SeppLepOverride] = []
    effective_height_m: Optional[float] = None
    effective_fsr: Optional[float] = None

    # Shadow
    shadow_storey_reduction: int = 0

    # Parking
    parking_spaces_required: Optional[float] = None
    parking_gfa_consumed_m2: Optional[float] = None

    # Final outputs
    # realistic_gfa_m2 = the LEP envelope (FSR cap vs height-as-storeys) — the
    # reliable headline figure. dcp_adjusted_gfa_m2 = the same envelope after DCP
    # setbacks/landscaping/site-coverage/shadow/parking erosion — a SECONDARY
    # figure, populated only when lot geometry is reliable enough to trust it.
    realistic_gfa_m2: Optional[float] = None
    dcp_adjusted_gfa_m2: Optional[float] = None
    realistic_dwellings: Optional[int] = None

    # Dwelling-yield RANGE (the count is a derived illustration of the GFA envelope,
    # not a single committed number). as_of_right_* = the conservative, always-true
    # baseline (a single dwelling unless the floor is later lifted by Housing-SEPP/LMR
    # as-of-right rights). max_permitted_* = the densest permitted form bounded by the
    # zone tier, i.e. the realistic upside SUBJECT TO a development application. The two
    # bracket the honest answer; never present the ceiling as achievable without a DA.
    as_of_right_form: Optional[str] = None
    as_of_right_dwellings: Optional[int] = None
    max_permitted_form: Optional[str] = None
    max_permitted_dwellings: Optional[int] = None

    # True when the ceiling form was raised above the base zone tier by the
    # Housing-SEPP / Low-and-Mid-Rise uplift (so the card can attribute it).
    ceiling_from_lmr: bool = False
    # Citation for that LMR uplift (from housing_sepp_standards) — set only when
    # ceiling_from_lmr AND a real clause exists. The card shows the LMR note ONLY
    # when this clause is present: no citation -> no claim.
    lmr_source_clause: Optional[str] = None
    lmr_source_document: Optional[str] = None
    lmr_legislation_url: Optional[str] = None
    lmr_effective_date: Optional[str] = None

    binding_constraint: Optional[ConstraintType] = None
    binding_constraint_label: str = ""

    # Full chain for transparency
    steps: list[ConstraintStep] = []

    # Data gaps that limited computation
    gaps: list[str] = []
    confidence: str = "low"  # low / medium / high based on data completeness

    disclaimer: str = (
        "Constraint arithmetic is a preliminary computational estimate only. "
        "It does not account for merit-based assessment, clause variations, or "
        "council-specific interpretation. Engage a qualified town planner for "
        "site-specific assessment."
    )
