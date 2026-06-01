"""
Terrain analysis service — whitebox-tools terrain metrics + flood susceptibility.

Stage A (ships immediately): slope, aspect, elevation, drainage, ruggedness
Stage B (gated behind calibration): HAND, ponding, TWI, composite flood score

Data source: 5m DEM via dem_service.py (GA WCS / SIX Maps)
Processing: whitebox-tools (legacy pip package, subprocess-based)
Memory: ~30 MB peak at 5m for 500m buffer, ~50 MB for 5000m buffer

POST /pipeline/terrain-analysis
"""
from __future__ import annotations

import logging
import math
import os
import tempfile
from typing import Optional

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from dem_service import fetch_dem_region
except ImportError:
    from services.dem_service import fetch_dem_region

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["satellite"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Stream extraction threshold for HAND — UNCALIBRATED placeholder.
# Must be calibrated against Copernicus EMS flood extents (EMSR567/570/586)
# before FloodSusceptibilityDetail can be shipped to users.
# See: memory/reference-flood-calibration-workflow.md
HAND_STREAM_THRESHOLD = 1000.0  # flow accumulation cell count

# HAND classification thresholds (metres above nearest drainage)
# These are starting points — will be refined during calibration.
_HAND_THRESHOLDS = {
    "very_high": 2.0,
    "high": 5.0,
    "moderate": 10.0,
    "low": 15.0,
    # > 15m = very_low
}

# TWI classification thresholds
_TWI_THRESHOLDS = {
    "very_high": 12.0,
    "high": 9.0,
    "moderate": 6.0,
    # < 6 = low
}

# Compass direction bins (centre of each 45° sector)
_COMPASS_DIRS = [
    (0, "N"), (45, "NE"), (90, "E"), (135, "SE"),
    (180, "S"), (225, "SW"), (270, "W"), (315, "NW"), (360, "N"),
]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class TerrainRequest(BaseModel):
    address: str = ""
    lat: float
    lng: float
    include_flood_susceptibility: bool = False


class TerrainAnalysisDetail(BaseModel):
    """Terrain metrics from whitebox-tools + 5m DEM."""
    slope_mean_deg: Optional[float] = None
    slope_max_deg: Optional[float] = None
    aspect_dominant_deg: Optional[float] = None
    aspect_direction: Optional[str] = None
    elevation_min_m: Optional[float] = None
    elevation_max_m: Optional[float] = None
    elevation_range_m: Optional[float] = None
    drainage_direction: Optional[str] = None
    terrain_ruggedness: Optional[float] = None


class FloodSusceptibilityDetail(BaseModel):
    """Terrain-based flood susceptibility from HAND + ponding + TWI."""
    hand_min_m: Optional[float] = None
    hand_mean_m: Optional[float] = None
    hand_class: Optional[str] = None
    ponding_max_depth_m: Optional[float] = None
    ponding_has_risk: Optional[bool] = None
    twi_mean: Optional[float] = None
    twi_class: Optional[str] = None
    composite_score: Optional[float] = None
    composite_class: Optional[str] = None
    disclaimer: str = "Indicative topographic screening only — not a flood study"


class TerrainResponse(BaseModel):
    terrain: Optional[TerrainAnalysisDetail] = None
    flood_susceptibility: Optional[FloodSusceptibilityDetail] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _aspect_to_compass(degrees: float) -> str:
    """Convert aspect angle (0-360, clockwise from north) to compass direction."""
    if math.isnan(degrees) or degrees < 0:
        return "flat"
    deg = degrees % 360
    # Find the closest compass direction
    for i in range(len(_COMPASS_DIRS) - 1):
        mid = (_COMPASS_DIRS[i][0] + _COMPASS_DIRS[i + 1][0]) / 2
        if deg < mid:
            return _COMPASS_DIRS[i][1]
    return "N"


def _classify_hand(hand_m: float) -> str:
    """Classify HAND value into flood susceptibility category."""
    if hand_m < _HAND_THRESHOLDS["very_high"]:
        return "very_high"
    if hand_m < _HAND_THRESHOLDS["high"]:
        return "high"
    if hand_m < _HAND_THRESHOLDS["moderate"]:
        return "moderate"
    if hand_m < _HAND_THRESHOLDS["low"]:
        return "low"
    return "very_low"


def _classify_twi(twi: float) -> str:
    """Classify TWI value into wetness category."""
    if twi >= _TWI_THRESHOLDS["very_high"]:
        return "very_high"
    if twi >= _TWI_THRESHOLDS["high"]:
        return "high"
    if twi >= _TWI_THRESHOLDS["moderate"]:
        return "moderate"
    return "low"


def _compute_composite_score(
    hand_m: float,
    ponding_depth: float,
    twi: float,
    slope_deg: float,
) -> float:
    """Compute composite flood susceptibility score (0-100).

    Higher = more susceptible. Weights are initial estimates —
    will be refined during calibration against observed flood extents.
    """
    # Normalise each metric to 0-1 (higher = more susceptible)
    hand_norm = max(0, 1 - hand_m / 20.0)  # 0m=1.0, 20m+=0.0
    pond_norm = min(ponding_depth / 1.0, 1.0)  # 0m=0.0, 1m+=1.0
    twi_norm = min(twi / 15.0, 1.0)  # 0=0.0, 15+=1.0
    slope_norm = max(0, 1 - slope_deg / 15.0)  # 0°=1.0, 15°+=0.0

    # Weighted sum — HAND dominates, others are complementary
    score = (
        0.45 * hand_norm
        + 0.20 * pond_norm
        + 0.20 * twi_norm
        + 0.15 * slope_norm
    )
    return round(score * 100, 1)


def _classify_composite(score: float) -> str:
    """Classify composite score."""
    if score >= 70:
        return "very_high"
    if score >= 50:
        return "high"
    if score >= 30:
        return "moderate"
    if score >= 15:
        return "low"
    return "very_low"


def _run_tool(tool_fn, *args, **kwargs) -> None:
    """Run a whitebox tool, raise on failure."""
    ret = tool_fn(*args, **kwargs)
    if ret != 0:
        name = getattr(tool_fn, "__name__", str(tool_fn))
        raise RuntimeError(f"whitebox {name} failed (return code {ret})")


def _read_band(work_dir: str, filename: str) -> np.ndarray:
    """Read band 1 from a GeoTIFF, masking nodata to NaN."""
    path = os.path.join(work_dir, filename)
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype(np.float64)
        nodata = ds.nodata
    if nodata is not None:
        arr[arr == nodata] = np.nan
    return arr


def _valid_stats(arr: np.ndarray) -> np.ndarray:
    """Return array with NaN/inf removed for stats computation."""
    return arr[np.isfinite(arr)]


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def _run_terrain_chain(work_dir: str) -> dict:
    """Run terrain analysis tools on dem.tif in work_dir.

    Returns dict with TerrainAnalysisDetail field values.
    """
    import whitebox

    wbt = whitebox.WhiteboxTools()
    wbt.set_working_dir(work_dir)
    wbt.set_verbose_mode(False)

    # Slope (degrees)
    _run_tool(wbt.slope, "dem.tif", "slope.tif", zfactor=1.0)

    # Aspect (degrees clockwise from north)
    _run_tool(wbt.aspect, "dem.tif", "aspect.tif", zfactor=1.0)

    # Read and compute stats
    dem_arr = _read_band(work_dir, "dem.tif")
    slope_arr = _read_band(work_dir, "slope.tif")
    aspect_arr = _read_band(work_dir, "aspect.tif")

    valid_dem = _valid_stats(dem_arr)
    valid_slope = _valid_stats(slope_arr)
    valid_aspect = _valid_stats(aspect_arr)

    # Dominant aspect: circular mean
    if len(valid_aspect) > 0:
        rad = np.radians(valid_aspect)
        mean_sin = np.nanmean(np.sin(rad))
        mean_cos = np.nanmean(np.cos(rad))
        dominant_aspect = np.degrees(np.arctan2(mean_sin, mean_cos)) % 360
    else:
        dominant_aspect = float("nan")

    # Drainage direction at centre pixel
    centre_row = dem_arr.shape[0] // 2
    centre_col = dem_arr.shape[1] // 2
    centre_aspect = aspect_arr[centre_row, centre_col]
    drainage_dir = _aspect_to_compass(centre_aspect) if np.isfinite(centre_aspect) else None

    # Terrain ruggedness — std dev of slope is a simple proxy
    ruggedness = float(np.nanstd(valid_slope)) if len(valid_slope) > 0 else None

    return {
        "slope_mean_deg": round(float(np.nanmean(valid_slope)), 2) if len(valid_slope) > 0 else None,
        "slope_max_deg": round(float(np.nanmax(valid_slope)), 2) if len(valid_slope) > 0 else None,
        "aspect_dominant_deg": round(float(dominant_aspect), 1) if np.isfinite(dominant_aspect) else None,
        "aspect_direction": _aspect_to_compass(dominant_aspect),
        "elevation_min_m": round(float(np.nanmin(valid_dem)), 2) if len(valid_dem) > 0 else None,
        "elevation_max_m": round(float(np.nanmax(valid_dem)), 2) if len(valid_dem) > 0 else None,
        "elevation_range_m": round(float(np.nanmax(valid_dem) - np.nanmin(valid_dem)), 2) if len(valid_dem) > 0 else None,
        "drainage_direction": drainage_dir,
        "terrain_ruggedness": round(float(ruggedness), 3) if ruggedness is not None else None,
    }


def _run_flood_chain(work_dir: str, slope_arr: Optional[np.ndarray] = None) -> dict:
    """Run HAND + ponding + TWI on dem.tif in work_dir.

    Expects a larger DEM (5000m buffer) for catchment-scale hydrology.
    Returns dict with FloodSusceptibilityDetail field values.
    """
    import whitebox

    wbt = whitebox.WhiteboxTools()
    wbt.set_working_dir(work_dir)
    wbt.set_verbose_mode(False)

    # 1. Breach depressions (DEM conditioning — preferred over fill for HAND)
    _run_tool(wbt.breach_depressions, "dem.tif", "breached.tif")

    # 2. Flow accumulation (D-infinity specific contributing area)
    _run_tool(
        wbt.d_inf_flow_accumulation,
        "breached.tif", "flowacc.tif",
        out_type="Specific Contributing Area",
        log=False,
    )

    # 3. Extract streams from flow accumulation
    _run_tool(
        wbt.extract_streams,
        "flowacc.tif", "streams.tif",
        threshold=HAND_STREAM_THRESHOLD,
        zero_background=False,
    )

    # 4. HAND — elevation above nearest stream
    _run_tool(
        wbt.elevation_above_stream,
        "breached.tif", "streams.tif", "hand.tif",
    )

    # 5. Depth in sink (ponding)
    _run_tool(wbt.depth_in_sink, "dem.tif", "ponding.tif", zero_background=False)

    # 6. Slope for TWI (if not provided)
    if slope_arr is None:
        _run_tool(wbt.slope, "dem.tif", "slope_flood.tif", zfactor=1.0)

    # 7. TWI = ln(SCA / tan(slope))
    # whitebox wetness_index needs SCA + slope as inputs
    sca_path = "flowacc.tif"
    slope_path = "slope_flood.tif" if slope_arr is None else "slope.tif"
    _run_tool(wbt.wetness_index, sca_path, slope_path, "twi.tif")

    # Read outputs — extract stats at property centre
    hand_arr = _read_band(work_dir, "hand.tif")
    ponding_arr = _read_band(work_dir, "ponding.tif")
    twi_arr = _read_band(work_dir, "twi.tif")

    # Stats from centre region (inner 20% — property footprint area)
    h, w = hand_arr.shape
    r1, r2 = int(h * 0.4), int(h * 0.6)
    c1, c2 = int(w * 0.4), int(w * 0.6)

    hand_centre = _valid_stats(hand_arr[r1:r2, c1:c2])
    ponding_centre = _valid_stats(ponding_arr[r1:r2, c1:c2])
    twi_centre = _valid_stats(twi_arr[r1:r2, c1:c2])

    hand_min = float(np.nanmin(hand_centre)) if len(hand_centre) > 0 else None
    hand_mean = float(np.nanmean(hand_centre)) if len(hand_centre) > 0 else None
    ponding_max = float(np.nanmax(ponding_centre)) if len(ponding_centre) > 0 else None
    twi_mean = float(np.nanmean(twi_centre)) if len(twi_centre) > 0 else None

    # Read slope for composite (centre region)
    if slope_arr is not None:
        slope_centre = _valid_stats(slope_arr[r1:r2, c1:c2])
    else:
        slope_full = _read_band(work_dir, "slope_flood.tif")
        slope_centre = _valid_stats(slope_full[r1:r2, c1:c2])
    slope_mean = float(np.nanmean(slope_centre)) if len(slope_centre) > 0 else 0.0

    # Composite scoring
    composite = None
    composite_cls = None
    if hand_mean is not None and twi_mean is not None:
        composite = _compute_composite_score(
            hand_m=hand_mean,
            ponding_depth=ponding_max or 0.0,
            twi=twi_mean,
            slope_deg=slope_mean,
        )
        composite_cls = _classify_composite(composite)

    return {
        "hand_min_m": round(hand_min, 2) if hand_min is not None else None,
        "hand_mean_m": round(hand_mean, 2) if hand_mean is not None else None,
        "hand_class": _classify_hand(hand_mean) if hand_mean is not None else None,
        "ponding_max_depth_m": round(ponding_max, 3) if ponding_max is not None else None,
        "ponding_has_risk": ponding_max is not None and ponding_max > 0.05,
        "twi_mean": round(twi_mean, 2) if twi_mean is not None else None,
        "twi_class": _classify_twi(twi_mean) if twi_mean is not None else None,
        "composite_score": composite,
        "composite_class": composite_cls,
        "disclaimer": "Indicative topographic screening only — not a flood study",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_terrain_analysis(
    lat: float,
    lng: float,
    include_flood: bool = False,
) -> dict:
    """Run terrain analysis for a property location.

    Args:
        lat: Latitude (WGS84)
        lng: Longitude (WGS84)
        include_flood: If True, also run HAND flood susceptibility
                       (requires calibrated HAND_STREAM_THRESHOLD)

    Returns:
        Dict with keys matching TerrainAnalysisDetail fields,
        plus optional FloodSusceptibilityDetail fields under "flood_susceptibility".
    """
    with tempfile.TemporaryDirectory(prefix="wbt_") as work_dir:
        # Fetch DEM and write to work_dir
        dem_bytes = fetch_dem_region(lat, lng, buffer_m=500)
        dem_path = os.path.join(work_dir, "dem.tif")

        with rasterio.open(dem_bytes) as src:
            profile = src.profile.copy()
            data = src.read(1)
        with rasterio.open(dem_path, "w", **profile) as dst:
            dst.write(data, 1)

        # Terrain analysis (500m buffer)
        result = _run_terrain_chain(work_dir)

        # Flood susceptibility (larger buffer for catchment context)
        if include_flood:
            flood_dir = tempfile.mkdtemp(prefix="wbt_flood_", dir=work_dir)
            dem_bytes_lg = fetch_dem_region(lat, lng, buffer_m=5000)
            dem_flood_path = os.path.join(flood_dir, "dem.tif")

            with rasterio.open(dem_bytes_lg) as src:
                profile_lg = src.profile.copy()
                data_lg = src.read(1)
            with rasterio.open(dem_flood_path, "w", **profile_lg) as dst:
                dst.write(data_lg, 1)

            # Also write slope.tif from terrain chain for TWI computation
            slope_path_src = os.path.join(work_dir, "slope.tif")
            if os.path.exists(slope_path_src):
                slope_arr = _read_band(work_dir, "slope.tif")
                # Slope is from 500m buffer — flood needs its own at 5000m
                result["flood_susceptibility"] = _run_flood_chain(flood_dir)
            else:
                result["flood_susceptibility"] = _run_flood_chain(flood_dir)

    return result


# ---------------------------------------------------------------------------
# FastAPI endpoint
# ---------------------------------------------------------------------------


@router.post("/terrain-analysis")
def terrain_analysis_endpoint(req: TerrainRequest):
    """Terrain analysis for a property location.

    Returns slope, aspect, elevation, drainage direction, and ruggedness.
    Optionally includes flood susceptibility (HAND + ponding + TWI).
    """
    try:
        result = run_terrain_analysis(
            req.lat, req.lng, include_flood=req.include_flood_susceptibility,
        )
        terrain = TerrainAnalysisDetail(**{
            k: v for k, v in result.items()
            if k in TerrainAnalysisDetail.model_fields
        })
        flood = None
        if "flood_susceptibility" in result and result["flood_susceptibility"]:
            flood = FloodSusceptibilityDetail(**result["flood_susceptibility"])

        return TerrainResponse(terrain=terrain, flood_susceptibility=flood)
    except Exception as e:
        logger.exception("Terrain analysis failed for (%.4f, %.4f): %s", req.lat, req.lng, e)
        raise HTTPException(status_code=500, detail=str(e))
