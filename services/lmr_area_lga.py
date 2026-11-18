# prior-art-checked: four sweeps 2026-11-18. (1) DB: lot_search_index already holds lga_name for 3,126,418 lots with a GiST index on geom (read-only here);
# no table or function resolves a council from a point for the area check. (2) Frontend: lib/ and app/api read the council through the live state layer
# or the property route, not this. (3) Python: services/lmr_area_inputs._lga_live is the live lookup this backs up; flood_planning/conveyancing connect to
# the database for other questions. (4) Plans: ce-boundary-snapshot-fallback-PLAN-2026-11-18.md (owner asked for it 2026-11-18).
"""The council for a point, read from OUR copy of the lot boundaries (lot_search_index), as a stand-in when the live state boundary service gives no answer.

The live service is asked first (services/lmr_area_inputs). This module is only the fallback, supplied by the caller (the only place here that opens a
database connection). It answers only when it is sure:
  - a lot CONTAINS the point                                   -> that lot's council (a lot lies in one council), with the copy's as-at date
  - no lot contains it, and exactly ONE council has a lot within about 100 m  -> that council
  - no lot within 100 m, or lots of two or more councils within 100 m (a border, a wide road, a park)  -> None
  - no DATABASE_URL, or the database does not answer in 3 s    -> None
It never raises and never guesses; None leaves the decision at "can't tell", exactly as if there were no fallback.
Measured 2026-11-18 (before the 100 m rule): lookups 11-38 ms; 60 of 60 random lots agreed with the live service.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

NEAR_DEG = 0.001   # about 100 m. Only used when no lot contains the point; a border or wide road inside it makes the answer None.
CONNECT_TIMEOUT_S = 3
STATEMENT_TIMEOUT_MS = 3000

_SQL = (
    "SELECT lga_name, bool_or(ST_Intersects(geom, ST_SetSRID(ST_Point(%s, %s), 4326))) AS inside, max(computed_at) "
    "FROM lot_search_index WHERE ST_DWithin(geom, ST_SetSRID(ST_Point(%s, %s), 4326), %s) GROUP BY lga_name"
)


def _connect() -> Any:
    import psycopg2

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    return psycopg2.connect(dsn, connect_timeout=CONNECT_TIMEOUT_S,
                            options=f"-c statement_timeout={STATEMENT_TIMEOUT_MS} -c default_transaction_read_only=on")


def _date(at: Any) -> Optional[str]:
    return at.date().isoformat() if hasattr(at, "date") else (str(at)[:10] if at else None)


def lga_from_snapshot(lat: float, lng: float, *, connect: Optional[Callable[[], Any]] = None) -> Optional[tuple[str, Optional[str], str]]:
    """(council, as_of 'YYYY-MM-DD', how) when a lot contains the point (how = "the lot at this point") or exactly one council is within about
    100 m (how = "the lots around this point"); else None. See the module note."""
    conn = None
    try:
        conn = (connect or _connect)()
        if conn is None:
            return None
        cur = conn.cursor()
        cur.execute(_SQL, (lng, lat, lng, lat, NEAR_DEG))
        raw = [((str(n).strip() if n else ""), bool(inside), at) for n, inside, at in cur.fetchall()]
        if any(not name for name, _inside, _at in raw):
            return None   # a lot with no council name nearby (above all one containing the point) makes the picture unsure: never skip it
        rows = raw
        containing = [r for r in rows if r[1]]
        if len(containing) == 1:
            return containing[0][0], _date(containing[0][2]), "the lot at this point"   # the lot the point is in decides, even near a border
        if containing:
            return None   # two lots of different councils contain one point: not possible in good data, so never guess
        if len(rows) == 1:
            return rows[0][0], _date(rows[0][2]), "the lots around this point"   # nothing contains it (a road): one council all round
        return None       # nothing near, or a border: never guess
    except Exception as exc:  # noqa: BLE001 -- a failed substitute is no answer, never a guess
        logger.warning("council snapshot lookup failed: %s", exc)
        return None
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:  # noqa: BLE001
            pass


_SQL_GUESS = (
    "SELECT lga_name, bool_or(ST_Intersects(geom, ST_SetSRID(ST_Point(%s, %s), 4326))) AS inside, "
    "min(ST_Distance(geom, ST_SetSRID(ST_Point(%s, %s), 4326))) AS dist, max(computed_at) "
    "FROM lot_search_index WHERE ST_DWithin(geom, ST_SetSRID(ST_Point(%s, %s), 4326), %s) AND lga_name IS NOT NULL GROUP BY lga_name"
)


def lga_best_guess(lat: float, lng: float, *, connect: Optional[Callable[[], Any]] = None) -> Optional[dict]:
    """Our best answer when lga_from_snapshot is unsure (a border, a road between councils): the council whose lot contains the point, else the
    nearest council's lot, with the other councils listed so the answer can say so. Returns {"council","as_of","alternatives"} or None
    (nothing within about 100 m, or any error). Used only after our own copy was unsure AND the live service gave no answer."""
    conn = None
    try:
        conn = (connect or _connect)()
        if conn is None:
            return None
        cur = conn.cursor()
        cur.execute(_SQL_GUESS, (lng, lat, lng, lat, lng, lat, NEAR_DEG))
        rows = [(str(n).strip(), bool(inside), float(dist or 0), at) for n, inside, dist, at in cur.fetchall() if n and str(n).strip()]
        if not rows:
            return None
        rows.sort(key=lambda r: (not r[1], r[2]))
        best = rows[0]
        return {"council": best[0], "as_of": _date(best[3]), "alternatives": [r[0] for r in rows[1:]]}
    except Exception as exc:  # noqa: BLE001 -- no guess is better than a wrong one
        logger.warning("council best-guess lookup failed: %s", exc)
        return None
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:  # noqa: BLE001
            pass


_BUSHFIRE_COPY = Path(__file__).resolve().parent.parent / "data" / "law" / "maps" / "bushfire_copy.json"
_SQL_BF_POINT = "SELECT EXISTS (SELECT 1 FROM spatial_overlays WHERE layer_type = 'bushfire' AND ST_Intersects(geom, ST_SetSRID(ST_Point(%s, %s), 4326)))"
_SQL_BF_LOT = ("SELECT EXISTS (SELECT 1 FROM spatial_overlays WHERE layer_type = 'bushfire' "
               "AND ST_Intersects(geom, ST_MakeValid(ST_SetSRID(ST_GeomFromText(%s), 4326))))")


def bushfire_copy_info() -> Optional[dict]:
    """The committed record of when our bush fire copy was refreshed and what it is known to lack, or None if unreadable."""
    import json

    try:
        info = json.loads(_BUSHFIRE_COPY.read_text(encoding="utf-8"))
        return info if isinstance(info, dict) and info.get("refreshed_on") else None
    except (OSError, ValueError):
        return None


def bushfire_from_snapshot(lat: float, lng: float, rings: Optional[list], *, connect: Optional[Callable[[], Any]] = None) -> Optional[dict]:
    """{"point": bool, "lot": bool | None, "as_of": date} from OUR copy of bush fire prone land, or None when it cannot answer (no connection, an
    error, or no record of when the copy was made). "lot" is None when no lot outline is given. Same read-only short-limit connection as the council lookup."""
    info = bushfire_copy_info()
    if info is None:
        return None
    conn = None
    try:
        conn = (connect or _connect)()
        if conn is None:
            return None
        cur = conn.cursor()
        cur.execute(_SQL_BF_POINT, (lng, lat))
        point = bool(cur.fetchone()[0])
        lot = None
        if rings and len(rings) >= 4:
            wkt = "POLYGON((" + ", ".join(f"{float(x)} {float(y)}" for x, y in rings) + "))"
            cur.execute(_SQL_BF_LOT, (wkt,))
            lot = bool(cur.fetchone()[0])
        return {"point": point, "lot": lot, "as_of": str(info.get("refreshed_on"))}
    except Exception as exc:  # noqa: BLE001 -- no answer from our copy: the live map is asked as before
        logger.warning("bush fire snapshot lookup failed: %s", exc)
        return None
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:  # noqa: BLE001
            pass


_SQL_LOT = (
    "SELECT ST_AsGeoJSON((d).geom), computed_at FROM (SELECT ST_Dump(geom) AS d, computed_at FROM lot_search_index "
    "WHERE ST_Intersects(geom, ST_SetSRID(ST_Point(%s, %s), 4326))) s "
    "WHERE ST_Contains((d).geom, ST_SetSRID(ST_Point(%s, %s), 4326)) ORDER BY ST_Area((d).geom) LIMIT 1"   # strictly inside, as the live reader requires: a point on a shared boundary gets no outline
)


def lot_outline_from_snapshot(lat: float, lng: float, *, connect: Optional[Callable[[], Any]] = None) -> Optional[tuple[list, Optional[str]]]:
    """(outer ring as [lng, lat] pairs, as_of date) of the smallest lot in OUR copy that contains the point, else None. Same read-only,
    short-limit connection as the council lookup; never raises; None leaves the caller to ask the live property service."""
    import json

    conn = None
    try:
        conn = (connect or _connect)()
        if conn is None:
            return None
        cur = conn.cursor()
        cur.execute(_SQL_LOT, (lng, lat, lng, lat))
        rows = cur.fetchall()
        if not rows:
            return None
        gj = json.loads(rows[0][0])
        ring = (gj.get("coordinates") or [[]])[0] if gj.get("type") == "Polygon" else None
        if not ring or len(ring) < 4:
            return None
        return [[float(x), float(y)] for x, y in ring], _date(rows[0][1])
    except Exception as exc:  # noqa: BLE001 -- no outline from our copy: the live service is asked
        logger.warning("lot outline snapshot lookup failed: %s", exc)
        return None
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:  # noqa: BLE001
            pass
