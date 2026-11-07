# prior-art-checked: four sweeps 2026-11-07 on feat/lmr-clean-law. (1) DB: reads no table; stations come from a
# committed file, everything else is a live state map layer. (2) Frontend: no surface measures from a lot
# outline. (3) Python: services/portal_constraints.py has point-only fetchers (fetch_sepp_exclusions,
# fetch_tod_catchment, fetch_town_centre_catchment: radial buffer, TOD folded into the area answer), and
# services/flood_planning.council_at (Spatial Services LGA layer, same URL used here); none queries by lot
# outline. (4) Plans: ce-NEXT-PROMPT-2026-11-07b-lmr-area-check-build.md section 4B, GATE-FIX-DESIGN s4.
"""Measure one lot for the low-and-mid-rise / TOD area check, from live state map layers only.

Makes the measurements; services/lmr_area_decision.py decides. Nothing here reads a database or any
council-plan data. A measurement that does not come back is None (never False).

Sources (all public NSW services, queried live; only coordinates and the lot outline are sent):
  lot outline        NSW Cadastre layer 9 (the lot containing the address point; must CONTAIN the point)
  TOD / accelerated / exclusion / Town Centres   ePlanning Planning_Portal_SEPP 752 / 759 / 776 / 766
  heritage           ePlanning Planning_Portal_Principal_Planning 16 (EPI Heritage, LAY_CLASS) and 221 (State Heritage Register curtilage)
  bush fire          Fire/BFPL layer 0
  council area       NSW Spatial Services administrative boundaries layer 8
  stations           data/law/lmr_station_entrances.json (OSM entrances for the Schedule 11 and 12 stations, names read from the law)
  walking            services/lmr_walk_surface.py
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

import requests

from services import lmr_area_decision as dec
from services import lmr_walk_surface as walk_mod

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIONS_PATH = REPO_ROOT / "data" / "law" / "lmr_station_entrances.json"

_EPL = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning"
LAYERS = {
    "tod_map": f"{_EPL}/Planning_Portal_SEPP/MapServer/752/query",
    "accelerated": f"{_EPL}/Planning_Portal_SEPP/MapServer/759/query",
    "exclusion": f"{_EPL}/Planning_Portal_SEPP/MapServer/776/query",
    "town_centres": f"{_EPL}/Planning_Portal_SEPP/MapServer/766/query",
    "heritage_epi": f"{_EPL}/Planning_Portal_Principal_Planning/MapServer/16/query",
    "heritage_shr": f"{_EPL}/Planning_Portal_Principal_Planning/MapServer/221/query",
    "bushfire": "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire/BFPL/MapServer/0/query",
    # prior-art-checked: reuse not viable as a function: services/portal_constraints.fetch_coastal queries layers 1, 6 and 3 by POINT
    # and counts the coastal ENVIRONMENT area (layer 6), which s164(1)(b) does not name; these need lot-outline queries on exactly three maps.
    # Flood (f) and (f1) catchment layers: probed 2026-11-07, Hurstville and Bankstown hit 147, Penrith hits 157, Ashfield neither.
    # Layer 251 is labelled "No map at this time" but holds 10 areas (Port Stephens and Coffs coast), so it is queried, not assumed empty.
    "georges_catchment": f"{_EPL}/Planning_Portal_SEPP/MapServer/147/query",
    "hn_catchment": f"{_EPL}/Planning_Portal_SEPP/MapServer/157/query",
    "coastal_vuln": f"{_EPL}/Planning_Portal_SEPP/MapServer/251/query",
    "coastal_wetlands": "https://mapprod1.environment.nsw.gov.au/arcgis/rest/services/CoastalManagementSEPP/CoastalManagementSEPP/MapServer/1/query",
    "littoral": "https://mapprod1.environment.nsw.gov.au/arcgis/rest/services/CoastalManagementSEPP/CoastalManagementSEPP/MapServer/3/query",
    "lga": "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer/8/query",
    # prior-art-checked: the existing lot readers (app/api/property/route.ts, lib/nsw-planning-portal.ts,
    # for-property/route.ts) are TypeScript frontend code and for-property is a council-mixed route that the boundary
    # check (R3) forbids this module to call; this Python service needs the lot ring by point as one contract.
    # Lot outline: the SIX Property layer first (answered in 2-10 s on 2026-11-07), the SIX Cadastre layer second
    # (it timed out three times at 25 s the same day).
    "lot": "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Property/MapServer/4/query",
    "lot_fallback": "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer/9/query",
}
TIMEOUT_S = 12
_UA = {"User-Agent": "plotdetect-lmr-area-check/1.0"}

# LAY_CLASS values seen on the EPI Heritage layer (distinct values read live 2026-11-07). Anything not
# listed here makes the heritage answer "unknown" rather than a silent clear.
HERITAGE_ITEM_CLASSES = {"Item - General", "Item - Landscape", "Item - Archaeological", "Item - Aboriginal",
                         "Local Heritage - General"}
HERITAGE_CONSERVATION_CLASSES = {"Conservation Area - General", "Conservation Area - Landscape",
                                 "Conservation Area - Archaeological", "Conservation Area - Aboriginal",
                                 "Heritage Conservation Area"}
HERITAGE_UNDECIDED_CLASSES = {"Aboriginal Place of Heritage Significance", "Aboriginal Object"}  # text does not say


def _get_json(url: str, params: dict, post: bool = False) -> Optional[dict]:
    """The single network choke point (tests replace it). None = did not answer; never raises."""
    for attempt in range(2):
        try:
            r = (requests.post(url, data=params, headers=_UA, timeout=TIMEOUT_S) if post
                 else requests.get(url, params=params, headers=_UA, timeout=TIMEOUT_S))
            r.raise_for_status()
            j = r.json()
            if isinstance(j, dict) and "features" in j and "error" not in j:
                return j
            logger.warning("lmr inputs: %s returned no 'features' (%s)", url, str(j)[:120])
        except Exception as exc:  # noqa: BLE001 -- a failed layer is None, never False
            logger.warning("lmr inputs: %s failed: %s", url, exc)
        time.sleep(0.5 * (attempt + 1))
    return None


def _base(out_fields: str = "*", geometry: bool = False) -> dict:
    return {"outFields": out_fields, "returnGeometry": "true" if geometry else "false", "f": "json",
            "spatialRel": "esriSpatialRelIntersects"}


def _point_params(lat: float, lng: float, **kw) -> dict:
    return {**_base(**kw), "geometry": f"{lng},{lat}", "geometryType": "esriGeometryPoint", "inSR": "4326"}


def _poly_params(rings: list, **kw) -> dict:
    return {**_base(**kw), "geometry": json.dumps({"rings": [rings], "spatialReference": {"wkid": 4326}}),
            "geometryType": "esriGeometryPolygon", "inSR": "4326"}


def _features(j: Optional[dict]) -> Optional[list]:
    return None if j is None else (j.get("features") or [])


def _hit(url: str, params: dict) -> Optional[bool]:
    f = _features(_get_json(url, params, post=True))
    return None if f is None else len(f) > 0


# ---- lot outline ---------------------------------------------------------------------------------------
def fetch_lot_rings(lat: float, lng: float) -> Optional[list]:
    """Outer ring of the lot (lng,lat pairs) that contains the point; None when absent or not containing it."""
    from shapely.geometry import Point, Polygon
    for key in ("lot", "lot_fallback"):
        j = _get_json(LAYERS[key], {**_point_params(lat, lng, out_fields="*", geometry=True), "outSR": "4326"}, post=True)
        best = None
        for f in (_features(j) or []):
            rings = (f.get("geometry") or {}).get("rings")
            if not rings or len(rings[0]) < 4:
                continue
            try:
                poly = Polygon(rings[0]).buffer(0)
            except Exception:  # noqa: BLE001
                continue
            if poly.is_valid and not poly.is_empty and poly.contains(Point(lng, lat)):
                if best is None or poly.area < best[0]:  # smallest containing polygon: a lot, not common property
                    best = (poly.area, rings[0])
        if best:
            return best[1]
    return None


# ---- station anchors -----------------------------------------------------------------------------------
def load_stations(path: Path = STATIONS_PATH) -> Optional[dict]:
    """{'built','source','stations':[{name, lat, lon, entrances:[{id,lat,lon}], no_mapped_entrance}]} or None."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        return doc if isinstance(doc.get("stations"), list) and doc["stations"] else None  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    except (OSError, ValueError):
        return None


