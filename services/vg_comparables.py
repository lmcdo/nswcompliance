"""
VG Comparable Analysis Service — queries the NSW Valuer General MapServer
for comparable property values and recent sales.

Enables land-tax objection product and enriches intelligence brief
with market context.

See TIER1_BUILD_SPEC.md §2, §A1.4 (OBJECTID gotcha), §A1.5 (strata filtering).
"""
import logging
import math
import statistics
import time
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from services.arcgis_client import arcgis_get_with_retry

logger = logging.getLogger(__name__)

VG_LAYER5_URL = (
    "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query"
)
VG_SALES_URL = (
    "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/1/query"
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ComparableProperty(BaseModel):
    propid: int
    address: str
    zone: str
    area_m2: float
    land_value: Optional[int] = None
    valuation_date: Optional[str] = None


class ComparableAnalysis(BaseModel):
    subject_value: Optional[int] = None
    subject_area_m2: float
    comparable_count: int
    median_value: Optional[int] = None
    mean_value: Optional[int] = None
    percentile_rank: Optional[float] = None  # 0-100
    comparables: list[ComparableProperty]
    assessment_signal: Optional[str] = None  # "potentially_over" | "in_range" | "potentially_under"


class PropertySale(BaseModel):
    propid: int
    address: str
    price: int
    area_m2: float
    sale_date: Optional[str] = None
    price_per_m2: Optional[float] = None
    is_strata: bool


# ---------------------------------------------------------------------------
# String parsing helpers (confirmed from smoke test)
# ---------------------------------------------------------------------------

def parse_land_value(val_str) -> Optional[int]:
    """Parse VG land value string: ' $2,660,000' -> 2660000."""
    if val_str is None:
        return None
    if isinstance(val_str, (int, float)):
        return int(val_str) if val_str else None
    s = str(val_str).strip()
    if not s:
        return None
    cleaned = s.replace("$", "").replace(",", "").replace(" ", "")
    if not cleaned:
        return None
    try:
        return int(cleaned) if cleaned is not None else None
    except ValueError:
        return None


def parse_area(area_str) -> Optional[float]:
    """Parse VG area string: '651.3 square metres' -> 651.3."""
    if area_str is None:
        return None
    if isinstance(area_str, (int, float)):
        return float(area_str) if area_str else None
    s = str(area_str).strip()
    if not s:
        return None
    parts = s.split()
    if parts:
        try:
            return float(parts[0])
        except ValueError:
            pass
    return None


def parse_sale_date(date_str) -> Optional[str]:
    """Parse VG sale date: '20 September 2017' -> '2017-09-20'."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str.strip(), "%d %B %Y")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return date_str


# ---------------------------------------------------------------------------
# Haversine
# ---------------------------------------------------------------------------

def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
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


def _webmercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Convert Web Mercator (3857) to WGS84 (4326)."""
    lng = x / 20037508.34 * 180
    lat = math.degrees(
        2 * math.atan(math.exp(y / 20037508.34 * math.pi)) - math.pi / 2
    )
    return lat, lng


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# OBJECTID must be first field for spatial queries on VG Layer 5 (spec §A1.4)
_VG_OUT_FIELDS = "OBJECTID,propid,address,zone_desc,prop_area,val1_lv,val1_bd"
_VG_SALES_OUT_FIELDS = "OBJECTID,propid,house_no,street,suburb,postcode,price,sale_date,area,strata"


def get_comparable_values(
    lng: float,
    lat: float,
    zone: str,
    lot_area_m2: float,
    radius_m: int = 500,
    area_tolerance: float = 0.3,
    subject_propid: Optional[int] = None,
) -> ComparableAnalysis:
    """Find comparable property valuations within radius.

    Filters by same zone and similar lot area (+-tolerance).
    """
    lat_offset = radius_m / 111_000
    lng_offset = radius_m / (111_000 * max(math.cos(math.radians(lat)), 0.001))

    params = {
        "geometry": f"{lng - lng_offset},{lat - lat_offset},{lng + lng_offset},{lat + lat_offset}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": _VG_OUT_FIELDS,
        "returnGeometry": "true",
        "resultRecordCount": 1000,
        "f": "json",
    }

    start = time.monotonic()
    data = arcgis_get_with_retry(VG_LAYER5_URL, params)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    # arcgis_get_with_retry returns {} on ANY failure (circuit open, 429, 5xx,
    # ArcGIS error payload). A genuine empty result is {"features": []}. The
    # missing KEY must raise — otherwise a failed VG query is indistinguishable
    # from "zero comparable lots nearby" (the da_outcome silent-failure class).
    if "features" not in data:
        raise RuntimeError("VG valuation query failed (transport or ArcGIS error)")
    features = data.get("features") or []
    logger.info("vg_layer5 query: %d raw features in %dms", len(features), elapsed_ms)

    if not features:
        return ComparableAnalysis(
            subject_area_m2=lot_area_m2,
            comparable_count=0,
            comparables=[],
        )

    min_area = lot_area_m2 * (1 - area_tolerance)
    max_area = lot_area_m2 * (1 + area_tolerance)
    comparables: list[ComparableProperty] = []
    subject_value: Optional[int] = None

    for f in features:
        attrs = f.get("attributes") or {}
        geom = f.get("geometry") or {}

        propid = attrs.get("propid")
        zone_desc = attrs.get("zone_desc") or ""
        area = parse_area(attrs.get("prop_area"))
        value = parse_land_value(attrs.get("val1_lv"))
        val_date = attrs.get("val1_bd")

        if area is None or value is None:
            continue

        # Zone filter: zone_desc starts with zone code (e.g. "R2 - Low Density Residential")
        if zone and not zone_desc.startswith(zone):
            continue

        if area < min_area or area > max_area:
            continue

        # Haversine post-filter using Web Mercator geometry
        if geom and "x" in geom and "y" in geom:
            feat_lat, feat_lng = _webmercator_to_wgs84(geom.get("x", 0), geom.get("y", 0))
            dist = _haversine_m(lat, lng, feat_lat, feat_lng)
            if dist > radius_m:
                continue

        comp = ComparableProperty(
            propid=propid or 0,
            address=attrs.get("address") or "",
            zone=zone_desc,
            area_m2=area,
            land_value=value,
            valuation_date=val_date,
        )

        if subject_propid and propid == subject_propid:
            subject_value = value
        else:
            comparables.append(comp)

    if not comparables:
        return ComparableAnalysis(
            subject_value=subject_value,
            subject_area_m2=lot_area_m2,
            comparable_count=0,
            comparables=[],
        )

    values = [c.land_value for c in comparables if c.land_value is not None]
    if not values:
        return ComparableAnalysis(
            subject_value=subject_value,
            subject_area_m2=lot_area_m2,
            comparable_count=len(comparables),
            comparables=comparables,
        )

    median_val = int(statistics.median(values))
    mean_val = int(statistics.mean(values))

    percentile: Optional[float] = None
    signal: Optional[str] = None
    if subject_value is not None and values:
        below = sum(1 for v in values if v < subject_value)
        percentile = round(below / len(values) * 100, 1)

        subject_per_m2 = subject_value / max(lot_area_m2, 1)
        comp_per_m2 = sorted([
            c.land_value / max(c.area_m2, 1)
            for c in comparables
            if c.land_value is not None and c.area_m2 > 0
        ])
        if comp_per_m2:
            p75 = comp_per_m2[int(len(comp_per_m2) * 0.75)]
            p25 = comp_per_m2[int(len(comp_per_m2) * 0.25)]
            if subject_per_m2 > p75:
                signal = "potentially_over"
            elif subject_per_m2 < p25:
                signal = "potentially_under"
            else:
                signal = "in_range"

    return ComparableAnalysis(
        subject_value=subject_value,
        subject_area_m2=lot_area_m2,
        comparable_count=len(comparables),
        median_value=median_val,
        mean_value=mean_val,
        percentile_rank=percentile,
        comparables=comparables,
        assessment_signal=signal,
    )


def get_recent_sales(
    lng: float,
    lat: float,
    radius_m: int = 500,
    years_back: int = 3,
    exclude_strata: bool = False,
) -> list[PropertySale]:
    """Query VG Sales layer for recent sales within radius."""
    lat_offset = radius_m / 111_000
    lng_offset = radius_m / (111_000 * max(math.cos(math.radians(lat)), 0.001))

    params = {
        "geometry": f"{lng - lng_offset},{lat - lat_offset},{lng + lng_offset},{lat + lat_offset}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "outFields": _VG_SALES_OUT_FIELDS,
        "returnGeometry": "false",
        "resultRecordCount": 1000,
        "f": "json",
    }

    start = time.monotonic()
    data = arcgis_get_with_retry(VG_SALES_URL, params)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    # Same fail-loud rule as get_comparable_values: {} = failed query (raise);
    # {"features": []} = genuinely no sales. Never conflate the two.
    if "features" not in data:
        raise RuntimeError("VG sales query failed (transport or ArcGIS error)")
    features = data.get("features") or []
    logger.info("vg_sales query: %d features in %dms", len(features), elapsed_ms)

    cutoff_year = datetime.now().year - years_back
    results: list[PropertySale] = []

    for f in features:
        attrs = f.get("attributes") or {}
        price = attrs.get("price")
        if not price or price <= 0:
            continue

        sale_date_raw = attrs.get("sale_date")
        sale_date = parse_sale_date(sale_date_raw)

        if sale_date and len(sale_date) >= 4:
            try:
                sale_year = int(sale_date[:4])
                if sale_year < cutoff_year:
                    continue
            except ValueError:
                pass

        area = float(attrs.get("area") or 0)
        is_strata = bool(attrs.get("strata"))

        if exclude_strata and is_strata:
            continue

        parts = [
            str(attrs.get("house_no") or ""),
            str(attrs.get("street") or ""),
            str(attrs.get("suburb") or ""),
        ]
        address = " ".join(p for p in parts if p).strip()

        price_per_m2 = round(price / area, 2) if area > 0 else None

        results.append(PropertySale(
            propid=attrs.get("propid") or 0,
            address=address,
            price=price,
            area_m2=area,
            sale_date=sale_date,
            price_per_m2=price_per_m2,
            is_strata=is_strata,
        ))

    return results
