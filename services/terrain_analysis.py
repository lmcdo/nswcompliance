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
from enum import Enum
from typing import Optional

import numpy as np
import rasterio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# prior-art-checked: adds the provider-returning DEM variant plus the shared
# item-4 modules created this session — extending this pipeline's own path.
try:
    from dem_service import fetch_dem_region_with_provider
    from execution_manifest import build_manifest
    from geometry_checks import check_point_nsw
except ImportError:
    from services.dem_service import fetch_dem_region_with_provider
    from services.execution_manifest import build_manifest
    from services.geometry_checks import check_point_nsw

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["satellite"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# DEM buffer half-width (metres) fetched for the terrain chain. The buffer is
# needed for landform / solar-shadow / drainage context, but site gradient,
# elevation and ruggedness must be read from the LOT, not the neighbourhood —
# see _site_values and SITE_WINDOW_M.
TERRAIN_BUFFER_M = 500.0

# Algorithm revision for execution manifests (campaign item 4): whitebox-tools
# chain + interpretation thresholds. Bump on method change, not per deploy.
ALGORITHM_VERSION = "terrain-wbt-geomorph-1.0"

# Side length (metres) of the square, centred on the property, used for the
# gradient / elevation / ruggedness findings. ~90m comfortably covers a typical
# medium-density lot plus a small margin for geocode offset, while excluding the
# surrounding terrain that made these findings over-report — a steep bank 400m
# away is not the building pad.
SITE_WINDOW_M = 90.0

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

# Geomorphon landform classes (whitebox output values when forms=True)
_GEOMORPHON_LABELS = {
    1: "flat",
    2: "peak",
    3: "ridge",
    4: "shoulder",
    5: "spur",
    6: "slope",
    7: "hollow",
    8: "footslope",
    9: "valley",
    10: "pit",
}


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
    landform_class: Optional[int] = None
    landform_type: Optional[str] = None
    daylight_fraction: Optional[float] = None
    # Indicative shaded-relief image of the lot's DEM, as a base64 PNG data URI.
    hillshade_png_b64: Optional[str] = None


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


class TerrainSeverity(str, Enum):
    """Constraint severity for terrain findings."""
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class TerrainFinding(BaseModel):
    """Single terrain interpretation with full methodology transparency."""
    id: str
    title: str
    metric: dict
    classification: str
    narrative: str
    methodology: str
    severity: TerrainSeverity
    relevance: list[str]
    action_trigger: Optional[str] = None
    estimated_cost: Optional[str] = None


class TerrainInterpretation(BaseModel):
    """Structured interpretation of terrain analysis for professional users."""
    findings: list[TerrainFinding]
    data_source: str = (
        "Elevation model (provider not recorded for this run)"
    )
    methodology_note: str = (
        "Terrain metrics derived from whitebox-tools geomorphometric analysis. Landform, "
        "aspect and solar-shadow metrics use a 500m buffer around the property centroid; "
        "site gradient, elevation and ruggedness are read from a ~90m window over the lot "
        "footprint so they reflect the building pad, not the neighbourhood. Slope uses the "
        "Horn (1981) finite-difference method. Landform classification uses the Jasiewicz & Stepinski "
        "(2013) geomorphon algorithm. Daylight fraction computed via annual solar position "
        "modelling (sunrise–sunset, AEST UTC+10). All values are indicative — detailed "
        "design works from site-specific survey data."
    )
    disclaimer: str = (
        "This analysis is derived from a 5m resolution DEM which cannot resolve features "
        "smaller than the grid cell. Localised slope variations, retaining walls, and recent "
        "earthworks are not captured. This is a pre-feasibility screening tool — it does not "
        "replace a registered surveyor's site survey or a geotechnical investigation."
    )


class TerrainResponse(BaseModel):
    terrain: Optional[TerrainAnalysisDetail] = None
    interpretation: Optional[TerrainInterpretation] = None
    flood_susceptibility: Optional[FloodSusceptibilityDetail] = None
    error: Optional[str] = None
    # Campaign item 4: identity of the DEM/config this run actually consumed.
    execution_manifest: Optional[dict] = None


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


def _central_crop_bounds(
    ny: int,
    nx: int,
    buffer_m: float = TERRAIN_BUFFER_M,
    window_m: float = SITE_WINDOW_M,
) -> tuple[int, int, int, int]:
    """(r0, r1, c0, c1) of a window_m square centred on a DEM that spans
    2*buffer_m metres across nx columns. Pure arithmetic (no numpy) so it is
    unit-testable without native deps. A floor of 3px keeps a minimum window."""
    cell_m = (2.0 * buffer_m) / nx if nx else 0.0
    half_px = max(3, int(round((window_m / 2.0) / cell_m))) if cell_m > 0 else 3
    r0, r1 = max(0, ny // 2 - half_px), min(ny, ny // 2 + half_px + 1)
    c0, c1 = max(0, nx // 2 - half_px), min(nx, nx // 2 + half_px + 1)
    return r0, r1, c0, c1


def _site_values(
    arr: np.ndarray,
    buffer_m: float = TERRAIN_BUFFER_M,
    window_m: float = SITE_WINDOW_M,
) -> np.ndarray:
    """Return the finite values within a central window_m square of the DEM.

    The DEM spans 2*buffer_m metres across by construction (fetch_dem_region),
    so the ground cell size is (2*buffer_m / n_cols). We crop a window_m square
    centred on the array — the property footprint — and return its valid values.

    This exists so site gradient / elevation / ruggedness reflect the building
    pad rather than the whole 500m buffer: averaging a lot's grade over ~1 km²
    of roads, neighbours and creek-lines over-reports the constraint (a steep
    bank hundreds of metres away is not the pad).

    Falls back to the full array if the window contains no valid pixels (tiny or
    heavily-nodata DEMs).
    """
    if arr.ndim != 2 or arr.size == 0:
        return _valid_stats(arr)
    ny, nx = arr.shape
    r0, r1, c0, c1 = _central_crop_bounds(ny, nx, buffer_m, window_m)
    window = _valid_stats(arr[r0:r1, c0:c1])
    if window.size == 0:
        return _valid_stats(arr)
    return window


# prior-art-checked: no existing hillshade/shaded-relief renderer in services/
# (grep hillshade|LightSource|shaded_relief = none). This renders the DEM that
# _run_terrain_chain already loads into a presentation PNG — it is NOT a data
# source and does not fetch anything.
def _render_hillshade_png(dem_arr, max_px: int = 256) -> Optional[str]:
    """Render a coloured shaded-relief PNG of the DEM as a base64 data URI.

    Pure presentation: a shaded relief of the *same* DEM the terrain metrics are
    computed from (no extra fetch, no figure/backend — just LightSource.shade).
    Lighter = higher ground; the shadows convey slope and aspect.

    Failure-safety is the contract: ANY error returns None so the terrain
    numbers are never affected by a rendering problem.

    Args:
        dem_arr: 2-D elevation array (float, NaN at nodata) from _read_band.
        max_px: longest edge of the output image; the DEM is downsampled to fit
                so the data URI stays small.

    Returns:
        A ``data:image/png;base64,...`` string, or None if it can't be rendered.
    """
    try:
        import base64
        import io

        from matplotlib import colormaps
        from matplotlib.colors import LightSource, Normalize
        from PIL import Image

        arr = np.asarray(dem_arr, dtype=np.float64)
        if arr.ndim != 2 or arr.size == 0:
            return None
        finite = np.isfinite(arr)
        if int(finite.sum()) < 16:  # too little real data to depict
            return None

        # Downsample large DEMs so the inline data URI stays small.
        longest = max(arr.shape[0], arr.shape[1])
        step = max(1, int(longest // max_px))
        if step > 1:
            arr = arr[::step, ::step]
            finite = np.isfinite(arr)

        vmin = float(np.nanmin(arr))
        vmax = float(np.nanmax(arr))
        # Fill nodata with the low value so the shader doesn't choke; masked back
        # out via alpha below.
        filled = np.where(finite, arr, vmin)

        ls = LightSource(azdeg=315, altdeg=45)
        norm = Normalize(vmin=vmin, vmax=vmax if vmax > vmin else vmin + 1.0)
        # vert_exag lifts gentle urban relief into something legible; dx/dy = 5 m
        # DEM cell. This is an indicative diagram, not a measured surface.
        rgb = ls.shade(
            filled,
            cmap=colormaps["terrain"],  # noqa: bracket-access (built-in mpl colormap)
            norm=norm,
            blend_mode="soft",
            vert_exag=2.5,
            dx=5.0,
            dy=5.0,
        )  # -> (H, W, 4) floats in 0..1

        rgba = (np.clip(rgb, 0.0, 1.0) * 255).astype(np.uint8)
        rgba[..., 3] = np.where(finite, 255, 0).astype(np.uint8)  # nodata transparent

        img = Image.fromarray(rgba, mode="RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        if len(b64) > 400_000:  # guard the brief payload size
            return None
        return f"data:image/png;base64,{b64}"
    except Exception:
        logger.warning("hillshade render failed", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Terrain interpretation — professional-grade findings from raw metrics
# ---------------------------------------------------------------------------

_SLOPE_METHOD = (
    "Slope computed using Horn (1981) finite-difference method on 5m DEM cells, "
    "summarised over a ~90m window centred on the property (the lot footprint) "
    "rather than the wider analysis buffer, so the gradient reflects the building "
    "pad and not surrounding terrain. Slope values at 5m resolution may understate "
    "localised gradients — a 2m cliff within a single cell would not be resolved."
)

_LANDFORM_METHOD = (
    "Landform classification via Jasiewicz & Stepinski (2013) geomorphon algorithm "
    "at 250m search radius (50 cells at 5m resolution). Classification is for the "
    "property centroid cell — larger sites may span multiple landform types."
)

_ASPECT_METHOD = (
    "Dominant aspect computed as the circular mean of all valid aspect values within "
    "the 500m analysis buffer. Solar implications are qualitative assessments based "
    "on latitude (~33.8\u00b0S for Sydney) and standard ADG / BASIX performance "
    "expectations. Actual solar access depends on surrounding built form and "
    "vegetation, which are not captured in the DEM."
)

_SOLAR_METHOD = (
    "Annual daylight fraction computed using whitebox-tools time_in_daylight algorithm. "
    "Traces the solar azimuth and elevation path for every day of the year (sunrise to "
    "sunset, AEST UTC+10) and determines the fraction of daylight hours with clear "
    "line-of-sight to the sun from the site, considering terrain obstruction only. "
    "Vegetation and built form are not modelled. Maximum shadow-casting distance: "
    "500m (100 cells at 5m resolution)."
)

_ELEVATION_METHOD = (
    "Elevation values extracted from the 5m DEM over a ~90m window centred on the "
    "property (the lot footprint), not the wider analysis buffer. "
    "Values in metres above Australian Height Datum (AHD). Absolute elevation "
    "accuracy is \u00b15m — do not use for flood planning level compliance without "
    "a registered survey. Relative elevation differences across the lot are more "
    "reliable (\u00b11\u20132m) as systematic vertical bias cancels."
)

_RUGGEDNESS_METHOD = (
    "Terrain ruggedness computed as the standard deviation of slope values (degrees) "
    "over a ~90m window centred on the property (the lot footprint), not the wider "
    "analysis buffer. Captures gradient variability rather than "
    "magnitude — a consistent steep slope has low ruggedness; an undulating surface "
    "has high ruggedness. Features smaller than 5m are not resolved."
)

# Landform severity mapping
_LANDFORM_SEVERITY = {
    "flat": TerrainSeverity.GREEN,
    "spur": TerrainSeverity.GREEN,
    "ridge": TerrainSeverity.GREEN,
    "peak": TerrainSeverity.GREEN,
    "footslope": TerrainSeverity.AMBER,
    "shoulder": TerrainSeverity.AMBER,
    "slope": TerrainSeverity.AMBER,
    "hollow": TerrainSeverity.RED,
    "valley": TerrainSeverity.RED,
    "pit": TerrainSeverity.RED,
}

# Landform narrative templates — keyed by landform_type
_LANDFORM_NARRATIVES: dict[str, str] = {
    "flat": (
        "Geomorphon classification identifies this site as level terrain (flat landform). "
        "Surface water drains as sheet flow, predominantly towards the {drain}. "
        "Drainage design can follow standard practices. Foundation conditions are "
        "typically uniform, though fill and reactive clay soils are not resolved by the "
        "DEM — a geotechnical investigation identifies them."
    ),
    "footslope": (
        "This site occupies a footslope position — the transition zone where slope gradient "
        "decreases and overland flow from upslope accumulates. Surface water drains towards "
        "the {drain}. Footslope sites commonly receive concentrated runoff from upslope "
        "catchments, which must be managed through site drainage design. Colluvial (slope-wash) "
        "soils at footslope positions can be variable in depth and bearing capacity."
    ),
    "shoulder": (
        "This site occupies a shoulder position — the convex transition from ridge crest to "
        "slope. Drainage is divergent, flowing away from the site predominantly towards the "
        "{drain}. Shoulder sites are generally well-drained but the convex profile may indicate "
        "weathered or residual soils with variable depth to bedrock. The transition zone can "
        "be prone to shallow landslip if disturbed by excavation."
    ),
    "slope": (
        "This site occupies a mid-slope position with drainage flowing predominantly towards "
        "the {drain}. Cross-slope drainage interception will be required upslope of any "
        "building footprint to redirect overland flow. Cross-fall relative to building "
        "orientation drives the cut-and-fill asymmetry."
    ),
    "spur": (
        "This site is located on a convex spur — a projecting ridgeline with drainage diverging "
        "to both sides. The dominant drainage vector is towards the {drain}. Spur positions are "
        "typically well-drained with lower overland flow risk, but may be exposed to wind and "
        "have shallow soil profiles over bedrock."
    ),
    "ridge": (
        "This site occupies a ridge crest position with drainage diverging on both sides, "
        "predominantly towards the {drain}. Ridge sites are typically well-drained with minimal "
        "overland flow risk. However, soil profiles are often thin with shallow bedrock, which "
        "may affect foundation design. Wind exposure is elevated — AS 4055 wind classification "
        "may be higher than surrounding lower-lying sites."
    ),
    "peak": (
        "This site is at a topographic high point (peak landform). Drainage is radially divergent "
        "with no upslope catchment contributing flow. The site will be fully exposed to prevailing "
        "winds — AS 4055 wind classification is the relevant check for this exposure. Soil depth is "
        "typically minimal at peak positions."
    ),
    "hollow": (
        "This site is located in a terrain hollow — a concave landform where overland flow "
        "converges. Drainage concentrates towards the {drain}. Hollows are natural flow paths and "
        "represent the highest overland flood risk in the local terrain. Any development must "
        "address concentrated stormwater flows through the site. If the hollow aligns with a "
        "mapped watercourse or overland flow path, additional council controls under their "
        "flood/stormwater DCP may apply."
    ),
    "valley": (
        "This site is located on a valley floor — the lowest topographic position in the local "
        "terrain. Drainage from surrounding slopes converges through this position, flowing "
        "towards the {drain}. Valley floor sites have the highest exposure to concentrated "
        "overland flow and potential inundation. Floor levels relative to any identified "
        "flood planning level are the relevant check. Soils are typically alluvial with "
        "variable bearing capacity — the ground conditions a geotechnical investigation resolves."
    ),
    "pit": (
        "This site is located in a closed topographic depression (pit). Surface water drains "
        "inward with no natural outlet — ponding will occur during rainfall until infiltration "
        "or evaporation dissipates standing water. This landform requires engineered drainage "
        "to provide a positive outfall, or a detention/infiltration system. Council may require "
        "a stormwater management plan demonstrating that post-development flows do not "
        "exacerbate ponding on adjacent properties."
    ),
}


def _interpret_gradient(d: dict) -> TerrainFinding:
    """Interpret site gradient from slope metrics."""
    mean = d.get("slope_mean_deg") or 0.0
    mx = d.get("slope_max_deg") or 0.0

    if mean < 5 and mx < 10:
        sev = TerrainSeverity.GREEN
        cls = "Gentle gradient"
        narr = (
            f"Mean slope of {mean}\u00b0 across the analysis area with a maximum of "
            f"{mx}\u00b0 indicates a gently grading site. Standard residential construction "
            "methods are generally feasible without significant earthworks. Cut-and-fill "
            "volumes are likely to be minimal."
        )
        action = None
        cost = None
    elif mean < 10 and mx < 20:
        sev = TerrainSeverity.AMBER
        cls = "Moderate gradient"
        narr = (
            f"Mean slope of {mean}\u00b0 with a maximum of {mx}\u00b0 indicates a moderately "
            "grading site. Some cut-and-fill earthworks are likely, and retaining walls may "
            "be required depending on building footprint orientation. Driveway and access "
            "grades: AS 2890.1 sets 1:4 as the residential maximum (1:5 desirable). "
            "Slopes exceeding common local DCP thresholds "
            "(15\u201320% / 8.5\u201311.3\u00b0) trigger geotechnical report "
            "requirements at some councils."
        )
        action = "Geotechnical report may be required — verify against council DCP slope threshold"
        cost = "$3,000\u2013$8,000 (geotechnical investigation if required by council DCP)"
    elif mean < 10:
        sev = TerrainSeverity.AMBER
        cls = "Moderate gradient with localised steep zones"
        narr = (
            f"Mean slope of {mean}\u00b0 is moderate, but localised grades reach {mx}\u00b0. "
            "This suggests an undulating site with steep embankments or escarpment edges. "
            "Where the steepest zones fall relative to the building envelope determines "
            "the earthworks. Stability of any cut faces is the question a geotechnical "
            "investigation resolves, and council is likely to "
            "require a slope analysis diagram with the DA."
        )
        action = "Localised steep zones present — a geotechnical investigation resolves cut-face stability"
        cost = "$3,000\u2013$8,000 (geotechnical investigation)"
    elif mx < 25:
        sev = TerrainSeverity.RED
        cls = "Steep site"
        narr = (
            f"Mean slope of {mean}\u00b0 with a maximum of {mx}\u00b0 indicates a steeply "
            "grading site. Significant earthworks, engineered retaining structures, and "
            "potentially pier-and-beam or split-level construction will be required. Most "
            "NSW councils require a geotechnical investigation for sites with mean gradients "
            "exceeding 15% (8.5\u00b0). Stormwater management will need to address concentrated "
            "overland flow paths. Construction costs are typically 15\u201330% higher than "
            "equivalent flat sites."
        )
        action = "Geotechnical investigation required"
        cost = "$5,000\u2013$15,000 (geotechnical investigation + slope stability assessment)"
    else:
        sev = TerrainSeverity.RED
        cls = "Very steep site"
        narr = (
            f"Mean slope of {mean}\u00b0 with extreme localised grades of {mx}\u00b0 indicates "
            "a highly constrained site. Development feasibility depends on the location and "
            "extent of the steep zones relative to the proposed building envelope. Geotechnical "
            "investigation is mandatory. Slope stability assessment per AS 4678 (Earth-retaining "
            "structures) is likely required. Construction costs will be substantially higher "
            "than flat sites."
        )
        action = "Geotechnical investigation required — slope stability assessment per AS 4678"
        cost = "$5,000\u2013$15,000 (geotechnical investigation + slope stability assessment)"

    return TerrainFinding(
        id="site_gradient",
        title="Site Gradient",
        metric={"slope_mean_deg": mean, "slope_max_deg": mx},
        classification=cls,
        narrative=narr,
        methodology=_SLOPE_METHOD,
        severity=sev,
        relevance=["architect", "structural_engineer", "geotechnical_engineer", "quantity_surveyor"],
        action_trigger=action,
        estimated_cost=cost,
    )


def _interpret_landform(d: dict) -> TerrainFinding:
    """Interpret landform characterisation from geomorphon classification."""
    lf = d.get("landform_type", "flat")
    drain = d.get("drainage_direction") or "downslope"
    sev = _LANDFORM_SEVERITY.get(lf, TerrainSeverity.AMBER)
    narr_template = _LANDFORM_NARRATIVES.get(lf, _LANDFORM_NARRATIVES["slope"])
    narr = narr_template.format(drain=drain)

    action = None
    cost = None
    if lf in ("hollow", "valley"):
        action = "Overland flow path / flood assessment likely required"
        cost = (
            "$2,000\u2013$5,000 (overland flow / stormwater assessment) + "
            "$3,000\u2013$8,000 (geotechnical investigation)"
        )
    elif lf == "pit":
        action = "Engineered drainage solution required — no natural outfall"
        cost = (
            "$2,000\u2013$5,000 (stormwater management plan) + "
            "$3,000\u2013$8,000 (geotechnical investigation)"
        )
    elif lf in ("footslope", "shoulder"):
        action = "Variable soil profile — the condition a geotechnical investigation resolves"
        cost = "$3,000\u2013$8,000 (geotechnical investigation)"

    return TerrainFinding(
        id="landform",
        title="Landform Characterisation",
        metric={"landform_type": lf, "drainage_direction": drain},
        classification=f"{lf.title()} landform",
        narrative=narr,
        methodology=_LANDFORM_METHOD,
        severity=sev,
        relevance=["architect", "civil_engineer", "geotechnical_engineer", "hydraulic_engineer"],
        action_trigger=action,
        estimated_cost=cost,
    )


def _interpret_aspect(d: dict) -> TerrainFinding:
    """Interpret aspect and solar orientation."""
    aspect_dir = d.get("aspect_direction", "N")
    aspect_deg = d.get("aspect_dominant_deg", 0.0)
    slope_mean = d.get("slope_mean_deg", 0.0)

    if slope_mean is not None and slope_mean < 2:
        sev = TerrainSeverity.GREEN
        cls = "Effectively level — aspect not material"
        narr = (
            f"Mean slope of {slope_mean}\u00b0 is effectively level — the dominant aspect "
            f"({aspect_deg}\u00b0 / {aspect_dir}) has minimal practical effect on solar "
            "access or building orientation. ADG solar access requirements (Apartment Design "
            "Guide, SEPP 65) and BASIX thermal performance can be met through building design "
            "rather than site orientation."
        )
    elif aspect_dir in ("N", "NE", "NW"):
        sev = TerrainSeverity.GREEN
        cls = f"{aspect_dir} aspect — favourable solar orientation"
        narr = (
            f"The site has a {aspect_dir} aspect ({aspect_deg}\u00b0) at a mean slope of "
            f"{slope_mean}\u00b0. Northern orientation is the most favourable for solar access "
            "in the Southern Hemisphere. Living areas and private open space oriented towards "
            f"the {aspect_dir} will receive direct winter sun without terrain obstruction — "
            "the orientation ADG Objective 4A (solar access) measures, and the input "
            "BASIX thermal comfort scoring rewards."
        )
    elif aspect_dir in ("E", "W"):
        sev = TerrainSeverity.AMBER
        dir_desc = "morning" if aspect_dir == "E" else "afternoon"
        opp_desc = "afternoon living areas" if aspect_dir == "E" else "morning"
        sev = TerrainSeverity.AMBER
        cls = f"{aspect_dir} aspect — {dir_desc} sun exposure"
        narr = (
            f"The site has a {aspect_dir} aspect ({aspect_deg}\u00b0) at a mean slope of "
            f"{slope_mean}\u00b0. {aspect_dir}-facing orientation provides {dir_desc} sun but "
            "limits midday winter solar penetration to living areas. ADG solar access compliance "
            "(minimum 2 hours direct sun to 70% of apartments between 9am\u20133pm at mid-winter) "
            f"may require careful window placement and floor plate orientation. {aspect_dir}-facing "
            f"sites receive {dir_desc} sun (beneficial for some uses, less so for {opp_desc})."
        )
    elif slope_mean is not None and slope_mean >= 10:
        sev = TerrainSeverity.RED
        cls = f"Steep {aspect_dir} aspect — significant solar constraint"
        narr = (
            f"The site has a {aspect_dir} aspect ({aspect_deg}\u00b0) at a steep mean slope "
            f"of {slope_mean}\u00b0. The combination of steep gradient and south-facing terrain "
            "significantly reduces direct winter sun — the terrain itself casts shadow across the "
            "site during low solar elevation angles. ADG solar access requirements may not be "
            "achievable for multi-unit residential without significant design concessions "
            "(reduced density, increased setbacks, north-facing courtyards cut into the slope). "
            "BASIX heating loads will be elevated."
        )
    else:
        sev = TerrainSeverity.AMBER
        cls = f"{aspect_dir} aspect — reduced solar access"
        narr = (
            f"The site has a {aspect_dir} aspect ({aspect_deg}\u00b0) at a mean slope of "
            f"{slope_mean}\u00b0. South-facing slopes in the Southern Hemisphere receive reduced "
            "direct winter sun, as the terrain partly shadows the site during low solar elevation "
            "angles (May\u2013July). ADG solar access compliance will require design attention — "
            "south-facing apartments may struggle to achieve 2 hours direct sun at mid-winter "
            "without compensatory design measures (larger setbacks, clerestory windows, stepped "
            "massing). BASIX heating loads will be higher than equivalent north-facing sites."
        )

    return TerrainFinding(
        id="aspect_orientation",
        title="Aspect and Orientation",
        metric={"aspect_direction": aspect_dir, "aspect_dominant_deg": aspect_deg, "slope_mean_deg": slope_mean},
        classification=cls,
        narrative=narr,
        methodology=_ASPECT_METHOD,
        severity=sev,
        relevance=["architect", "sustainability_consultant", "planner"],
    )


def _interpret_solar(d: dict) -> TerrainFinding:
    """Interpret solar terrain access from daylight fraction."""
    frac = d["daylight_fraction"]  # noqa: bracket-access
    pct = round(frac * 100, 1)
    derate = round((1 - frac) * 100, 0)

    if frac >= 0.90:
        sev = TerrainSeverity.GREEN
        cls = "Full terrain solar access"
        narr = (
            f"The site receives direct sun for approximately {pct}% of annual daylight hours "
            f"({frac:.3f} fraction), indicating minimal terrain shadowing. Surrounding topography "
            "does not materially obstruct solar access. This value reflects terrain-only shadowing "
            "— built form and vegetation shadows are not included. ADG solar access compliance "
            "and photovoltaic yield assessments can assume unobstructed terrain conditions."
        )
    elif frac >= 0.75:
        sev = TerrainSeverity.AMBER
        cls = "Moderate terrain shadowing"
        narr = (
            f"The site receives direct sun for approximately {pct}% of annual daylight hours "
            f"({frac:.3f} fraction), indicating moderate terrain shadowing. Surrounding ridgelines, "
            "hillsides, or escarpments partially obstruct the solar path during morning or afternoon "
            "hours, or during winter when solar elevation is low. The 2-hour mid-winter ADG "
            "requirement is testable with a detailed shadow analysis that includes terrain. "
            f"The terrain shading derating on photovoltaic yield is approximately "
            f"{derate:.0f}%."
        )
    elif frac >= 0.60:
        sev = TerrainSeverity.RED
        cls = "Significant terrain shadowing"
        narr = (
            f"The site receives direct sun for approximately {pct}% of annual daylight hours "
            f"({frac:.3f} fraction), indicating significant terrain shadowing. The site is likely "
            "located on a south-facing slope below a ridgeline, or within a valley with restricted "
            "sky view. ADG solar access compliance will be challenging. Photovoltaic installations "
            f"will underperform relative to unshaded sites by approximately {derate:.0f}%. "
            "Heating energy loads will be materially higher."
        )
    else:
        sev = TerrainSeverity.RED
        cls = "Severe terrain shadowing"
        narr = (
            f"The site receives direct sun for approximately {pct}% of annual daylight hours "
            f"({frac:.3f} fraction), indicating severe terrain shadowing. The site experiences "
            "substantial solar obstruction from surrounding terrain — likely deep valley, narrow "
            "gorge, or steep south-facing slope with close ridgeline. ADG solar access requirements "
            "may not be achievable for multi-unit residential without significant design concessions. "
            "This level of terrain shading is a material constraint on development feasibility."
        )

    return TerrainFinding(
        id="solar_terrain_access",
        title="Solar Terrain Access",
        metric={"daylight_fraction": frac, "daylight_pct": pct},
        classification=cls,
        narrative=narr,
        methodology=_SOLAR_METHOD,
        severity=sev,
        relevance=["architect", "sustainability_consultant", "solar_designer", "planner"],
    )


def _interpret_elevation(d: dict) -> TerrainFinding:
    """Interpret elevation position within the local terrain."""
    elev_min = d.get("elevation_min_m", 0.0)
    elev_max = d.get("elevation_max_m", 0.0)
    elev_range = d.get("elevation_range_m", 0.0)
    lf = d.get("landform_type")
    low_lying = lf in ("valley", "hollow", "pit")

    if elev_range is not None and elev_range < 3:
        sev = TerrainSeverity.GREEN
        cls = "Level site — minimal elevation variation"
        narr = (
            f"Elevation ranges from {elev_min}m to {elev_max}m AHD across the analysis area "
            f"({elev_range}m total variation). This minimal grade change indicates a site "
            "suitable for single-level slab-on-ground construction. Stormwater grades can be "
            "achieved with standard falls (1:100 minimum). The comparison datum for this "
            "elevation is any applicable flood planning level (FPL) for the area."
        )
        action = None
        cost = None
    elif elev_range is not None and elev_range <= 10 and low_lying:
        sev = TerrainSeverity.AMBER
        cls = f"Moderate variation in {lf} position — drainage sensitivity"
        narr = (
            f"Elevation ranges from {elev_min}m to {elev_max}m AHD ({elev_range}m variation) "
            f"in a {lf} position. The low-lying landform combined with moderate grade change "
            "suggests a site that transitions into a drainage concentration zone. Floor levels "
            "relative to any identified flood planning level are the relevant check. The "
            f"minimum site elevation of {elev_min}m "
            "AHD is the critical datum for that comparison."
        )
        action = "Verify minimum elevation against applicable flood planning level"
        cost = None
    elif elev_range is not None and elev_range <= 10:
        sev = TerrainSeverity.AMBER
        cls = "Moderate elevation variation"
        narr = (
            f"Elevation ranges from {elev_min}m to {elev_max}m AHD ({elev_range}m variation). "
            "This grade change will likely require split-level design, stepped footings, or "
            "localised retaining walls. Earthworks volume depends on building footprint "
            "orientation relative to the contours. A contour survey at 0.5m intervals is the "
            "input that resolves building placement and cut-and-fill balance. "
            "Retaining walls exceeding 600mm height require engineering design under AS 4678."
        )
        action = "Contour survey — the input design development works from"
        cost = "$2,000\u2013$5,000 (contour survey by registered surveyor)"
    else:
        sev = TerrainSeverity.RED
        cls = "Significant elevation variation"
        narr = (
            f"Elevation ranges from {elev_min}m to {elev_max}m AHD ({elev_range}m variation). "
            "This significant grade change indicates a steeply undulating site that will require "
            "multi-level design, substantial retaining structures, and careful management of "
            "overland flow paths across the grade change. A detailed contour survey and "
            "geotechnical investigation are prerequisites for design development."
        )
        action = "Contour survey and geotechnical investigation required"
        cost = (
            "$2,000\u2013$5,000 (contour survey) + "
            "$5,000\u2013$15,000 (geotechnical investigation)"
        )

    return TerrainFinding(
        id="elevation_position",
        title="Elevation Position",
        metric={"elevation_min_m": elev_min, "elevation_max_m": elev_max, "elevation_range_m": elev_range},
        classification=cls,
        narrative=narr,
        methodology=_ELEVATION_METHOD,
        severity=sev,
        relevance=["architect", "structural_engineer", "geotechnical_engineer", "hydraulic_engineer"],
        action_trigger=action,
        estimated_cost=cost,
    )


def _interpret_ruggedness(d: dict) -> TerrainFinding:
    """Interpret surface complexity from terrain ruggedness index."""
    rug = d["terrain_ruggedness"]  # noqa: bracket-access

    if rug < 2.0:
        sev = TerrainSeverity.GREEN
        cls = "Uniform surface — consistent gradient"
        narr = (
            f"Terrain ruggedness index of {rug}\u00b0 (standard deviation of slope) indicates a "
            "uniform surface with consistent gradient across the analysis area. The site does not "
            "exhibit significant undulation, rock outcrops, or abrupt grade changes at the 5m "
            "resolution. Earthworks volumes are predictable and foundation conditions are likely "
            "to be consistent across the building footprint."
        )
        action = None
        cost = None
    elif rug <= 5.0:
        sev = TerrainSeverity.AMBER
        cls = "Moderate surface variability"
        narr = (
            f"Terrain ruggedness index of {rug}\u00b0 indicates moderate surface variability. "
            "The site has a mix of gradients — some areas are relatively flat while others are "
            "steeper, or the surface undulates. This may indicate benched terrain, rock outcrops "
            "interspersed with soil, or natural terracing. Variable bearing conditions are "
            "typical of this surface profile. A detailed contour survey resolves whether the "
            "variability is gradual undulation or abrupt changes (e.g. sandstone shelf edges "
            "common in Sydney Basin geology)."
        )
        action = "Variable bearing conditions likely — a contour survey resolves them"
        cost = "$2,000\u2013$5,000 (contour survey by registered surveyor)"
    else:
        sev = TerrainSeverity.RED
        cls = "High surface complexity — irregular terrain"
        narr = (
            f"Terrain ruggedness index of {rug}\u00b0 indicates high surface complexity. The "
            "terrain exhibits significant irregular variation in slope — likely rock outcrops, "
            "escarpment edges, gullies, or highly dissected terrain. This substantially constrains "
            "building footprint placement and increases construction costs. Individual foundation "
            "elements may need different bearing conditions. Access road and driveway grades may "
            "be difficult to achieve within AS 2890.1 limits. This level of variability is "
            "what a geotechnical investigation with multiple test locations across the "
            "site resolves."
        )
        action = "Geotechnical investigation with multiple test locations — high surface complexity"
        cost = "$5,000\u2013$15,000 (geotechnical investigation with multiple boreholes/test pits)"

    return TerrainFinding(
        id="surface_complexity",
        title="Surface Complexity",
        metric={"terrain_ruggedness": rug},
        classification=cls,
        narrative=narr,
        methodology=_RUGGEDNESS_METHOD,
        severity=sev,
        relevance=["architect", "geotechnical_engineer", "quantity_surveyor", "civil_engineer"],
        action_trigger=action,
        estimated_cost=cost,
    )


def _build_terrain_interpretation(terrain_dict: dict) -> Optional[TerrainInterpretation]:
    """Build structured interpretation from raw terrain metrics.

    Pure threshold logic — no LLM, no external calls.
    Returns None if critical inputs (slope) are missing.
    """
    if terrain_dict.get("slope_mean_deg") is None:
        return None

    findings: list[TerrainFinding] = []
    findings.append(_interpret_gradient(terrain_dict))

    if terrain_dict.get("landform_type") is not None:
        findings.append(_interpret_landform(terrain_dict))
    if terrain_dict.get("aspect_direction") is not None:
        findings.append(_interpret_aspect(terrain_dict))
    if terrain_dict.get("daylight_fraction") is not None:
        findings.append(_interpret_solar(terrain_dict))
    if terrain_dict.get("elevation_min_m") is not None:
        findings.append(_interpret_elevation(terrain_dict))
    if terrain_dict.get("terrain_ruggedness") is not None:
        findings.append(_interpret_ruggedness(terrain_dict))

    # data_source reflects the provider that ACTUALLY served the DEM — the
    # static GA claim used to be asserted even when the SIX Maps photogrammetry
    # fallback served the raster (campaign item 4 census, DQ-46).
    provider = terrain_dict.get("dem_provider")
    if provider == "six_maps_elevation":
        source = "NSW SIX Maps Elevation service (5m elevation model)"
    elif provider == "ga_wcs_5m":
        # No lineage/accuracy parenthetical: the previous "(SRTM-derived,
        # ±5m vertical accuracy)" asserted sensor lineage and an accuracy
        # figure not derived from the returned dataset (Sol finding,
        # 2026-08-03) — state only the provider and product scale.
        source = "Geoscience Australia 5m DEM (GA elevation service)"
    else:
        source = "Elevation model (provider not recorded for this run)"
    return TerrainInterpretation(findings=findings, data_source=source)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------


def _run_terrain_chain(
    work_dir: str,
    lat: float = 0.0,
    lng: float = 0.0,
    buffer_m: float = TERRAIN_BUFFER_M,
) -> dict:
    """Run terrain analysis tools on dem.tif in work_dir.

    Args:
        work_dir: Directory containing dem.tif
        lat: Property latitude (for solar position in time_in_daylight)
        lng: Property longitude (for solar position in time_in_daylight)
        buffer_m: Half-width (m) of the fetched DEM box — used to size the
            central lot window for the site-scoped gradient/elevation/ruggedness.

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

    # Geomorphons — landform classification (10 classes)
    # search=50 cells = 250m at 5m resolution
    _run_tool(wbt.geomorphons, "dem.tif", "geomorphons.tif", search=50, threshold=0.0, forms=True)

    # Time in daylight — annual terrain-shadow solar access (sunrise–sunset)
    # Full year, AEST (UTC+10). Output: fraction 0.0–1.0 of daylight hours
    # not blocked by surrounding terrain.
    try:
        _run_tool(
            wbt.time_in_daylight, "dem.tif", "daylight.tif",
            lat=lat, long=lng,
            az_fraction=10.0,
            max_dist=100.0,
            utc_offset="+10:00",
            start_day=1, end_day=365,
            start_time="sunrise", end_time="sunset",
        )
        daylight_ok = True
    except (RuntimeError, Exception) as e:
        # time_in_daylight is slow and may fail on some DEMs — non-fatal
        logger.warning("time_in_daylight failed: %s — skipping", e)
        daylight_ok = False

    # Read and compute stats
    dem_arr = _read_band(work_dir, "dem.tif")
    slope_arr = _read_band(work_dir, "slope.tif")
    aspect_arr = _read_band(work_dir, "aspect.tif")

    valid_dem = _valid_stats(dem_arr)
    valid_slope = _valid_stats(slope_arr)
    valid_aspect = _valid_stats(aspect_arr)

    # Site-scoped (lot-footprint) values for the gradient / elevation /
    # ruggedness findings. These must reflect the building pad, NOT the 500m
    # neighbourhood — otherwise a steep bank hundreds of metres away inflates
    # slope/elevation/ruggedness and manufactures a false earthworks/geotech
    # constraint. Landform, aspect, drainage and solar stay buffer-scoped below
    # because they are meaningless without surrounding terrain.
    site_dem = _site_values(dem_arr, buffer_m)
    site_slope = _site_values(slope_arr, buffer_m)

    # Dominant aspect: circular mean
    if len(valid_aspect) > 0:
        rad = np.radians(valid_aspect)
        mean_sin = np.nanmean(np.sin(rad))
        mean_cos = np.nanmean(np.cos(rad))
        dominant_aspect = np.degrees(np.arctan2(mean_sin, mean_cos)) % 360
    else:
        dominant_aspect = float("nan")

    # Centre pixel for point-specific metrics
    centre_row = dem_arr.shape[0] // 2
    centre_col = dem_arr.shape[1] // 2

    # Drainage direction at centre pixel
    centre_aspect = aspect_arr[centre_row, centre_col]
    drainage_dir = _aspect_to_compass(centre_aspect) if np.isfinite(centre_aspect) else None

    # Terrain ruggedness — std dev of slope over the lot footprint (a steep bank
    # in the wider buffer is not "my building pad is uneven").
    ruggedness = float(np.nanstd(site_slope)) if len(site_slope) > 0 else None

    # Geomorphon landform at centre pixel
    geomorph_arr = _read_band(work_dir, "geomorphons.tif")
    centre_geomorph = int(geomorph_arr[centre_row, centre_col])
    landform_class = centre_geomorph if centre_geomorph in _GEOMORPHON_LABELS else None
    landform_type = _GEOMORPHON_LABELS.get(centre_geomorph)

    # Daylight fraction at centre pixel
    daylight_fraction = None
    if daylight_ok and os.path.exists(os.path.join(work_dir, "daylight.tif")):
        daylight_arr = _read_band(work_dir, "daylight.tif")
        centre_daylight = daylight_arr[centre_row, centre_col]
        if centre_daylight is not None and np.isfinite(centre_daylight):
            daylight_fraction = round(float(centre_daylight), 3)

    return {
        # Site-scoped (lot window): gradient + elevation reflect the building pad
        "slope_mean_deg": round(float(np.nanmean(site_slope)), 2) if len(site_slope) > 0 else None,
        "slope_max_deg": round(float(np.nanmax(site_slope)), 2) if len(site_slope) > 0 else None,
        "aspect_dominant_deg": round(float(dominant_aspect), 1) if np.isfinite(dominant_aspect) else None,
        "aspect_direction": _aspect_to_compass(dominant_aspect),
        "elevation_min_m": round(float(np.nanmin(site_dem)), 2) if len(site_dem) > 0 else None,
        "elevation_max_m": round(float(np.nanmax(site_dem)), 2) if len(site_dem) > 0 else None,
        "elevation_range_m": round(float(np.nanmax(site_dem) - np.nanmin(site_dem)), 2) if len(site_dem) > 0 else None,
        "drainage_direction": drainage_dir,
        "terrain_ruggedness": round(float(ruggedness), 3) if ruggedness is not None else None,
        "landform_class": landform_class,
        "landform_type": landform_type,
        "daylight_fraction": daylight_fraction,
        "hillshade_png_b64": _render_hillshade_png(dem_arr),
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
        # Fetch DEM and write to work_dir — recording WHICH provider actually
        # served it (GA WCS vs SIX Maps fallback; campaign item 4).
        dem_bytes, dem_provider = fetch_dem_region_with_provider(
            lat, lng, buffer_m=TERRAIN_BUFFER_M)
        dem_path = os.path.join(work_dir, "dem.tif")

        with rasterio.open(dem_bytes) as src:
            profile = src.profile.copy()
            data = src.read(1)
        with rasterio.open(dem_path, "w", **profile) as dst:
            dst.write(data, 1)

        # Terrain analysis: landform/aspect/solar use the full buffer; gradient/
        # elevation/ruggedness are scoped to the lot window (see _site_values).
        result = _run_terrain_chain(work_dir, lat=lat, lng=lng, buffer_m=TERRAIN_BUFFER_M)
        result["dem_provider"] = dem_provider
        result["execution_manifest"] = build_manifest(
            product="terrain",
            algorithm_version=ALGORITHM_VERSION,
            inputs={"dem": {"provider": dem_provider,
                            "buffer_m": TERRAIN_BUFFER_M,
                            "capture_date_published": False}},
            query_params={"lat": lat, "lng": lng},
        )

        # Structured interpretation (professional findings with methodology) —
        # fail-safe: a narrative failure must never blank the terrain metrics.
        try:
            interp = _build_terrain_interpretation(result)
            if interp is not None:
                result["interpretation"] = interp.model_dump()
        except Exception as e:
            logger.warning("terrain interpretation failed: %s", e)

        # Flood susceptibility (larger buffer for catchment context)
        if include_flood:
            flood_dir = tempfile.mkdtemp(prefix="wbt_flood_", dir=work_dir)
            dem_bytes_lg, flood_dem_provider = fetch_dem_region_with_provider(
                lat, lng, buffer_m=5000)
            # The flood-susceptibility DEM is a SEPARATE fetch and can be
            # served by a different provider than the terrain DEM — record it
            # or the manifest gives incomplete provenance for the flood
            # values (Sol finding, 2026-08-03).
            result["execution_manifest"]["inputs"]["flood_dem"] = {
                "provider": flood_dem_provider,
                "buffer_m": 5000,
                "capture_date_published": False,
            }
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
    # Units/CRS entry check (campaign item 4): typed unavailable via the
    # response's own error field — never metrics computed for the wrong place.
    coord_reason = check_point_nsw(req.lat, req.lng)
    if coord_reason:
        return TerrainResponse(
            error=f"Terrain analysis could not be determined: {coord_reason}")

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

        interpretation = _build_terrain_interpretation(result) if terrain else None
        return TerrainResponse(
            terrain=terrain,
            interpretation=interpretation,
            flood_susceptibility=flood,
            execution_manifest=result.get("execution_manifest"),
        )
    except Exception as e:
        logger.exception("Terrain analysis failed for (%.4f, %.4f): %s", req.lat, req.lng, e)
        raise HTTPException(status_code=500, detail=str(e))
