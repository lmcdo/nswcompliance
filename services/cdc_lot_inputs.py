"""Server-side property inputs for the CDC Housing Code lot-requirements screen.

prior-art-checked: reuse not viable because parse_controls (scripts/
generate_conveyancing_report.py) keeps only the FIRST zone and the FIRST acid
sulfate class of a property, so a split-zoned lot reads as single-zoned, and
lib/property-data.ts turns missing data into "clear" (heritage false, acid
sulfate 'Class 5'). This module reuses the same fetchers (resolve_address with
its GATE-0 parcel identity check, layerintersect, the Valuer General service,
the cadastre lot, services/lot_dimensions area) and parses their raw output with
three-state semantics. Nothing here takes a fact from the caller.

Pure parsing helpers (parse_zone_blocks, parse_ass_blocks, combine_*) are split
from the network calls so they can be tested without the Portal.
"""

from __future__ import annotations

import logging
import math
import re
import sys
from pathlib import Path
from typing import Optional

try:
    from services.cdc_lot_requirements import AreaReading, LotInputs
except ImportError:  # local (non-Docker) import path
    from cdc_lot_requirements import AreaReading, LotInputs  # type: ignore

logger = logging.getLogger(__name__)

_project_root = Path(__file__).parent.parent
for _p in (_project_root / "scripts", _project_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

ZONE_SOURCE = "NSW Planning Portal layerintersect (whole property), Land Zoning Map"
ASS_SOURCE = "NSW Planning Portal layerintersect (whole property), Acid Sulfate Soils Map"
WIDTH_SOURCE = (
    "cadastre lot polygon (Planning Portal), rectangular lot: the width at any "
    "building line equals a side length"
)
WIDTH_REASON_NOT_RECT = (
    "the lot is not a rectangle, so its width at the building line depends on where "
    "the building line falls. The bounding-box frontage in services/lot_dimensions.py "
    "is a shorter-side heuristic, not a width measured at the building line"
)
# Geometry tolerances (not regulatory values): a vertex turning less than this is
# treated as a point on a straight boundary, and a corner within this of 90 degrees
# as square. Segments shorter than MIN_SEGMENT_M are survey noise.
STRAIGHT_TOLERANCE_DEG = 0.5
SQUARE_TOLERANCE_DEG = 1.0
MIN_SEGMENT_M = 0.05

_ZONE_CODE_RE = re.compile(r"^[A-Z]{1,3}[0-9]{0,2}[A-Z]?$")
_ASS_CLASS_RE = re.compile(r"^class\s*([1-5])$", re.IGNORECASE)


class PropertyNotIdentified(Exception):
    """The address did not resolve to exactly one parcel (GATE-0)."""


def parse_zone_blocks(raw: list) -> tuple[Optional[frozenset], Optional[str]]:
    """All zones on the property, or (None, reason)."""
    if not isinstance(raw, list) or not raw:
        return None, "Planning Portal returned no planning layers for this property"
    blocks = [b for b in raw if isinstance(b, dict) and "zoning" in str(b.get("layerName") or "").lower()]
    if not blocks:
        return None, "Planning Portal returned no Land Zoning Map result for this property"
    zones: set = set()
    for b in blocks:
        results = b.get("results") or []
        if not results:
            return None, "a Land Zoning Map result carried no features"
        for r in results:
            z = str((r or {}).get("Zone") or "").strip().upper()
            if not _ZONE_CODE_RE.match(z):
                return None, f"a zoning feature has no valid zone code ({z!r})"
            zones.add(z)
    return frozenset(zones), None


def parse_ass_blocks(raw: list) -> tuple[Optional[frozenset], Optional[str]]:
    """Acid sulfate classes mapped on the property: a set (empty = not on a map),
    or (None, reason). Requires a zoning result in the SAME response as evidence
    that the response is a real, complete answer for this property."""
    zones, why = parse_zone_blocks(raw)
    if zones is None:
        return None, f"planning layers incomplete ({why})"
    blocks = [b for b in raw if isinstance(b, dict) and "acid sulfate" in str(b.get("layerName") or "").lower()]
    classes: set = set()
    for b in blocks:
        for r in b.get("results") or []:
            label = str((r or {}).get("Class") or (r or {}).get("title") or "").strip()
            m = _ASS_CLASS_RE.match(label)
            if not m:
                return None, f"acid sulfate map label {label!r} is not a Class 1-5"
            classes.add(int(m.group(1)))
    return frozenset(classes), None


def combine_ass(portal: Optional[frozenset], portal_reason: Optional[str],
                postgis_classes: Optional[frozenset], excluded_max: int
                ) -> tuple[Optional[frozenset], Optional[str]]:
    """Cross-check the live Portal answer against the PostGIS copy of the map.
    A copy showing an excluded class where the Portal shows none is a conflict."""
    if portal is None:
        return None, portal_reason
    excluded = set(range(1, excluded_max + 1))
    if postgis_classes is not None and (set(postgis_classes) & excluded) and not (set(portal) & excluded):
        return None, (f"sources conflict: the Planning Portal shows classes {sorted(portal) or 'none'} "
                      f"but the stored Acid Sulfate Soils Map copy shows {sorted(postgis_classes)}")
    return portal, None


def rectangle_width_range(geometry) -> tuple[Optional[tuple], Optional[str]]:
    """(shortest side, longest side) in metres when the lot is a rectangle, else
    (None, reason).

    In a rectangle every line parallel to a side crosses the lot at that side's
    full length, so the width at ANY building line is one of the side lengths,
    whichever boundary faces the road. The range therefore bounds the width at
    the building line exactly; it is not an estimate. Any other shape -> None.
    """
    try:
        from services.lot_dimensions import _scale_factor_for_ring, _usable_ring
    except ImportError:
        from lot_dimensions import _scale_factor_for_ring, _usable_ring  # type: ignore
    rings = (geometry or {}).get("rings") if isinstance(geometry, dict) else None
    if not rings or len(rings) != 1:
        return None, "lot geometry unavailable or has more than one ring"
    ring = _usable_ring(rings[0])  # noqa: bracket-access — length checked
    if not ring or len(ring) < 4:
        return None, "lot geometry is malformed"
    scale = _scale_factor_for_ring(ring)
    pts = [(p[0] / scale, p[1] / scale) for p in ring]  # noqa: bracket-access — _usable_ring guarantees (x, y)
    if math.dist(pts[0], pts[-1]) < MIN_SEGMENT_M:  # noqa: bracket-access — len >= 4
        pts = pts[:-1]
    # Drop survey-noise points and points on a straight boundary, repeating until stable.
    changed = True
    while changed and len(pts) > 4:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            if math.dist(a, b) < MIN_SEGMENT_M or abs(_turn_deg(a, b, c)) < STRAIGHT_TOLERANCE_DEG:
                del pts[i]
                changed = True
                break
    if len(pts) != 4:
        return None, WIDTH_REASON_NOT_RECT
    for i in range(4):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % 4]
        if abs(abs(_turn_deg(a, b, c)) - 90.0) > SQUARE_TOLERANCE_DEG:
            return None, WIDTH_REASON_NOT_RECT
    sides = [math.dist(pts[i], pts[(i + 1) % 4]) for i in range(4)]
    return (round(min(sides), 2), round(max(sides), 2)), None


