"""Split overlay shapes into small valid pieces before they are stored.

A broken or huge shape makes every PostGIS lookup repair it again: a 2.27M-point
Cessnock flood outline took the live flood answer past its limit, and repairing it
in the database hung the connection (2026-10-29). 269 such flood rows were repaired
by splitting them on this PC. Loaders call `explode_rows` so a re-run writes the same
pieces under the same keys, instead of re-adding the broken originals beside them.

prior-art-checked: no shared make_valid/subdivide helper in services/ or scripts/
(ingest_coastal_inundation.py and others call ST_MakeValid inline per query).
"""
from __future__ import annotations

from typing import Iterable

import shapely
from shapely import wkt as _wkt
from shapely.geometry import MultiPolygon, Polygon, box

MAX_POINTS = 1000
# Only a broken shape, or one over this many points, is split -- the same rule the
# 2026-10-29 repair used, so a re-run lands on the keys already stored.
SPLIT_OVER_POINTS = 50000
# Piece keys: PIECE_OID_BASE + original_oid * 100000 + piece_number (1-based).
PIECE_OID_BASE = 10 ** 12
_EXECUTE_VALUES = None  # tests swap in a recorder


def _polys(g) -> list[Polygon]:
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    return [p for part in getattr(g, "geoms", []) for p in _polys(part)]


def valid_pieces(geom, cap: int = MAX_POINTS) -> list[MultiPolygon]:
    """Make the shape valid, then halve it (longer side) until each piece has <= cap points."""
    g = MultiPolygon(_polys(shapely.make_valid(geom)))
    out, stack = [], [g]
    while stack:
        h = stack.pop()
        if h.is_empty:
            continue
        if len(shapely.get_coordinates(h)) <= cap:
            ps = [p for p in _polys(h) if p.area > 0]
            if ps:
                out.append(MultiPolygon(ps))
            continue
        x0, y0, x1, y1 = h.bounds
        if x1 - x0 >= y1 - y0:
            m = (x0 + x1) / 2
            cells = (box(x0, y0, m, y1), box(m, y0, x1, y1))
        else:
            m = (y0 + y1) / 2
            cells = (box(x0, y0, x1, m), box(x0, m, x1, y1))
        for cell in cells:
            stack.append(MultiPolygon(_polys(h.intersection(cell))))
    return out


def explode_rows(rows: Iterable[tuple], oid_index: int, wkt_index: int, cap: int = MAX_POINTS,
                 split_over: int = SPLIT_OVER_POINTS) -> list[tuple]:
    """Rows whose shape is valid and not over split_over points pass through unchanged. Any other row
    becomes one row per valid piece, keyed PIECE_OID_BASE + oid * 100000 + n."""
    out = []
    for row in rows:
        g = _wkt.loads(row[wkt_index])
        if g.is_valid and len(shapely.get_coordinates(g)) <= split_over:
            out.append(tuple(row))
            continue
        if row[oid_index] is None:
            raise ValueError("a broken or huge shape has no feature number to key its pieces by")
        ps = valid_pieces(g, cap)
        if not ps:
            raise ValueError(f"feature {row[oid_index]}: no polygon left after repair")
        if len(ps) > 99999:  # keys reserve 1..99999 pieces per feature
            raise ValueError(f"feature {row[oid_index]}: {len(ps)} pieces exceed the 99,999 key range")
        for n, piece in enumerate(ps, 1):
            r = list(row)
            r[oid_index] = PIECE_OID_BASE + int(row[oid_index]) * 100000 + n
            r[wkt_index] = piece.wkt
            out.append(tuple(r))
    return out


def delete_replaced(cur, rows: Iterable[tuple], key_index: int = 0, layer_index: int = 2, oid_index: int = 6) -> int:
    """Before upserting `rows` (the loader's rows BEFORE explode_rows), delete what an
    earlier run stored for the same features: the whole original and every piece key in
    its range. Otherwise a changed source leaves stale or surplus pieces queryable."""
    keys = sorted({(r[key_index], r[layer_index], int(r[oid_index])) for r in rows if r[oid_index] is not None})
    if not keys:
        return 0
    from psycopg2.extras import execute_values
    _run = _EXECUTE_VALUES or execute_values
    _run(cur, f"""
        DELETE FROM spatial_overlays s USING (VALUES %s) AS v(k, l, o)
        WHERE s.instrument_key = v.k AND s.layer_type = v.l
          AND (s.source_oid = v.o OR s.source_oid BETWEEN {PIECE_OID_BASE} + v.o * 100000 + 1
                                                  AND {PIECE_OID_BASE} + v.o * 100000 + 99999)""",
                   keys, template="(%s, %s, %s::bigint)", page_size=1000)
    return cur.rowcount
