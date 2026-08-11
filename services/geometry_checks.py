# prior-art-checked: no existing module validates coordinate plausibility or
# geometry CRS at pipeline entry (repo grep 2026-08-03: address_identity.py
# matches address STRINGS, portal_constraints/strata_lookup build queries with
# unvalidated floats, and the only bounds check is flood_truth's per-raster
# window test). This is the single shared home so every satellite pipeline
# fails the same way: typed unavailable, never a number from wrong-CRS input.
"""Units/CRS runtime checks for geometry entering the satellite pipelines.

Output-grounding campaign item 4 (§7 finding 3): recomputation can NEVER catch
a stable unit or CRS error — a lat/lng pair fed in as lng/lat, or Web-Mercator
metres fed where WGS84 degrees are expected, reproduces identically every run.
These entry checks are the only defence.

Contract: every check returns ``None`` when the input is plausible, else a
short reason string. A non-None reason must be routed into the caller's
typed-absence machinery (the product returns its unavailable state) — it is
NEVER a crash and NEVER a number.

Bounds are deliberately generous NSW envelopes — the goal is catching
wrong-CRS/wrong-axis-order inputs (off by orders of magnitude or hemisphere),
not adjudicating edge-of-state parcels.
"""
from __future__ import annotations

from typing import Optional

# NSW bounding envelope, WGS84 degrees (generous: covers Lord Howe westward).
NSW_LAT_MIN, NSW_LAT_MAX = -38.0, -27.5
NSW_LNG_MIN, NSW_LNG_MAX = 140.5, 160.0

# NSW envelope in Web Mercator (EPSG:3857) metres — x = lng·R·π/180,
# y = R·ln(tan(π/4 + φ/2)) over the degree envelope above. World-extent
# bounds alone would accept OTHER projected CRSes (an MGA Zone 56 easting
# like 334000 is comfortably inside the world extent — Sol finding,
# 2026-08-03), so rings must land inside NSW's own Mercator box.
_M3857_X_MIN, _M3857_X_MAX = 15_640_000.0, 17_810_000.0
_M3857_Y_MIN, _M3857_Y_MAX = -4_610_000.0, -3_180_000.0


def check_point_nsw(lat, lng) -> Optional[str]:
    """A WGS84 point that should sit in NSW. Catches swapped axis order
    (a lng in the lat slot is > 0 and > 90-out-of-range), Mercator metres,
    and null-island defaults."""
    try:
        lat_f, lng_f = float(lat), float(lng)
    except (TypeError, ValueError):
        return f"coordinates not numeric: lat={lat!r} lng={lng!r}"
    if lat_f == 0.0 and lng_f == 0.0:
        return "coordinates are (0, 0) — null-island default, not a property"
    # Swap detection FIRST: a swapped NSW pair puts ~151 in the lat slot,
    # which the degree-range branch would otherwise misdiagnose as metres.
    if NSW_LAT_MIN <= lng_f <= NSW_LAT_MAX and NSW_LNG_MIN <= lat_f <= NSW_LNG_MAX:
        return (f"lat/lng appear swapped (lat={lat_f}, lng={lng_f}) — "
                f"axis order error")
    if abs(lat_f) > 90 or abs(lng_f) > 180:
        return (f"coordinates outside degree range (lat={lat_f}, lng={lng_f}) "
                f"— projected metres passed where WGS84 degrees expected?")
    if not (NSW_LAT_MIN <= lat_f <= NSW_LAT_MAX):
        return f"latitude {lat_f} outside the NSW envelope [{NSW_LAT_MIN}, {NSW_LAT_MAX}]"
    if not (NSW_LNG_MIN <= lng_f <= NSW_LNG_MAX):
        return f"longitude {lng_f} outside the NSW envelope [{NSW_LNG_MIN}, {NSW_LNG_MAX}]"
    return None


