"""NARCliM 2.0 raster point sampling for climate risk projections.

Pattern: same as flood_truth.py — config dict + file-based raster sampling.
NetCDF files stored in data/narclim/ (gitignored). Regular lat/lon grid (EPSG:4326),
no CRS transform needed.

Usage:
    from services.climate_risk_raster import query_narclim
    result = query_narclim(-33.8688, 151.2093)  # Sydney CBD
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict

import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────

# Raster location. Local dev defaults to repo/data/narclim (gitignored, ~1.8 GB).
# On Railway the rasters are downloaded from R2 to a writable dir at startup by
# scripts/download_narclim_rasters.py — point both at it via NARCLIM_DIR.
DATA_DIR = (
    Path(os.environ["NARCLIM_DIR"])  # noqa: bracket-access (guarded by the .get() below)
    if os.environ.get("NARCLIM_DIR")
    else Path(__file__).resolve().parent.parent / "data" / "narclim"
)

# Each entry: variable code → {scenario → file path}
# Files follow NARCliM naming: {var}_{scenario}_{gcm}_{rcm}_{domain}.nc
NARCLIM_FILES: dict[str, dict[str, str]] = {
    "TXge35": {
        "ssp245": "TXge35_ssp245_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
        "ssp370": "TXge35_ssp370_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
    },
    "prAdjust": {
        "ssp245": "prAdjust_ssp245_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
        "ssp370": "prAdjust_ssp370_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
    },
    "tas": {
        "ssp245": "tas_ssp245_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
        "ssp370": "tas_ssp370_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
    },
}

# Unit conversions applied after extraction (raw NetCDF units → human-readable)
UNIT_CONVERSIONS: dict[str, dict] = {
    "prAdjust": {"factor": 86400.0, "display_units": "mm/day", "description": "kg/m²/s → mm/day"},
    "tas": {"offset": -273.15, "display_units": "°C", "description": "Kelvin → Celsius"},
    # TXge35 is already in days — no conversion needed
}

# Time periods for extraction (year ranges → slice indices computed from time axis)
TIME_PERIODS = {
    "baseline": (2015, 2024),   # First ~10 years of projection
    "near_future": (2030, 2049),
    "mid_century": (2050, 2069),
    "late_century": (2080, 2099),
}

# Spatial bounds check (SE Australia domain)
LAT_BOUNDS = (-39.58, -23.82)
LON_BOUNDS = (135.62, 153.98)

# NSW-specific tighter bounds for validation warnings
NSW_LAT_BOUNDS = (-37.5, -28.0)
NSW_LON_BOUNDS = (141.0, 154.0)


# ── Types ─────────────────────────────────────────────────────────────────────

class PeriodProjection(TypedDict):
    period: str
    year_range: tuple[int, int]
    mean: float
    min: float
    max: float


class ScenarioResult(TypedDict):
    scenario: str
    periods: list[PeriodProjection]


class NARCliMResult(TypedDict):
    variable: str
    variable_long_name: str
    units: str
    lat: float
    lng: float
    grid_lat: float
    grid_lng: float
    grid_distance_km: float
    scenarios: list[ScenarioResult]


# ── Core functions ────────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two points."""
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def _find_nearest_idx(lat_arr: np.ndarray, lon_arr: np.ndarray, lat: float, lng: float) -> tuple[int, int]:
    """Find nearest grid cell index for a given lat/lng on a regular grid."""
    lat_idx = int(np.argmin(np.abs(lat_arr - lat)))
    lon_idx = int(np.argmin(np.abs(lon_arr - lng)))
    return lat_idx, lon_idx


