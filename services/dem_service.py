"""
DEM acquisition service — fetches elevation rasters from public NSW/AU services.

Primary: Geoscience Australia 5m LiDAR DEM via WCS (245K km², urban/coastal)
Fallback: NSW SIX Maps 5m photogrammetry DEM via ArcGIS ImageServer (full NSW)

No auth required. CC-BY 4.0 licence.
Data sources documented in: memory/reference-elvis-programmatic-access.md
"""
from __future__ import annotations

import io
import logging
import math
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

# Geoscience Australia — 5m LiDAR-derived DEM (WCS 2.0.1)
GA_WCS_URL = (
    "https://services.ga.gov.au/gis/services/"
    "DEM_LiDAR_5m_2025/MapServer/WCSServer"
)
GA_COVERAGE_ID = "1"

# NSW SIX Maps — 5m photogrammetry-derived DEM (ArcGIS ImageServer)
SIXMAPS_URL = (
    "https://maps.six.nsw.gov.au/arcgis/rest/services/"
    "public/NSW_5M_Elevation/ImageServer"
)

# TIFF magic bytes for content validation
_TIFF_LE = b"II*\x00"  # little-endian
_TIFF_BE = b"MM\x00*"  # big-endian

# Default timeout for remote requests (seconds). The SIX Maps fallback
# (exportImage) is slow AND variable — ~26s typical, but observed >40s. This is
# the TRUE limit on terrain reliability: the brief's outer collection budget is
# moot if this inner HTTP call dies first, so give it real room: 65s.
_TIMEOUT = 65

# GA WCS is tried first but currently returns HTTP 400 (ArcGIS Server Error) for
# every request — it fast-fails in ~9.6s. Cap its per-attempt timeout so a slow
# failure on the broken primary can never consume the budget the working SIX Maps
# fallback needs.
_GA_TIMEOUT_CAP = 12

# Approximate metres-per-degree at the equator
_M_PER_DEG_LAT = 111_320.0


# ---------------------------------------------------------------------------
# Buffer helpers
# ---------------------------------------------------------------------------


def _buffer_to_degrees(lat: float, buffer_m: float) -> tuple[float, float]:
    """Convert a metric buffer to lat/lng degree deltas.

    Returns (d_lat, d_lng) — half-widths of the bounding box in degrees.
    """
    d_lat = buffer_m / _M_PER_DEG_LAT
    d_lng = buffer_m / (_M_PER_DEG_LAT * math.cos(math.radians(lat)))
    return d_lat, d_lng


def _is_tiff(content: bytes) -> bool:
    """Check first 4 bytes for GeoTIFF magic."""
    return len(content) >= 4 and content[:4] in (_TIFF_LE, _TIFF_BE)


# ---------------------------------------------------------------------------
# GA WCS fetch (primary)
# ---------------------------------------------------------------------------