def check_polygon_wgs84(geojson: Optional[dict],
                        max_span_deg: float = 0.05) -> Optional[str]:
    """A GeoJSON Polygon that should be a WGS84 lot/parcel shape near Sydney
    scale. Validates structure, ring closure/size, degree-range coordinates,
    NSW envelope, and a span sanity bound (a lot spanning > ~5 km of degrees
    is not a parcel — likely metres fed as degrees)."""
    if not isinstance(geojson, dict):
        return f"polygon is {type(geojson).__name__}, expected GeoJSON dict"
    if geojson.get("type") != "Polygon":
        return f"geometry type {geojson.get('type')!r}, expected 'Polygon'"
    coords = geojson.get("coordinates")
    if not coords or not isinstance(coords, (list, tuple)) or not coords[0]:
        return "polygon has no coordinate rings"
    import math

    # EVERY ring (outer + holes) gets the per-vertex checks — a hole carrying
    # projected metres or NaN corrupts a clip as surely as the outer ring
    # (Sol finding, 2026-08-03). Span sanity applies to the outer ring only.
    lngs, lats = [], []
    for ring_ix, ring in enumerate(coords):
        if not isinstance(ring, (list, tuple)) or len(ring) < 4:
            return (f"ring {ring_ix} has "
                    f"{len(ring) if isinstance(ring, (list, tuple)) else 'no'} "
                    f"points — not a closed polygon")
        for pt in ring:
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                return f"malformed coordinate {pt!r} in ring {ring_ix}"
            lng, lat = pt[0], pt[1]  # GeoJSON axis order: [lng, lat]
            try:
                lng_f = float(lng)  # qa-ignore: TypeError arm below IS the None guard — a None coordinate returns a reason
                lat_f = float(lat)  # qa-ignore: same guard
            except (TypeError, ValueError):
                return f"non-numeric coordinate {pt!r} in ring {ring_ix}"
            if not (math.isfinite(lng_f) and math.isfinite(lat_f)):
                return f"non-finite coordinate in ring {ring_ix}"
            vertex_reason = check_point_nsw(lat_f, lng_f)
            if vertex_reason:
                return (f"ring {ring_ix} vertex ({lng_f}, {lat_f}): "
                        f"{vertex_reason}")
            if ring_ix == 0:
                lngs.append(lng_f)
                lats.append(lat_f)
    span_lng = max(lngs) - min(lngs)
    span_lat = max(lats) - min(lats)
    if span_lng == 0 or span_lat == 0:
        return "polygon is degenerate (zero extent)"
    if span_lng > max_span_deg or span_lat > max_span_deg:
        return (f"polygon spans {span_lat:.4f}° x {span_lng:.4f}° — far larger "
                f"than a parcel; metres fed where degrees expected?")
    return None


def check_rings_epsg3857(rings) -> Optional[str]:
    """ArcGIS-style rings that should be EPSG:3857 (Web Mercator metres)
    covering a NSW parcel. Every vertex is checked (a single trailing bad
    vertex corrupts the clip just as surely) against the NSW Mercator
    envelope — which also rejects OTHER projected CRSes such as MGA, whose
    metre values are plausible under a bare world-extent test."""
    import math

    if not rings or not isinstance(rings, (list, tuple)) or not rings[0]:
        return "no rings"
    ring = rings[0]
    if len(ring) < 4:
        return f"outer ring has {len(ring)} points — not a closed polygon"
    for pt in ring:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            return f"malformed ring coordinate {pt!r}"
        try:
            x, y = float(pt[0]), float(pt[1])  # qa-ignore: TypeError arm below IS the None guard
        except (TypeError, ValueError):
            return f"non-numeric ring coordinate {pt!r}"
        if not (math.isfinite(x) and math.isfinite(y)):
            return f"non-finite ring coordinate ({x}, {y})"
        if abs(x) <= 180 and abs(y) <= 90:
            return (f"ring coordinate ({x}, {y}) is degree-scale — WGS84 fed "
                    f"where EPSG:3857 metres expected")
        if not (_M3857_X_MIN <= x <= _M3857_X_MAX
                and _M3857_Y_MIN <= y <= _M3857_Y_MAX):
            return (f"ring coordinate ({x}, {y}) outside the NSW Web Mercator "
                    f"envelope — another projected CRS (e.g. MGA) fed as "
                    f"EPSG:3857?")
    return None
