"""Our own saved copy of the small state map layers the area check asks for, read from data/law/maps (step 2 of ce-layers-own-copy-SCOPE-2026-11-18.md).

prior-art-checked: four sweeps 2026-11-20. (1) DB: spatial_overlays holds bush fire, heritage items and coastal wetlands, not these 8 layers. (2) Frontend: no reader.
(3) Python: services/lmr_area_inputs._layer asks the live service per lot; services/lmr_area_lga.py is the council/lot/bush fire copy read from the database
(a different store); nothing reads data/law/maps. town_centre_polygons reads one committed file but only for one layer. (4) Plans: the scope file above, approved
2026-11-20 (45-day limit, monthly refresh).

THIS MODULE ONLY ANSWERS FROM A COPY IT CAN PROVE:
  * the file's sha256 must equal the manifest's, and the loaded feature count must equal the manifest's;
  * the copy must be no older than MAX_AGE_DAYS (the manifest's read_on date);
  * anything else (missing file, bad hash, wrong count, too old, unreadable) gives None = "no answer", and the caller asks the live map. It never gives a clear.
The answer carries as_of (the day the copy was read) and near_edge: a point within EDGE_M of a polygon edge, where a copy and the live map can differ by a
few metres. The caller must confirm a near_edge answer on the live map.

Measured 2026-11-20 against the live service: 799 of 800 points agreed over all 8 layers (320 of them about 10 m from a polygon edge); the one difference sat
exactly on a polygon edge; 0 cases of copy clear / live hit. Loading and indexing all 8 layers takes about 2 s, once per process.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

MAPS_DIR = Path(__file__).resolve().parent.parent / "data" / "law" / "maps"
MAX_AGE_DAYS = 45      # noqa: regulatory-number -- owner-approved staleness limit for our own copy, not a planning figure
EDGE_M = 5.0           # noqa: regulatory-number -- engineering tolerance for "close enough to an edge to ask the live map", not a planning figure
_DEG_PER_M = 1.0 / 111000.0

# The area check's layer key -> the file name in the manifest.
COPY_KEYS = {
    "tod_map": "tod_sites", "accelerated": "accelerated_tod", "exclusion": "lmr_exclusion", "hn_catchment": "hn_catchment",
    "georges_catchment": "georges_catchment", "coastal_vuln": "coastal_vuln", "airport_noise": "airport_noise", "heritage_shr": "heritage_shr",
}


class _Layer:
    def __init__(self, geoms: list, props: list, as_of: date, skipped: int):
        from shapely.strtree import STRtree

        self.geoms, self.props, self.as_of, self.skipped = geoms, props, as_of, skipped
        self.tree = STRtree(geoms)


class MapCopy:
    """Read-only view of the saved layers. Each layer loads once, on first use; a layer that cannot be proven stays unavailable."""

    def __init__(self, maps_dir: Path = MAPS_DIR):
        self.dir = Path(maps_dir)
        self._layers: dict[str, Optional[_Layer]] = {}
        self._lock = threading.Lock()
        self._manifest: Optional[dict] = None

    # ---- loading ----------------------------------------------------------------------------------------
    def _read_manifest(self) -> Optional[dict]:
        if self._manifest is None:
            try:
                self._manifest = json.loads((self.dir / "manifest.json").read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                logger.warning("map copy: manifest unreadable: %s", exc)
                return None
        return self._manifest

    def _load(self, name: str) -> Optional[_Layer]:
        from shapely.geometry import shape

        m = self._read_manifest()
        meta = ((m or {}).get("layers") or {}).get(name)
        try:
            as_of = datetime.strptime(str((m or {}).get("read_on")), "%Y-%m-%d").date()
        except ValueError:
            logger.warning("map copy: %s has no readable read_on date", name)
            return None
        if not isinstance(meta, dict) or not meta.get("files"):
            logger.warning("map copy: %s is not in the manifest", name)
            return None
        geoms: list = []
        props: list = []
        skipped = 0
        try:
            for f in meta["files"]:  # noqa: bracket-access -- own committed manifest, checked non-empty above; a missing key is caught below and the layer is unavailable
                raw = (self.dir / f["file"]).read_bytes()  # noqa: bracket-access -- same: a missing key is caught below, never a clear
                if hashlib.sha256(raw).hexdigest() != f.get("sha256"):
                    logger.warning("map copy: %s hash does not match the manifest", f["file"])  # noqa: bracket-access -- same
                    return None
                for ft in json.loads(gzip.decompress(raw))["features"]:
                    g = ft.get("geometry")
                    if not g:
                        skipped += 1
                        continue
                    s = shape(g)
                    if not s.is_valid:
                        s = s.buffer(0)
                    if s.is_empty or s.area == 0:   # a zero-area polygon can never contain a point; counted, not guessed at
                        skipped += 1
                        continue
                    geoms.append(s)
                    props.append(ft.get("properties") or {})
        except Exception as exc:  # noqa: BLE001 -- an unreadable layer is unavailable, never clear
            logger.warning("map copy: %s unreadable: %s", name, exc)
            return None
        if len(geoms) + skipped != meta.get("features") or not geoms:
            logger.warning("map copy: %s has %d shapes + %d skipped, manifest says %s", name, len(geoms), skipped, meta.get("features"))
            return None
        return _Layer(geoms, props, as_of, skipped)

    def layer(self, name: str, today: Optional[date] = None) -> Optional[_Layer]:
        today = today or date.today()
        with self._lock:
            if name not in self._layers:
                self._layers[name] = self._load(name)
            lay = self._layers[name]
        if lay is None or (today - lay.as_of).days > MAX_AGE_DAYS:
            return None
        return lay

    # ---- answers ----------------------------------------------------------------------------------------
    def check(self, key: str, lat: float, lng: float, rings: Optional[list] = None, today: Optional[date] = None) -> Optional[dict]:
        """{"point": bool, "lot": bool|None, "as_of": 'YYYY-MM-DD', "near_edge": bool} or None (no answer: ask the live map).

        lot is None when no lot outline was given; the caller treats a point-only answer as it does for the live layer."""
        from shapely.geometry import Point, Polygon

        name = COPY_KEYS.get(key)
        lay = self.layer(name, today) if name else None
        if lay is None:
            return None
        pt = Point(lng, lat)
        near = pt.buffer(EDGE_M * _DEG_PER_M)
        point_hit = any(lay.geoms[i].intersects(pt) for i in lay.tree.query(pt))
        near_edge = any(lay.geoms[i].boundary.distance(pt) <= EDGE_M * _DEG_PER_M for i in lay.tree.query(near))
        lot_hit: Optional[bool] = None
        if rings and len(rings) >= 4:
            try:
                poly = Polygon(rings)
                poly = poly if poly.is_valid else poly.buffer(0)
                if not poly.is_empty:
                    lot_hit = any(lay.geoms[i].intersects(poly) for i in lay.tree.query(poly))
            except Exception as exc:  # noqa: BLE001 -- an unusable outline gives no lot answer, never a clear
                logger.warning("map copy: lot outline unusable: %s", exc)
        return {"point": point_hit, "lot": lot_hit, "as_of": lay.as_of.isoformat(), "near_edge": near_edge}

    def noise_bands(self, lat: float, lng: float, rings: Optional[list] = None, today: Optional[date] = None) -> Optional[list]:
        """Every airport-noise band the lot (or the point) touches, as the live reader returns them; None = no answer."""
        from shapely.geometry import Point, Polygon

        lay = self.layer("airport_noise", today)
        if lay is None:
            return None
        target: Any = Point(lng, lat)
        if rings and len(rings) >= 4:
            try:
                p = Polygon(rings)
                target = p if p.is_valid else p.buffer(0)
            except Exception:  # noqa: BLE001 -- fall back to the point
                target = Point(lng, lat)
        return [{"code": lay.props[i].get("ANEF_CODE"), "name": lay.props[i].get("LAY_NAME")}
                for i in lay.tree.query(target) if lay.geoms[i].intersects(target)]


_default = MapCopy()


def check(key: str, lat: float, lng: float, rings: Optional[list] = None, today: Optional[date] = None) -> Optional[dict]:
    return _default.check(key, lat, lng, rings, today)


def noise_bands(lat: float, lng: float, rings: Optional[list] = None, today: Optional[date] = None) -> Optional[list]:
    return _default.noise_bands(lat, lng, rings, today)
