"""Backend Housing-SEPP / Low-and-Mid-Rise eligibility engine — single source of truth.

prior-art-checked: this PORTS the gate logic from the frontend
`app/api/housing-sepp/eligibility/route.ts` (the only prior implementation, which is
frontend TypeScript) into the backend, and computes its two inputs AUTHORITATIVELY instead
of trusting the caller: ``inLMRArea`` from the live 776 low/mid-rise exclusion layer (the
frontend defaulted it to true — a silent over-eligibility bug) and the TOD catchment from
the published 752/759 polygons (the frontend used a mock hardcoded station list + Haversine).
This is the consolidation's single source of truth: the capacity brief ceiling derives from
it, and the LEP/SEPP tab migrates onto it (P3) — so the two surfaces can no longer disagree.

Per Housing SEPP 2021 (LMR reforms). Determinism + fail-safety: any gate-query failure or
unconfirmed lot dimension yields a CONSERVATIVE "ineligible" for the affected form, never a
false eligibility; non-LMR forms (dwelling house, secondary dwelling, dual occ) are unaffected
by the LMR/TOD gates.
"""
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from services.portal_constraints import (
    fetch_sepp_exclusions,
    fetch_dual_occ_prohibition,
    fetch_tod_catchment,
)

logger = logging.getLogger(__name__)

RESIDENTIAL_ZONES = {"R1", "R2", "R3", "R4"}

# Low-density / base residential forms that are legitimately permitted without an LMR
# lot-size uplift gate. Any OTHER (denser) form must have a confirmable min_lot_size in
# the dataset to be eligible — so a form with a missing lot standard (e.g. manor_house,
# a known gap) is treated conservatively rather than passed by default.
_BASE_FORMS = {"dwelling_houses", "dwelling_house", "dual_occupancy", "secondary_dwelling"}


@dataclass
class FormEligibility:
    """Per-development-type eligibility outcome (serves both the brief and the tab)."""

    development_type: str
    eligible: bool
    reason: str
    requires_lmr_area: bool
    applicable_zones: list = field(default_factory=list)
    min_lot_size_m2: Optional[float] = None
    min_lot_width_m: Optional[float] = None


def normalize_zone(zone_code: Optional[str]) -> str:
    """"R2 Low Density Residential" -> "R2"; None/"" -> ""."""
    parts = (zone_code or "").strip().split()
    return parts[0].upper() if parts else ""


def _fetch_standards_grouped() -> dict:
    """housing_sepp_standards grouped by development_type.

    Returns {dev_type: {requires_lmr_area, applicable_zones, min_lot_size, min_lot_width}}.
    Reads thresholds from the table — none are hardcoded.
    """
    import psycopg2

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise EnvironmentError("DATABASE_URL not set")
    conn = None
    try:
        conn = psycopg2.connect(db_url, options="-c statement_timeout=5000")
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            "SELECT development_type, standard_type, numeric_value, applicable_zones, "
            "requires_lmr_area FROM housing_sepp_standards"
        )
        rows = cur.fetchall()
    finally:
        if conn:
            conn.close()

    grouped: dict = {}
    for dev_type, standard_type, numeric_value, zones, lmr in rows:
        g = grouped.get(dev_type)
        if g is None:
            g = {
                "requires_lmr_area": bool(lmr),
                "applicable_zones": list(zones) if zones else [],
                "min_lot_size": None,
                "min_lot_width": None,
            }
            grouped[dev_type] = g
        if numeric_value is None:
            continue
        if standard_type == "min_lot_size":
            g["min_lot_size"] = float(numeric_value)
        elif standard_type == "min_lot_width":
            g["min_lot_width"] = float(numeric_value)
    return grouped


def _gate_inputs(lat: Optional[float], lng: Optional[float]) -> dict:
    """Compute the authoritative gate inputs from live government layers, fail-safe.

    - in_lmr_area: NOT in the 776 low/mid-rise exclusion map. Conservatively False when the
      query fails or is indeterminate (so requires_lmr_area forms are not falsely eligible).
    - in_tod: inside a published TOD catchment (752/759).
    - dual_occ_prohibited: inside the ePlanning 452 dual-occupancy prohibition area.
    """
    in_lmr_area = False
    in_tod = False
    dual_occ_prohibited = False
    if lat is None or lng is None:
        return {"in_lmr_area": False, "in_tod": False, "dual_occ_prohibited": False}
    try:
        excl = fetch_sepp_exclusions(lat, lng)
        in_lmr_area = bool(excl and excl.get("low_mid_rise") is False)
    except Exception:
        logger.warning("LMR exclusion gate (776) query failed")
    try:
        tod = fetch_tod_catchment(lat, lng)
        in_tod = bool(tod and tod.get("in_tod"))
    except Exception:
        logger.warning("TOD catchment gate (752/759) query failed")
    try:
        dop = fetch_dual_occ_prohibition(lat, lng)
        dual_occ_prohibited = bool(dop and dop.get("prohibited"))
    except Exception:
        logger.warning("dual-occ prohibition gate (452) query failed")
    return {
        "in_lmr_area": in_lmr_area,
        "in_tod": in_tod,
        "dual_occ_prohibited": dual_occ_prohibited,
    }


