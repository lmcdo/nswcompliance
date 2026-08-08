"""
NSW SIX Maps WMTS tile fetcher.

Fetches 10cm aerial imagery tiles from the NSW Government SIX Maps service.
Licence: CC-BY 4.0 NSW Government — must be included in report metadata.

Tile URL: https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/LPI_Imagery_Best/MapServer/tile/{z}/{y}/{x}
Zoom 20 ≈ 10cm/pixel in NSW.
"""

import math
import os
import hashlib
import logging
from pathlib import Path
from typing import Optional

import requests
from PIL import Image
import io

logger = logging.getLogger(__name__)

TILE_URL = "https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/LPI_Imagery_Best/MapServer/tile/{z}/{y}/{x}"
ZOOM = 20
TILE_SIZE = 256  # pixels per tile
LICENCE = "CC-BY 4.0 NSW Government — Six Maps LPI Imagery"

CACHE_DIR = Path(os.getenv("TILE_CACHE_DIR", "/tmp/sixmaps_tiles"))


def _lat_lng_to_tile(lat: float, lng: float, zoom: int) -> tuple[int, int]:
    """Convert WGS84 lat/lng to Web Mercator tile x, y at given zoom."""
    n = 2 ** zoom
    x = int((lng + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def _tile_to_lat_lng(x: int, y: int, zoom: int) -> tuple[float, float]:
    """Convert tile x, y to the NW corner lat/lng."""
    n = 2 ** zoom
    lng = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lng


def _fetch_tile(z: int, x: int, y: int, session: requests.Session) -> Optional[Image.Image]:
    """Fetch a single tile. Returns PIL Image or None on failure."""
    url = TILE_URL.format(z=z, x=x, y=y)
    cache_path = CACHE_DIR / f"{z}_{x}_{y}.png"

    if cache_path.exists():
        try:
            return Image.open(cache_path).convert("RGB")
        except Exception:
            # Corrupt cache file (partial write, disk full, etc.) — delete and re-fetch
            logger.warning(f"Cached tile {z}/{x}/{y} is corrupt — deleting and re-fetching")
            cache_path.unlink(missing_ok=True)

    # Ensure cache dir exists before the retry loop so mkdir failures surface clearly
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    for attempt in range(3):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 404:
                # Tile doesn't exist at this zoom — no point retrying
                logger.debug(f"Tile {z}/{x}/{y} not found (404) — skipping retries")
                return None
            if resp.status_code == 429:
                # Rate-limited — retrying immediately would make it worse
                logger.warning(f"Tile {z}/{x}/{y} rate-limited (429) — skipping retries")
                return None
            resp.raise_for_status()
            # Guard against HTML error pages returned with 200 status
            content_type = resp.headers.get("content-type", "")
            if "image" not in content_type:
                logger.warning(
                    f"Tile {z}/{x}/{y} returned non-image content-type '{content_type}' — skipping retries"
                )
                return None
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img.save(cache_path)
            return img
        except Exception as e:
            logger.warning(f"Tile {z}/{x}/{y} attempt {attempt+1}/3 failed: {e}")
            if attempt == 2:
                return None


def fetch_tile_for_location(
    lat: float,
    lng: float,
    grid: int = 3,
    zoom: int = ZOOM,
) -> tuple[Image.Image, str, dict]:
    """
    Fetch a stitched aerial tile centred on lat/lng.

    Args:
        lat: Latitude (WGS84)
        lng: Longitude (WGS84)
        grid: Grid size (3 = 3×3 tiles). Must be odd.
        zoom: WMTS zoom level (20 = ~10cm/pixel)

    Returns:
        (image, licence_string, bbox_dict)
        bbox_dict keys: min_lat, max_lat, min_lng, max_lng
    """
    assert grid % 2 == 1, "grid must be odd"
    half = grid // 2

    cx, cy = _lat_lng_to_tile(lat, lng, zoom)

    tiles: list[list[Optional[Image.Image]]] = []
    with requests.Session() as session:
        session.headers["User-Agent"] = "PlotDetect/1.0 (property intelligence; contact@plotdetect.com)"
        for dy in range(-half, half + 1):
            row = []
            for dx in range(-half, half + 1):
                row.append(_fetch_tile(zoom, cx + dx, cy + dy, session))
            tiles.append(row)

    # Stitch into single image
    w = grid * TILE_SIZE
    h = grid * TILE_SIZE
    canvas = Image.new("RGB", (w, h), (128, 128, 128))
    for iy, row in enumerate(tiles):
        for ix, tile in enumerate(row):
            if tile is not None:
                canvas.paste(tile, (ix * TILE_SIZE, iy * TILE_SIZE))

    # Compute bounding box (NW corner of top-left tile → SE corner of bottom-right tile)
    nw_lat, nw_lng = _tile_to_lat_lng(cx - half, cy - half, zoom)
    se_lat, se_lng = _tile_to_lat_lng(cx + half + 1, cy + half + 1, zoom)

    bbox = {
        "min_lat": se_lat,
        "max_lat": nw_lat,
        "min_lng": nw_lng,
        "max_lng": se_lng,
    }

    return canvas, LICENCE, bbox


# prior-art-checked: this module's own fetch gains a tile-identity meta return
# for item-4 execution manifests — the z/x/y values already exist transiently
# here and are simply no longer discarded; no new source is added.
def _tile_meta(lat: float, lng: float, grid: int, zoom: int,
               cached_file: bool) -> dict:
    """Tile identity for execution manifests (campaign item 4), derived from
    the values this fetch actually used. The LPI 'Best' mosaic publishes no
    capture date — recorded explicitly rather than implied."""
    cx, cy = _lat_lng_to_tile(lat, lng, zoom)
    return {
        "provider": "NSW SIX Maps LPI_Imagery_Best",
        "tile_url_template": TILE_URL,
        "zoom": zoom,
        "grid": grid,
        "centre_tile_xy": [cx, cy],
        "served_from_disk_cache": cached_file,
        "capture_date_published": False,
    }


def fetch_tile_to_file(
    lat: float,
    lng: float,
    output_path: Optional[str] = None,
    grid: int = 3,
) -> tuple[str, str, dict, dict]:
    """
    Fetch tile and save to a file. Returns (file_path, licence, bbox, meta) —
    meta is the tile identity for execution manifests.
    If output_path is None, saves to /tmp keyed by lat/lng.
    """
    if output_path is None:
        key = hashlib.md5(f"{lat:.6f},{lng:.6f},{grid}".encode()).hexdigest()[:12]
        output_path = f"/tmp/sixmaps_{key}.png"

    zoom_sidecar = output_path + ".zoom"

    if os.path.exists(output_path):
        logger.debug(f"Using cached tile at {output_path}")
        # Read zoom from sidecar so bbox is computed at the correct zoom level.
        # Legacy cache files (no sidecar) fall back to ZOOM=20.
        cached_zoom = ZOOM
        try:
            cached_zoom = int(Path(zoom_sidecar).read_text().strip())
        except Exception:
            pass
        _, licence, bbox = _compute_bbox_only(lat, lng, grid, cached_zoom)
        return (output_path, licence, bbox,
                _tile_meta(lat, lng, grid, cached_zoom, cached_file=True))

    import numpy as np

    half = grid // 2
    center_slice = (
        slice(half * TILE_SIZE, (half + 1) * TILE_SIZE),
        slice(half * TILE_SIZE, (half + 1) * TILE_SIZE),
    )

    # Try zoom 20 first; fall back to zoom 19 if tiles are unavailable (404s)
    zoom_candidates = [ZOOM, ZOOM - 1]
    for zoom in zoom_candidates:
        image, licence, bbox = fetch_tile_for_location(lat, lng, grid=grid, zoom=zoom)

        arr = np.array(image)
        # Check center tile specifically — that's where the lot sits.
        # Checking full canvas std can pass if only distant outer tiles have colour.
        center_arr = arr[center_slice[0], center_slice[1]]
        if center_arr.std() < 2:
            logger.warning(
                f"Center tile grey at zoom {zoom} for ({lat:.5f}, {lng:.5f})"
                + (f" — trying zoom {zoom - 1}" if zoom != zoom_candidates[-1] else "")
            )
            continue

        if zoom != ZOOM:
            logger.info(f"Zoom {ZOOM} unavailable — used zoom {zoom} fallback for ({lat:.5f}, {lng:.5f})")

        image.save(output_path)
        Path(zoom_sidecar).write_text(str(zoom))
        logger.info(f"Saved {grid}x{grid} tile grid to {output_path} — {image.size[0]}x{image.size[1]}px (zoom {zoom})")
        return (output_path, licence, bbox,
                _tile_meta(lat, lng, grid, zoom, cached_file=False))

    raise RuntimeError(
        f"SIX Maps center tile unavailable for ({lat:.5f}, {lng:.5f}) at zooms "
        f"{zoom_candidates} — no imagery at this location."
    )


def _compute_bbox_only(lat: float, lng: float, grid: int, zoom: int = ZOOM) -> tuple[None, str, dict]:
    half = grid // 2
    cx, cy = _lat_lng_to_tile(lat, lng, zoom)
    nw_lat, nw_lng = _tile_to_lat_lng(cx - half, cy - half, zoom)
    se_lat, se_lng = _tile_to_lat_lng(cx + half + 1, cy + half + 1, zoom)
    bbox = {
        "min_lat": se_lat,
        "max_lat": nw_lat,
        "min_lng": nw_lng,
        "max_lng": se_lng,
    }
    return None, LICENCE, bbox
