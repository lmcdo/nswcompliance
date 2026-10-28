"""
The ONE answer to "is this lot on the council's flood planning map?".

Owner ruling 2026-10-19: one producer per common fact. Before this, the flood
tool, the site brief, the conveyancing report, the CDC screen and the verify
app each answered it their own way (20 producer sites, scripts/page_integrity/
producer_baseline.json). Plan: ~/.claude/plans/ce-flood-one-answer-PLAN-2026-10-28.md.

value
  True   a planning-category flood line (flood planning area, or a flood of
         1-in-100 or more frequent) touches the point
  False  ONLY when: the council is known, we hold that council's flood
         planning map, and the nearest planning line is more than
         NEAR_EDGE_M away
  None   anything else -- with the reason. Never "no" for a council whose
         map we do not hold: on 2026-10-28, 167 of 310 checked addresses were
         in such councils and the flood tool said "outside the mapped extent".

Wording for False everywhere: "not on the council's flood planning map".
Never "not flood prone" or "no flood risk": some LEPs define the flood
planning area by level in words, so the map is not the whole rule.

prior-art-checked: _query_ses_flood_study (flood_truth.py) is the closest
existing reader; it is rewired to call this rather than duplicated. lga_lookup
supplies the first council lookup; Spatial Services is the measured fallback.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# How far a point-only miss must be from a planning line before it is "no".
# Rural lots can be hundreds of metres wide, so within this distance the lot
# itself may touch the line and the honest answer is "not known" until the
# whole lot is tested. 200 m, not 50: of the 22 covered point-misses measured
# on 2026-10-28, 19 were further than 200 m, so the wider margin costs 2 "no"
# answers and removes the wide-rural-lot false "no" (cross-review).
NEAR_EDGE_M = 200.0

# Every value stored under spatial_overlays with layer_type flood (33 on
# 2026-10-28), sorted into what it means. A value not listed here is
# "unclassified": it never makes a "yes" and is logged so it gets classified.
_PLANNING = {
    "Flood Planning Area", "flood_planning_area", "Flood Planning area",
    "1%AEP", "1.0%AEP", "100AEP", "1 in 100 AEP Flood Extent",
    "1 in 100 year flood extents", "design_flood",
    "Flood Prone and Major Creeks Land", "Dungog Tailwater Area",
}
_FREQUENT = {  # more frequent than 1-in-100: inside it means inside the 1% too
    "20.0%AEP", "5.0%AEP", "2.0%AEP", "2AEP", "5AEP", "10AEP", "20AEP", "50AEP",
}
_EXTREME = {  # rarer than 1-in-100: real flood lines, but NOT the planning line
    "PMF", "Probable Maximum Flood Line", "Level of Probable Maximum Flood",
    "0.5%AEP", "0.2%AEP", "200AEP", "500AEP", "1000AEP", "2000AEP", "5000AEP",
}
_NOT_FLOOD = {
    "Other", "Area 1", "Transitional Land", "Cultural Heritage Landscape Area",
    "Land Identified in Section 3.27",
}
_YES = _PLANNING | _FREQUENT


def _cols(row, *names):
    """A row as a tuple, whether the cursor returns tuples or dicts."""
    if isinstance(row, dict):
        return tuple(row.get(n) for n in names)
    return tuple(row)


def category_of(value: Optional[str]) -> str:
    v = (value or "").strip()
    if v in _PLANNING:
        return "planning"
    if v in _FREQUENT:
        return "frequent"
    if v in _EXTREME:
        return "extreme"
    if v in _NOT_FLOOD:
        return "not_flood"
    return "unclassified"


_SS_LGA = ("https://portal.spatial.nsw.gov.au/server/rest/services/"
           "NSW_Administrative_Boundaries_Theme/FeatureServer/8/query")
_COVERED_TTL_S = 3600
_covered_cache: dict = {"at": 0.0, "councils": None}


def _covered_councils(cur) -> Optional[set]:
    """Councils whose flood planning map we hold (>= 1 planning-category row).

    Derived from the rows themselves, never from spatial_overlays_coverage,
    which said 12 councils on 2026-10-28 while 72 held flood rows.
    Completeness: 56 of the 70 councils loaded from NSW_Flood_Risk match its
    feature count exactly (2026-10-28); the rest came from council sources.
    """
    now = time.time()
    if _covered_cache.get("councils") is not None and now - (_covered_cache.get("at") or 0.0) < _COVERED_TTL_S:
        return _covered_cache.get("councils")
    # PARTIAL_ maps cover only a studied area, never the whole council
    # (scripts/ingest_flood_studies.py); they count only via a study-area
    # outline (_inside_study_area), never here.
    cur.execute(
        "SELECT DISTINCT lga_name FROM spatial_overlays "
        "WHERE layer_type = 'flood' AND value = ANY(%s) AND lga_name <> 'UNKNOWN' "
        "AND instrument_key NOT LIKE 'PARTIAL\_%%'",
        (sorted(_YES),),
    )
    councils = {_cols(r, "lga_name")[0] for r in cur.fetchall()}
    _covered_cache.update(at=now, councils=councils)
    return councils


def _inside_study_area(cur, lat: float, lng: float, council: str) -> bool:
    """Is the point inside a loaded study-area outline for this council? A
    partial council map supports a "no" only there."""
    cur.execute(
        "SELECT EXISTS(SELECT 1 FROM spatial_overlays WHERE layer_type = 'flood_coverage' "
        "AND lga_name = %s AND ST_Covers(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)))",
        (council, lng, lat),
    )
    row = cur.fetchone()
    return bool(_cols(row, "exists")[0]) if row else False


def council_at(lat: float, lng: float, cur) -> Optional[str]:
    """Council (LGA) name at a point, in spatial_overlays' naming.

    Height layer first (lga_lookup); it failed for 75 of 310 checked points on
    2026-10-28. NSW Spatial Services administrative boundaries resolved all 75,
    and its `lganame` matches spatial_overlays.lga_name exactly. None = unknown.
    """
    cur.execute(
        "SELECT lga_name FROM spatial_overlays WHERE layer_type = 'height' "
        "AND ST_Contains(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) LIMIT 1",
        (lng, lat),
    )
    row = cur.fetchone()
    name = _cols(row, "lga_name")[0] if row else None
    if name and name.strip().upper() != "UNKNOWN":  # 'UNKNOWN' is no answer: fall through
        return name
    try:
        r = requests.get(_SS_LGA, params={
            "geometry": f"{lng},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects", "outFields": "lganame",
            "returnGeometry": "false", "f": "json"}, timeout=5)
        r.raise_for_status()
        feats = r.json().get("features") or []
        name = (feats[0].get("attributes") or {}).get("lganame") if feats else None
        return name.strip().upper() if name else None
    except Exception as e:  # noqa: BLE001 -- unknown council is None, never "no"
        logger.warning(f"Council lookup (Spatial Services) failed: {e}")
        return None


def _trusted_lot(cur, lot_wkt: Optional[str], lat: float, lng: float) -> Optional[str]:
    """The lot outline, only if it is a valid polygon that CONTAINS the address
    point. A stale or neighbouring boundary is ignored, so it can never give a
    whole-lot answer for the wrong parcel (same rule as lib/flood/flood-map.ts)."""
    if not lot_wkt:
        return None
    # A savepoint: a malformed outline must not abort the transaction and take
    # the point answer down with it (cross-review).
    try:
        cur.execute("SAVEPOINT flood_lot_check")
        cur.execute(
            "SELECT ST_IsValid(g) AND GeometryType(g) IN ('POLYGON','MULTIPOLYGON') "
            "AND ST_Covers(g, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) "
            "FROM (SELECT ST_GeomFromText(%s, 4326) AS g) t",
            (lng, lat, lot_wkt),
        )
        row = cur.fetchone()
        ok = _cols(row, "ok")[0] if row else False
        cur.execute("RELEASE SAVEPOINT flood_lot_check")
        return lot_wkt if ok else None
    except Exception:  # noqa: BLE001 -- an unreadable outline is simply not used
        try:
            cur.execute("ROLLBACK TO SAVEPOINT flood_lot_check")
        except Exception:  # noqa: BLE001
            pass
        return None


def _nearest_yes_m(cur, lat: float, lng: float, council: Optional[str] = None) -> Optional[float]:
    """Metres to the nearest planning-map polygon within NEAR_EDGE_M, else None.
    With council, only that council's rows count (a neighbour's line is not
    "the council's flood planning map" for this lot).

    prior-art-checked: the existing near-edge query below, moved into a function
    so the partial-council path can use it too; no new source.
    """
    cur.execute("SET LOCAL statement_timeout = '5000'")
    cur.execute(
        "SELECT min(ST_Distance(geom::geography, "
        "ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography)) FROM spatial_overlays "
        # Index-friendly pre-filter in degrees (0.003 deg >= 270 m in NSW), then
        # the exact metres on the few rows left. A bare geography DWithin
        # cannot use the geom index and timed out at 5 s.
        "WHERE layer_type = 'flood' AND value = ANY(%s) "
        "AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326), 0.003) "
        "AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s) "
        "AND (%s::text IS NULL OR lga_name = %s)",
        (lng, lat, sorted(_YES), lng, lat, lng, lat, NEAR_EDGE_M, council, council),
    )
    got = cur.fetchone()
    d = _cols(got, "min")[0] if got else None
    return round(float(d), 1) if d is not None else None


def _flood_planning_core(lat: float, lng: float, conn, lot_wkt: Optional[str] = None) -> dict:
    """The one answer. Never raises; a failure is value None with its reason.

    With lot_wkt (a WGS84 POLYGON WKT the caller already holds), the WHOLE lot is
    tested: a hit anywhere on it is yes, and a covered council with nothing on
    it is a real "no" -- no point-distance guess.
    """
    out = {"value": None, "category": None, "council": None, "reason": None,
           "hits": [], "nearest_m": None, "whole_lot": False}
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '5000'")
            lot = _trusted_lot(cur, lot_wkt, lat, lng)
            out["whole_lot"] = lot is not None
            cur.execute(
                "SELECT DISTINCT value, instrument_key, lga_name FROM spatial_overlays "
                "WHERE layer_type = 'flood' "
                "AND (ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) "
                "OR (%s::text IS NOT NULL AND ST_Intersects(geom, ST_GeomFromText(%s, 4326))))",
                (lng, lat, lot, lot),
            )
            hits = [{"value": v, "instrument_key": k, "lga_name": l, "category": category_of(v)}
                    for v, k, l in (_cols(r, "value", "instrument_key", "lga_name")
                                    for r in cur.fetchall())]
            out["hits"] = hits
            for h in hits:
                if h.get("category") == "unclassified":
                    logger.warning(f"flood value not classified: {h['value']!r}")
            yes = [h for h in hits if h.get("category") in ("planning", "frequent")]
            if yes:
                out.update(value=True, category="planning", council=yes[0].get("lga_name"),
                           reason="on the council's flood planning map")
                return out
            extreme_only = any(h.get("category") == "extreme" for h in hits)
            if any(h.get("category") == "unclassified" for h in hits):
                # A flood value nobody has sorted yet touches this point: it may
                # be a planning line, so the honest answer is "not known".
                out["reason"] = "an unclassified flood line touches this point"
                return out

            council = council_at(lat, lng, cur)
            out["council"] = council
            if council is None:
                out["reason"] = "council could not be identified"
                return out
            covered = _covered_councils(cur)
            if council not in covered and not _inside_study_area(cur, lat, lng, council):
                # A partial council map (study areas only) can still hold a
                # planning line right next to this point. Say so, rather than
                # "we do not hold this council's map": Heddon Greta 2026-10-28,
                # point 6 m from Cessnock's 1% AEP extent, 44.7 m2 of the lot on it.
                d = None if lot is not None else _nearest_yes_m(cur, lat, lng, council)
                if d is not None:
                    out.update(nearest_m=d, reason=(
                        f"within {d:.0f} m of the council's flood planning map; the whole lot was not checked"))
                    return out
                out["reason"] = "we do not hold this council's flood planning map for this area"
                return out
            if lot is not None:
                out.update(value=False, category="extreme_only" if extreme_only else None,
                           reason=("no part of the lot is on the council's flood planning map; "
                                   "it is inside a rarer (extreme) flood extent" if extreme_only
                                   else "no part of the lot is on the council's flood planning map"))
                return out
            d = _nearest_yes_m(cur, lat, lng)
            if d is not None:
                out.update(nearest_m=d,
                           reason=f"within {NEAR_EDGE_M:.0f} m of the council's flood planning map; the whole lot was not checked")
                return out
            out.update(value=False, category="extreme_only" if extreme_only else None,
                       reason=("not on the council's flood planning map; inside a rarer (extreme) flood extent"
                               if extreme_only else "not on the council's flood planning map"))
            return out
    except Exception as e:  # noqa: BLE001 -- a failure is unknown, never "no"
        logger.warning(f"flood_planning_status failed: {e}")
        out["reason"] = "flood planning map could not be checked"
        return out


def _council_info(conn, council: Optional[str]) -> Optional[dict]:
    """What the council publishes about flooding (council_flood_context,
    migration 118): only facts confirmed on the council's own page, each with
    its link. None when we hold nothing for the council or the lookup fails."""
    if not council:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT viewer_label, viewer_url, certificate_label, certificate_url, certificate_fee, "
                "fpl_quote, fpl_url, data_sources, checked_on FROM council_flood_context WHERE lga_name = %s",
                (council.strip().upper(),),
            )
            row = cur.fetchone()
        if not row:
            return None
        keys = ("viewer_label", "viewer_url", "certificate_label", "certificate_url", "certificate_fee",
                "fpl_quote", "fpl_url", "data_sources", "checked_on")
        info = dict(zip(keys, _cols(row, *keys)))
        info["checked_on"] = str(info.get("checked_on")) if info.get("checked_on") else None  # noqa: bracket-access
        return info
    except Exception as e:  # noqa: BLE001 -- missing context never changes the answer
        logger.warning(f"council_flood_context lookup failed: {e}")
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None


def council_info_sentence(info: Optional[dict]) -> Optional[str]:
    """One plain sentence on where to get this council's flood information,
    built only from confirmed facts. None when there is nothing to say."""
    if not info:
        return None
    parts = []
    if info.get("certificate_url"):
        fee = f" (fee: {info.get('certificate_fee')})" if info.get("certificate_fee") else ""
        parts.append(f"the council issues {info.get('certificate_label') or 'flood information'}{fee}: "
                     f"{info.get('certificate_url')}")
    if info.get("viewer_url"):
        parts.append(f"it publishes a flood map ({info.get('viewer_label') or 'online viewer'}): {info.get('viewer_url')}")
    if info.get("fpl_quote"):
        parts.append(f"its flood planning level: \"{info.get('fpl_quote')}\" ({info.get('fpl_url')})")
    data = info.get("data_sources") or []
    if not parts and data:
        parts.append(f"its flood studies are listed at {data[0].get('url')}")
    if not parts:
        return None
    when = f" (checked {info.get('checked_on')})" if info.get("checked_on") else ""
    return "For this council, " + "; ".join(parts) + "." + when


def flood_planning_status(lat: float, lng: float, conn, lot_wkt: Optional[str] = None) -> dict:
    """The one answer, plus what the council itself publishes about flooding
    (viewer, certificate, data links) so a "not known" tells the user where to go."""
    out = _flood_planning_core(lat, lng, conn, lot_wkt=lot_wkt)
    out["council_info"] = _council_info(conn, out.get("council"))
    out["council_info_text"] = council_info_sentence(out.get("council_info"))
    return out
