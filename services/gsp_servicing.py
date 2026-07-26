# prior-art-checked: reuse not viable because no module reads sydney_water_gsp_servicing
#   (migration 058) — grep for sydney_water_gsp / fetch_gsp_servicing across services/
#   scripts/ returns only the ingest. The mine/contam fetchers wrap portal_constraints
#   (external ArcGIS); this is a DB point-in-polygon lookup of our own ingested table.
"""Sydney Water Growth Servicing Plan (GSP) per-address lookup.

Reusable across surfaces (conveyancer PDF today; Site Report / workbench later).
Reads the `sydney_water_gsp_servicing` table (migration 058) by point-in-polygon.

Three-state contract (mirrors the mine-subsidence / contaminated-land fetchers):
  {"status": "found", "data": {"ww": {...}|None, "dw": {...}|None}}
      the point falls inside at least one GSP growth-servicing polygon
  {"status": "empty"}    the point resolved but sits in NO GSP precinct — the
                         established-suburb gap (Section 73 territory), NOT "clear"
  {"status": "failed"}   lookup unavailable — callers render "Not assessed", never "clear"

Licensing: source is © Sydney Water, "guide only, no warranty". Any surface must
attribute + link (GSP_URL) and must NOT present dsp_price_per_et as the live charge —
it is a CPI-excluded base figure.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

GSP_URL = (
    "https://www.sydneywater.com.au/plumbing-building-developing/developing/"
    "growth-servicing-plan.html"
)
GSP_SOURCE = "Sydney Water Growth Servicing Plan 2025–2030"

# ST_Covers (not ST_Contains) so a point exactly on a polygon boundary counts as
# inside — otherwise a lot on a GSP edge would falsely read as "not in a precinct".
_SQL = """
    SELECT product, polygon_name, growth_area, status_code, constrained,
           timeframe, dsp_price_per_et, special_comments
    FROM sydney_water_gsp_servicing
    WHERE ST_Covers(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
"""


def _row_to_dict(row: tuple) -> dict:
    (product, polygon_name, growth_area, status_code, constrained,
     timeframe, dsp_price_per_et, special_comments) = row
    return {
        "product": product,
        "polygon_name": polygon_name,
        "growth_area": growth_area,
        "status_code": status_code,
        "constrained": bool(constrained),
        "timeframe": timeframe,
        "dsp_price_per_et": (
            float(dsp_price_per_et) if dsp_price_per_et is not None else None
        ),
        "special_comments": special_comments,
    }


def fetch_gsp_servicing(lat: float, lng: float) -> dict:
    """Resolve a lon/lat to its GSP servicing status. Never raises — a failure
    returns {"status": "failed"} so a caller's whole report is not lost."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.warning("DATABASE_URL unset — GSP servicing lookup unavailable")
        return {"status": "failed"}

    conn = None
    try:
        import psycopg2

        conn = psycopg2.connect(db_url, connect_timeout=10)
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = 15000")  # 15s hard cap
            cur.execute(_SQL, (lng, lat))  # ST_MakePoint is (x=lng, y=lat)
            rows = cur.fetchall()
    except Exception as e:  # noqa: BLE001 — degrade to three-state, never crash caller
        logger.warning("GSP servicing lookup failed: %s", e)
        return {"status": "failed"}
    finally:
        if conn is not None:
            conn.close()

    if not rows:
        return {"status": "empty"}

    by_product = {r[0]: _row_to_dict(r) for r in rows}
    return {
        "status": "found",
        "data": {"ww": by_product.get("WW"), "dw": by_product.get("DW")},
    }


_STAGE_HUMAN = {
    "IN_DELIVERY": "servicing in delivery",
    "PLANNED": "servicing planned",
    "NO_CURRENT_PROJECT": "no current servicing project",
    "UNKNOWN_STAGE": "servicing stage not stated",
}


def summarize_servicing(servicing: dict | None) -> str | None:
    """One-line human summary for a Site Report row / workbench tile.

    Returns None for a failed or missing lookup (caller shows "Not assessed"),
    a factual sentence otherwise. Shared wording so every web surface reads the
    same; the conveyancer PDF keeps its own richer row. Never says "serviceable".
    """
    if not servicing:
        return None
    status = servicing.get("status")
    if status == "empty":
        return (
            "Not in a Sydney Water growth-servicing precinct — capacity for an "
            "established-area site is set via a Section 73 application, not the GSP. "
            f"Source: {GSP_SOURCE}."
        )
    if status == "found":
        data = servicing.get("data") or {}
        ww, dw = data.get("ww"), data.get("dw")
        parts = []
        for label, d in (("wastewater", ww), ("water", dw)):
            if not d:
                continue
            human = _STAGE_HUMAN.get(d.get("status_code"), "stage not stated")
            tf = (d.get("timeframe") or "").strip()
            tf_s = f" ({tf})" if tf and tf.lower() != "no timeframe noted." else ""
            parts.append(f"{label} {human}{tf_s}")
        constrained = bool((ww or {}).get("constrained") or (dw or {}).get("constrained"))
        text = "Within a Sydney Water growth-servicing area — " + "; ".join(parts) + "."
        if constrained:
            text += " Capacity/timescale constraints noted."
        text += (
            " Trunk capacity is not service-readiness — feasibility and connection works "
            f"are still required. Source: {GSP_SOURCE}."
        )
        return text
    return None  # failed / unknown
