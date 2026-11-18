# prior-art-checked: four sweeps 2026-11-18. (1) DB: lot_search_index already holds lga_name for 3,126,418 lots with a GiST index on geom (read-only here);
# no table or function resolves a council from a point for the area check. (2) Frontend: lib/ and app/api read the council through the live state layer
# or the property route, not this. (3) Python: services/lmr_area_inputs._lga is the live lookup this backs up; flood_planning/conveyancing connect to the
# database for other questions. (4) Plans: ce-boundary-snapshot-fallback-PLAN-2026-11-18.md (owner asked for it 2026-11-18).
"""The council for a point, read from OUR copy of the lot boundaries (lot_search_index), as a stand-in when the live state boundary service does not answer.

The live service is asked first (services/lmr_area_inputs._lga). This module is only the fallback, supplied by the caller (this is the only place
here that opens a database connection). It answers only when it is sure:
  - exactly ONE council has a lot within 40 m of the point  -> (council, as_of date)
  - no lot within 40 m, or lots of two or more councils within 40 m (a border, or a road between councils)  -> None
  - no DATABASE_URL, or the database does not answer in 3 s  -> None
It never raises and never guesses; None leaves the decision at "can't tell", exactly as if there were no fallback.
Measured 2026-11-18: lookups 11-38 ms; 60 of 60 random lots agreed with the live service.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

NEAR_DEG = 0.0004   # about 40 m: a point on the road in front of a lot still finds that lot
CONNECT_TIMEOUT_S = 3
STATEMENT_TIMEOUT_MS = 3000

_SQL = (
    "SELECT lga_name, max(computed_at) FROM lot_search_index "
    "WHERE ST_DWithin(geom, ST_SetSRID(ST_Point(%s, %s), 4326), %s) GROUP BY lga_name"
)


def _connect() -> Any:
    import psycopg2

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    return psycopg2.connect(dsn, connect_timeout=CONNECT_TIMEOUT_S,
                            options=f"-c statement_timeout={STATEMENT_TIMEOUT_MS} -c default_transaction_read_only=on")


def lga_from_snapshot(lat: float, lng: float, *, connect: Optional[Callable[[], Any]] = None) -> Optional[tuple[str, Optional[str]]]:
    """(council, as_of 'YYYY-MM-DD') when exactly one council is within 40 m of the point, else None. See the module note."""
    conn = None
    try:
        conn = (connect or _connect)()
        if conn is None:
            return None
        cur = conn.cursor()
        cur.execute(_SQL, (lng, lat, NEAR_DEG))
        rows = [(str(n).strip(), at) for n, at in cur.fetchall() if n and str(n).strip()]
        if len(rows) != 1:
            return None   # nothing near, or a border: never guess
        name, at = rows[0]
        return name, (at.date().isoformat() if hasattr(at, "date") else (str(at)[:10] if at else None))
    except Exception as exc:  # noqa: BLE001 -- a failed substitute is no answer, never a guess
        logger.warning("council snapshot lookup failed: %s", exc)
        return None
    finally:
        try:
            if conn is not None:
                conn.close()
        except Exception:  # noqa: BLE001
            pass