_tc_cache: dict = {"at": 0.0, "polys": None}


def town_centre_polygons(ttl_s: int = 6 * 3600) -> Optional[list]:
    """All Town Centres Map polygons statewide (116 on 2026-11-07), cached; list of {label, rings}."""
    now = time.time()
    if _tc_cache["polys"] is not None and now - _tc_cache["at"] < ttl_s:  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        return _tc_cache["polys"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    j = _get_json(LAYERS["town_centres"], {"where": "1=1", "outFields": "LABEL,EPI_NAME", "returnGeometry": "true",
                                           "outSR": "4326", "f": "json", "resultRecordCount": 500}, post=True)
    if j is None or j.get("exceededTransferLimit"):
        return None
    polys = [{"label": (f.get("attributes") or {}).get("LABEL"), "rings": (f.get("geometry") or {}).get("rings")}
             for f in (j.get("features") or []) if (f.get("geometry") or {}).get("rings")]
    if not polys:
        return None
    _tc_cache.update(at=now, polys=polys)
    return polys


# ---- measurement ---------------------------------------------------------------------------------------
def _heritage(rings: Optional[list]) -> dict:
    """Heritage item / conservation area from LAY_CLASS on the lot outline; State Register curtilage on the outline."""
    out: dict[str, Any] = {"item": None, "conservation_area": None, "state_register": None}
    if not rings:
        return out
    feats = _features(_get_json(LAYERS["heritage_epi"], _poly_params(rings, out_fields="LAY_CLASS"), post=True))
    if feats is not None:
        classes = {(f.get("attributes") or {}).get("LAY_CLASS") for f in feats}
        if classes & HERITAGE_ITEM_CLASSES:
            out["item"] = True
        elif classes - HERITAGE_CONSERVATION_CLASSES - HERITAGE_UNDECIDED_CLASSES - {None}:
            out["item"] = None  # a class this code has not classified: never called clear
        elif classes & HERITAGE_UNDECIDED_CLASSES:
            out["item"] = None
        else:
            out["item"] = False
        out["conservation_area"] = bool(classes & HERITAGE_CONSERVATION_CLASSES)
    out["state_register"] = _hit(LAYERS["heritage_shr"], _poly_params(rings, out_fields="OBJECTID"))
    return out


def _layer(key: str, lat: float, lng: float, rings: Optional[list]) -> dict:
    pt = _hit(LAYERS[key], _point_params(lat, lng, out_fields="OBJECTID"))
    lot = _hit(LAYERS[key], _poly_params(rings, out_fields="OBJECTID")) if rings else None
    return {"point": pt, "lot": lot}


def _lga(lat: float, lng: float) -> Optional[str]:
    f = _features(_get_json(LAYERS["lga"], _point_params(lat, lng, out_fields="lganame"), post=True))
    if not f:
        return None
    name = (f[0].get("attributes") or {}).get("lganame")
    return name.strip() if isinstance(name, str) and name.strip() else None


def _epsg_for(lng: float) -> int:
    zone = int((lng + 180) // 6) + 1
    if not 49 <= zone <= 56:
        raise ValueError("longitude outside the MGA zones")
    return 28300 + zone


# prior-art-checked: reuse not viable: the heritage and bush fire code the guard lists is TypeScript page and PDF code; fetch_layers is
# the same Python block that was inside gather(), moved into its own function. No new source and no new query.
def _flood_answer(lga: Optional[str], rings: Optional[list], flood_fn: Any) -> Optional[dict]:
    """The flood-planning answer, asked only for a lot in a council s164(1)(g) names. Any failure is value None, never False."""
    try:
        fac = dec.LawFacts.load()
        if not lga or not dec._in_names(lga, fac.council_names("g", "roman")):
            return None   # not a named council: the decision clears (g) by the council alone
        wkt = None
        if rings:
            wkt = "POLYGON((" + ", ".join(f"{x} {y}" for x, y in rings) + "))"
        out = flood_fn(wkt)
        v = out.get("value") if isinstance(out, dict) else None
        return {"value": v if isinstance(v, bool) else None, "reason": (out or {}).get("reason") if isinstance(out, dict) else None}
    except Exception as exc:  # noqa: BLE001 -- a failed flood lookup is unknown, never a clear
        logger.warning("lmr inputs: flood answer failed: %s", exc)
        return {"value": None, "reason": f"flood lookup failed: {type(exc).__name__}"}


def fetch_layers(lat: float, lng: float, rings: Optional[list]) -> dict:
    """The map-service measurements for one lot (TOD, accelerated TOD, exclusion map, bush fire, heritage, council). Network only."""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {k: ex.submit(_layer, k, lat, lng, rings) for k in (
            "tod_map", "accelerated", "exclusion", "bushfire",
            "georges_catchment", "hn_catchment", "coastal_vuln", "coastal_wetlands", "littoral")}
        f_her = ex.submit(_heritage, rings)
        f_lga = ex.submit(_lga, lat, lng)
        out: dict[str, Any] = {k: f.result() for k, f in futs.items()}
        out["heritage"] = f_her.result()
        out["lga"] = f_lga.result()
    return out


def gather(lat: float, lng: float, *, rings: Optional[list] = None, stations: Optional[dict] = None,
           walk_surfaces: Optional[list] = None, layers: Optional[dict] = None,
           flood_fn: Optional[Any] = None) -> dict:
    """Measurements for decide(): layer hits (point and lot outline), council, distances, walking.

    `flood_fn` (optional) is called with the lot outline as WKT (or None) ONLY when the lot is in one of the 23 councils s164(1)(g) names,
    and returns the existing flood answer (services/flood_planning.flood_planning_status): a dict with "value" True / False / None.
    The caller owns the database connection; this module holds none. Without it, a lot in a named council cannot be answered yes.
    """
    from pyproj import Transformer
    from shapely.geometry import MultiPoint, Polygon
    from shapely.ops import transform, unary_union

    if rings is None:
        rings = fetch_lot_rings(lat, lng)
    # prior-art-checked: the heritage/bushfire readers found by the guard are TypeScript pages and PDF code; this is the same
    # Python block moved into a function so its result can be saved and passed back in (no new source, no new query).
    # `layers` may be passed in (saved from an earlier call) so that a re-run after the walking files change needs no map calls.
    m: dict[str, Any] = dict(layers) if layers is not None else fetch_layers(lat, lng, rings)
    m["lot_outline"] = bool(rings)
    if flood_fn is not None and "flood_planning" not in m:
        m["flood_planning"] = _flood_answer(m.get("lga"), rings, flood_fn)

    # Distances need a lot outline and the station file; without either they stay None (cant_tell), never a number.
    m["straight_m"] = None
    m["sched12_straight_m"] = None
    m["walk"] = None
    stations = stations if stations is not None else load_stations()
    tcs = town_centre_polygons()
    if not rings or not stations or tcs is None:
        m["distance_note"] = ("no lot outline" if not rings else "station file unreadable" if not stations
                              else "Town Centres Map did not answer")
        return m
    fac = dec.LawFacts.load()
    s12_names = set(fac.names("schedule_12_stations"))
    s11_names = set(fac.names("schedule_11_stations"))
    have = {s["name"] for s in stations["stations"]}  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    if (s11_names | s12_names) - have:
        m["distance_note"] = f"station file lacks {len((s11_names | s12_names) - have)} listed stations"
        return m
    to_m = Transformer.from_crs(4326, _epsg_for(lng), always_xy=True).transform
    lot = transform(to_m, Polygon(rings).buffer(0))
    outer = fac.number("lmr_outer_distance")
    ent11, ent12 = [], []
    near_anchors: set[str] = set()  # every anchor whose straight distance is within the walking limit
    for st in stations["stations"]:  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        pts = [(e["lon"], e["lat"]) for e in st.get("entrances", [])] or [(st["lon"], st["lat"])]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        pm = [to_m(x, y) for x, y in pts]
        if st["name"] in s12_names:  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
            ent12 += pm
        elif st["name"] in s11_names:  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
            ent11 += pm
            if lot.distance(MultiPoint(pm)) <= outer:
                near_anchors.add(st["name"])  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    tc_geoms = [transform(to_m, unary_union([Polygon(r).buffer(0) for r in p["rings"]])) for p in tcs]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    for p, g in zip(tcs, tc_geoms):
        if lot.distance(g) <= outer:
            near_anchors.add(str(p["label"]))  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    ds = [lot.distance(MultiPoint(ent11))] + [lot.distance(g) for g in tc_geoms]
    m["straight_m"] = min(ds)
    m["sched12_straight_m"] = lot.distance(MultiPoint(ent12))
    if m["straight_m"] > outer:  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        return m  # decided by the straight line alone; no walk needed
    touches = m["straight_m"] < 1.0  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    ring_m = [to_m(x, y) for x, y in rings]
    # The walk is the MINIMUM over every anchor within reach, so every such anchor must have a built surface:
    # otherwise a farther anchor's longer walk would be taken as the answer (a wrong "no").
    m["walk"] = walk_mod.walk_from_lot(ring_m, _epsg_for(lng), m["straight_m"], touches, walk_surfaces,  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
                                       required_anchors=near_anchors)
    return m


def area_check(lat: float, lng: float, **kw) -> dict:
    """Measure the lot, then decide. The measurements are echoed on the answer so a reader can see them."""
    try:
        m = gather(lat, lng, **kw)
    except Exception as exc:  # noqa: BLE001 -- never raise, never a silent yes
        logger.warning("lmr area check measurement failed: %s", exc)
        return dec._failed(f"measurement failed: {type(exc).__name__}: {exc}")
    r = dec.decide(m)
    r["measured"] = {**r.get("measured", {}), "lot_outline": m.get("lot_outline"), "distance_note": m.get("distance_note")}
    return r
