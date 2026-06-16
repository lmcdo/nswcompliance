"""
DA Outcome Enrichment Service — queries the NSW DA Tracking MapServer
for actual approval outcomes (Approved/Refused/Deferred Commencement).

Fixes the structural limitation where the ePlanning API only shows
"Determined" without distinguishing approved vs refused.

See TIER1_BUILD_SPEC.md §1.
"""
import json
import logging
import math
import re
import time
from typing import Optional

from pydantic import BaseModel, Field

from services.arcgis_client import arcgis_get_with_retry

logger = logging.getLogger(__name__)

DA_TRACKING_URL = (
    "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/"
    "Planning_Portal_Application_Tracking/MapServer/0/query"
)

DA_MAX_PER_PAGE = 4000  # MapServer MaxRecordCount


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class DAOutcome(BaseModel):
    planning_portal_number: str
    da_number: Optional[str] = None
    status: str
    outcome: Optional[str] = None  # ASSESMENT_RESULT
    determining_authority: Optional[str] = None
    dev_type: Optional[str] = None
    dwellings_constructed: Optional[int] = None
    cost: Optional[str] = None
    address: str
    suburb: str
    x: Optional[float] = None
    y: Optional[float] = None
    lodgement_date: Optional[str] = None
    determined_date: Optional[str] = None


class RefusalStats(BaseModel):
    lga: str
    zone: Optional[str] = None
    dev_type: Optional[str] = None
    period_years: int
    total_determined: int
    approved: int
    refused: int
    deferred_commencement: int
    refusal_rate: float = Field(
        ..., ge=0.0, le=1.0, description="refused / total_determined"
    )


# ---------------------------------------------------------------------------
# Field parsing helpers
# ---------------------------------------------------------------------------

_DATE_14_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})\d{6}$")  # "20210730000000"
_DATE_8_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")          # "20211215"


