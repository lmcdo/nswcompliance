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
import math
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

MAPS_DIR = Path(__file__).resolve().parent.parent / "data" / "law" / "maps"
MAX_AGE_DAYS = 45      # noqa: regulatory-number -- owner-approved staleness limit for our own copy, not a planning figure
EDGE_M = 5.0           # noqa: regulatory-number -- engineering tolerance for "close enough to an edge to ask the live map", not a planning figure
_DEG_PER_M = 1.0 / 111000.0


def _edge_deg(lat: float) -> float:
    """EDGE_M as degrees. A degree of longitude is shorter than a degree of latitude away from the equator, so the longitude figure (the larger
    number of degrees) is used for both: it flags a little more, never less."""
    return EDGE_M * _DEG_PER_M / max(math.cos(math.radians(lat)), 0.1)

# The area check's layer key -> the file name in the manifest.
COPY_KEYS = {
    "tod_map": "tod_sites", "accelerated": "accelerated_tod", "exclusion": "lmr_exclusion", "hn_catchment": "hn_catchment",
    "georges_catchment": "georges_catchment", "coastal_vuln": "coastal_vuln", "airport_noise": "airport_noise", "heritage_shr": "heritage_shr",
    # the 2024 Hawkesbury-Nepean River Flood Study extents (see flood_distance); a study, so each layer carries its own read_on and age limit in the manifest
    "hn_pmf": "hn_pmf", "hn_500aep": "hn_500aep", "hn_100aep": "hn_100aep",
}
FLOOD_EDGE_M = 100.0   # noqa: regulatory-number -- engineering margin: 15 m flood-model cell plus the coarse scale of the law's Figure 1-1, not a planning figure
FLOOD_SEARCH_DEG = 0.3   # about 30 km: a flood area farther than this is reported as "none within the search distance"


