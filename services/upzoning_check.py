"""Upzoning check — FastAPI router for the free per-address tool.

POST /pipeline/upzoning -- "what can I build here under the 2025 LMR/TOD reforms?"

prior-art-checked: this is a THIN EXPOSURE layer over existing engines — address
resolution + controls parsing reused from scripts/generate_conveyancing_report
(the conveyancing pipeline's own path), lot dimensions from services/lot_dimensions,
and ALL eligibility logic delegated verbatim to
services.housing_sepp_eligibility.evaluate_eligibility (live 776/752/759/452 gates,
heritage suppression, fail-closed). No new gate or eligibility logic is written here.
The pre-impl smoke test (2026-07-13) proved a hand-rolled shortcut produces a
heritage false-positive (Haberfield); the engine is the single source of truth.

Response contract:
{
  "address": str, "prop_id": int | null, "lat": float, "lng": float,
  "run_date": str,
  "zone": str | null, "zone_full": str | null, "zone_epi": str | null,
  "legislation_url": str | null,
  "lot_area_m2": float | null, "lot_width_m": float | null,
  "heritage": {"flag": bool, "items": list[str], "hca": list[str]},
  "gates": {"in_lmr_area": bool, "in_tod": bool, "dual_occ_prohibited": bool},
  "status": "ok" | "not_residential" | "unavailable",
  "forms": list[dict],   # FormEligibility fields, engine wording verbatim
  "data_sources": list[str]
}

Three-state discipline: evaluate_eligibility returns [] BOTH for non-residential
zones and for a standards-table failure. Those must not render the same — the
endpoint separates them via ``status`` so the UI never shows a data outage as
"nothing is possible here" (silent-failure rule, pre-pr-review #4).
"""
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
import re
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Same path setup as services/conveyancing.py — the address/controls helpers
# live in scripts/generate_conveyancing_report.py (Docker and local layouts).
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_project_root))

from generate_conveyancing_report import (  # noqa: E402
    detect_former_council,
    resolve_address,
    get_raw_controls,
    parse_controls,
)

try:  # Docker (PYTHONPATH=/app)
    import services.housing_sepp_eligibility as hse
    from services.lot_dimensions import (
        calculate_lot_dimensions,
        eligibility_lot_width,
        fetch_lot_geometry,
    )
except ImportError:  # local (run from services/)
    import housing_sepp_eligibility as hse
    from lot_dimensions import (
        calculate_lot_dimensions,
        eligibility_lot_width,
        fetch_lot_geometry,
    )

router = APIRouter(prefix="/pipeline", tags=["upzoning"])

_DATA_SOURCES = [
    "NSW Planning Portal (layerintersect: zone, heritage, LEP controls)",
    "NSW Planning Portal lot geometry (area and frontage derived)",
    "NSW ePlanning MapServer live layers 776 / 752 / 759 / 452 (LMR exclusion, TOD, dual-occupancy prohibition)",
    "housing_sepp_standards (extracted SEPP standards with source clauses)",
]


class UpzoningRequest(BaseModel):
    address: str


def _former_council_safe(address: str, zone_epi: Optional[str]) -> Optional[str]:
    """dcp_setback_controls lga slug, or None — a resolver failure must never
    fail the whole check (the tool result stands without the DCP snapshot)."""
    try:
        return detect_former_council(address, zone_epi or "")
    except Exception as e:
        logger.warning("upzoning: former-council resolution failed: %s", e)
        return None


def _controls_for(prop_id: Optional[int]) -> dict:
    """Zone + heritage via the conveyancing pipeline's own parser (never raises)."""
    if not prop_id:
        return parse_controls([])
    try:
        return parse_controls(get_raw_controls(prop_id))
    except Exception as e:
        logger.warning("upzoning: controls fetch failed for prop %s: %s", prop_id, e)
        return parse_controls([])


def _lot_dims(prop_id: Optional[int]) -> tuple[Optional[float], Optional[float], Optional[str]]:
    """(area_m2, eligibility_width_m, lot_type) from Portal lot geometry.

    Width is battleaxe-aware (developable head width on a flag lot, cadastral
    frontage otherwise) — the value the SEPP minimum-lot-width tests need.
    (None, None, None) on any gap.
    """
    if not prop_id:
        return None, None, None
    try:
        dims = calculate_lot_dimensions(fetch_lot_geometry(str(prop_id)))
    except Exception as e:
        logger.warning("upzoning: lot dimensions failed for prop %s: %s", prop_id, e)
        return None, None, None
    if dims is None:
        return None, None, None
    return dims.area_m2, eligibility_lot_width(dims), dims.lot_type


