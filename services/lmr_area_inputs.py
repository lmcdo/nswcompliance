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
  Sydney Airport noise   services/sydney_anef.py (the endorsed 2045 ANEF chart's contours, committed in data/anef/; local geometry, no network)
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

import requests

from services import lmr_area_decision as dec
from services import lmr_walk_surface as walk_mod
from services import sydney_anef

logger = logging.getLogger(__name__)


_STAGE_LOG = logging.getLogger("uvicorn.error")   # uvicorn configures this one at INFO, so the lines reach the service log (this module has no logging setup of its own)


def _stage(name: str, fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Call fn and log how long it took ("lmr stage <name> <seconds>"), so the time of a slow evidence call can be read from the service log. Nothing about the answer changes; an exception passes through."""
    t0 = time.perf_counter()
    try:
        return fn(*args, **kwargs)
    finally:
        _STAGE_LOG.info("lmr stage %s %.2fs", name, time.perf_counter() - t0)

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
    # prior-art-checked: reuse not viable: portal_constraints.fetch_anef reads the Sydney-only anef_zones table, which flags about half of Sydney lots
    # (223 of 400 test lots at ANEF 25 or more, 2026-11-07); layer 235 is the portal's own table of contour bands (Western Sydney Airport and several
    # council areas), queried by lot outline. No pipeline reader exists (grep services/, 2026-11-07); Geoscience Australia's open gas pipeline layer
    # (CC BY 4.0) holds the Moomba-Sydney and Sydney-Newcastle lines and is queried with the law's distance.
    "airport_noise": f"{_EPL}/Planning_Portal_Protection/MapServer/235/query",
    "pipeline": "https://services.ga.gov.au/gis/rest/services/Oil_Gas_Pipelines/MapServer/1/query",
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


# prior-art-checked: reuse not viable because the only hits are pip's vendored copy of requests; this adds two optional arguments to this
# module's own network helper so the council lookup can fail fast (its defaults are unchanged for every other caller).
def _get_json(url: str, params: dict, post: bool = False, *, timeout: Optional[float] = None,
              attempts: Optional[int] = None) -> Optional[dict]:
    """The single network choke point (tests replace it). None = did not answer; never raises.

    `timeout` and `attempts` default to TIMEOUT_S and 2; the council lookup passes shorter limits because it has a local substitute.
    """
    limit = timeout or TIMEOUT_S
    for attempt in range(attempts or 2):
        try:
            r = (requests.post(url, data=params, headers=_UA, timeout=limit) if post
                 else requests.get(url, params=params, headers=_UA, timeout=limit))
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


def _hit(url: str, params: dict, **limits: Any) -> Optional[bool]:
    f = _features(_get_json(url, params, post=True, **limits))
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


# prior-art-checked: reuse not viable as a function: this wraps this module's own _layer for the layers services/lmr_map_copy.py holds; the copy is injected by the
# caller (copy_fn) like the council and bush fire copies, so tests and other callers are unchanged. Side by side on 200 lots (7 layers, point and lot outline, 2026-11-21):
# 2800 comparisons, 0 differences from the live service.
COPY_LAYERS = ("tod_map", "accelerated", "exclusion", "georges_catchment", "hn_catchment", "coastal_vuln")


def _copy_answer(key: str, lat: float, lng: float, rings: Optional[list], copy_fn: Optional[Any]) -> Optional[dict]:
    """The layer answer from our own copy, or None to ask the live map. A copy answer is used only when it is proven and fresh (copy_fn gives None otherwise),
    when the point and the lot outline are not near a layer edge (the copy and the live map can differ by a few metres there) and, if a lot outline was
    given, when the copy could test it. Any doubt asks the live map, exactly as before."""
    if copy_fn is None or key not in COPY_LAYERS:
        return None
    try:
        got = copy_fn(key, lat, lng, rings)
    except Exception as exc:  # noqa: BLE001 -- a failing copy asks the live map, never answers
        logger.warning("lmr inputs: map copy failed for %s: %s", key, exc)
        return None
    if not isinstance(got, dict) or got.get("near_edge") is not False or not isinstance(got.get("point"), bool):
        return None
    if rings and not isinstance(got.get("lot"), bool):
        return None
    as_of = got.get("as_of")
    if not isinstance(as_of, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of):   # an answer with no date could not be disclosed, so it is not used
        return None
    return {"point": got.get("point"), "lot": got.get("lot") if rings else None, "copy_as_of": got.get("as_of")}


def _layer(key: str, lat: float, lng: float, rings: Optional[list], copy_fn: Optional[Any] = None, **limits: Any) -> dict:
    own = _copy_answer(key, lat, lng, rings, copy_fn)
    if own is not None:
        return own
    pt = _hit(LAYERS[key], _point_params(lat, lng, out_fields="OBJECTID"), **limits)
    lot = _hit(LAYERS[key], _poly_params(rings, out_fields="OBJECTID"), **limits) if rings else None
    return {"point": pt, "lot": lot}


# prior-art-checked: reuse not viable because this wraps this module's own _layer for one layer; the own-copy lookup is services/lmr_area_lga.py,
# injected by the caller like the council lookup. Rule: our copy lacks about 800 live areas, so its "clear" is never trusted alone.
BUSHFIRE_LIVE_CHECK_TIMEOUT_S = 6


def _bushfire_resolved(lat: float, lng: float, rings: Optional[list], own: Optional[Any]) -> tuple[dict, Optional[dict]]:
    """(layer result, source). Our copy first: a point on bush fire prone land is final (keeping an area only makes the check stricter).
    A "clear" in our copy is NEVER an answer: measured 2026-11-18, 6 of 60 random lots were clear in our copy but bush fire prone on the live map.
    So the live map confirms; if it does not answer the result stays unknown (can't tell) and the source says what our copy showed.
    source is None when the live map gave the answer."""
    mine = None
    if own is not None:
        try:
            got = own(lat, lng, rings)
            if isinstance(got, dict) and isinstance(got.get("point"), bool) and got.get("as_of"):
                mine = got
        except Exception as exc:  # noqa: BLE001
            logger.warning("lmr inputs: own bush fire copy failed: %s", exc)
    if mine is not None and mine.get("point") is True:
        return {"point": True, "lot": mine.get("lot")}, {"source": "snapshot", "as_of": str(mine.get("as_of")), "confirmed": False, "found": "hit"}
    limits = {"timeout": BUSHFIRE_LIVE_CHECK_TIMEOUT_S, "attempts": 1} if mine is not None else {}
    live = _layer("bushfire", lat, lng, rings, **limits)
    if live.get("point") is not None and (live.get("lot") is not None or not rings):
        return live, None
    if mine is not None:   # the live map is silent: stay unknown, and say what our (known to be incomplete) copy showed
        return live, {"source": "snapshot", "as_of": str(mine.get("as_of")), "confirmed": False, "found": "clear_unconfirmed" if not (mine.get("lot") or mine.get("point")) else "part"}
    return live, None


def _noise_bands(lat: float, lng: float, rings: Optional[list]) -> Optional[list]:
    """Every airport-noise contour band the lot touches (code like '25 - 30' and the map's own name), [] if none, None if the map did not answer."""
    geom = _poly_params(rings, out_fields="ANEF_CODE,LAY_NAME") if rings else _point_params(lat, lng, out_fields="ANEF_CODE,LAY_NAME")
    feats = _features(_get_json(LAYERS["airport_noise"], geom, post=True))
    if feats is None:
        return None
    return [{"code": (f.get("attributes") or {}).get("ANEF_CODE"), "name": (f.get("attributes") or {}).get("LAY_NAME")} for f in feats]


# prior-art-checked: reuse not viable because the hits are pip internals and a blog page; this reads the flood-study copy through the injected function (services/lmr_map_copy.flood_distance),
# the same pattern as copy_fn, and validates every field because a malformed answer must never read as "clear".
FLOOD_STUDY_LAYERS = {"pmf": "hn_pmf", "aep500": "hn_500aep", "aep100": "hn_100aep"}


def _num_or_none(v: Any) -> bool:
    return v is None or (isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v >= 0 and v != float("inf"))


def _flood_answer_consistent(got: dict) -> bool:
    """The distances must agree with the inside flag, or the decision could read a contradiction as clear. Inside means the lot touches a flood area: the distance to one is 0 and an edge
    distance exists. Outside means it does not: both distances are None together (no flood area within the search distance), or both are numbers, equal (the nearest area's distance
    is its edge distance for a point outside it) and above 0."""
    edge, near = got.get("edge_m"), got.get("nearest_m")
    if got.get("inside") is True:
        return near == 0 and edge is not None
    if edge is None or near is None:
        return edge is None and near is None
    return near > 0 and abs(edge - near) <= 1.0   # noqa: regulatory-number -- tolerance in metres between two distances measured the same way, not a planning figure


def _flood_study(lat: float, lng: float, rings: Optional[list], fn: Any, all_layers: bool = False) -> dict:
    """How the lot sits against the saved flood-study layers: {"pmf": {...}} and, for the evidence page (all_layers), "aep500" and "aep100" too. The two flood-frequency layers are
    context only and cost about 0.1 s each, so the public check reads the Probable Maximum Flood layer alone. A layer that gave no valid answer is left out, never filled in,
    so the decision falls back to what it did before."""
    out: dict[str, Any] = {}
    for name, key in FLOOD_STUDY_LAYERS.items():
        if name != "pmf" and not all_layers:
            continue
        try:
            got = fn(key, lat, lng, rings)
        except Exception as exc:  # noqa: BLE001 -- a failing copy leaves the layer out
            logger.warning("lmr inputs: flood study copy failed for %s: %s", key, exc)
            continue
        if (isinstance(got, dict) and isinstance(got.get("inside"), bool) and isinstance(got.get("within_box"), bool)
                and "edge_m" in got and "nearest_m" in got   # a missing key is a malformed answer, never "no flood area nearby" (None means that only when the key is present)
                and _num_or_none(got.get("edge_m")) and _num_or_none(got.get("nearest_m")) and _flood_answer_consistent(got)
                and isinstance(got.get("as_of"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", got.get("as_of") or "")):
            out[name] = got
    return out


PIPELINE_LADDER_M = (5000, 20000, 60000)


def _pipeline_nearest(lat: float, lng: float) -> dict:
    """The nearest gas pipeline on Geoscience Australia's national map, in metres, for the evidence page. One to three small queries, widening: 5 km, 20 km, 60 km.
    {"nearest_m", "nearest_name"} or {"nearest_m": None, "searched_m": 60000} when none within the widest search; {} when the service did not answer."""
    import math

    mx, my = 111320.0 * math.cos(math.radians(lat)), 110540.0
    for radius in PIPELINE_LADDER_M:
        params = {**_point_params(lat, lng, out_fields="feature_name"), "distance": str(radius), "units": "esriSRUnit_Meter", "returnGeometry": "true", "outSR": "4326"}
        feats = _features(_get_json(LAYERS["pipeline"], params, post=True))
        if feats is None:
            return {}
        best = None
        for f in feats:
            for path in ((f.get("geometry") or {}).get("paths") or []):
                pts = [((x - lng) * mx, (y - lat) * my) for x, y in path]
                for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                    dx, dy = x2 - x1, y2 - y1
                    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(x1 * dx + y1 * dy) / (dx * dx + dy * dy)))
                    d = math.hypot(x1 + t * dx, y1 + t * dy)
                    if best is None or d < best[0]:
                        best = (d, (f.get("attributes") or {}).get("feature_name"))
        if best is not None:
            return {"nearest_m": round(best[0]), "nearest_name": best[1]}
    return {"nearest_m": None, "searched_m": PIPELINE_LADDER_M[-1]}


def _pipeline_near(lat: float, lng: float, rings: Optional[list], metres: float) -> dict:
    """Is a gas pipeline on Geoscience Australia's national map within `metres` of the lot? hit True / False, or None when the service did not answer."""
    extra = {"distance": str(metres), "units": "esriSRUnit_Meter"}
    geom = {**(_poly_params(rings, out_fields="feature_name,operator") if rings else _point_params(lat, lng, out_fields="feature_name,operator")), **extra}
    feats = _features(_get_json(LAYERS["pipeline"], geom, post=True))
    if feats is None:
        return {"hit": None, "names": []}
    return {"hit": len(feats) > 0, "names": [(f.get("attributes") or {}).get("feature_name") for f in feats]}


# The live council lookup fails fast (5 s, one try) because a local substitute exists; the state servers stall in waves (measured 2026-11-18).
LGA_LIVE_TIMEOUT_S = 5
LGA_LIVE_ATTEMPTS = 1


# prior-art-checked: reuse not viable because this splits this module's own council lookup in two (answered or not) so a live "no council"
# answer is never overridden by the fallback; no new source or query.
def _lga_live(lat: float, lng: float) -> tuple[bool, Optional[str]]:
    """(answered, council). answered False = the live service gave no answer (stall or error). answered True with None = it answered and
    named no council (or a blank one): that is the authority's answer and the fallback must not override it."""
    f = _features(_get_json(LAYERS["lga"], _point_params(lat, lng, out_fields="lganame"), post=True,
                            timeout=LGA_LIVE_TIMEOUT_S, attempts=LGA_LIVE_ATTEMPTS))
    if f is None:
        return False, None
    if not f:
        return True, None
    name = (f[0].get("attributes") or {}).get("lganame")
    return True, (name.strip() if isinstance(name, str) and name.strip() else None)


def _lga(lat: float, lng: float) -> Optional[str]:
    return _lga_live(lat, lng)[1]


# prior-art-checked: reuse not viable because no other code resolves the council from our own lot table; the lookups live in
# services/lmr_area_lga.py and are injected by the caller (this module holds no database connection), the same pattern as flood_fn.
def _lga_resolved(lat: float, lng: float, fallback: Optional[Any], guess: Optional[Any] = None) -> tuple[Optional[str], Optional[dict]]:
    """(council, source). Order: (1) our own copy when it is sure, no network wait; (2) the live state service; (3) our best guess from the
    copy, marked unsure with the other possibilities. source is None only when the live service named the council."""
    if fallback is not None:
        try:
            got = fallback(lat, lng)
            if isinstance(got, (tuple, list)) and len(got) in (2, 3) and isinstance(got[0], str) and got[0].strip():
                src = {"source": "snapshot", "as_of": str(got[1]) if got[1] else None}
                if len(got) == 3 and got[2]:
                    src["how"] = str(got[2])
                return got[0].strip(), src
        except Exception as exc:  # noqa: BLE001 -- our copy failing is no answer; try the live service
            logger.warning("lmr inputs: own council copy failed: %s", exc)
    answered, name = _lga_live(lat, lng)
    if answered:
        return name, None   # the live service answered (even "no council"): never overridden by a guess
    if guess is not None:
        try:
            g = guess(lat, lng)
            gname = g.get("council") if isinstance(g, dict) else None
            if isinstance(gname, str) and gname.strip():
                return gname.strip(), {"source": "snapshot", "as_of": g.get("as_of"), "unsure": True,
                                              "alternatives": [str(a) for a in (g.get("alternatives") or [])]}
        except Exception as exc:  # noqa: BLE001
            logger.warning("lmr inputs: council best guess failed: %s", exc)
    return None, None


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


# prior-art-checked: reuse not viable because the hits are pip internals and a blog page; this only adds one optional argument to this
# module's own fetch_layers (the council fallback, supplied by the caller) and changes no layer, source or query.
def fetch_layers(lat: float, lng: float, rings: Optional[list], lga_fallback: Optional[Any] = None, lga_guess: Optional[Any] = None,
                 bushfire_fn: Optional[Any] = None, copy_fn: Optional[Any] = None) -> dict:
    """The map-service measurements for one lot (TOD, accelerated TOD, exclusion map, bush fire, heritage, council). Network only,
    except the optional `lga_fallback(lat, lng) -> (council, as_of) | None`, which the caller supplies (it owns any database connection)."""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {k: ex.submit(_layer, k, lat, lng, rings, copy_fn) for k in (
            "tod_map", "accelerated", "exclusion",
            "georges_catchment", "hn_catchment", "coastal_vuln", "coastal_wetlands", "littoral")}
        f_her = ex.submit(_heritage, rings)
        f_bf = ex.submit(_bushfire_resolved, lat, lng, rings, bushfire_fn)
        f_lga = ex.submit(_lga_resolved, lat, lng, lga_fallback, lga_guess)
        f_noise = ex.submit(_noise_bands, lat, lng, rings)
        out: dict[str, Any] = {k: f.result() for k, f in futs.items()}
        copied = {k: v.get("copy_as_of") for k, v in out.items() if isinstance(v, dict) and v.get("copy_as_of")}
        if copied:
            out["map_copy"] = copied  # noqa: bracket-access -- assignment into our own dict
        out["airport_noise"] = f_noise.result()
        out["heritage"] = f_her.result()
        out["bushfire"], bf_source = f_bf.result()  # noqa: bracket-access -- assignment into our own dict
        if bf_source:
            out["bushfire_source"] = bf_source  # noqa: bracket-access -- assignment into our own dict
        lga_name, lga_source = f_lga.result()
        out["lga"] = lga_name  # noqa: bracket-access -- assignment into our own dict
        if lga_source:
            out["lga_source"] = lga_source  # noqa: bracket-access -- assignment into our own dict
    return out


def gather(lat: float, lng: float, *, rings: Optional[list] = None, stations: Optional[dict] = None,
           walk_surfaces: Optional[list] = None, safe_surfaces: Optional[list] = None, layers: Optional[dict] = None,
           flood_fn: Optional[Any] = None, lga_fallback: Optional[Any] = None, lga_guess: Optional[Any] = None,
           bushfire_fn: Optional[Any] = None, lot_fn: Optional[Any] = None, copy_fn: Optional[Any] = None,
           want_route: bool = False, route_surfaces: Optional[list] = None,
           flood_study_fn: Optional[Any] = None, want_distances: bool = False) -> dict:
    """Measurements for decide(): layer hits (point and lot outline), council, distances, walking.

    `want_route` (the evidence page only) also keeps the route each walk followed: a "route" entry on the crossings-only walk (from its own
    files), and a "route_normal" entry from the separate normal set built for drawing (data/lmr_route_normal/). It changes no distance and no answer.

    `flood_fn` (optional) is called with the lot outline as WKT (or None) ONLY when the lot is in one of the 23 councils s164(1)(g) names,
    and returns the existing flood answer (services/flood_planning.flood_planning_status): a dict with "value" True / False / None.
    The caller owns the database connection; this module holds none. Without it, a lot in a named council cannot be answered yes.
    """
    from pyproj import Transformer
    from shapely.geometry import MultiPoint, Polygon
    from shapely.ops import transform, unary_union

    lot_source = None
    if rings is None and lot_fn is not None:   # our own copy of the lot outline first: no wait on the state property service
        try:
            got = _stage("lot_outline_db", lot_fn, lat, lng)
            if isinstance(got, (tuple, list)) and len(got) == 2 and got[0]:
                rings, lot_source = got[0], {"source": "snapshot", "as_of": str(got[1]) if got[1] else None}
        except Exception as exc:  # noqa: BLE001
            logger.warning("lmr inputs: own lot outline failed: %s", exc)
    if rings is None:
        rings = _stage("lot_outline_live", fetch_lot_rings, lat, lng)
    # prior-art-checked: the heritage/bushfire readers found by the guard are TypeScript pages and PDF code; this is the same
    # Python block moved into a function so its result can be saved and passed back in (no new source, no new query).
    # `layers` may be passed in (saved from an earlier call) so that a re-run after the walking files change needs no map calls.
    m: dict[str, Any] = dict(layers) if layers is not None else _stage("layers", fetch_layers, lat, lng, rings, lga_fallback, lga_guess, bushfire_fn, **({"copy_fn": copy_fn} if copy_fn is not None else {}))
    m["lot_outline"] = bool(rings) and len(rings) >= 4
    if lot_source:
        m["lot_source"] = lot_source  # noqa: bracket-access -- assignment into our own dict   # fewer than 4 points is not an outline (services/sydney_anef.py ignores it too)
    if "sydney_anef" not in m:
        try:   # Sydney Airport's endorsed 2045 chart: local geometry on committed data, no network. A lot wholly off the chart's map is "outside".
            m["sydney_anef"] = sydney_anef.classify_all(lat, lng, rings)
        except Exception as exc:  # noqa: BLE001 -- the decision reports this as "no answer", never as clear
            logger.warning("sydney anef chart failed: %s", exc)
            m["sydney_anef"] = "error"
    if "pipeline" not in m:
        try:   # the distance is the law's (s164(1)(i)), read from the saved facts, never typed here
            m["pipeline"] = _stage("pipeline_near", _pipeline_near, lat, lng, rings, dec.LawFacts.load().number("s164_i_distance"))
        except dec.LawFactsError:
            m["pipeline"] = {"hit": None, "names": []}
    if flood_study_fn is not None and "flood_study" not in m:
        m["flood_study"] = _stage("flood_study", _flood_study, lat, lng, rings, flood_study_fn, all_layers=want_distances)
    pl = m.get("pipeline")
    if want_distances and isinstance(pl, dict) and pl.get("hit") is False and "nearest_m" not in pl:   # only the evidence page asks: the public check stays one query
        m["pipeline"] = {**pl, **_stage("pipeline_nearest", _pipeline_nearest, lat, lng)}
    if flood_fn is not None and "flood_planning" not in m:
        m["flood_planning"] = _stage("flood_planning_db", _flood_answer, m.get("lga"), rings, flood_fn)

    # Distances need a lot outline and the station file; without either they stay None (cant_tell), never a number.
    m["straight_m"] = None
    m["sched12_straight_m"] = None
    m["walk"] = None
    m["walk_safe"] = None   # the walk that crosses busy roads only at signals, zebra or marked crossings; shown beside the normal walk, never decides
    stations = stations if stations is not None else load_stations()
    tcs = _stage("town_centres", town_centre_polygons)
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
        pts = [(e["lon"], e["lat"]) for e in (st.get("entrances") or [])] or [(st["lon"], st["lat"])]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
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
    m["walk"] = _stage("walk", walk_mod.walk_from_lot, ring_m, _epsg_for(lng), m["straight_m"], touches, walk_surfaces,  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
                                       required_anchors=near_anchors)
    try:   # the second walk must never break the first: any failure here is a reason string, not an exception
        safe_list = safe_surfaces if safe_surfaces is not None else [walk_mod.load_surface(str(p)) for p in walk_mod.available_surfaces(walk_mod.SAFE_SURFACE_DIR)]
        if safe_list:
            m["walk_safe"] = _stage("walk_safe", walk_mod.walk_from_lot_safe, ring_m, _epsg_for(lng), m["straight_m"], touches, safe_list, required_anchors=near_anchors,  # noqa: bracket-access -- set above in this function
                                                         want_route=want_route)
    except Exception as exc:  # noqa: BLE001
        logger.warning("crossings-only walk failed: %s", exc)
        m["walk_safe"] = {"m": None, "valid": False, "reason": f"the crossings-only map could not be read ({type(exc).__name__})"}
    if want_route:
        try:   # the normal route is drawn from its own set; a failure here is a missing route, never a change to the walk or the answer
            rl = route_surfaces if route_surfaces is not None else [walk_mod.load_surface(str(p)) for p in walk_mod.available_surfaces(walk_mod.ROUTE_SURFACE_DIR)]
            if rl:
                m["route_normal"] = _stage("route_normal", walk_mod.walk_from_lot, ring_m, _epsg_for(lng), m["straight_m"], touches, rl, required_anchors=near_anchors, want_route=True)  # noqa: bracket-access -- set above in this function
        except Exception as exc:  # noqa: BLE001
            logger.warning("normal route failed: %s", exc)
            m["route_normal"] = {"m": None, "valid": False, "reason": f"the route map could not be read ({type(exc).__name__})"}
    return m


def area_check(lat: float, lng: float, **kw) -> dict:
    """Measure the lot, then decide. The measurements are echoed on the answer so a reader can see them."""
    try:
        m = gather(lat, lng, **kw)
    except Exception as exc:  # noqa: BLE001 -- never raise, never a silent yes
        logger.warning("lmr area check measurement failed: %s", exc)
        return dec._failed(f"a map or lookup did not respond, or returned something unexpected ({type(exc).__name__})")
    r = dec.decide(m)
    r["measured"] = {**(r.get("measured") or {}), "lot_outline": m.get("lot_outline"), "distance_note": m.get("distance_note")}
    if kw.get("want_route"):
        try:   # the route map is extra: whatever happens here, the answer above is already complete
            from services import lmr_route_map
            r["route_map"] = _stage("route_map", lmr_route_map.build, m, kw.get("stations") if kw.get("stations") is not None else load_stations())
        except Exception as exc:  # noqa: BLE001
            logger.warning("route map failed: %s", exc)
            r["route_map"] = {"status": "unavailable", "reason": f"the route map could not be built ({type(exc).__name__})"}
    return r
