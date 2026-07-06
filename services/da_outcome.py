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
    # Data-derived window — the tracking layer is a point-in-time extract
    # (frozen at 2023-04 as of 2026-07), so "last N years" arithmetic from
    # period_years overstates coverage. Renderers must state this window.
    window_start: Optional[str] = Field(
        None, description="Lodgement-date floor actually applied (YYYY-MM-DD)"
    )
    data_currency: Optional[str] = Field(
        None, description="Newest lodgement date present on the layer (YYYY-MM-DD)"
    )


# ---------------------------------------------------------------------------
# Field parsing helpers
# ---------------------------------------------------------------------------

# Live values carry fractional seconds ("20230429151817.89") — without the
# optional suffix those rows passed through unparsed as raw strings.
_DATE_14_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})\d{6}(?:\.\d+)?$")  # "20210730000000"
_DATE_8_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")          # "20211215"
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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
        dev_type=attrs.get("TYPE_OF_DEVELOPMENT"),
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

# Field names verified against the LIVE layer metadata (2026-07-04): the layer
# calls the development-type column TYPE_OF_DEVELOPMENT; requesting the old
# DEVELOPMENT_TYPE name made ArcGIS return "Failed to execute query" -> {} ->
# a silent zero for every consumer (LODGEMENT_DATE is a string field; the
# lexicographic date filter was never the problem).
_OUT_FIELDS = (
    "OBJECTID,PLANNING_PORTAL_APP_NUMBER,DA_NUMBER,STATUS,"
    "ASSESMENT_RESULT,DETERMINING_AUTHORITY,TYPE_OF_DEVELOPMENT,"
    "DWELLINGS_TO_BE_CONSTRUCTED,COST_OF_DEVELOPMENT,"
    "PRIMARY_ADDRESS,SUBURBNAME,X,Y,"
    "LODGEMENT_DATE,DETERMINED_DATE"
)


# Per-process cache: the layer is a static extract, so one lookup per worker
# lifetime is enough; a stale cache can only ever understate currency.
_currency_cache: dict[str, str] = {}


def get_data_currency() -> str:
    """Newest LODGEMENT_DATE present on the tracking layer, as YYYY-MM-DD.

    prior-art-checked: no existing currency probe for this layer — this module
    owns all DA-tracking MapServer access; InstrumentCurrency.tsx is a
    legislation-instrument UI badge, unrelated to this ArcGIS layer.

    Cheap (one row, no geometry), cached per process. Raises on any failure —
    a data-window claim must never be fabricated or silently defaulted, per
    the module's no-silent-zero convention.
    """
    cached = _currency_cache.get("newest_lodgement")
    if cached:
        return cached

    params = {
        "where": "LODGEMENT_DATE IS NOT NULL",
        "outFields": "LODGEMENT_DATE",
        "orderByFields": "LODGEMENT_DATE DESC",
        "resultRecordCount": 1,
        "returnGeometry": "false",
        "f": "json",
    }
    data = arcgis_get_with_retry(DA_TRACKING_URL, params)
    if "features" not in data:
        raise RuntimeError("DA tracking currency query failed (transport or ArcGIS error)")
    features = data.get("features") or []
    if not features:
        raise RuntimeError("DA tracking currency query returned no rows — cannot state a data window")
    raw = (features[0].get("attributes") or {}).get("LODGEMENT_DATE")
    parsed = _parse_date_str(raw)
    if not parsed or not _ISO_DATE_RE.match(parsed):
        raise RuntimeError(
            f"DA tracking currency value unparseable ({raw!r}) — cannot state a data window"
        )
    _currency_cache["newest_lodgement"] = parsed
    return parsed


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

    if "features" not in data:
        raise RuntimeError("DA tracking query failed (transport or ArcGIS error)")
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
    if "features" not in data:
        raise RuntimeError("DA tracking PAN lookup failed (transport or ArcGIS error)")
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
        # LGA_NAME is stored uppercase ('CANADA BAY') — normalise both sides so
        # a mixed-case council name can't silently match nothing.
        f"UPPER(LGA_NAME) LIKE '%{lga.upper()}%'",
        f"LODGEMENT_DATE >= '{date_cutoff}'",
        "ASSESMENT_RESULT IS NOT NULL",
    ]
    if zone:
        # Verified live: the layer has NO zone column — a ZONE_DESC filter made
        # ArcGIS error and the stats silently vanish. Refuse loudly instead.
        raise ValueError("zone filtering is not supported: the DA tracking layer has no zone field")
    if dev_type:
        where_parts.append(f"TYPE_OF_DEVELOPMENT='{dev_type}'")

    # Resolve the layer's data window BEFORE counting: stats without a window
    # would render as if current. Raises on failure (fail closed).
    data_currency = get_data_currency()

    # The layer advertises supportsStatistics but the outStatistics query
    # returns "Unable to complete operation" (verified live 2026-07-04).
    # returnCountOnly per outcome value works reliably — three cheap counts.
    base_where = " AND ".join(where_parts)
    counts: dict[str, int] = {}
    for outcome in ("Approved", "Refused", "Deferred Commencement Consent"):
        params = {
            "where": f"{base_where} AND ASSESMENT_RESULT = '{outcome}'",
            "returnCountOnly": "true",
            "f": "json",
        }
        data = arcgis_get_with_retry(DA_TRACKING_URL, params)
        if "count" not in data:
            # {} from the client = a FAILED query — a refusal rate must never be
            # built on a silently-zero count.
            raise RuntimeError("DA refusal-rate count query failed (transport or ArcGIS error)")
        counts[outcome] = int(data.get("count") or 0)

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
        window_start=f"{cutoff_year}-01-01",
        data_currency=data_currency,
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
