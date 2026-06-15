"""
Exempt Development Screening Calculator — classifies detected structures
against Codes SEPP exempt thresholds with +-30% uncertainty margin.

Critical prerequisite for Product B: without this, every 'no matching
approval' flag could be a false alarm on a perfectly legal exempt
structure (shed, deck, pergola, carport).

See TIER1_BUILD_SPEC.md §3, §A1.6, §A1.7.
Thresholds are sourced at runtime from the database — NEVER hardcoded.
"""
import logging
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Uncertainty margins (from QA validation — Phase 3 test 3.4)
# ---------------------------------------------------------------------------

SAMGEO_AREA_UNCERTAINTY = 0.30   # +-30% based on validation (7/11 correct)
SAMGEO_HEIGHT_UNCERTAINTY = 1.0  # +-1m for DEM-derived height estimates


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ExemptCategory(str, Enum):
    GARDEN_SHED = "garden_shed"
    DECK = "deck"
    PERGOLA = "pergola"
    CARPORT = "carport"
    FENCE = "fence"
    POOL = "pool"
    OTHER = "other"


class ExemptThresholds(BaseModel):
    """Thresholds from authoritative source (DB or API). Never hardcoded."""
    category: ExemptCategory
    max_area_m2: Optional[float] = None
    max_height_m: Optional[float] = None
    min_setback_m: Optional[float] = None
    source_ref: str = ""
    effective_date: Optional[str] = None


class ExemptScreenResult(BaseModel):
    classification: Literal["LIKELY_EXEMPT", "APPROVAL_GAP", "INDETERMINATE"]
    category_tested: ExemptCategory
    area_m2: float
    height_m: Optional[float] = None
    boundary_distance_m: Optional[float] = None
    thresholds_checked: dict = {}
    thresholds_exceeded: list[str] = []
    confidence: Literal["high", "medium", "low"] = "low"
    notes: list[str] = []


class StructureScreenResult(BaseModel):
    structure_area_m2: float
    structure_height_m: Optional[float] = None
    exempt_screen: ExemptScreenResult
    matching_approval_pan: Optional[str] = None
    final_classification: Literal[
        "APPROVAL_LOCATED",
        "LIKELY_EXEMPT",
        "APPROVAL_GAP",
        "INDETERMINATE",
    ]
    consumer_summary: str


# ---------------------------------------------------------------------------
# Core classification logic
# ---------------------------------------------------------------------------

def classify_with_uncertainty(
    measured_area_m2: float,
    threshold_area_m2: Optional[float],
    measured_height_m: Optional[float] = None,
    threshold_height_m: Optional[float] = None,
    measured_setback_m: Optional[float] = None,
    threshold_setback_m: Optional[float] = None,
) -> tuple[Literal["LIKELY_EXEMPT", "APPROVAL_GAP", "INDETERMINATE"], list[str], list[str]]:
    """Classify a structure against thresholds with uncertainty margins.

    Returns (classification, thresholds_exceeded, notes).

    Conservative by design: minimises false accusations.
    """
    exceeded: list[str] = []
    notes: list[str] = []

    # --- Area check ---
    if threshold_area_m2 is not None:
        area_margin = measured_area_m2 * SAMGEO_AREA_UNCERTAINTY
        if measured_area_m2 + area_margin < threshold_area_m2:
            pass  # Clearly under
        elif measured_area_m2 - area_margin > threshold_area_m2:
            exceeded.append("max_area_m2")
            notes.append(
                f"Estimated area {measured_area_m2:.0f}m\u00b2 exceeds "
                f"{threshold_area_m2:.0f}m\u00b2 threshold (measurement accuracy \u00b130%)"
            )
        else:
            notes.append(
                f"Estimated area {measured_area_m2:.0f}m\u00b2 is near "
                f"{threshold_area_m2:.0f}m\u00b2 threshold (within measurement uncertainty)"
            )
            return "INDETERMINATE", [], notes

    # --- Height check ---
    if measured_height_m is not None and threshold_height_m is not None:
        if measured_height_m + SAMGEO_HEIGHT_UNCERTAINTY < threshold_height_m:
            pass  # Clearly under
        elif measured_height_m - SAMGEO_HEIGHT_UNCERTAINTY > threshold_height_m:
            exceeded.append("max_height_m")
            notes.append(
                f"Estimated height {measured_height_m:.1f}m exceeds "
                f"{threshold_height_m:.1f}m threshold (\u00b11m accuracy)"
            )
        else:
            notes.append(
                f"Estimated height {measured_height_m:.1f}m is near "
                f"{threshold_height_m:.1f}m threshold (within measurement uncertainty)"
            )
            if not exceeded:
                return "INDETERMINATE", [], notes
    elif threshold_height_m is not None and measured_height_m is None:
        notes.append("Height could not be estimated from available elevation data")
        if not exceeded:
            return "INDETERMINATE", [], notes

    # --- Setback check ---
    if measured_setback_m is not None and threshold_setback_m is not None:
        if measured_setback_m < threshold_setback_m:
            exceeded.append("min_setback_m")
            notes.append(
                f"Estimated setback {measured_setback_m:.1f}m is less than "
                f"{threshold_setback_m:.1f}m minimum"
            )

    # --- Final classification ---
    if exceeded:
        return "APPROVAL_GAP", exceeded, notes
    return "LIKELY_EXEMPT", [], notes


