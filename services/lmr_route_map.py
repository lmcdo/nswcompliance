"""Data for the route map on the evidence page: the walk to the station drawn as a line, once for the normal rule and once for the
crossings-only rule, with the lot, the station entrance and the nearby busy roads.

The page draws; this module only decides WHAT may be drawn and shapes it. A route is drawn only when it is the walk the page already
shows, so a map can never carry a distance that disagrees with the number beside it:
  - the crossings-only route comes from the same files as the crossings-only walk, so its length must equal that walk (within 2 m of rounding);
  - the normal route comes from a separate normal-rule set built from the current map cut (data/lmr_route_normal/), because the files that
    decide the answer carry no route pointers. It is drawn only when it goes to the same station and its length is within 15 m of the
    measured walk; otherwise the page says why there is no normal route. It never changes the walk or the answer.
Everything is a line between mapped footpath points; crossing types and road names are not in the saved files and are not shown.
"""
# prior-art-checked: 2026-11-21. Nothing in services/ computes route geometry (lmr_walk_surface returned distances only until route pointers
# were added in this change). The only route drawing is the outreach tool lead-finder/outreach/route_map_lib.py, which downloads live map
# data per lot and is not part of the repo; this reads the saved walking files instead so the route and the walk agree.
from __future__ import annotations

import math
from typing import Any, Optional

from pyproj import Transformer

CAREFUL_AGREE_M = 2.0   # noqa: regulatory-number -- engineering tolerance: the careful route and walk come from one file, so only rounding can differ
NORMAL_AGREE_M = 15.0   # noqa: regulatory-number -- engineering tolerance: how far the drawing map's normal walk may differ from the measured one
MIN_LINK_M = 1.0   # noqa: regulatory-number -- engineering tolerance: a station link shorter than this is rounding, not a missing stretch
ATTRIBUTION = "Footpath and road data: OpenStreetMap contributors (Open Database Licence)."
NOTE = ("Lines join mapped footpath points, so they are approximate. Crossing types and road names are not shown. "
        "The crossings-only line is drawn from the same saved footpath data as its walking distance. The normal line is drawn from a separate copy "
        f"of the footpath data and is shown only when it leads to the same station and agrees with the measured walk to within {NORMAL_AGREE_M:.0f} m.")


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _entrance(stations: Optional[dict], entrance_id: Any, anchor_name: Any) -> Optional[dict]:
    """The entrance the walk ends at, as lon/lat. An entrance id names it exactly; with none, the station point stands in and says so.
    A walk that ends at the edge of a town centre has no entrance: it does not end at a station, so none is drawn."""
    if entrance_id == "town centre edge":
        return None
    for st in (stations or {}).get("stations") or []:
        for e in st.get("entrances") or []:
            lon, lat = e.get("lon"), e.get("lat")
            if entrance_id and e.get("id") == entrance_id and _num(lon) and _num(lat):
                return {"lon": float(lon), "lat": float(lat), "name": st.get("name"), "exact": True}
    for st in (stations or {}).get("stations") or []:
        lon, lat = st.get("lon"), st.get("lat")
        if anchor_name and st.get("name") == anchor_name and _num(lon) and _num(lat):
            return {"lon": float(lon), "lat": float(lat), "name": st.get("name"), "exact": False}
    return None


def _destination(route: dict) -> dict:
    """What the walk ends at: a named station entrance, the outline of a station whose entrance is not mapped, or the edge of a town centre."""
    eid = route.get("entrance_id")
    kind = ("town_centre_edge" if eid == "town centre edge" else
            "station_outline" if isinstance(eid, str) and eid.startswith("station outline") else "entrance")
    return {"name": route.get("anchor"), "kind": kind}