def _extract_time_periods(
    ds,
    var_name: str,
    lat_idx: int,
    lon_idx: int,
) -> list[PeriodProjection]:
    """Extract mean/min/max for each time period at the given grid cell."""
    import netCDF4 as nc
    import cftime

    time_var = ds.variables["time"]
    times = nc.num2date(
        time_var[:],
        time_var.units,
        time_var.calendar if hasattr(time_var, "calendar") else "standard",
    )
    # Convert cftime to year integers
    years = np.array([t.year for t in times])

    data = ds.variables[var_name][:, lat_idx, lon_idx]
    # Handle masked values
    if hasattr(data, "mask"):
        data = np.where(data.mask, np.nan, data.data)

    # Apply unit conversion if defined
    conv = UNIT_CONVERSIONS.get(var_name)
    if conv:
        if "factor" in conv:
            data = data * conv["factor"]
        if "offset" in conv:
            data = data + conv["offset"]

    periods: list[PeriodProjection] = []
    for period_name, (y_start, y_end) in TIME_PERIODS.items():
        mask = (years >= y_start) & (years <= y_end)
        if not mask.any():
            continue
        subset = data[mask]
        valid = subset[~np.isnan(subset)]
        if len(valid) == 0:
            continue
        periods.append(PeriodProjection(
            period=period_name,
            year_range=(y_start, y_end),
            mean=round(float(np.mean(valid)), 2),
            min=round(float(np.min(valid)), 2),
            max=round(float(np.max(valid)), 2),
        ))

    return periods


def query_narclim(lat: float, lng: float, variables: list[str] | None = None) -> list[NARCliMResult]:
    """Query NARCliM 2.0 projections for a given lat/lng.

    Args:
        lat: Latitude (WGS84)
        lng: Longitude (WGS84)
        variables: List of variable codes to query. Defaults to all available.

    Returns:
        List of NARCliMResult dicts, one per variable.

    Raises:
        ValueError: If coordinates are outside the NARCliM domain.
        FileNotFoundError: If NetCDF files are not present in data/narclim/.
    """
    import netCDF4 as nc

    # Bounds check
    if not (LAT_BOUNDS[0] <= lat <= LAT_BOUNDS[1]):
        raise ValueError(f"Latitude {lat} outside NARCliM domain {LAT_BOUNDS}")
    if not (LON_BOUNDS[0] <= lng <= LON_BOUNDS[1]):
        raise ValueError(f"Longitude {lng} outside NARCliM domain {LON_BOUNDS}")

    if variables is None:
        variables = list(NARCLIM_FILES.keys())

    results: list[NARCliMResult] = []

    for var_code in variables:
        if var_code not in NARCLIM_FILES:
            raise ValueError(f"Unknown variable: {var_code}. Available: {list(NARCLIM_FILES.keys())}")

        scenarios_data: list[ScenarioResult] = []
        grid_lat = grid_lng = grid_dist = 0.0
        long_name = ""
        units = ""

        for scenario, filename in NARCLIM_FILES[var_code].items():
            filepath = DATA_DIR / filename
            if not filepath.exists():
                raise FileNotFoundError(f"NARCliM file not found: {filepath}")

            ds = nc.Dataset(str(filepath), "r")
            try:
                lat_arr = ds.variables["lat"][:]
                lon_arr = ds.variables["lon"][:]
                lat_idx, lon_idx = _find_nearest_idx(lat_arr, lon_arr, lat, lng)

                grid_lat = float(lat_arr[lat_idx])
                grid_lng = float(lon_arr[lon_idx])
                grid_dist = _haversine_km(lat, lng, grid_lat, grid_lng)

                var_obj = ds.variables[var_code]
                long_name = getattr(var_obj, "long_name", var_code)
                conv = UNIT_CONVERSIONS.get(var_code)
                units = conv["display_units"] if conv else getattr(var_obj, "units", "")

                periods = _extract_time_periods(ds, var_code, lat_idx, lon_idx)
                scenarios_data.append(ScenarioResult(
                    scenario=scenario,
                    periods=periods,
                ))
            finally:
                ds.close()

        results.append(NARCliMResult(
            variable=var_code,
            variable_long_name=long_name,
            units=units,
            lat=lat,
            lng=lng,
            grid_lat=grid_lat,
            grid_lng=grid_lng,
            grid_distance_km=round(grid_dist, 2),
            scenarios=scenarios_data,
        ))

    return results