class _Layer:
    def __init__(self, geoms: list, props: list, as_of: date, skipped: int, max_age_days: int = MAX_AGE_DAYS):
        from shapely.strtree import STRtree

        self.geoms, self.props, self.as_of, self.skipped = geoms, props, as_of, skipped
        self.max_age_days = max_age_days
        self.tree = STRtree(geoms)
        bs = [g.bounds for g in geoms]
        self.bounds = (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))   # lng/lat box the layer covers


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
        if not isinstance(meta, dict) or not meta.get("files"):
            logger.warning("map copy: %s is not in the manifest", name)
            return None
        # A layer may carry its own read_on and max_age_days (a dated study, not a monthly-changing legal map); otherwise the file-wide date and the 45-day limit apply.
        try:
            as_of = datetime.strptime(str(meta.get("read_on") or (m or {}).get("read_on")), "%Y-%m-%d").date()
        except ValueError:
            logger.warning("map copy: %s has no readable read_on date", name)
            return None
        own_age = meta.get("max_age_days")
        max_age = own_age if isinstance(own_age, int) and not isinstance(own_age, bool) and own_age > 0 else MAX_AGE_DAYS
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
        return _Layer(geoms, props, as_of, skipped, max_age)

    def layer(self, name: str, today: Optional[date] = None) -> Optional[_Layer]:
        today = today or date.today()
        with self._lock:
            if name not in self._layers:
                self._layers[name] = self._load(name)
            lay = self._layers[name]
        if lay is None:
            return None
        if lay.as_of > today:   # a read_on date in the future is a typo or a clock fault; it must not keep a copy fresh
            logger.warning("map copy: %s read_on %s is in the future", name, lay.as_of)
            return None
        if (today - lay.as_of).days > lay.max_age_days:
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
        tol = _edge_deg(lat)
        near = pt.buffer(tol)
        point_hit = any(lay.geoms[i].intersects(pt) for i in lay.tree.query(pt))
        near_edge = any(lay.geoms[i].boundary.distance(pt) <= tol for i in lay.tree.query(near))
        lot_hit: Optional[bool] = None
        if rings and len(rings) >= 4:
            try:
                poly = Polygon(rings)
                poly = poly if poly.is_valid else poly.buffer(0)
                if not poly.is_empty:
                    lot_hit = any(lay.geoms[i].intersects(poly) for i in lay.tree.query(poly))
                    # a lot whose edge is within the tolerance of a layer edge can differ from the live map too, even when the point is far away
                    near_edge = near_edge or any(lay.geoms[i].boundary.distance(poly) <= tol for i in lay.tree.query(poly.buffer(tol)))
            except Exception as exc:  # noqa: BLE001 -- an unusable outline gives no lot answer, never a clear
                logger.warning("map copy: lot outline unusable: %s", exc)
        return {"point": point_hit, "lot": lot_hit, "as_of": lay.as_of.isoformat(), "near_edge": near_edge}

    def flood_distance(self, key: str, lat: float, lng: float, rings: Optional[list] = None, today: Optional[date] = None) -> Optional[dict]:
        """How the lot sits against one flood-study layer, in metres, or None (no answer: the copy is missing, unproven or too old).

        {"inside": the lot (its outline when given, else the point) touches the flood area,
         "edge_m": metres from the lot to the nearest flood-area EDGE (0 when the lot straddles it), None if none within the search distance,
         "nearest_m": metres to the nearest flood area itself (0 when inside), None if none within the search distance,
         "within_box": the lot lies inside the box the layer covers (a lot outside it was never mapped by the study),
         "used_outline": whether the lot outline was used, "as_of": date the copy was read, "polygons": how many flood areas were searched}"""
        from shapely.geometry import Point, Polygon
        from shapely.ops import transform

        name = COPY_KEYS.get(key)
        lay = self.layer(name, today) if name else None
        if lay is None or lay.skipped:   # a flood layer with even one unreadable or empty area is incomplete: a lot in that area would read as clear, so it gives no answer
            return None
        target: Any = Point(lng, lat)
        used_outline = False
        if rings and len(rings) >= 4:
            try:
                p = Polygon(rings)
                p = p if p.is_valid else p.buffer(0)
                if not p.is_empty:   # a degenerate outline repairs to nothing: fall back to the point, never to "nothing found"
                    target, used_outline = p, True
            except Exception as exc:  # noqa: BLE001 -- an unusable outline falls back to the point
                logger.warning("map copy: lot outline unusable: %s", exc)
        mx, my = 111320.0 * math.cos(math.radians(lat)), 110540.0   # metres per degree here (the same flat scale the walking maps use)

        def metric(g: Any) -> Any:
            return transform(lambda x, y, z=None: ((x - lng) * mx, (y - lat) * my), g)

        minx, miny, maxx, maxy = lay.bounds
        tb = target.bounds
        within_box = tb[0] >= minx and tb[2] <= maxx and tb[1] >= miny and tb[3] <= maxy
        cand = list(lay.tree.query(target.buffer(FLOOD_SEARCH_DEG)))
        inside = any(lay.geoms[i].intersects(target) for i in cand)
        nearest = edge = None
        if cand:
            t_m = metric(target)
            nearest = 0.0 if inside else min(t_m.distance(metric(lay.geoms[i])) for i in cand)
            edge = min(t_m.distance(metric(lay.geoms[i].boundary)) for i in cand)
        return {"inside": inside, "edge_m": None if edge is None else round(edge, 1), "nearest_m": None if nearest is None else round(nearest, 1),
                "within_box": within_box, "used_outline": used_outline, "as_of": lay.as_of.isoformat(), "polygons": len(cand)}

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
                p = p if p.is_valid else p.buffer(0)
                if not p.is_empty:   # a degenerate ring repairs to nothing; searching with nothing would read as no band
                    target = p
            except Exception:  # noqa: BLE001 -- fall back to the point
                target = Point(lng, lat)
        return [{"code": lay.props[i].get("ANEF_CODE"), "name": lay.props[i].get("LAY_NAME")}
                for i in lay.tree.query(target) if lay.geoms[i].intersects(target)]


_default = MapCopy()


def check(key: str, lat: float, lng: float, rings: Optional[list] = None, today: Optional[date] = None) -> Optional[dict]:
    return _default.check(key, lat, lng, rings, today)


def noise_bands(lat: float, lng: float, rings: Optional[list] = None, today: Optional[date] = None) -> Optional[list]:
    return _default.noise_bands(lat, lng, rings, today)


def flood_distance(key: str, lat: float, lng: float, rings: Optional[list] = None, today: Optional[date] = None) -> Optional[dict]:
    return _default.flood_distance(key, lat, lng, rings, today)