def _fetch_ga_wcs(
    lat: float,
    lng: float,
    buffer_m: float,
    timeout: float = _TIMEOUT,
) -> Optional[io.BytesIO]:
    """Fetch DEM region from GA 5m LiDAR WCS.

    Tries WCS 1.0.0 (matches existing codebase pattern in flood_truth.py),
    falls back to WCS 2.0.1 if the server rejects 1.0.0.

    Returns BytesIO containing a GeoTIFF, or None on failure.
    """
    d_lat, d_lng = _buffer_to_degrees(lat, buffer_m)
    bbox_str = (
        f"{lng - d_lng},{lat - d_lat},"
        f"{lng + d_lng},{lat + d_lat}"
    )

    # Cap GA's per-attempt timeout — it currently fast-fails (HTTP 400) and must
    # never starve the working SIX Maps fallback of the budget it needs.
    timeout = min(timeout, _GA_TIMEOUT_CAP)

    # 5m ≈ 0.00005° at this latitude
    res = "0.00005"

    # --- Attempt WCS 1.0.0 ---
    params_v1 = {
        "service": "WCS",
        "version": "1.0.0",
        "request": "GetCoverage",
        "coverage": GA_COVERAGE_ID,
        "format": "GeoTIFF",
        "bbox": bbox_str,
        "crs": "EPSG:4326",
        "resx": res,
        "resy": res,
    }

    try:
        r = requests.get(GA_WCS_URL, params=params_v1, timeout=timeout)
        if r.status_code < 400 and _is_tiff(r.content):
            logger.info("GA WCS 1.0.0: %d bytes for (%.4f,%.4f) buf=%dm", len(r.content), lat, lng, buffer_m)
            return io.BytesIO(r.content)
        logger.info("GA WCS 1.0.0 rejected (status=%d), trying 2.0.1", r.status_code)
    except requests.RequestException as e:
        logger.warning("GA WCS 1.0.0 failed: %s — trying 2.0.1", e)

    # --- Fallback WCS 2.0.1 ---
    # Axis labels for this coverage are "y x" (EPSG:4283), NOT "Lat"/"Long" —
    # the old labels returned an InvalidAxisLabel ServiceException. (GA still
    # rejects the GetCoverage on another param; SIX Maps is the working path.)
    params_v2 = {
        "service": "WCS",
        "version": "2.0.1",
        "request": "GetCoverage",
        "CoverageId": f"Coverage{GA_COVERAGE_ID}",
        "format": "image/tiff",
        "subset": [
            f"y({lat - d_lat},{lat + d_lat})",
            f"x({lng - d_lng},{lng + d_lng})",
        ],
    }

    try:
        r = requests.get(GA_WCS_URL, params=params_v2, timeout=timeout)
        r.raise_for_status()
        if _is_tiff(r.content):
            logger.info("GA WCS 2.0.1: %d bytes for (%.4f,%.4f) buf=%dm", len(r.content), lat, lng, buffer_m)
            return io.BytesIO(r.content)
        logger.warning("GA WCS 2.0.1: response is not TIFF (%d bytes, ct=%s)", len(r.content), r.headers.get("Content-Type"))
        return None
    except requests.RequestException as e:
        logger.warning("GA WCS 2.0.1 failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# NSW SIX Maps fallback
# ---------------------------------------------------------------------------


def _fetch_sixmaps(
    lat: float,
    lng: float,
    buffer_m: float,
    timeout: float = _TIMEOUT,
) -> Optional[io.BytesIO]:
    """Fetch DEM region from NSW SIX Maps 5m ImageServer (exportImage).

    Full NSW coverage (photogrammetry-derived, lower accuracy than GA LiDAR).
    """
    d_lat, d_lng = _buffer_to_degrees(lat, buffer_m)

    # Pixel count: buffer_m * 2 / 5m resolution
    dim = max(int(buffer_m * 2 / 5), 100)

    params = {
        "bbox": (
            f"{lng - d_lng},{lat - d_lat},"
            f"{lng + d_lng},{lat + d_lat}"
        ),
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": f"{dim},{dim}",
        "format": "tiff",
        "interpolation": "RSP_BilinearInterpolation",
        "f": "image",
    }

    try:
        r = requests.get(
            f"{SIXMAPS_URL}/exportImage",
            params=params,
            timeout=timeout,
        )
        r.raise_for_status()
        if _is_tiff(r.content):
            logger.info("SIX Maps: %d bytes for (%.4f,%.4f) buf=%dm", len(r.content), lat, lng, buffer_m)
            return io.BytesIO(r.content)
        logger.warning("SIX Maps: response is not TIFF (%d bytes)", len(r.content))
        return None
    except requests.RequestException as e:
        logger.warning("SIX Maps fetch failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


# prior-art-checked: this module's own fetch gains a provider-returning
# variant so consumers can record WHICH source actually served the DEM —
# previously the GA-vs-SIX-Maps decision was only logged, and terrain's
# static "Geoscience Australia 5m DEM" claim was asserted even for SIX Maps
# fallback data (campaign item 4 census). No new source is added.
def fetch_dem_region_with_provider(
    lat: float,
    lng: float,
    buffer_m: float = 500,
    timeout: float = _TIMEOUT,
) -> tuple[io.BytesIO, str]:
    """As fetch_dem_region, but also returns which provider actually served
    the raster: 'ga_wcs_5m' or 'six_maps_elevation'."""
    result = _fetch_ga_wcs(lat, lng, buffer_m, timeout)
    if result is not None:
        return result, "ga_wcs_5m"

    logger.info("GA WCS unavailable, falling back to SIX Maps for (%.4f,%.4f)", lat, lng)
    result = _fetch_sixmaps(lat, lng, buffer_m, timeout)
    if result is not None:
        return result, "six_maps_elevation"

    raise RuntimeError(
        f"DEM fetch failed for ({lat:.4f}, {lng:.4f}) buffer={buffer_m}m — "
        "both GA WCS and SIX Maps returned no data"
    )


def fetch_dem_region(
    lat: float,
    lng: float,
    buffer_m: float = 500,
    timeout: float = _TIMEOUT,
) -> io.BytesIO:
    """Fetch a 5m DEM GeoTIFF for the area around (lat, lng).

    Tries GA WCS first (higher quality LiDAR), falls back to NSW SIX Maps
    (full state coverage). Raises RuntimeError if both fail.

    Args:
        lat: Latitude (WGS84)
        lng: Longitude (WGS84)
        buffer_m: Half-width of bounding box in metres (default 500 = 1km²)
        timeout: HTTP timeout in seconds

    Returns:
        io.BytesIO containing a GeoTIFF raster
    """
    data, _provider = fetch_dem_region_with_provider(lat, lng, buffer_m, timeout)
    return data
