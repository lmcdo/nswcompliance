# prior-art-checked: no existing endpoint exposes the guarded DCP controls
# read (repo grep 2026-08-03: fetch_dcp_setbacks is consumed only in-process
# by conveyancing/intelligence_brief/constraint_arithmetic/build_lot_search_
# index; the ~5 frontend routes each run their OWN inline SQL — that
# duplication is exactly what this endpoint exists to end, campaign item 5).
"""/pipeline/dcp-controls — the single guarded DCP controls read, over HTTP.

Output-grounding campaign item 5: the frontend routes that used to query
``dcp_setback_controls`` with their own inline SQL (each omitting a different
part of the guard stack — arbitrary LIMIT 3 rows, flagged rows served as
numbers, superseded-row weakenings) proxy THIS endpoint instead. It serves
``conveyancing_db.fetch_dcp_setbacks`` verbatim: is_current, needs_review
exclusion, zone filtering, dev-type routing, deterministic ordering, and the
plan-level as-at — one implementation, one drift surface.

Consumers SHAPE (filter control types, pick rates, build citation links);
they never re-implement guards.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

logger = logging.getLogger(__name__)

_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root / "scripts"))
sys.path.insert(0, str(_project_root))

from conveyancing_db import fetch_dcp_setbacks  # noqa: E402

router = APIRouter(prefix="/pipeline", tags=["dcp"])


@router.get("/dcp-controls")
def dcp_controls(lga: str, zone: Optional[str] = None):
    """Guarded DCP controls for one LGA slug.

    Three states (never two):
      available=True             — guarded rows follow
      available=False + reason   — queried, nothing serves for this slug
      status='unavailable'       — the read itself failed (HTTP 503)
    """
    import psycopg2

    lga_slug = (lga or "").strip().lower()
    if not lga_slug:
        return {"available": False, "lga": lga,
                "reason": "no LGA slug supplied"}

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        from fastapi import HTTPException

        raise HTTPException(503, "DCP controls source unavailable: no "
                                 "database configured")

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        # prior-art-checked: same endpoint's own call gains raise_on_error —
        # a swallowed query failure must surface as 503 here, never as
        # available:false, or every proxy consumer renders an outage as a
        # clean no-controls result (Sol, 2026-08-04). No new capability.
        result = fetch_dcp_setbacks(conn, lga_slug, zone, raise_on_error=True)
    except Exception as e:
        logger.error("dcp-controls read failed for %s: %s", lga_slug, e)
        from fastapi import HTTPException

        raise HTTPException(503, "DCP controls source unavailable")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    if result is None:
        # With raise_on_error, None now means exactly one thing: the guarded
        # query COMPLETED and found no current rows for this slug.
        return {
            "available": False,
            "lga": lga_slug,
            "reason": "no current controls for this LGA",
        }

    rows = list(result.get("setbacks") or []) + list(result.get("sd_setbacks") or [])
    return {
        "available": True,
        "lga": lga_slug,
        "dcp_name": result.get("dcp_name"),
        "dcp_url": result.get("dcp_url"),
        "caveat": result.get("caveat"),
        "clause_ref": result.get("clause_ref"),
        "zone_filter_applied": result.get("zone_filter_applied"),
        "as_at": result.get("as_at"),
        "as_at_status": result.get("as_at_status"),
        "as_at_line": result.get("as_at_line"),
        "registry_pdf_urls": result.get("registry_pdf_urls") or {},
        "rows": rows,
    }