def evaluate_eligibility(
    zone_code: Optional[str],
    lot_area_m2: Optional[float],
    lot_width_m: Optional[float],
    lat: Optional[float],
    lng: Optional[float],
    *,
    heritage: bool = False,
    gate_inputs: Optional[dict] = None,
) -> list[FormEligibility]:
    """Per-development-type Housing-SEPP eligibility for a lot.

    ``heritage`` (a heritage item or conservation-area lot) suppresses the LMR-reform forms,
    which the Low and Mid-Rise reforms exclude (the 776 exclusion map alone does not catch
    heritage). ``gate_inputs`` may be supplied to reuse already-fetched gate results (avoids
    repeat ArcGIS calls); otherwise they are fetched here. Returns [] for non-residential
    zones or if the standards table is unavailable (fail-safe — caller keeps base controls).
    """
    zone = normalize_zone(zone_code)
    if zone not in RESIDENTIAL_ZONES:
        return []
    try:
        grouped = _fetch_standards_grouped()
    except Exception as e:
        logger.warning("housing_sepp_standards fetch failed: %s", e)
        return []
    if not grouped:
        return []

    gates = gate_inputs if gate_inputs is not None else _gate_inputs(lat, lng)
    in_lmr_area = bool(gates.get("in_lmr_area"))
    in_tod = bool(gates.get("in_tod"))
    dual_occ_prohibited = bool(gates.get("dual_occ_prohibited"))

    results: list[FormEligibility] = []
    for dev_type, g in grouped.items():
        zones = g.get("applicable_zones") or []
        if zone not in zones:
            continue  # form not applicable to this zone
        lmr_req = bool(g.get("requires_lmr_area"))
        min_size = g.get("min_lot_size")
        min_width = g.get("min_lot_width")

        def _result(eligible: bool, reason: str) -> FormEligibility:
            return FormEligibility(
                development_type=dev_type, eligible=eligible, reason=reason,
                requires_lmr_area=lmr_req, applicable_zones=zones,
                min_lot_size_m2=min_size, min_lot_width_m=min_width,
            )

        if heritage and lmr_req:
            results.append(_result(False, "Excluded on heritage land — the Low and Mid-Rise reforms do not apply"))
            continue
        if lmr_req and not in_lmr_area:
            results.append(_result(False, "Not in a Low and Mid-Rise reform area (or area unconfirmed)"))
            continue
        # Conservative data-gap guard: a denser/uplift form must have a confirmable lot
        # standard. Forms missing min_lot_size that are not TOD-gated (e.g. manor_house —
        # a known dataset gap) are treated as ineligible rather than passed by default.
        if (
            dev_type not in _BASE_FORMS
            and "residential_flat_r3r4" not in dev_type
            and min_size is None
        ):
            results.append(_result(False, "Lot standard for this form is not in the dataset (treated conservatively)"))
            continue
        if min_size is not None and (lot_area_m2 is None or lot_area_m2 < min_size):
            reason = (
                f"Lot area unconfirmed (minimum {min_size:.0f} m²)" if lot_area_m2 is None
                else f"Lot area {lot_area_m2:.0f} m² is below the minimum {min_size:.0f} m²"
            )
            results.append(_result(False, reason))
            continue
        if min_width is not None and (lot_width_m is None or lot_width_m < min_width):
            reason = (
                f"Lot width unconfirmed (minimum {min_width:.0f} m)" if lot_width_m is None
                else f"Lot width {lot_width_m:.0f} m is below the minimum {min_width:.0f} m"
            )
            results.append(_result(False, reason))
            continue
        if "residential_flat" in dev_type and not in_tod:
            # Residential flat buildings are the MID-RISE tier (R1/R2 and R3/R4) and apply
            # only within a catchment — not statewide like the low-rise LMR forms. (The
            # frontend gated only the R3/R4 variant; the R1/R2 variant needs it too.)
            results.append(_result(False, "Not in a Transport Oriented Development catchment"))
            continue
        if "dual_occ" in dev_type and dual_occ_prohibited:
            results.append(_result(False, "Dual occupancy is prohibited on this lot (LEP local provision)"))
            continue
        results.append(_result(True, "Meets the applicable Housing SEPP standards (subject to a development application)"))
    return results
