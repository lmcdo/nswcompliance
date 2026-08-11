"""
Compound Constraints — Stage 3.

Cross-layer constraint rules that only emerge from combining data.
Each rule: predicate (does it apply?) + caveat (what to verify) + severity.

Also: staleness detection and gap disclosure with verify_url.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

from services.intelligence_brief import (
    CompoundConstraint,
    CompoundSeverity,
    ConfidenceLevel,
    DataField,
    EmpiricalFinding,
    GapEntry,
)


# ---------------------------------------------------------------------------
# Staleness thresholds (days)
# ---------------------------------------------------------------------------

STALENESS_THRESHOLDS = {
    "plotdetect_dcp": 180,           # DCP controls: 6 months
    "nsw_valuation_service": 365,    # VG values: 12 months
    "postgis_overlays": 365,         # Spatial overlays: 12 months
    "postgis_heritage": 365,
}

# Empirical finding staleness — keyed by hazard type, in days
EMPIRICAL_STALENESS_THRESHOLDS = {
    "urban_heat_island": 3650,       # 10 years — dataset is 2016, flag after 2026
    "extreme_rainfall": 365,         # IFD tables updated annually
    "active_fire": 30,               # FIRMS detections are near-real-time
}


# ---------------------------------------------------------------------------
# Compound constraint rules
# ---------------------------------------------------------------------------


def evaluate_compound_constraints(
    *,
    heritage_items: list[str],
    heritage_hca: list[str],
    heritage_postgis: Optional[dict],
    bushfire_designation: Optional[str],
    flood_epi: bool,
    tod_area: bool,
    lot_area_m2: Optional[float],
    min_lot_size_m2: Optional[float],
    zone_code: Optional[str],
    nearby_das: list[dict],
    overlays: list[dict],
) -> list[CompoundConstraint]:
    """Evaluate all compound constraint rules. Returns list of triggered constraints."""
    constraints: list[CompoundConstraint] = []

    has_heritage_item = bool(heritage_items)
    has_heritage_hca = bool(heritage_hca)
    is_bushfire_prone = bool(bushfire_designation)

    # ── Rule 1: Heritage HCA + Bushfire ─────────────────────────────────
    if has_heritage_hca and is_bushfire_prone:
        # Check heritage subtype for severity
        overlay_values = [(o.get("value") or "") for o in overlays if o.get("layer_type") == "heritage"]
        postgis_elements = []
        if heritage_postgis and heritage_postgis.get("raw"):
            for r in heritage_postgis["raw"]:
                postgis_elements.append((r.get("heritage_element") or "").lower())

        is_landscape = any("landscape" in (v or "").lower() for v in overlay_values)
        has_garden = any("garden" in el for el in postgis_elements)

        if is_landscape or has_garden:
            constraints.append(CompoundConstraint(
                id="heritage_hca_bushfire_vegetation",
                description=(
                    "10/50 vegetation clearing entitlement may conflict with heritage "
                    "landscape character requirements."
                ),
                caveat=(
                    "Verify with council whether 10/50 clearing is permitted within "
                    "this heritage conservation area. Heritage landscape significance "
                    "may restrict vegetation removal."
                ),
                severity=CompoundSeverity.WARNING,
                data_sources_used=["postgis_overlays", "planning_portal"],
            ))
        else:
            constraints.append(CompoundConstraint(
                id="heritage_hca_bushfire_general",
                description=(
                    "10/50 vegetation clearing may apply — heritage character does not "
                    "appear to involve vegetation."
                ),
                caveat="Verify with council whether 10/50 clearing applies within this HCA.",
                severity=CompoundSeverity.INFO,
                data_sources_used=["postgis_overlays", "planning_portal"],
            ))

    # ── Rule 2: Heritage item + Flood planning area ─────────────────────
    if has_heritage_item and flood_epi:
        constraints.append(CompoundConstraint(
            id="heritage_item_flood",
            description="Flood mitigation works may require Heritage NSW concurrence.",
            caveat=(
                "Heritage-listed properties in flood planning areas may face "
                "conflicting requirements between flood mitigation (raised floor levels) "
                "and heritage conservation. Verify concurrence requirements with council."
            ),
            severity=CompoundSeverity.WARNING,
            data_sources_used=["planning_portal", "postgis_overlays"],
        ))

    # ── Rule 3: TOD precinct + Heritage HCA ────────────────────────────
    if tod_area and has_heritage_hca:
        constraints.append(CompoundConstraint(
            id="tod_heritage_hca",
            description="Heritage character may restrict TOD density bonus.",
            caveat=(
                "Transport Oriented Development provisions may allow increased density, "
                "but heritage conservation area requirements may limit the achievable "
                "built form. Check if heritage provisions override TOD incentives."
            ),
            severity=CompoundSeverity.INFO,
            data_sources_used=["planning_portal"],
        ))

    # ── Rule 4: Marginal lot size ──────────────────────────────────────
    if lot_area_m2 is not None and min_lot_size_m2 is not None and min_lot_size_m2 > 0:
        if lot_area_m2 < (min_lot_size_m2 * 1.1) and lot_area_m2 >= min_lot_size_m2:
            constraints.append(CompoundConstraint(
                id="marginal_lot_size",
                description=(
                    f"Lot area ({lot_area_m2:.0f}m\u00b2) is within 10% of zone minimum "
                    f"({min_lot_size_m2:.0f}m\u00b2) — verify with registered survey."
                ),
                caveat=(
                    "Valuer General lot areas may differ from surveyed areas. "
                    "A registered survey is recommended before relying on lot size "
                    "compliance for development assessment."
                ),
                severity=CompoundSeverity.WARNING,
                data_sources_used=["nsw_valuation_service", "planning_portal"],
            ))

    # ── Rule 5: Flood EPI + Heritage item ──────────────────────────────
    if flood_epi and has_heritage_item:
        constraints.append(CompoundConstraint(
            id="flood_heritage_floor_level",
            description="Floor level mitigation may be heritage-restricted.",
            caveat=(
                "Flood planning level requirements may conflict with heritage "
                "conservation constraints on floor level modifications. "
                "Council may require alternative flood mitigation strategies."
            ),
            severity=CompoundSeverity.WARNING,
            data_sources_used=["planning_portal", "postgis_overlays"],
        ))

    # ── Rule 6: Fix B — Zone permits higher density ────────────────────
    # DQ-30 (.claude/DATA_QUALITY_TRACKER.md): B1/B2 are retired NSW zone
    # codes (April 2023 Employment Zones Reform); zone_code here is a live
    # property's CURRENT zone from the Planning Portal, which is never a
    # legacy code, so this check silently never fired for commercial-zoned
    # properties. Real current equivalent is E1 (was B1/B2).
    zone_prefix = _zone_prefix(zone_code)
    if zone_prefix in ("R3", "R4", "E1", "MU1"):  # noqa: zone-codes -- current-era codes only, no legacy alias needed (see comment above)
        constraints.append(CompoundConstraint(
            id="zone_higher_density_advisory",
            description=(
                f"Zone {zone_prefix} permits higher-density development types. "
                f"Controls shown are for dwelling house only."
            ),
            caveat=(
                f"This zone ({zone_prefix}) permits multi-dwelling housing, "
                f"residential flat buildings, or other higher-density types. "
                f"If not developing a single dwelling house, request controls "
                f"for the intended development type."
            ),
            severity=CompoundSeverity.INFO,
            data_sources_used=["planning_portal"],
        ))

    # ── Rule 7: Fix C — DA-shadow interaction ──────────────────────────
    _evaluate_da_shadow_interaction(nearby_das, constraints)

    return constraints


def _evaluate_da_shadow_interaction(
    nearby_das: list[dict],
    constraints: list[CompoundConstraint],
) -> None:
    """Fix C: approved/assessed DA within 100m with multi-storey description."""
    multi_storey_pattern = re.compile(
        r"(multi.?storey|residential.?flat|apartment|rfb|"
        r"mixed.?use|boarding.?house|3\s*storey|4\s*storey|5\s*storey|"
        r"6\s*storey|7\s*storey|8\s*storey|9\s*storey|10\s*storey|"
        r"new\s+building|demolition\s+and\s+construction)",
        re.IGNORECASE,
    )
    relevant_statuses = {"approved", "under assessment", "determination pending", "assessed"}

    for da in nearby_das:
        distance = da.get("distance_m")
        if distance is None or distance > 100:
            continue
        status = (da.get("status") or "").lower()
        if not any(s in status for s in relevant_statuses):
            continue
        desc = da.get("description") or da.get("dev_type") or ""
        if multi_storey_pattern.search(desc):
            constraints.append(CompoundConstraint(
                id="da_shadow_interaction",
                description=(
                    f"Active/approved DA ({da.get('number', 'unknown')}) within "
                    f"{distance}m may affect future shadow environment."
                ),
                caveat=(
                    "Shadow analysis reflects current height controls only. "
                    "This nearby development application, if built, may alter "
                    "the shadow environment on or near this property."
                ),
                severity=CompoundSeverity.WARNING,
                data_sources_used=["eplanning_da_api", "shadow_detector"],
            ))
            break  # One warning is enough


# ---------------------------------------------------------------------------
# Satellite compound constraints — evaluated when satellite data present
# ---------------------------------------------------------------------------


def evaluate_satellite_constraints(
    *,
    granny_flat_structures: Optional[int],
    nearby_das: list[dict],
    flood_epi: bool,
    flood_jrc_pct: Optional[float],
    flood_wofs_pct: Optional[float],
) -> list[CompoundConstraint]:
    """Satellite-dependent compound constraints (Stage 4a).

    Only called when include_satellite=True and satellite data is available.
    """
    constraints: list[CompoundConstraint] = []

    # Structure detected but no DA record → potential unapproved structure
    if granny_flat_structures is not None and granny_flat_structures > 1:
        # Multiple structures detected — check if any DAs for secondary dwelling
        has_sd_da = any(
            "secondary" in (da.get("description") or da.get("dev_type") or "").lower()
            or "granny" in (da.get("description") or da.get("dev_type") or "").lower()
            for da in nearby_das
        )
        if not has_sd_da:
            constraints.append(CompoundConstraint(
                id="structure_no_da_record",
                description=(
                    f"{granny_flat_structures} structures detected on lot but no "
                    f"secondary dwelling DA found in recent records."
                ),
                caveat=(
                    "AI-detected structure count requires user confirmation. "
                    "The absence of a DA record does not confirm non-compliance — "
                    "the structure may pre-date digital records or be exempt development."
                ),
                severity=CompoundSeverity.INFO,
                data_sources_used=["granny_flat_detect", "eplanning_da_api"],
            ))

    # Flood evidence exceeds statutory designation
    if not flood_epi:
        sat_flood_detected = False
        if flood_jrc_pct is not None and flood_jrc_pct > 2.0:
            sat_flood_detected = True
        if flood_wofs_pct is not None and flood_wofs_pct > 2.0:
            sat_flood_detected = True

        if sat_flood_detected:
            constraints.append(CompoundConstraint(
                id="flood_evidence_exceeds_statutory",
                description=(
                    "Satellite/historical flood evidence detected but property is "
                    "NOT in a statutory Flood Planning Area."
                ),
                caveat=(
                    "JRC Global Surface Water or DEA WOfS data indicates historical "
                    "water presence at this location, despite no EPI flood designation. "
                    "This may reflect localised flooding not captured in statutory mapping."
                ),
                severity=CompoundSeverity.WARNING,
                data_sources_used=["flood_truth", "postgis_overlays"],
            ))

    return constraints


# ---------------------------------------------------------------------------
# Staleness detection
# ---------------------------------------------------------------------------


def detect_staleness(brief) -> list[str]:
    """Walk DataField instances, flag any with as_at older than source threshold.

    Returns list of human-readable staleness warnings.
    Also mutates stale fields: sets confidence to STALE.
    """
    from pydantic import BaseModel

    warnings: list[str] = []
    today = date.today()

    def _walk(obj):
        if isinstance(obj, EmpiricalFinding):
            threshold_days = EMPIRICAL_STALENESS_THRESHOLDS.get(obj.hazard)
            if threshold_days is None or not obj.data_date:
                return
            try:
                # data_date may be "2016" (year only) or "2026-05-30" (full date)
                if len(obj.data_date) == 4:
                    field_date = date(int(obj.data_date), 1, 1)
                else:
                    field_date = datetime.strptime(obj.data_date, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                return
            age_days = (today - field_date).days
            if age_days > threshold_days:
                obj.confidence = ConfidenceLevel.STALE
                # #745 D7-7: user-facing copy, not a log line.
                years = age_days / 365.25
                warnings.append(
                    f"The {obj.hazard.replace('_', ' ')} reading is about "
                    f"{years:.0f} years old — the most recent published dataset."
                )
        elif isinstance(obj, DataField):
            if obj.confidence != ConfidenceLevel.NOT_AVAILABLE:
                threshold_days = STALENESS_THRESHOLDS.get(obj.source)
                if threshold_days and obj.as_at:
                    try:
                        field_date = datetime.strptime(obj.as_at, "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        field_date = None
                    if field_date:
                        age_days = (today - field_date).days
                        if age_days > threshold_days:
                            obj.confidence = ConfidenceLevel.STALE
                            warnings.append(
                                f"{obj.source}: data is {age_days} days old "
                                f"(threshold: {threshold_days} days)"
                            )
            # Walk into the wrapped value (may contain EmpiricalFinding etc.)
            if obj.value is not None:
                _walk(obj.value)
        elif isinstance(obj, BaseModel):
            for field_name in obj.model_fields:
                _walk(getattr(obj, field_name, None))
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(brief)
    return warnings


# ---------------------------------------------------------------------------
# Gap disclosure — verify_url population
# ---------------------------------------------------------------------------

_DCP_VERIFY_URLS = {
    "marrickville": "https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-control-plans/marrickville-development-control-plan-2011",
    "leichhardt": "https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-control-plans/leichhardt-development-control-plan-2013",
    "ashfield": "https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-control-plans/ashfield-development-control-plan-2007",
}


def enrich_gaps_with_verify_url(
    gaps: list[GapEntry],
    lga_slug: Optional[str],
) -> list[GapEntry]:
    """Add verify_url to gaps where we know where to point the user."""
    for gap in gaps:
        if "dcp_controls" in gap.field and lga_slug and lga_slug in _DCP_VERIFY_URLS:
            gap.verify_url = _DCP_VERIFY_URLS[lga_slug]
        elif "planning_portal" in (gap.reason or "").lower():
            gap.verify_url = "https://www.planningportal.nsw.gov.au/spatialviewer/"
        elif "valuation" in gap.field or "land_value" in gap.field:
            gap.verify_url = "https://www.valuergeneral.nsw.gov.au/land_value_search/search.php"
    return gaps


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _zone_prefix(zone: Optional[str]) -> str:
    """Extract zone prefix (e.g. 'R3' from 'R3 Medium Density')."""
    if not zone or not zone.strip():
        return ""
    parts = zone.strip().split()
    return parts[0].upper() if parts else ""