def query_narclim_summary(lat: float, lng: float) -> dict:
    """Simplified query returning key metrics for climate risk scoring.

    Returns a flat dict with the most decision-relevant numbers per variable:
    - hot_days_*: annual days >=35C (TXge35)
    - precip_*: mean daily precipitation in mm/day (prAdjust)
    - temp_*: mean near-surface temperature in °C (tas)
    - *_delta_2050 / *_delta_2090: change from baseline (worst scenario)
    """
    results = query_narclim(lat, lng)
    if not results:
        return {}

    summary: dict = {
        "grid_distance_km": results[0]["grid_distance_km"],
    }

    VAR_PREFIXES = {"TXge35": "hot_days", "prAdjust": "precip", "tas": "temp"}

    for var_result in results:
        prefix = VAR_PREFIXES.get(var_result["variable"], var_result["variable"])

        for sc in var_result["scenarios"]:
            scenario_suffix = "mid" if sc["scenario"] == "ssp245" else "high"
            for p in sc["periods"]:
                key = f"{prefix}_{p['period']}_{scenario_suffix}"
                summary[key] = p["mean"]

        # Compute deltas from baseline (use whichever scenario has baseline data)
        baseline = summary.get(f"{prefix}_baseline_mid") or summary.get(f"{prefix}_baseline_high")
        if baseline is not None:
            summary[f"{prefix}_baseline"] = baseline
            for horizon, period_key in [("2050", "mid_century"), ("2090", "late_century")]:
                high_val = summary.get(f"{prefix}_{period_key}_high")
                mid_val = summary.get(f"{prefix}_{period_key}_mid")
                val = high_val if high_val is not None else mid_val
                if val is not None:
                    summary[f"{prefix}_delta_{horizon}"] = round(val - baseline, 2)

    return summary


def query_narclim_state(lat: float, lng: float) -> dict:
    """State envelope over :func:`query_narclim_summary` for renderers.

    prior-art-checked: thin exception->state wrapper over the existing
    query_narclim_summary (same module) — adds NO new data source, query or
    hazard logic; only classifies that function's result/exceptions into four
    render states so consumers don't each re-implement the try/except mapping.

    Keeps the four data states DISTINCT so a consumer (e.g. the conveyancing
    PDF) can render a permanent geographic limit (``out_of_domain``) differently
    from a fixable infrastructure gap (``unavailable``) — the two must never be
    collapsed into a single line, which would imply missing projections are
    fixable when they are a domain boundary (or vice versa).

    Returns one of:
      ``{"state": "present", "summary": {...}}``  populated grid coverage
      ``{"state": "no_coverage"}``                queried, no delta returned
      ``{"state": "out_of_domain"}``              lat/lng outside NARCliM domain
      ``{"state": "unavailable"}``                rasters absent / lookup failed
    """
    try:
        summary = query_narclim_summary(lat, lng)
    except ValueError:
        # Bounds check in query_narclim — a permanent geographic limit.
        return {"state": "out_of_domain"}
    except FileNotFoundError:
        # Rasters not deployed to this runtime — an infrastructure gap.
        import logging
        logging.getLogger(__name__).warning(
            "NARCliM rasters not found (NARCLIM_DIR=%s)", DATA_DIR
        )
        return {"state": "unavailable"}
    except Exception:
        import logging
        logging.getLogger(__name__).warning("NARCliM lookup failed", exc_info=True)
        return {"state": "unavailable"}
    if summary and any(k.endswith("_delta_2090") for k in summary):
        return {"state": "present", "summary": summary}
    return {"state": "no_coverage"}


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    import sys

    # Default: Sydney CBD
    test_lat = float(sys.argv[1]) if len(sys.argv) > 1 else -33.8688
    test_lng = float(sys.argv[2]) if len(sys.argv) > 2 else 151.2093

    print(f"Querying NARCliM for ({test_lat}, {test_lng})...\n")

    # Full query
    results = query_narclim(test_lat, test_lng)
    print("=== FULL RESULTS ===")
    print(json.dumps(results, indent=2, default=str))

    # Summary
    print("\n=== SUMMARY ===")
    summary = query_narclim_summary(test_lat, test_lng)
    print(json.dumps(summary, indent=2))