def _turn_deg(a, b, c) -> float:
    """Signed turn at b travelling a -> b -> c, in degrees (0 = straight on)."""
    h1 = math.atan2(b[1] - a[1], b[0] - a[0])
    h2 = math.atan2(c[1] - b[1], c[0] - b[0])
    d = math.degrees(h2 - h1)
    return (d + 180.0) % 360.0 - 180.0


def area_readings(cadastre_m2, vg_m2) -> tuple[tuple, Optional[str]]:
    """Valid readings, or a reason. A source that answered with a malformed value
    (NaN, Infinity, zero, negative, non-numeric) makes the area UNKNOWN; it is not
    silently dropped in favour of the other source. A source that returned
    nothing (None) is simply absent."""
    out = []
    for src, v in (("cadastre lot polygon (geodesic area)", cadastre_m2),
                   ("NSW Valuer General property area", vg_m2)):
        if v is None:
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0:
            out.append(AreaReading(src, float(v)))
        else:
            return (), f"{src} returned an invalid area ({v!r})"
    return tuple(out), None


def _postgis_ass(conn, lot_wkt: Optional[str], excluded_max: int
                 ) -> tuple[Optional[frozenset], Optional[float]]:
    """(standard classes intersecting the lot, fraction of the lot covered by
    excluded classes) from spatial_overlays; (None, None) when unavailable."""
    if conn is None or not lot_wkt:
        return None, None
    labels = [f"Class {c}" for c in range(1, excluded_max + 1)]
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT value FROM spatial_overlays
            WHERE layer_type = 'acid_sulfate'
              AND ST_Intersects(geom, ST_SetSRID(ST_GeomFromText(%s), 4326))
            """,
            (lot_wkt,),
        )
        found = set()
        for (v,) in cur.fetchall():
            m = _ASS_CLASS_RE.match(str(v or "").strip())
            if m:
                found.add(int(m.group(1)))
        cur.execute(
            """
            WITH lot AS (SELECT ST_MakeValid(ST_SetSRID(ST_GeomFromText(%s), 4326)) g)
            SELECT ST_Area(ST_Intersection(lot.g, ST_Union(ST_MakeValid(o.geom)))::geography)
                   / NULLIF(ST_Area(lot.g::geography), 0)
            FROM lot JOIN spatial_overlays o
              ON o.layer_type = 'acid_sulfate' AND o.value = ANY(%s) AND ST_Intersects(o.geom, lot.g)
            GROUP BY lot.g
            """,
            (lot_wkt, labels),
        )
        row = cur.fetchone()
        cur.close()
        frac = float(row[0]) if row and row[0] is not None else 0.0  # noqa: bracket-access — row checked
        return frozenset(found), frac if math.isfinite(frac) else None
    except Exception as e:  # noqa: BLE001
        logger.warning("cdc lot inputs: PostGIS acid sulfate query failed: %s", e)
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        return None, None


def load_lot_inputs(address: str, conn, excluded_ass_max: int) -> tuple[dict, LotInputs]:
    """Resolve the parcel from the address and fetch every fact server-side.

    Raises PropertyNotIdentified when the address does not resolve to one parcel.
    Upstream failures never raise; they surface as UNKNOWN with a reason.
    """
    from generate_conveyancing_report import (  # noqa: E402
        _portal_get, get_raw_controls, get_valuation, resolve_address,
    )
    try:
        from services.lot_dimensions import calculate_lot_dimensions
    except ImportError:
        from lot_dimensions import calculate_lot_dimensions  # type: ignore

    prop_id, _lat, _lng, lot_wkt = resolve_address(address)
    if not prop_id:
        raise PropertyNotIdentified(address)

    lots = _portal_get("lot", {"propId": prop_id})
    lot_desc = None
    cadastre = None
    area_reason = None
    single_lot = False
    width_range = None
    width_reason = "cadastre lot geometry unavailable or the property is not a single lot"
    if not isinstance(lots, list) or not lots:
        area_reason = "cadastre lot geometry unavailable"
    elif len(lots) != 1:
        area_reason = f"the property comprises {len(lots)} lots; this screen needs a single lot"
    else:
        lot0 = lots[0] if isinstance(lots[0], dict) else {}  # noqa: bracket-access — length checked
        geom = lot0.get("geometry") or {}
        lot_desc = (lot0.get("attributes") or {}).get("LotDescription")
        if len(geom.get("rings") or []) != 1:
            area_reason = "the lot geometry has more than one ring"
        else:
            single_lot = True
            width_range, width_reason = rectangle_width_range(geom)
            dims = calculate_lot_dimensions(geom)
            cadastre = dims.area_m2 if dims else None
    vg = (get_valuation(prop_id) or {}).get("lot_area_m2") if single_lot else None
    readings: tuple = ()
    if single_lot:
        readings, area_reason = area_readings(cadastre, vg)

    raw = get_raw_controls(prop_id)
    zones, zone_reason = parse_zone_blocks(raw)
    portal_ass, ass_reason = parse_ass_blocks(raw)
    pg_classes, frac = _postgis_ass(conn, lot_wkt if single_lot else None, excluded_ass_max)
    ass, ass_reason = combine_ass(portal_ass, ass_reason, pg_classes, excluded_ass_max)
    ass_source = ASS_SOURCE + ("; whole-lot coverage from stored Acid Sulfate Soils Map copy"
                               if frac is not None else "")

    inputs = LotInputs(
        zones=zones, zone_source=ZONE_SOURCE, zone_reason=zone_reason,
        areas=readings, area_reason=area_reason,
        width_range_m=width_range, width_source=WIDTH_SOURCE if width_range else "none",
        width_reason=None if width_range else width_reason,
        ass_classes=ass, ass_source=ass_source, ass_reason=ass_reason,
        ass_excluded_fraction=frac,
    )
    prop = {"address": address, "prop_id": int(prop_id), "lot": lot_desc}
    return prop, inputs
