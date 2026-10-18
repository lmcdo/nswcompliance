"""Low and Mid-Rise housing area gates for one point, over HTTP.

prior-art-checked: reuse of housing_sepp_eligibility._gate_inputs is not enough on its own -- it folds a failed
query into False, which is right for its callers (a form is then not passed) but wrong for a page that prints
"Not applicable": that states a negative nobody measured. No HTTP endpoint exposed these gates (grep of
services/ for routers mentioning sepp/eligib/housing/lmr, 2026-10-18). The website decided the same question
from a hardcoded list of council names (frontend-nextjs/lib/regulatory-constants.ts STAGE2_REGION_LGAS), which
put every R1-R4 lot in those councils in a reform area: 19 of 23 residential lots on the 28-address
rules-per-address panel that the map layers place outside one (6 Berrigan St Winston Hills: no Town Centres Map
polygon within the catchment distance, nearest Northmead Village; not in a TOD catchment).

Same layers and the same rule as _gate_inputs (Town Centres Map 766 catchment OR a TOD catchment 752/759, AND not
in the 776 exclusion map; 452 dual-occupancy prohibition), but each answer is True / False / None, where None
means the query did not answer. The combined in_lmr_area is None whenever its answer depends on a layer that
did not answer.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from services.portal_constraints import (
    fetch_dual_occ_prohibition,
    fetch_sepp_exclusions,
    fetch_tod_catchment,
    fetch_town_centre_catchment,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["housing-sepp"])

# NSW bounding box, used only to reject a swapped or foreign coordinate before any query.
_NSW_LAT = (-38.0, -28.0)  # noqa: regulatory-number -- geographic bounds, not a planning figure
_NSW_LNG = (140.0, 154.5)  # noqa: regulatory-number -- geographic bounds, not a planning figure


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:  # noqa: BLE001 -- a failed layer is reported as None, never as False
        logger.warning("housing SEPP gate %s failed: %s", getattr(fn, "__name__", fn), e)
        return None


def _tri(value: object) -> Optional[bool]:
    """True / False only for a real bool; anything else (missing key, None, a string) is None, never False."""
    return value if isinstance(value, bool) else None


def lmr_gates(lat: float, lng: float) -> dict:
    """True / False / None (not answered) for each gate, and the combined Low and Mid-Rise area answer."""
    excl = _safe(fetch_sepp_exclusions, lat, lng)
    tod = _safe(fetch_tod_catchment, lat, lng)
    tc = _safe(fetch_town_centre_catchment, lat, lng)
    dop = _safe(fetch_dual_occ_prohibition, lat, lng)

    excluded = _tri((excl or {}).get("low_mid_rise"))
    in_tod = _tri((tod or {}).get("in_tod"))
    near_tc = _tri((tc or {}).get("within_catchment"))
    dual_occ_prohibited = _tri((dop or {}).get("prohibited"))

    if in_tod is True or near_tc is True:
        anchored: Optional[bool] = True
    elif in_tod is False and near_tc is False:
        anchored = False
    else:
        anchored = None

    if anchored is False or excluded is True:
        in_lmr_area: Optional[bool] = False
    elif anchored is True and excluded is False:
        in_lmr_area = True
    else:
        in_lmr_area = None

    return {
        "in_lmr_area": in_lmr_area,
        "in_tod": in_tod,
        "near_town_centre": near_tc,
        "town_centre": (tc or {}).get("label"),
        "lmr_excluded": excluded,
        "dual_occ_prohibited": dual_occ_prohibited,
        "source": "NSW Planning Portal SEPP layers: Town Centres Map 766, TOD 752/759, exclusions 776, "
                  "dual occupancy prohibition 452",
    }


@router.get("/housing-sepp/gates")
def housing_sepp_gates(lat: float, lng: float) -> dict:
    """GET /pipeline/housing-sepp/gates?lat=&lng= -- see lmr_gates."""
    if not (_NSW_LAT[0] <= lat <= _NSW_LAT[1] and _NSW_LNG[0] <= lng <= _NSW_LNG[1]):
        raise HTTPException(status_code=422, detail="lat/lng outside NSW")
    return lmr_gates(lat, lng)