def _draw(route: Optional[dict], walk: Optional[dict], tol: float, what: str, stations: Optional[dict]) -> tuple[Optional[dict], Optional[str]]:
    """(line, None) when this route may be drawn, else (None, plain reason). `walk` is the walk the page shows for the same rule."""
    if not isinstance(walk, dict) or walk.get("valid") is not True or not _num(walk.get("m")):
        return None, f"No {what} route is drawn: the {what} walk was not measured for this lot."
    if (not isinstance(route, dict) or not route.get("points") or not _num(route.get("length_m"))
            or not _num(route.get("end_gap_m")) or float(route.get("end_gap_m")) < 0):   # the link length decides whether the line is complete
        return None, f"No {what} route is drawn: the footpath map for this area holds no route information."
    if route.get("anchor") != walk.get("anchor") or route.get("entrance_id") != walk.get("entrance_id"):
        return None, f"No {what} route is drawn: the map used for drawing leads to a different station or entrance from the measured walk."
    rlen, wlen = float(route.get("length_m")), float(walk.get("m"))   # both were checked to be numbers above
    if abs(rlen - wlen) > tol:
        return None, (f"No {what} route is drawn: the map used for drawing gives a walk of {rlen:.0f} m for this lot, and the "
                      f"walk shown is {wlen:.0f} m. A route is drawn only when the two agree to within {tol:.0f} m.")
    try:
        epsg = int(route.get("epsg"))
        to_ll = Transformer.from_crs(epsg, 4326, always_xy=True)
        to_m = Transformer.from_crs(4326, epsg, always_xy=True)
        pts_m = [tuple(route.get("lot_xy") or [])] + [tuple(p) for p in route.get("points") or []]
        ent = _entrance(stations, route.get("entrance_id"), route.get("anchor"))
        entrance_out = None
        end_gap = float(route.get("end_gap_m"))
        link_drawn = False
        if ent is not None:
            elon, elat = float(ent.get("lon")), float(ent.get("lat"))
            ex, ey = to_m.transform(elon, elat)
            last = pts_m[-1]
            # the last stored point is joined to the entrance by the station link; draw it only when the entrance is as far away as the link says
            # (too near would draw a shorter link than the walk counts, too far would draw a longer one)
            if abs(math.hypot(ex - last[0], ey - last[1]) - end_gap) <= 5.0:
                pts_m.append((ex, ey))
                link_drawn = True
            entrance_out = {"lat": round(elat, 6), "lon": round(elon, 6), "name": ent.get("name"), "exact": ent.get("exact")}
        ll = [to_ll.transform(x, y) for x, y in pts_m]
        busy = [to_ll.transform(x, y) for x, y in (route.get("busy_pts") or [])]
        return {"length_m": round(rlen, 1), "walk_m": round(wlen, 1),
                "points": [[round(lat, 6), round(lon, 6)] for lon, lat in ll], "entrance": entrance_out, "destination": _destination(route),
                "busy_road_points": [[round(lat, 6), round(lon, 6)] for lon, lat in busy], "osm_extract": route.get("osm_extract") or None,
                # The walk's last stretch joins the end of the line to the station. When that link cannot be drawn (the entrance is not on the list, or is not
                # where the link says), say how long it is, so a line shorter than the distance beside it is never unexplained.
                "end_link_not_drawn_m": 0.0 if link_drawn or end_gap < MIN_LINK_M else round(end_gap, 1)}, None
    except Exception as exc:  # noqa: BLE001 -- a map that cannot be built is a reason on the page, never an error or a wrong line
        return None, f"No {what} route is drawn: it could not be built ({type(exc).__name__})."


def build(m: dict, stations: Optional[dict] = None) -> dict:
    """The route map data from an area-check measurement `m` gathered with want_route=True. Always returns a dict with a status."""
    careful_walk = m.get("walk_safe") if isinstance(m.get("walk_safe"), dict) else None
    normal_walk = m.get("walk") if isinstance(m.get("walk"), dict) else None
    careful, careful_note = _draw((careful_walk or {}).get("route"), careful_walk, CAREFUL_AGREE_M, "crossings-only", stations)
    normal_out = m.get("route_normal") if isinstance(m.get("route_normal"), dict) else None
    normal, normal_note = _draw((normal_out or {}).get("route"), normal_walk, NORMAL_AGREE_M, "normal", stations)
    if normal is None and normal_note and normal_out is not None and normal_out.get("valid") is not True:
        normal_note = "No normal route is drawn: the map used for drawing has no walk for this lot."
    if careful is None and normal is None:
        return {"status": "unavailable", "reason": " ".join(n for n in (normal_note, careful_note) if n)}
    drawn = careful or normal or {}
    entrance = (careful or {}).get("entrance") or (normal or {}).get("entrance")
    start = (drawn.get("points") or [[None, None]])[0]
    # The two walks can end at different places (the nearest station can differ between the rules): the page must then name and mark both ends.
    c_raw, n_raw = (careful_walk or {}).get("route") or {}, (normal_out or {}).get("route") or {}
    differ = bool(careful and normal and (careful.get("destination") != normal.get("destination") or c_raw.get("entrance_id") != n_raw.get("entrance_id")))
    return {"status": "ok", "lot": {"lat": start[0], "lon": start[1]}, "entrance": entrance, "destination": drawn.get("destination"), "destinations_differ": differ,
            "careful": careful, "careful_note": careful_note, "normal": normal, "normal_note": normal_note,
            "attribution": ATTRIBUTION, "note": NOTE}
