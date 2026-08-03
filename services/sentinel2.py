"""
Sentinel-2 L2A pipeline — Element84 Earth Search (free, no auth).

Used by shadow_detector.py and threat_radar.py for BSI construction change detection.

Environment required:
  AWS_NO_SIGN_REQUEST=YES
  GDAL_HTTP_UNSAFESSL=YES
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

CATALOG_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-c1-l2a"

os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")
os.environ.setdefault("GDAL_HTTP_UNSAFESSL", "YES")

BSI_CHANGE_THRESHOLD = 0.12  # delta above this = construction activity likely
DEFAULT_MAX_CLOUD = 20       # eo:cloud_cover ceiling for scene search

# Algorithm revision for execution manifests (campaign item 4). Bump when the
# BSI method/threshold/scene-selection changes — deploy identity is recorded
# separately (execution_manifest.deploy_sha).
ALGORITHM_VERSION = "s2-bsi-change-1.0"


def _make_bbox(lat: float, lng: float, radius_m: float) -> list:
    """lat/lng + radius metres -> WGS84 bbox [W, S, E, N]."""
    deg_lat = 1.0 / 111_320.0
    deg_lng = 1.0 / (111_320.0 * abs(np.cos(np.radians(lat))))
    return [
        lng - radius_m * deg_lng,
        lat - radius_m * deg_lat,
        lng + radius_m * deg_lng,
        lat + radius_m * deg_lat,
    ]


def _load_band(item, bbox: list, asset_key: str) -> Optional[np.ndarray]:
    """Range-request one S2 band as float32 reflectance. Returns None on failure."""
    try:
        import rasterio
        from rasterio.windows import from_bounds as win_from_bounds
        href = item.assets[asset_key].href
        with rasterio.open(href) as src:
            window = win_from_bounds(*bbox, src.transform)
            data = src.read(1, window=window, out_dtype="float32")
            return data / 10_000.0 if data.size > 0 else None
    except Exception as e:
        logger.debug(f"Band {asset_key}: {e}")
        return None


def _compute_bsi_scene(item, bbox: list) -> Optional[float]:
    """
    Mean Bare Soil Index for one scene over bbox.
    BSI = ((Red+SWIR1) - (NIR+Blue)) / ((Red+SWIR1) + (NIR+Blue))
    Positive = more bare soil / construction.
    """
    red   = _load_band(item, bbox, "red")
    nir   = _load_band(item, bbox, "nir")
    blue  = _load_band(item, bbox, "blue")
    swir1 = _load_band(item, bbox, "swir16")
    if any(b is None for b in (red, nir, blue, swir1)):
        return None
    num = (red + swir1) - (nir + blue)
    den = (red + swir1) + (nir + blue)
    with np.errstate(invalid="ignore", divide="ignore"):
        bsi = np.where(den != 0, num / den, 0.0)
    return float(np.nanmean(bsi))


# prior-art-checked: same function, default hoisted to the module constant so
# the manifest reports the value actually in force — no new capability.
def get_scenes(lat: float, lng: float, radius_m: float,
               date_start: str, date_end: str,
               max_cloud: int = DEFAULT_MAX_CLOUD) -> list:
    """Search Element84 for S2 L2A scenes, sorted newest first."""
    try:
        from pystac_client import Client
    except ImportError:
        raise RuntimeError("pystac-client not installed")
    bbox = _make_bbox(lat, lng, radius_m)
    client = Client.open(CATALOG_URL)
    search = client.search(
        collections=[COLLECTION],
        bbox=bbox,
        datetime=f"{date_start}/{date_end}",
        query={"eo:cloud_cover": {"lt": max_cloud}},
        max_items=50,
    )
    items = list(search.items())
    # Sort newest-first in Python — sentinel-2-c1-l2a doesn't support server-side datetime sort
    items.sort(key=lambda i: i.datetime or datetime.min, reverse=True)
    logger.debug(f"get_scenes: {len(items)} items {date_start}/{date_end}")
    return items


def compute_change_score(lat: float, lng: float, radius_m: float = 100,
                         months_back: int = 24) -> dict:
    """
    BSI construction change score for a location.

    Compares median BSI of 4 recent scenes (<90 days) vs 4 baseline scenes
    (12+ months ago). Returns signed delta.

    Returns dict: change_score, construction_detected, recent_bsi, baseline_bsi,
    recent_scene_count, baseline_scene_count, date_range
    """
    today = datetime.utcnow().date()
    recent_start = (today - timedelta(days=90)).isoformat()
    recent_end = today.isoformat()
    baseline_start = (today - timedelta(days=months_back * 30)).isoformat()
    baseline_end = (today - timedelta(days=365)).isoformat()

    bbox = _make_bbox(lat, lng, radius_m)
    recent = get_scenes(lat, lng, radius_m, recent_start, recent_end)
    baseline = get_scenes(lat, lng, radius_m, baseline_start, baseline_end)

    def _median_bsi(scenes):
        """Median BSI over up to 4 scenes, plus the identity of every scene
        actually consumed — derived from the pystac Items themselves at the
        point of use (campaign item 4: a manifest is never a parallel
        lookup). ``used`` marks the scenes whose BSI contributed to the
        median; a scene attempted but unreadable is recorded with
        used=False, so the manifest cannot claim inputs that were dropped."""
        try:
            from services.execution_manifest import stac_item_identity
        except ImportError:
            # Flat-import deploy mode (services/ on PYTHONPATH) — the same
            # dual-path every service module uses.
            from execution_manifest import stac_item_identity

        scores = []
        consumed = []
        for item in scenes[:4]:
            score = _compute_bsi_scene(item, bbox)
            ident = stac_item_identity(item)
            ident["used"] = score is not None
            consumed.append(ident)
            if score is not None:
                scores.append(score)
        return (float(np.median(scores)) if scores else None), consumed

    r_bsi, recent_used = _median_bsi(recent)
    b_bsi, baseline_used = _median_bsi(baseline)

    scene_identity = {
        "algorithm_version": ALGORITHM_VERSION,
        "collection": COLLECTION,
        "recent_scenes": recent_used,
        "baseline_scenes": baseline_used,
        "query": {
            "bbox_wgs84": [round(v, 6) for v in bbox],
            "radius_m": radius_m,
            "max_cloud_pct": DEFAULT_MAX_CLOUD,
            "recent_window": f"{recent_start}/{recent_end}",
            "baseline_window": f"{baseline_start}/{baseline_end}",
        },
    }

    if r_bsi is None or b_bsi is None:
        return {
            "change_score": 0.0, "construction_detected": False,
            "recent_scene_count": len(recent), "baseline_scene_count": len(baseline),
            "date_range": f"{baseline_start}/{recent_end}",
            "note": "Insufficient cloud-free scenes",
            "scene_identity": scene_identity,
        }

    delta = round(r_bsi - b_bsi, 4)
    return {
        "change_score": delta,
        "construction_detected": delta > BSI_CHANGE_THRESHOLD,
        "recent_bsi": round(r_bsi, 4),
        "baseline_bsi": round(b_bsi, 4),
        "recent_scene_count": len(recent),
        "baseline_scene_count": len(baseline),
        "date_range": f"{baseline_start}/{recent_end}",
        "scene_identity": scene_identity,
    }
