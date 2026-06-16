"""
Strata Classification Service — queries the NSW StrataHub FeatureServer
to determine if a property is strata and classify its dwelling type.

Discriminates apartment vs townhouse vs duplex vs house.
Prerequisite for apartment risk report and VG comparable filtering.

See TIER1_BUILD_SPEC.md §5.
"""
import datetime
import logging
import math
import time
from typing import Optional

from pydantic import BaseModel

from services.arcgis_client import arcgis_get_with_retry

logger = logging.getLogger(__name__)

STRATA_HUB_URL = (
    "https://portal.spatial.nsw.gov.au/server/rest/services/"
    "StrataHub/FeatureServer/0/query"
)

# Windows-safe epoch parsing (BUG-1 fix from QA Phase 2)
_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class StrataInfo(BaseModel):
    plan_number: int
    plan_label: str
    address: str
    suburb: str
    lga: str
    lot_total: int
    registration_date: Optional[str] = None  # YYYY-MM-DD
    area_m2: float
    dwelling_type: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_epoch_to_datetime(epoch_ms) -> Optional[datetime.datetime]:
    """Convert epoch milliseconds to datetime. Works on Windows for pre-1970 dates."""
    if epoch_ms is None:
        return None
    try:
        return _EPOCH + datetime.timedelta(milliseconds=int(epoch_ms))
    except (OverflowError, ValueError, TypeError):
        return None


def classify_dwelling_type(lottotal: int) -> str:
    """Classify dwelling type from strata lot count.

    Boundaries validated by smoke test against known buildings:
    - SP670 (2 lots) = duplex
    - SP13481 (3 lots) = townhouse
    - SP5436 (6 lots) = small apartment
    - SP55792 (474 lots) = apartment building
    """
    if lottotal <= 2:
        return "duplex"
    if lottotal <= 4:
        return "townhouse"
    if lottotal <= 8:
        return "small_apartment"
    return "apartment"


def _parse_strata_feature(attrs: dict) -> StrataInfo:
    """Parse a StrataHub feature into a StrataInfo model."""
    epoch_ms = attrs.get("registrationdate")
    reg_dt = safe_epoch_to_datetime(epoch_ms)
    reg_str = reg_dt.strftime("%Y-%m-%d") if reg_dt else None

    lot_total = attrs.get("lottotal") or 0

    return StrataInfo(
        plan_number=attrs.get("plannumber") or 0,
        plan_label=attrs.get("planlabel") or "",
        address=attrs.get("address") or "",
        suburb=attrs.get("suburb") or "",
        lga=attrs.get("lga") or "",
        lot_total=lot_total,
        registration_date=reg_str,
        area_m2=attrs.get("Shape__Area") or 0.0,
        dwelling_type=classify_dwelling_type(lot_total),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_OUT_FIELDS = "plannumber,planlabel,registrationdate,address,suburb,lga,lottotal,postcode,Shape__Area"


def query_strata_at_point(
    lng: float,
    lat: float,
) -> Optional[StrataInfo]:
    """Spatial intersect query — is this point inside a strata plan polygon?

    Returns strata plan info or None (not strata = house/standalone).
    If multiple strata plans overlap, returns the one with smallest area
    (most specific match).
    """
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": 4326,
        "outFields": _OUT_FIELDS,
        "returnGeometry": "false",
        "resultRecordCount": 10,
        "f": "json",
    }

    start = time.monotonic()
    data = arcgis_get_with_retry(STRATA_HUB_URL, params)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    features = data.get("features") or []
    logger.info("strata_hub point query: %d results in %dms", len(features), elapsed_ms)

    if not features:
        return None

    # If multiple strata plans overlap, take the smallest (most specific)
    parsed = [_parse_strata_feature(f.get("attributes") or {}) for f in features]
    parsed.sort(key=lambda s: s.area_m2)
    return parsed[0]


def query_strata_near(
    lng: float,
    lat: float,
    radius_m: int = 200,
) -> list[StrataInfo]:
    """Nearby strata plans within radius — for neighbourhood density analysis."""
    lat_offset = radius_m / 111_000
    lng_offset = radius_m / (111_000 * max(math.cos(math.radians(lat)), 0.001))

    params = {
        "geometry": f"{lng - lng_offset},{lat - lat_offset},{lng + lng_offset},{lat + lat_offset}",
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": 4326,
        "outFields": _OUT_FIELDS,
        "returnGeometry": "false",
        "resultRecordCount": 200,
        "f": "json",
    }

    start = time.monotonic()
    data = arcgis_get_with_retry(STRATA_HUB_URL, params)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    features = data.get("features") or []
    logger.info("strata_hub radius query: %d results in %dms", len(features), elapsed_ms)

    return [_parse_strata_feature(f.get("attributes") or {}) for f in features]
