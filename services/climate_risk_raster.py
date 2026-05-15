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

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "narclim"

# Each entry: variable code → {scenario → file path}
# Files follow NARCliM naming: {var}_{scenario}_{gcm}_{rcm}_{domain}.nc
NARCLIM_FILES: dict[str, dict[str, str]] = {
    "TXge35": {
        "ssp245": "TXge35_ssp245_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
        "ssp370": "TXge35_ssp370_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
    },
    # Precipitation will be added when download completes:
    # "pr": {
    #     "ssp245": "pr_ssp245_...",
    #     "ssp370": "pr_ssp370_...",
    # },
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
                units = getattr(var_obj, "units", "")

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

    Returns a flat dict with the most decision-relevant numbers:
    - hot_days_baseline: current annual days >=35C
    - hot_days_2050_mid: projected under SSP2-4.5
    - hot_days_2050_high: projected under SSP3-7.0
    - hot_days_2090_mid: late-century SSP2-4.5
    - hot_days_2090_high: late-century SSP3-7.0
    - hot_days_delta_2050: change from baseline (worst scenario)
    - hot_days_delta_2090: change from baseline (worst scenario)
    """
    results = query_narclim(lat, lng, variables=["TXge35"])
    if not results:
        return {}

    txge35 = results[0]
    summary: dict = {
        "grid_distance_km": txge35["grid_distance_km"],
    }

    # Extract per-scenario/period values
    for sc in txge35["scenarios"]:
        scenario_suffix = "mid" if sc["scenario"] == "ssp245" else "high"
        for p in sc["periods"]:
            key = f"hot_days_{p['period']}_{scenario_suffix}"
            summary[key] = p["mean"]

    # Compute deltas from baseline (use whichever scenario has baseline data)
    baseline = summary.get("hot_days_baseline_mid") or summary.get("hot_days_baseline_high")
    if baseline is not None:
        summary["hot_days_baseline"] = baseline
        mid_2050 = summary.get("hot_days_mid_century_mid")
        high_2050 = summary.get("hot_days_mid_century_high")
        mid_2090 = summary.get("hot_days_late_century_mid")
        high_2090 = summary.get("hot_days_late_century_high")

        if high_2050 is not None:
            summary["hot_days_delta_2050"] = round(high_2050 - baseline, 2)
        elif mid_2050 is not None:
            summary["hot_days_delta_2050"] = round(mid_2050 - baseline, 2)

        if high_2090 is not None:
            summary["hot_days_delta_2090"] = round(high_2090 - baseline, 2)
        elif mid_2090 is not None:
            summary["hot_days_delta_2090"] = round(mid_2090 - baseline, 2)

    return summary


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
