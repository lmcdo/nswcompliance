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
        return Image.open(cache_path).convert("RGB")

    for attempt in range(3):
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
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
    session = requests.Session()
    session.headers["User-Agent"] = "PlotDetect/1.0 (property intelligence; contact@plotdetect.com)"

    tiles: list[list[Optional[Image.Image]]] = []
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


def fetch_tile_to_file(
    lat: float,
    lng: float,
    output_path: Optional[str] = None,
    grid: int = 3,
) -> tuple[str, str, dict]:
    """
    Fetch tile and save to a file. Returns (file_path, licence, bbox).
    If output_path is None, saves to /tmp keyed by lat/lng.
    """
    if output_path is None:
        key = hashlib.md5(f"{lat:.6f},{lng:.6f},{grid}".encode()).hexdigest()[:12]
        output_path = f"/tmp/sixmaps_{key}.png"

    if os.path.exists(output_path):
        logger.debug(f"Using cached tile at {output_path}")
        # Recompute bbox without re-fetching
        _, licence, bbox = _compute_bbox_only(lat, lng, grid)
        return output_path, licence, bbox

    image, licence, bbox = fetch_tile_for_location(lat, lng, grid=grid)

    # Sanity check: reject uniform grey canvas (all tile fetches failed)
    import numpy as np
    arr = np.array(image)
    if arr.std() < 2:
        raise RuntimeError(
            f"All SIX Maps tile fetches failed for ({lat:.5f}, {lng:.5f}) — "
            "server may be temporarily unavailable. Not caching grey canvas."
        )

    image.save(output_path)
    logger.info(f"Saved {grid}x{grid} tile grid to {output_path} — {image.size[0]}x{image.size[1]}px")
    return output_path, licence, bbox


def _compute_bbox_only(lat: float, lng: float, grid: int) -> tuple[None, str, dict]:
    half = grid // 2
    cx, cy = _lat_lng_to_tile(lat, lng, ZOOM)
    nw_lat, nw_lng = _tile_to_lat_lng(cx - half, cy - half, ZOOM)
    se_lat, se_lng = _tile_to_lat_lng(cx + half + 1, cy + half + 1, ZOOM)
    bbox = {
        "min_lat": se_lat,
        "max_lat": nw_lat,
        "min_lng": nw_lng,
        "max_lng": se_lng,
    }
    return None, LICENCE, bbox