def screen_structure_exempt(
    area_m2: float,
    thresholds: ExemptThresholds,
    height_m: Optional[float] = None,
    boundary_distance_m: Optional[float] = None,
) -> ExemptScreenResult:
    """Screen a single structure against exempt development thresholds.

    Thresholds MUST be sourced from the database or API — never hardcoded.
    """
    classification, exceeded, notes = classify_with_uncertainty(
        measured_area_m2=area_m2,
        threshold_area_m2=thresholds.max_area_m2,
        measured_height_m=height_m,
        threshold_height_m=thresholds.max_height_m,
        measured_setback_m=boundary_distance_m,
        threshold_setback_m=thresholds.min_setback_m,
    )

    has_height = height_m is not None
    has_setback = boundary_distance_m is not None
    if has_height and has_setback:
        confidence = "high"
    elif has_height or has_setback:
        confidence = "medium"
    else:
        confidence = "low"

    thresholds_dict = {}
    if thresholds.max_area_m2 is not None:
        thresholds_dict["max_area_m2"] = thresholds.max_area_m2
    if thresholds.max_height_m is not None:
        thresholds_dict["max_height_m"] = thresholds.max_height_m
    if thresholds.min_setback_m is not None:
        thresholds_dict["min_setback_m"] = thresholds.min_setback_m

    return ExemptScreenResult(
        classification=classification,
        category_tested=thresholds.category,
        area_m2=area_m2,
        height_m=height_m,
        boundary_distance_m=boundary_distance_m,
        thresholds_checked=thresholds_dict,
        thresholds_exceeded=exceeded,
        confidence=confidence,
        notes=notes,
    )


def classify_approval_gap(
    structure_area_m2: Optional[float],
    da_outcome: Optional[str],
    exempt_classification: Optional[str],
) -> str:
    """Full approval gap classifier — the decision tree from QA Phase 3.

    Returns: APPROVAL_LOCATED | LIKELY_EXEMPT | APPROVAL_GAP | INDETERMINATE | DATA_INSUFFICIENT
    """
    if structure_area_m2 is None:
        return "DATA_INSUFFICIENT"

    if da_outcome is not None:
        return "APPROVAL_LOCATED"

    if exempt_classification == "LIKELY_EXEMPT":
        return "LIKELY_EXEMPT"
    elif exempt_classification == "APPROVAL_GAP":
        return "APPROVAL_GAP"
    elif exempt_classification == "INDETERMINATE":
        return "INDETERMINATE"
    else:
        return "DATA_INSUFFICIENT"


def make_consumer_summary(
    classification: str,
    area_m2: Optional[float] = None,
    pan: Optional[str] = None,
    determined_date: Optional[str] = None,
    outcome: Optional[str] = None,
) -> str:
    """Generate factual consumer-facing summary. No banned liability words."""
    if classification == "APPROVAL_LOCATED":
        parts = ["A development application"]
        if pan:
            parts[0] = f"A development application ({pan}"
            if outcome:
                parts[0] += f", {outcome.lower()}"
            if determined_date:
                parts[0] += f" {determined_date}"
            parts[0] += ")"
        parts.append("was found matching this structure.")
        return " ".join(parts)

    if classification == "LIKELY_EXEMPT":
        area_str = f" ({area_m2:.0f}m\u00b2)" if area_m2 else ""
        return (
            f"This structure's estimated dimensions{area_str} fall within the "
            f"exempt development thresholds. No development application was "
            f"required based on these dimensions."
        )

    if classification == "APPROVAL_GAP":
        area_str = f" (estimated {area_m2:.0f}m\u00b2)" if area_m2 else ""
        return (
            f"This structure{area_str} exceeds exempt development limits, "
            f"and no matching application was found on the public register "
            f"(records from ~2019 onward). This does not indicate "
            f"non-compliance \u2014 the structure may predate digital records or "
            f"may have received consent under a different reference. "
            f"A council Building Information Certificate (s6.26) can confirm."
        )

    if classification == "INDETERMINATE":
        return (
            "A structure was detected with estimated dimensions near the "
            "exempt development thresholds (measurement accuracy \u00b130%). "
            "A council Building Information Certificate search can confirm "
            "whether development consent was required."
        )

    return "Insufficient data to assess. No assessment was generated."