@router.post("/upzoning")
def run_upzoning_check(req: UpzoningRequest):
    """Per-address Housing-SEPP form eligibility under the 2025 LMR/TOD reforms.

    Reports CURRENT rights only (not a before/after diff — no pre-2025 baseline
    exists). Mid-rise catchment forms are handled by the engine's TOD gate; the
    tool makes no claim beyond what the engine returns.
    """
    if not (req.address or "").strip():
        raise HTTPException(status_code=400, detail="Address required")

    try:
        prop_id, lat, lng, _lot_wkt = resolve_address(req.address)
    except Exception as e:
        logger.error("upzoning: address resolution failed: %s", e)
        raise HTTPException(status_code=422, detail=f"Could not resolve address: {req.address}")
    if not lat or not lng:
        raise HTTPException(status_code=422, detail=f"Could not determine coordinates for: {req.address}")

    # Controls, lot dimensions and live gates are independent — fetch in parallel
    # (same executor pattern as /pipeline/conveyancing).
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_controls = pool.submit(_controls_for, prop_id)
        f_dims = pool.submit(_lot_dims, prop_id)
        f_gates = pool.submit(hse._gate_inputs, lat, lng)
        controls = f_controls.result(timeout=50)
        lot_area_m2, lot_width_m, lot_type = f_dims.result(timeout=50)
        gates = f_gates.result(timeout=50)

    heritage_items = controls.get("heritage_items") or []
    heritage_hca = controls.get("heritage_hca") or []
    heritage = bool(heritage_items or heritage_hca)

    # parse_controls field semantics (generate_conveyancing_report.py:3999):
    # "zone" carries the CODE (portal Zone attr, e.g. "R2"); "zone_full" is the
    # portal's zone NAME with no code (e.g. "Low Density Residential"). Normalising
    # the name yields garbage ("LOW") and mislabels every lot not_residential —
    # caught by the live verify run 2026-07-13, pinned in
    # test_zone_code_comes_from_the_zone_field_not_the_name.
    zone_code_src = controls.get("zone")
    zone = hse.normalize_zone(zone_code_src)
    zone_name = controls.get("zone_full")
    # Bare LGA name derived from the EPI name ("Wingecarribee Local Environmental
    # Plan 2010" -> "Wingecarribee") — the vocabulary the lep_zone_coverage table
    # and /api/lep/permissibility use (verified against the live table; deliberately
    # NOT the "...Shire Council" normalisation the DA API wants).
    zone_epi = controls.get("zone_epi")
    lga_name = None
    if zone_epi:
        m = re.match(r"(.+?)\s+Local Environmental Plan\s+\d{4}", zone_epi, re.IGNORECASE)
        # Match-based, not strip-based: a non-LEP instrument name yields None
        # (no land-use panel) rather than leaking the whole title as an "LGA".
        lga_name = m.group(1).strip() if m else None

    forms = hse.evaluate_eligibility(
        zone_code_src,
        lot_area_m2,
        lot_width_m,
        lat,
        lng,
        heritage=heritage,
        gate_inputs=gates,
    )

    # [] is ambiguous (non-residential OR standards outage) — disambiguate so the
    # UI can fail visibly instead of rendering an outage as "nothing possible".
    if forms:
        status = "ok"
    elif zone not in hse.RESIDENTIAL_ZONES:
        status = "not_residential"
    else:
        status = "unavailable"

    return {
        "address": req.address,
        "prop_id": prop_id,
        "lat": lat,
        "lng": lng,
        "run_date": date.today().isoformat(),
        "zone": zone or None,
        "zone_full": zone_name or zone_code_src,
        "zone_epi": zone_epi,
        "lga_name": lga_name,
        # dcp_setback_controls slug (Inner West disambiguates to its former
        # council by suburb; None when the LGA's DCP data isn't onboarded).
        # Distinct from lga_name — this is what structured-controls lookups key on.
        "former_council": _former_council_safe(req.address, zone_epi),
        "legislation_url": controls.get("legislation_url"),
        "lot_area_m2": lot_area_m2,
        # Battleaxe-aware: on a flag lot this is the developable HEAD width (what
        # the SEPP width tests use), not the access-handle frontage. lot_type
        # tells the UI which label to render.
        "lot_width_m": lot_width_m,
        "lot_type": lot_type,
        "heritage": {"flag": heritage, "items": heritage_items, "hca": heritage_hca},
        "gates": gates,
        "status": status,
        "forms": [asdict(f) for f in forms],
        "data_sources": _DATA_SOURCES,
    }
