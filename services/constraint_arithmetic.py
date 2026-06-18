"""
Constraint Arithmetic Engine — binding constraint identification and realistic yield.

Takes a DevelopmentBrief (or its components) and computes:
1. LEP envelope (height → storeys → footprint × storeys = max GFA from height; FSR × lot = max GFA from FSR)
2. DCP erosion (setbacks reduce buildable footprint, site coverage caps it, landscaping removes more)
3. Shadow plane reduction (worst-case shadow overlap may cut top storey on north side)
4. SEPP override application (where SEPP height/FSR > LEP, use SEPP values)
5. Parking consumption (parking spaces × area per space consumed from GFA or as additional cost)
6. Binding constraint identification — which single constraint most limits yield
7. Realistic yield — actual dwelling count after all constraints applied

All inputs come from existing DevelopmentBrief models.  No database queries, no API calls.
Pure arithmetic on structured data already collected by the intelligence brief pipeline.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from services.intelligence_brief import DevelopmentBrief

from fastapi import APIRouter
from pydantic import BaseModel

from services.constraint_models import (
    ConstraintArithmeticResult,
    ConstraintStep,
    ConstraintType,
    DCPControl,
    LotDimensions,
    SEPPStandard,
    SeppLepOverride,
    ShadowResult,
)

router = APIRouter(tags=["constraint-arithmetic"])


# ---------------------------------------------------------------------------
# Constants — geometry defaults (not regulatory data, just arithmetic)
# ---------------------------------------------------------------------------

# Assumed storey height for converting height limit to storey count.
# Standard residential: 3.0m floor-to-floor (inc. slab).
STOREY_HEIGHT_M = 3.0

# Minimum dwelling GFA for yield calculation (m²).
# Based on ADG minimums: studio 35m², 1-bed 50m², 2-bed 70m².
# Use 65m² as a blended average for small-medium dwellings.
MIN_DWELLING_GFA_M2 = 65.0

# Common corridor / circulation factor — proportion of gross floor area
# consumed by stairs, lifts, corridors, plant rooms.
# Single dwelling / dual occ: ~0% (direct entry).  Apartments: ~15-20%.
CIRCULATION_FACTOR_APARTMENT = 0.18
CIRCULATION_FACTOR_HOUSE = 0.0

# Parking area per space (m² of floor area consumed if at-grade/undercroft).
# Typical: 30m² per space including access aisle.
PARKING_AREA_PER_SPACE_M2 = 30.0

# Shadow — continuous reduction parameters.
# Below MIN: no reduction.  Above MAX: full half-storey cut.
# Between MIN and MAX: linear interpolation.
SHADOW_OVERLAP_MIN = 0.20   # below 20% overlap — minor, no reduction
SHADOW_OVERLAP_MAX = 0.60   # at 60%+ overlap — full half-storey north-side cut
# Legacy threshold kept for backwards compat in tests referencing it.
SHADOW_OVERLAP_THRESHOLD = 0.40


# ---------------------------------------------------------------------------
# Enums and response models
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_numeric(val: Optional[str]) -> Optional[float]:
    """Parse a string like '11' or '0.75:1' or '9m' to a float."""
    if val is None:
        return None
    s = str(val).strip().lower()
    # Remove units
    for suffix in ("m", "m²", "sqm", ":1"):
        s = s.replace(suffix, "")
    s = s.strip()
    if not s:
        return None
    # s is guaranteed non-None and non-empty at this point
    if s is not None:
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _get_dcp_value(
    controls: list[DCPControl],
    control_type: str,
    dev_type: str,
    prefer_max: bool = False,
) -> Optional[float]:
    """Find the DCP control value for a given type and dev_type.

    Matches exact dev_type first, then falls back to 'dwelling_house'.

    By default returns value_min (the minimum requirement — correct for setbacks,
    landscaping, deep soil). For CAP controls (e.g. max_site_coverage), the limit
    is stored in value_max, so pass ``prefer_max=True`` — otherwise the cap is
    read as value_min (usually None) and silently dropped (GATE-3). ``prefer_max``
    falls back to value_min when value_max is absent.
    """
    exact = None
    fallback = None
    for c in controls:
        if c.control_type != control_type:
            continue
        if c.dev_type == dev_type:
            exact = c
        elif c.dev_type == "dwelling_house" and fallback is None:
            fallback = c
    match = exact or fallback
    if match is None:
        return None
    if prefer_max:
        return match.value_max if match.value_max is not None else match.value_min
    return match.value_min


def _dcp_controls_from_setback_rows(
    rows: list[dict],
    clause_ref: Optional[str] = None,
) -> list[DCPControl]:
    """Convert ``fetch_dcp_setbacks()`` row dicts into typed ``DCPControl`` objects.

    The control type is taken from ``semantic_type`` (the real control —
    ``front_setback``, ``rear_setback``, ``side_setback``, ...), NOT the
    ``prescribed`` / ``site_derived`` *kind*, so downstream setback lookups in
    :func:`_get_dcp_value` match. This is the seam where an untyped setback would
    silently fail to feed the footprint calc, so it is covered by a regression
    test (``tests/test_setback_taxonomy.py``).

    ``requirement`` may be free text; it is coerced to a number or kept as the
    ``condition`` (never forced into the float ``value_min`` field).

    Args:
        rows: setback row dicts as returned by ``fetch_dcp_setbacks`` (the
            ``setbacks`` + ``sd_setbacks`` lists).
        clause_ref: fallback clause reference when a row has no ``clause``.

    Returns:
        One ``DCPControl`` per input row, preserving order.
    """
    controls: list[DCPControl] = []
    for s in rows:
        raw_min = s.get("value_min")
        if raw_min is None:
            raw_min = s.get("requirement")
        val_min = _parse_numeric(raw_min)
        condition = s.get("notes") or s.get("condition")
        if val_min is None and isinstance(raw_min, str) and raw_min.strip():
            condition = condition or raw_min.strip()
        controls.append(DCPControl(
            control_type=s.get("semantic_type") or s.get("control_type") or s.get("type", ""),
            dev_type=s.get("dev_type", "dwelling_house"),
            value_min=val_min,
            value_max=_parse_numeric(s.get("value_max")),
            unit=s.get("unit", "m"),
            condition=condition,
            source_ref=s.get("clause") or clause_ref,
        ))
    return controls


def _estimate_lot_dimensions(
    lot_dims: Optional[LotDimensions],
    lot_area_m2: float,
) -> tuple[float, float]:
    """Return (frontage_m, depth_m) — use actual dimensions or estimate from area.

    Estimation assumes a 1:2.5 frontage:depth ratio (typical suburban lot).
    """
    if lot_dims and lot_dims.frontage_m and lot_dims.depth_m:
        return (lot_dims.frontage_m, lot_dims.depth_m)
    if lot_dims and lot_dims.frontage_m:
        return (lot_dims.frontage_m, lot_area_m2 / lot_dims.frontage_m)
    if lot_dims and lot_dims.depth_m:
        return (lot_area_m2 / lot_dims.depth_m, lot_dims.depth_m)
    # Estimate: frontage = sqrt(area / 2.5), depth = 2.5 x frontage
    if lot_area_m2 <= 0:
        return (0.0, 0.0)
    frontage = math.sqrt(lot_area_m2 / 2.5)
    depth = lot_area_m2 / frontage
    return (frontage, depth)


def _is_apartment_type(dev_type: str) -> bool:
    """Determine if a development type involves apartments (multi-storey shared circulation)."""
    apartment_keywords = (
        "apartment", "residential_flat", "multi_dwelling", "shop_top",
        "mixed_use", "boarding_house",
    )
    return any(kw in dev_type.lower() for kw in apartment_keywords)


def _dwellings_for_form(dev_type: str, gfa_based: int) -> int:
    """Dwelling yield must respect the permitted built FORM, not just GFA (GATE-1).

    By the Standard Instrument a *dwelling house* is ONE dwelling regardless of how
    much GFA the envelope allows; a *dual occupancy* is two. Only multi-unit forms
    (multi-dwelling housing, residential flat buildings, apartments, terraces /
    townhouses, manor houses, medium-density) scale their dwelling count with GFA.
    Unknown / single forms default to 1 — conservative, never over-reporting a
    yield the built form does not permit (this is what produced "6 dwellings" for a
    dwelling_house on R2).
    """
    dt = (dev_type or "").lower()
    if (_is_apartment_type(dt) or "townhouse" in dt or "terrace" in dt
            or "attached" in dt or "manor" in dt or "medium_density" in dt):
        return max(1, gfa_based)
    if "dual" in dt:        # dual occupancy
        return 2
    if "secondary" in dt:   # primary dwelling + secondary dwelling
        return 2
    return 1                # dwelling house / single / unknown


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------


def compute_constraint_arithmetic(
    *,
    lot_area_m2: float,
    dev_type: str,
    ceiling_dev_type: Optional[str] = None,
    lep_height_str: Optional[str] = None,
    lep_fsr_str: Optional[str] = None,
    lot_dimensions: Optional[LotDimensions] = None,
    dcp_controls: Optional[list[DCPControl]] = None,
    sepp_standards: Optional[list[SEPPStandard]] = None,
    sepp_lep_overrides: Optional[list[SeppLepOverride]] = None,
    shadow_result: Optional[ShadowResult] = None,
) -> ConstraintArithmeticResult:
    """Compute constraint arithmetic chain.

    Pure function — no side effects, no I/O.
    All inputs are pre-fetched structured data from the intelligence brief pipeline.
    """
    steps: list[ConstraintStep] = []
    gaps: list[str] = []
    dcp_controls = dcp_controls or []

    result = ConstraintArithmeticResult(
        lot_area_m2=lot_area_m2,
        dev_type=dev_type,
    )

    # -----------------------------------------------------------------------
    # Step 0: Parse LEP controls
    # -----------------------------------------------------------------------
    lep_height_m = _parse_numeric(lep_height_str)
    lep_fsr = _parse_numeric(lep_fsr_str)
    result.lep_height_m = lep_height_m
    result.lep_fsr = lep_fsr

    if lep_height_m is None:
        gaps.append("LEP height limit not available — cannot compute height envelope")
    if lep_fsr is None:
        gaps.append("LEP FSR not available — cannot compute FSR envelope")

    # -----------------------------------------------------------------------
    # Step 1: Apply SEPP overrides (before envelope calculation)
    # -----------------------------------------------------------------------
    effective_height_m = lep_height_m
    effective_fsr = lep_fsr
    applied_overrides: list[SeppLepOverride] = []

    if sepp_lep_overrides:
        for ovr in sepp_lep_overrides:
            # GATE-2b: an override applies ONLY to the form it belongs to. The old
            # `or not applied_overrides` fallback applied the first override (often
            # an LMR form bonus, e.g. dual-occ/manor 9.5m) to ANY dev_type — so a
            # dwelling_house wrongly inherited a 7/8.5m -> 9.5m / 3-storey uplift.
            if ovr.dev_type == dev_type:
                if ovr.control == "height" and effective_height_m is not None:
                    if ovr.sepp_value > effective_height_m:
                        effective_height_m = ovr.sepp_value
                        applied_overrides.append(ovr)
                elif ovr.control == "fsr" and effective_fsr is not None:
                    if ovr.sepp_value > effective_fsr:
                        effective_fsr = ovr.sepp_value
                        applied_overrides.append(ovr)

    result.effective_height_m = effective_height_m
    result.effective_fsr = effective_fsr
    result.sepp_overrides_applied = applied_overrides

    if applied_overrides:
        for ovr in applied_overrides:
            steps.append(ConstraintStep(
                constraint=ConstraintType.SEPP_OVERRIDE,
                label=f"SEPP overrides LEP {ovr.control}",
                note=(
                    f"SEPP {ovr.control} {ovr.sepp_value} > LEP {ovr.lep_value} "
                    f"for {ovr.dev_type} — SEPP prevails"
                ),
            ))

    # -----------------------------------------------------------------------
    # Step 2: LEP envelope — FSR path
    # -----------------------------------------------------------------------
    gfa_from_fsr: Optional[float] = None
    if effective_fsr is not None:
        gfa_from_fsr = effective_fsr * lot_area_m2
        result.lep_max_gfa_from_fsr_m2 = round(gfa_from_fsr, 1)
        steps.append(ConstraintStep(
            constraint=ConstraintType.LEP_FSR,
            label="LEP FSR envelope",
            output_gfa_m2=round(gfa_from_fsr, 1),
            note=f"FSR {effective_fsr} x {lot_area_m2}m2 lot = {gfa_from_fsr:.1f}m2 max GFA",
        ))

    # -----------------------------------------------------------------------
    # Step 3: LEP envelope — height path
    # -----------------------------------------------------------------------
    gfa_from_height: Optional[float] = None
    max_storeys: Optional[int] = None

    if effective_height_m is not None:
        max_storeys = max(1, int(effective_height_m / STOREY_HEIGHT_M))
        result.lep_max_storeys = max_storeys

        # Height-path GFA depends on buildable footprint (after setbacks).
        # We compute this AFTER setback erosion below, but need storeys now.
        # Store for later combination.

        steps.append(ConstraintStep(
            constraint=ConstraintType.LEP_HEIGHT,
            label="LEP height envelope",
            note=f"{effective_height_m}m ÷ {STOREY_HEIGHT_M}m/storey = {max_storeys} storeys",
        ))

    # -----------------------------------------------------------------------
    # Step 4: DCP setback erosion → buildable footprint
    # -----------------------------------------------------------------------
    frontage_m, depth_m = _estimate_lot_dimensions(lot_dimensions, lot_area_m2)
    has_dimensions = (
        lot_dimensions is not None
        and lot_dimensions.frontage_m is not None
        and lot_dimensions.depth_m is not None
    )

    front_setback = _get_dcp_value(dcp_controls, "front_setback", dev_type)
    rear_setback = _get_dcp_value(dcp_controls, "rear_setback", dev_type)
    side_setback = _get_dcp_value(dcp_controls, "side_setback", dev_type)

    result.setback_front_m = front_setback
    result.setback_rear_m = rear_setback
    result.setback_side_m = side_setback

    if front_setback is not None or rear_setback is not None or side_setback is not None:
        effective_front = front_setback or 0.0
        effective_rear = rear_setback or 0.0
        effective_side = side_setback or 0.0

        buildable_width = max(0.0, frontage_m - 2 * effective_side)
        buildable_depth = max(0.0, depth_m - effective_front - effective_rear)
        buildable_footprint = buildable_width * buildable_depth
        result.buildable_footprint_m2 = round(buildable_footprint, 1)

        if not has_dimensions:
            gaps.append(
                "Lot dimensions estimated from area (1:2.5 ratio) — "
                "actual setback erosion may differ"
            )

        steps.append(ConstraintStep(
            constraint=ConstraintType.DCP_SETBACKS,
            label="DCP setback erosion",
            footprint_m2=round(buildable_footprint, 1),
            note=(
                f"Lot {frontage_m:.1f}m x {depth_m:.1f}m -> "
                f"setbacks F:{effective_front}m R:{effective_rear}m S:{effective_side}m -> "
                f"buildable {buildable_width:.1f}m x {buildable_depth:.1f}m = "
                f"{buildable_footprint:.1f}m2"
            ),
        ))
    else:
        # No setback data — use lot area as footprint (conservative: no erosion)
        buildable_footprint = lot_area_m2
        result.buildable_footprint_m2 = round(buildable_footprint, 1)
        gaps.append("No DCP setback controls available — footprint not reduced")

    # -----------------------------------------------------------------------
    # Step 5: DCP site coverage cap
    # -----------------------------------------------------------------------
    # max_site_coverage is a CAP — its limit is in value_max, not value_min.
    site_coverage_pct = _get_dcp_value(dcp_controls, "max_site_coverage", dev_type, prefer_max=True)

    # Also check SEPP max_site_coverage_pct for the dev type
    sepp_coverage_pct: Optional[float] = None
    if sepp_standards:
        for std in sepp_standards:
            if std.dev_type == dev_type and std.max_site_coverage_pct is not None:
                sepp_coverage_pct = std.max_site_coverage_pct
                break

    effective_coverage_pct = site_coverage_pct or sepp_coverage_pct
    if effective_coverage_pct is not None:
        coverage_cap = lot_area_m2 * (effective_coverage_pct / 100.0)
        result.site_coverage_cap_m2 = round(coverage_cap, 1)
        if coverage_cap < buildable_footprint:
            steps.append(ConstraintStep(
                constraint=ConstraintType.DCP_SITE_COVERAGE,
                label="Site coverage cap",
                footprint_m2=round(coverage_cap, 1),
                note=(
                    f"{effective_coverage_pct}% of {lot_area_m2}m2 = {coverage_cap:.1f}m2 cap. "
                    f"Reduces footprint from {buildable_footprint:.1f}m2"
                ),
            ))
            buildable_footprint = coverage_cap

    # -----------------------------------------------------------------------
    # Step 6: DCP landscaping / deep soil reduction
    # -----------------------------------------------------------------------
    landscaping_pct = _get_dcp_value(dcp_controls, "landscaping_min", dev_type)
    deep_soil_pct = _get_dcp_value(dcp_controls, "deep_soil_min", dev_type)

    # Landscaping and deep soil overlap — take the larger requirement.
    # Both reduce the site area available for building.
    landscape_reduction_m2 = 0.0
    if landscaping_pct is not None:
        landscape_area = lot_area_m2 * (landscaping_pct / 100.0)
        landscape_reduction_m2 = max(landscape_reduction_m2, landscape_area)
    if deep_soil_pct is not None:
        deep_soil_area = lot_area_m2 * (deep_soil_pct / 100.0)
        landscape_reduction_m2 = max(landscape_reduction_m2, deep_soil_area)

    if landscape_reduction_m2 > 0:
        result.landscaping_reduction_m2 = round(landscape_reduction_m2, 1)
        new_footprint = max(0.0, buildable_footprint - landscape_reduction_m2)
        steps.append(ConstraintStep(
            constraint=ConstraintType.DCP_LANDSCAPING,
            label="Landscaping / deep soil",
            footprint_m2=round(new_footprint, 1),
            reduction_m2=round(landscape_reduction_m2, 1),
            note=(
                f"Landscaping/deep soil requires {landscape_reduction_m2:.1f}m2 -- "
                f"footprint {buildable_footprint:.1f}m2 -> {new_footprint:.1f}m2"
            ),
        ))
        buildable_footprint = new_footprint

    # -----------------------------------------------------------------------
    # Step 7: Compute GFA from height path (now that footprint is known)
    # -----------------------------------------------------------------------
    clean_height_gfa: Optional[float] = None
    if max_storeys is not None:
        # Eroded height GFA (DCP-reduced footprint) feeds the secondary
        # dcp_adjusted figure; clean height GFA (full lot footprint) feeds the
        # headline LEP envelope and does not depend on the frontage/depth heuristic.
        gfa_from_height = buildable_footprint * max_storeys
        clean_height_gfa = lot_area_m2 * max_storeys
        result.lep_max_gfa_from_height_m2 = round(gfa_from_height, 1)
        # Update the height step with GFA
        for step in steps:
            if step.constraint == ConstraintType.LEP_HEIGHT:
                step.output_gfa_m2 = round(gfa_from_height, 1)
                step.footprint_m2 = round(buildable_footprint, 1)
                step.note += (
                    f" -> {buildable_footprint:.1f}m2 footprint x "
                    f"{max_storeys} storeys = {gfa_from_height:.1f}m2 GFA"
                )

    # -----------------------------------------------------------------------
    # Step 8: LEP envelope = min(FSR path, height path)
    # -----------------------------------------------------------------------
    def _min_opt(a: Optional[float], b: Optional[float]) -> Optional[float]:
        vals = [v for v in (a, b) if v is not None]
        return min(vals) if vals else None

    # Headline LEP envelope: FSR cap vs clean height envelope (full footprint).
    envelope_gfa = _min_opt(gfa_from_fsr, clean_height_gfa)
    if envelope_gfa is not None:
        result.lep_envelope_gfa_m2 = round(envelope_gfa, 1)

    # DCP-adjusted path (secondary): FSR cap vs eroded height envelope. Shadow and
    # parking erode this figure further below.
    current_gfa = _min_opt(gfa_from_fsr, gfa_from_height)

    # -----------------------------------------------------------------------
    # Step 9: Shadow access plane — continuous reduction
    # -----------------------------------------------------------------------
    # Uses per-scenario overlap data for a proportional GFA reduction rather
    # than a binary gate.  Noon scenario is the primary ADG reference; if no
    # noon scenario exists, falls back to worst-case across all scenarios.
    # Shadow reach vs lot depth amplifies the reduction when shadow penetrates
    # deeply into the lot.
    shadow_reduction = 0
    if shadow_result and max_storeys and max_storeys > 1:
        # Find noon scenario (primary ADG gate) or fall back to worst overlap
        noon_overlap: Optional[float] = None
        worst_overlap = 0.0
        noon_shadow_length: Optional[float] = None
        for scenario in (shadow_result.scenarios or []):
            if scenario.overlap_pct is not None:
                frac = scenario.overlap_pct / 100.0
                worst_overlap = max(worst_overlap, frac)
                if scenario.time_label and "12:" in scenario.time_label:
                    noon_overlap = frac
                    noon_shadow_length = scenario.shadow_length_m

        # Use noon overlap if available, otherwise worst-case
        effective_overlap = noon_overlap if noon_overlap is not None else worst_overlap

        if effective_overlap > SHADOW_OVERLAP_MIN:
            # Linear ramp: 0 at MIN, 1.0 at MAX, capped at 1.0
            shadow_severity = min(
                1.0,
                (effective_overlap - SHADOW_OVERLAP_MIN) / (SHADOW_OVERLAP_MAX - SHADOW_OVERLAP_MIN),
            )

            # Depth amplifier: if shadow reaches > 50% of lot depth, increase severity
            depth_amplifier = 1.0
            lot_depth = lot_dimensions.depth_m if lot_dimensions and lot_dimensions.depth_m else None
            shadow_len = noon_shadow_length
            if lot_depth and lot_depth > 0 and shadow_len and shadow_len > 0:
                depth_ratio = shadow_len / lot_depth
                if depth_ratio > 0.5:
                    # Amplify by up to 25% when shadow covers entire lot depth
                    depth_amplifier = 1.0 + min(0.25, (depth_ratio - 0.5) * 0.5)

            # GFA loss: up to half a storey of footprint on the north side
            max_shadow_loss = buildable_footprint * 0.5
            shadow_gfa_loss = max_shadow_loss * shadow_severity * depth_amplifier
            shadow_gfa_loss = min(shadow_gfa_loss, max_shadow_loss)  # cap at half storey

            shadow_reduction = 1
            result.shadow_storey_reduction = 1

            if current_gfa is not None:
                current_gfa = max(0.0, current_gfa - shadow_gfa_loss)

            note_parts = [
                f"Shadow overlap {effective_overlap:.0%}",
                f"severity {shadow_severity:.0%}",
            ]
            if depth_amplifier > 1.0:
                note_parts.append(f"depth amplifier {depth_amplifier:.2f}")
            note_parts.append(f"top storey reduced by {shadow_gfa_loss:.1f}m2")

            steps.append(ConstraintStep(
                constraint=ConstraintType.SHADOW_ACCESS,
                label="Solar access plane",
                reduction_m2=round(shadow_gfa_loss, 1),
                output_gfa_m2=round(current_gfa, 1) if current_gfa else None,
                note=" -- ".join(note_parts),
            ))

    # -----------------------------------------------------------------------
    # Step 10: Parking consumption
    # -----------------------------------------------------------------------
    parking_rate = _get_dcp_value(dcp_controls, "car_parking", dev_type)
    sepp_parking: Optional[float] = None
    if sepp_standards:
        for std in sepp_standards:
            if std.dev_type == dev_type and std.parking_spaces is not None:
                sepp_parking = std.parking_spaces
                break

    if current_gfa is not None:
        circulation = (
            CIRCULATION_FACTOR_APARTMENT
            if _is_apartment_type(dev_type)
            else CIRCULATION_FACTOR_HOUSE
        )
        sellable_gfa = current_gfa * (1 - circulation)
        est_dwellings = _dwellings_for_form(dev_type, int(sellable_gfa / MIN_DWELLING_GFA_M2))

        # Parking spaces — use DCP rate if available, else SEPP, else skip
        spaces_required: Optional[float] = None
        if parking_rate is not None:
            spaces_required = parking_rate * est_dwellings
        elif sepp_parking is not None:
            spaces_required = sepp_parking * est_dwellings

        if spaces_required is not None:
            result.parking_spaces_required = round(spaces_required, 1)
            # At-grade parking consumes floor area (conservative assumption).
            # Basement parking doesn't consume GFA but adds cost.
            # We model at-grade for binding constraint purposes.
            parking_gfa = spaces_required * PARKING_AREA_PER_SPACE_M2
            result.parking_gfa_consumed_m2 = round(parking_gfa, 1)

            # Only deduct parking if it's at-grade (single/dual occ, not apartments)
            if not _is_apartment_type(dev_type):
                current_gfa = max(0.0, current_gfa - parking_gfa)
                steps.append(ConstraintStep(
                    constraint=ConstraintType.PARKING,
                    label="Parking floor area",
                    reduction_m2=round(parking_gfa, 1),
                    output_gfa_m2=round(current_gfa, 1),
                    note=(
                        f"{spaces_required:.0f} spaces x {PARKING_AREA_PER_SPACE_M2}m2 = "
                        f"{parking_gfa:.1f}m2 consumed (at-grade)"
                    ),
                ))
            else:
                steps.append(ConstraintStep(
                    constraint=ConstraintType.PARKING,
                    label="Parking (basement — cost, not GFA)",
                    note=(
                        f"{spaces_required:.0f} spaces assumed basement — "
                        f"adds ~${parking_gfa * 80:.0f} cost, does not reduce GFA"
                    ),
                ))

    # -----------------------------------------------------------------------
    # Step 11: Realistic yield
    # -----------------------------------------------------------------------
    # Headline = LEP envelope (reliable, never zero for a buildable lot).
    if envelope_gfa is not None:

        def _dwellings_for(form: str) -> int:
            """Dwelling count for a built form against the same LEP envelope.

            The GFA envelope is form-independent; the form only sets the counting
            method (1 for a house, 2 for a dual occ, envelope ÷ unit size for
            multi-unit) and the circulation deduction for shared-access forms.
            """
            circ = (
                CIRCULATION_FACTOR_APARTMENT
                if _is_apartment_type(form)
                else CIRCULATION_FACTOR_HOUSE
            )
            return _dwellings_for_form(
                form, int(envelope_gfa * (1 - circ) / MIN_DWELLING_GFA_M2)
            )

        result.realistic_gfa_m2 = round(envelope_gfa, 1)
        # Primary dev_type drives the (conservative) realistic_dwellings — unchanged.
        result.realistic_dwellings = _dwellings_for(dev_type)
        # Dwelling-yield RANGE: as-of-right floor (the primary dev_type) and the
        # permitted ceiling (subject to a DA). The count is a derived illustration of
        # the envelope, so both ends share the same envelope_gfa.
        result.as_of_right_form = dev_type
        result.as_of_right_dwellings = result.realistic_dwellings
        if ceiling_dev_type:
            result.max_permitted_form = ceiling_dev_type
            result.max_permitted_dwellings = _dwellings_for(ceiling_dev_type)

    # Secondary "after-DCP" figure — only surfaced when lot geometry is reliable
    # (real frontage/depth) AND the eroded result is plausible (>0). Otherwise we
    # do not show a DCP-adjusted number rather than show a misleading/zero one.
    if has_dimensions and current_gfa is not None and current_gfa > 0:
        result.dcp_adjusted_gfa_m2 = round(current_gfa, 1)

    # -----------------------------------------------------------------------
    # Step 12: Binding constraint on the headline (LEP envelope = FSR vs height)
    # -----------------------------------------------------------------------
    if gfa_from_fsr is not None and clean_height_gfa is not None:
        if gfa_from_fsr <= clean_height_gfa:
            result.binding_constraint = ConstraintType.LEP_FSR
            result.binding_constraint_label = "FSR is the binding control on maximum GFA"
        else:
            result.binding_constraint = ConstraintType.LEP_HEIGHT
            result.binding_constraint_label = "Height limit is the binding control on maximum GFA"
    elif gfa_from_fsr is not None:
        result.binding_constraint = ConstraintType.LEP_FSR
        result.binding_constraint_label = "FSR is the binding control on maximum GFA"
    elif clean_height_gfa is not None:
        result.binding_constraint = ConstraintType.LEP_HEIGHT
        result.binding_constraint_label = "Height limit is the binding control on maximum GFA"

    # -----------------------------------------------------------------------
    # Confidence assessment
    # -----------------------------------------------------------------------
    result.gaps = gaps
    result.steps = steps

    data_points = 0
    available_points = 0
    for val in [lep_height_m, lep_fsr, front_setback, rear_setback, side_setback]:
        data_points += 1
        if val is not None:
            available_points += 1
    if lot_dimensions and lot_dimensions.frontage_m:
        available_points += 1
    data_points += 1  # lot dimensions

    if sepp_lep_overrides:
        available_points += 1
    data_points += 1

    ratio = available_points / max(data_points, 1)
    if ratio >= 0.8 and has_dimensions:
        result.confidence = "high"
    elif ratio >= 0.5:
        result.confidence = "medium"
    else:
        result.confidence = "low"

    return result


def _identify_binding_constraint(
    *,
    gfa_from_fsr: Optional[float],
    gfa_from_height: Optional[float],
    setback_footprint: float,
    final_footprint: float,
    max_storeys: Optional[int],
    site_coverage_cap_m2: Optional[float],
    landscape_reduction_m2: float,
    shadow_reduction: int,
    lot_area_m2: float,
) -> Optional[tuple[ConstraintType, str]]:
    """Determine which constraint is most limiting on yield.

    Strategy: compare the GFA each constraint path would allow if it were
    the ONLY constraint applied (in isolation).  The constraint producing
    the LOWEST isolated GFA is binding.

    setback_footprint: footprint after setbacks only (before coverage/landscaping).
    final_footprint: footprint after all area reductions.
    """
    candidates: list[tuple[ConstraintType, str, float]] = []

    storeys_for_calc = max_storeys or 1

    # Height in isolation: lot_area * storeys (no setback erosion)
    if max_storeys is not None:
        height_isolated_gfa = lot_area_m2 * storeys_for_calc
        candidates.append((
            ConstraintType.LEP_HEIGHT,
            "Height is the binding constraint -- limits number of storeys",
            height_isolated_gfa,
        ))

    # FSR in isolation: FSR * lot_area (no height cap)
    if gfa_from_fsr is not None:
        candidates.append((
            ConstraintType.LEP_FSR,
            "FSR is the binding constraint -- limits total floor area",
            gfa_from_fsr,
        ))

    # Setbacks in isolation: setback_footprint * storeys
    if setback_footprint < lot_area_m2:
        setback_gfa = setback_footprint * storeys_for_calc
        candidates.append((
            ConstraintType.DCP_SETBACKS,
            "Setbacks are the binding constraint -- reduce buildable footprint",
            setback_gfa,
        ))

    # Coverage in isolation: coverage_cap * storeys
    if site_coverage_cap_m2 is not None:
        coverage_gfa = site_coverage_cap_m2 * storeys_for_calc
        candidates.append((
            ConstraintType.DCP_SITE_COVERAGE,
            "Site coverage is the binding constraint -- caps ground floor area",
            coverage_gfa,
        ))

    # Landscaping in isolation: (setback_footprint - landscape) * storeys
    if landscape_reduction_m2 > 0:
        landscape_gfa = max(0.0, setback_footprint - landscape_reduction_m2) * storeys_for_calc
        candidates.append((
            ConstraintType.DCP_LANDSCAPING,
            "Landscaping/deep soil is the binding constraint -- reduces buildable area",
            landscape_gfa,
        ))

    # Shadow in isolation: removes half a storey of footprint
    if shadow_reduction > 0 and gfa_from_height is not None:
        shadow_gfa = gfa_from_height - (final_footprint * 0.5)
        candidates.append((
            ConstraintType.SHADOW_ACCESS,
            "Solar access is the binding constraint -- shadow plane cuts top storey",
            max(0.0, shadow_gfa),
        ))

    if not candidates:
        return None

    # Binding = lowest GFA
    candidates.sort(key=lambda c: c[2])
    return (candidates[0][0], candidates[0][1])


# ---------------------------------------------------------------------------
# Convenience: compute from a DevelopmentBrief
# ---------------------------------------------------------------------------


def compute_from_brief(
    brief: DevelopmentBrief,
    dev_type: str = "dwelling_house",
) -> ConstraintArithmeticResult:
    """Extract inputs from a DevelopmentBrief and run constraint arithmetic.

    This is the primary entry point for the intelligence brief pipeline.
    """
    pc = brief.planning_controls
    lot_dims = pc.lot_dimensions.value if pc.lot_dimensions else None

    # Lot area: prefer lot dimensions, then economics, then lot_size control
    lot_area: Optional[float] = None
    if lot_dims and lot_dims.area_m2:
        lot_area = lot_dims.area_m2
    elif brief.economics.lot_area_m2 and brief.economics.lot_area_m2.value:
        lot_area = brief.economics.lot_area_m2.value
    else:
        lot_area = _parse_numeric(pc.lot_size.value if pc.lot_size else None)

    if lot_area is None or lot_area <= 0:
        return ConstraintArithmeticResult(
            lot_area_m2=0.0,
            dev_type=dev_type,
            gaps=["Lot area not available — cannot compute constraint arithmetic"],
            confidence="low",
        )

    # DCP controls
    dcp_list = brief.dcp_controls.controls.value if brief.dcp_controls.controls else []

    # SEPP standards
    sepp_list = brief.sepp_housing.value if brief.sepp_housing else []

    # Shadow
    shadow = None
    if brief.neighbourhood and brief.neighbourhood.shadow:
        shadow = brief.neighbourhood.shadow.value

    return compute_constraint_arithmetic(
        lot_area_m2=lot_area,
        dev_type=dev_type,
        lep_height_str=pc.height.value if pc.height else None,
        lep_fsr_str=pc.fsr.value if pc.fsr else None,
        lot_dimensions=lot_dims,
        dcp_controls=dcp_list,
        sepp_standards=sepp_list,
        sepp_lep_overrides=brief.sepp_lep_overrides,
        shadow_result=shadow,
    )


# ---------------------------------------------------------------------------
# FastAPI endpoint — lightweight wrapper for frontend calls
# ---------------------------------------------------------------------------


class ConstraintArithmeticRequest(BaseModel):
    """Request body for /constraint-arithmetic endpoint."""

    lot_area_m2: float
    dev_type: str = "dwelling_house"
    lep_height_str: Optional[str] = None
    lep_fsr_str: Optional[str] = None
    frontage_m: Optional[float] = None
    depth_m: Optional[float] = None
    dcp_controls: list[DCPControl] = []
    sepp_standards: list[SEPPStandard] = []
    sepp_lep_overrides: list[SeppLepOverride] = []


@router.post(
    "/constraint-arithmetic",
    response_model=ConstraintArithmeticResult,
)
async def constraint_arithmetic_endpoint(
    req: ConstraintArithmeticRequest,
) -> ConstraintArithmeticResult:
    """Compute constraint arithmetic from pre-gathered property data.

    The frontend gathers LEP/DCP/SEPP data and posts it here.
    This endpoint runs the pure computation and returns the result.
    No DB queries or API calls — all data is in the request body.
    """
    lot_dims = None
    if req.frontage_m or req.depth_m:
        lot_dims = LotDimensions(
            area_m2=req.lot_area_m2,
            frontage_m=req.frontage_m,
            depth_m=req.depth_m,
            is_corner=False,
        )

    return compute_constraint_arithmetic(
        lot_area_m2=req.lot_area_m2,
        dev_type=req.dev_type,
        lep_height_str=req.lep_height_str,
        lep_fsr_str=req.lep_fsr_str,
        lot_dimensions=lot_dims,
        dcp_controls=req.dcp_controls,
        sepp_standards=req.sepp_standards,
        sepp_lep_overrides=req.sepp_lep_overrides,
    )


# ---------------------------------------------------------------------------
# Full endpoint — fetches DCP/SEPP from DB, computes overrides, runs engine
# ---------------------------------------------------------------------------


def _fetch_constraint_data_from_db(
    lga: Optional[str],
    zone: Optional[str],
    lot_area_m2: float,
    lep_height_str: Optional[str],
    lep_fsr_str: Optional[str],
) -> tuple[list[DCPControl], list[SEPPStandard], list[SeppLepOverride]]:
    """Fetch DCP controls, SEPP standards, and overrides from the database.

    Returns (dcp_controls, sepp_standards, sepp_lep_overrides).
    On any failure, returns empty lists for affected data.
    """
    import logging
    import os

    _logger = logging.getLogger(__name__)

    dcp_controls: list[DCPControl] = []
    sepp_standards: list[SEPPStandard] = []
    sepp_lep_overrides: list[SeppLepOverride] = []

    db_url = os.getenv("DATABASE_URL")
    if not db_url or not (lga or zone):
        return dcp_controls, sepp_standards, sepp_lep_overrides

    conn = None
    try:
        import psycopg2

        sys_path_orig = __import__("sys").path[:]
        import sys as _sys
        scripts_dir = str(__import__("pathlib").Path(__file__).resolve().parent.parent / "scripts")
        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)
        try:
            from conveyancing_db import fetch_dcp_setbacks, fetch_sepp_housing_standards
        finally:
            _sys.path[:] = sys_path_orig

        from services.intelligence_brief import (
            _build_sepp_housing,
            _detect_sepp_lep_overrides,
        )

        conn = psycopg2.connect(db_url, options="-c statement_timeout=5000")
        conn.autocommit = True

        # 1. Fetch DCP controls
        if lga:
            dcp_raw = fetch_dcp_setbacks(conn, lga, zone)
            if dcp_raw:
                all_setbacks = (dcp_raw.get("setbacks") or []) + (dcp_raw.get("sd_setbacks") or [])
                dcp_controls.extend(
                    _dcp_controls_from_setback_rows(all_setbacks, dcp_raw.get("clause_ref"))
                )

        # 2. Fetch SEPP Housing standards
        if zone:
            sepp_raw = fetch_sepp_housing_standards(conn, zone_code=zone)
            sepp_standards = _build_sepp_housing(sepp_raw, zone, lot_area_m2)

        # 3. Compute SEPP-LEP overrides
        lep_height = _parse_numeric(lep_height_str)
        lep_fsr = _parse_numeric(lep_fsr_str)
        sepp_lep_overrides = _detect_sepp_lep_overrides(
            sepp_standards, lep_height, lep_fsr,
        )

    except Exception as e:
        _logger.warning("constraint-arithmetic/full DB fetch failed: %s", e)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    return dcp_controls, sepp_standards, sepp_lep_overrides


class ConstraintArithmeticFullRequest(BaseModel):
    """Request body for /constraint-arithmetic/full endpoint.

    Unlike the base endpoint, this only needs property identifiers +
    LEP values. DCP controls, SEPP standards, and overrides are fetched
    server-side from the database.
    """

    lot_area_m2: float
    dev_type: str = "dwelling_house"
    zone: Optional[str] = None
    lga: Optional[str] = None  # formerCouncil slug
    lep_height_str: Optional[str] = None
    lep_fsr_str: Optional[str] = None
    frontage_m: Optional[float] = None
    depth_m: Optional[float] = None


@router.post(
    "/constraint-arithmetic/full",
    response_model=ConstraintArithmeticResult,
)
async def constraint_arithmetic_full(
    req: ConstraintArithmeticFullRequest,
) -> ConstraintArithmeticResult:
    """Compute constraint arithmetic with server-side data gathering.

    Fetches DCP setback controls and SEPP Housing standards from the
    database, computes SEPP-LEP overrides, then runs the constraint
    arithmetic engine. The frontend only needs to supply property
    identifiers and LEP values (from the Planning Portal).
    """
    lot_dims = None
    if req.frontage_m or req.depth_m:
        lot_dims = LotDimensions(
            area_m2=req.lot_area_m2,
            frontage_m=req.frontage_m,
            depth_m=req.depth_m,
            is_corner=False,
        )

    dcp_controls, sepp_standards, sepp_lep_overrides = _fetch_constraint_data_from_db(
        lga=req.lga,
        zone=req.zone,
        lot_area_m2=req.lot_area_m2,
        lep_height_str=req.lep_height_str,
        lep_fsr_str=req.lep_fsr_str,
    )

    return compute_constraint_arithmetic(
        lot_area_m2=req.lot_area_m2,
        dev_type=req.dev_type,
        lep_height_str=req.lep_height_str,
        lep_fsr_str=req.lep_fsr_str,
        lot_dimensions=lot_dims,
        dcp_controls=dcp_controls,
        sepp_standards=sepp_standards,
        sepp_lep_overrides=sepp_lep_overrides,
    )