def _parse_date_str(raw: Optional[str]) -> Optional[str]:
    """Normalise DA Tracking date strings to YYYY-MM-DD."""
    if not raw:
        return None
    raw = raw.strip()
    m = _DATE_14_RE.match(raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _DATE_8_RE.match(raw)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return raw  # unrecognised format — return as-is


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _parse_feature(attrs: dict) -> DAOutcome:
    """Parse a MapServer feature into a DAOutcome model."""
    return DAOutcome(
        planning_portal_number=attrs.get("PLANNING_PORTAL_APP_NUMBER") or "",
        da_number=attrs.get("DA_NUMBER"),
        status=attrs.get("STATUS") or "Unknown",
        outcome=attrs.get("ASSESMENT_RESULT"),  # Their typo, not ours
        determining_authority=attrs.get("DETERMINING_AUTHORITY"),
        dev_type=attrs.get("DEVELOPMENT_TYPE"),
        dwellings_constructed=_safe_int(attrs.get("DWELLINGS_TO_BE_CONSTRUCTED")),
        cost=str(attrs.get("COST_OF_DEVELOPMENT")) if attrs.get("COST_OF_DEVELOPMENT") is not None else None,
        address=attrs.get("PRIMARY_ADDRESS") or "",
        suburb=attrs.get("SUBURBNAME") or "",
        x=_safe_float(attrs.get("X")),
        y=_safe_float(attrs.get("Y")),
        lodgement_date=_parse_date_str(attrs.get("LODGEMENT_DATE")),
        determined_date=_parse_date_str(attrs.get("DETERMINED_DATE")),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_OUT_FIELDS = (
    "OBJECTID,PLANNING_PORTAL_APP_NUMBER,DA_NUMBER,STATUS,"
    "ASSESMENT_RESULT,DETERMINING_AUTHORITY,DEVELOPMENT_TYPE,"
    "DWELLINGS_TO_BE_CONSTRUCTED,COST_OF_DEVELOPMENT,"
    "PRIMARY_ADDRESS,SUBURBNAME,X,Y,"
    "LODGEMENT_DATE,DETERMINED_DATE"
)


def query_da_outcomes_near(
    lng: float,
    lat: float,
    radius_m: int = 200,
    years_back: int = 8,
) -> list[DAOutcome]:
    """Query DA Tracking MapServer for DAs within radius of a point.

    Uses esriGeometryEnvelope with bbox (distance buffer not supported
    on this endpoint). Post-filters by Haversine distance.

    Returns list of DAOutcome, empty list on failure.
    """
    lat_offset = radius_m / 111_000
    lng_offset = radius_m / (111_000 * max(math.cos(math.radians(lat)), 0.001))

    # Date cutoff — 8-char prefix for lexicographic filter
    import datetime
    cutoff_year = datetime.date.today().year - years_back
    date_cutoff = f"{cutoff_year}0101"

    params = {
        "geometry": f"{lng - lng_offset},{lat - lat_offset},{lng + lng_offset},{lat + lat_offset}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "where": f"LODGEMENT_DATE >= '{date_cutoff}'",
        "outFields": _OUT_FIELDS,
        "resultRecordCount": DA_MAX_PER_PAGE,
        "f": "json",
    }

    start = time.monotonic()
    data = arcgis_get_with_retry(DA_TRACKING_URL, params)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    features = data.get("features") or []
    results = []
    for f in features:
        attrs = f.get("attributes") or {}
        da = _parse_feature(attrs)
        # Post-filter by Haversine distance
        if da.x is not None and da.y is not None:
            dist = _haversine_m(lat, lng, da.y, da.x)
            if dist > radius_m:
                continue
        results.append(da)

    logger.info(
        "da_tracking query: %d results (%d pre-filter) in %dms",
        len(results), len(features), elapsed_ms,
    )
    return results


def query_da_by_pan(pan: str) -> Optional[DAOutcome]:
    """Look up a single DA by its PlanningPortalApplicationNumber.

    Used for cross-referencing ePlanning DAs with actual outcomes.
    """
    params = {
        "where": f"PLANNING_PORTAL_APP_NUMBER='{pan}'",
        "outFields": _OUT_FIELDS,
        "resultRecordCount": 1,
        "f": "json",
    }
    data = arcgis_get_with_retry(DA_TRACKING_URL, params)
    features = data.get("features") or []
    if not features:
        return None
    return _parse_feature(features[0].get("attributes") or {})


def get_refusal_rate(
    lga: str,
    years: int = 3,
    zone: Optional[str] = None,
    dev_type: Optional[str] = None,
) -> Optional[RefusalStats]:
    """Aggregate refusal rate for an LGA/zone/dev_type cohort.

    Uses groupByFieldsForStatistics on the MapServer for server-side aggregation.
    """
    import datetime
    cutoff_year = datetime.date.today().year - years
    date_cutoff = f"{cutoff_year}0101"

    where_parts = [
        f"LGA_NAME LIKE '%{lga}%'",
        f"LODGEMENT_DATE >= '{date_cutoff}'",
        "ASSESMENT_RESULT IS NOT NULL",
    ]
    if zone:
        where_parts.append(f"ZONE_DESC LIKE '%{zone}%'")
    if dev_type:
        where_parts.append(f"DEVELOPMENT_TYPE='{dev_type}'")

    params = {
        "where": " AND ".join(where_parts),
        "groupByFieldsForStatistics": "ASSESMENT_RESULT",
        "outStatistics": json.dumps([{
            "statisticType": "count",
            "onStatisticField": "OBJECTID",
            "outStatisticFieldName": "count",
        }]),
        "f": "json",
    }

    data = arcgis_get_with_retry(DA_TRACKING_URL, params)
    features = data.get("features") or []
    if not features:
        return None

    counts: dict[str, int] = {}
    for f in features:
        attrs = f.get("attributes") or {}
        result = attrs.get("ASSESMENT_RESULT") or "Unknown"
        counts[result] = attrs.get("count", 0)

    approved = counts.get("Approved") or 0
    refused = counts.get("Refused") or 0
    deferred = counts.get("Deferred Commencement Consent") or 0
    total = approved + refused + deferred

    if total == 0:
        return None

    return RefusalStats(
        lga=lga,
        zone=zone,
        dev_type=dev_type,
        period_years=years,
        total_determined=total,
        approved=approved,
        refused=refused,
        deferred_commencement=deferred,
        refusal_rate=round(refused / total, 4),
    )


# ---------------------------------------------------------------------------
# Haversine distance helper
# ---------------------------------------------------------------------------

def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in metres between two WGS84 points."""
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
