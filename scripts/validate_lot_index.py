#!/usr/bin/env python3
"""Lot-index validation harness.

Samples N lots per LGA from lot_search_index and compares the stored LEP values
(lep_fsr, lep_height_m) against the LIVE NSW Planning MapServer at each lot's
centroid — the same source the index was built from. Surfaces silent drift
(stale snapshot vs current instrument) at scale, the failure mode that the
9 m-vs-53 m height bug slipped through.

READ-ONLY: reads lot_search_index + nsw_cadastre_lots + the public MapServer.
Writes nothing.

Usage:
    python scripts/validate_lot_index.py --lga "BLACKTOWN" --sample 25
    python scripts/validate_lot_index.py --all --sample 10        # sample every LGA
    # exit 0 = drift under threshold; exit 1 = drift over threshold (CI-friendly)
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

import psycopg2
import requests

PLANNING_BASE = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning"
# (layer_id, value_field) for the Principal Planning Layers MapServer.
LAYERS = {
    "fsr": (4, "FSR"),
    "height": (7, "MAX_B_H_M"),
}
# Match tolerances — below these a stored/live difference is treated as agreement.
TOL = {"fsr": 0.01, "height": 0.5}


def _classify(stored: Optional[float], live: Optional[float], tol: float) -> str:
    """Classify a stored-vs-live pair.

    Returns 'match' | 'mismatch' | 'both_null' | 'stored_only' | 'live_only'.
    Pure function — unit-tested; the harness's correctness hinges on it.
    """
    s_null = stored is None
    l_null = live is None
    if s_null and l_null:
        return "both_null"
    if s_null and not l_null:
        return "live_only"      # source has a value the index lacks (stale/missing)
    if l_null and not s_null:
        return "stored_only"    # index has a value the source no longer returns
    return "match" if abs(float(stored) - float(live)) <= tol else "mismatch"


def _query_mapserver_point(lon: float, lat: float, layer_id: int, field: str) -> Optional[float]:
    """Return the numeric layer value at a WGS84 point, or None if no feature."""
    url = f"{PLANNING_BASE}/Principal_Planning_Layers/MapServer/{layer_id}/query"
    params = {
        "f": "json",
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": field,
        "returnGeometry": "false",
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        feats = r.json().get("features", [])
    except Exception:
        return None
    if not feats:
        return None
    val = feats[0].get("attributes", {}).get(field)
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None


def _sample_lots(conn, lga: str, n: int) -> list[tuple]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT l.lotidstring, l.lep_fsr, l.lep_height_m,
               ST_X(ST_Centroid(ST_Transform(c.geom, 4326))) AS lon,
               ST_Y(ST_Centroid(ST_Transform(c.geom, 4326))) AS lat
        FROM lot_search_index l
        JOIN nsw_cadastre_lots c USING (lotidstring)
        WHERE l.lga_name = %s
          AND (l.lep_fsr IS NOT NULL OR l.lep_height_m IS NOT NULL)
        ORDER BY random()
        LIMIT %s
        """,
        (lga.upper(), n),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def validate_lga(conn, lga: str, n: int) -> dict:
    rows = _sample_lots(conn, lga, n)
    counts = {"fsr": {}, "height": {}}
    examples: list[str] = []
    for lotid, fsr, height, lon, lat in rows:
        if lon is None or lat is None:
            continue
        stored = {"fsr": fsr, "height": height}
        for key, (layer_id, field) in LAYERS.items():
            live = _query_mapserver_point(lon, lat, layer_id, field)
            verdict = _classify(stored[key], live, TOL[key])
            counts[key][verdict] = counts[key].get(verdict, 0) + 1
            if verdict in ("mismatch", "live_only") and len(examples) < 8:
                examples.append(
                    f"    {lotid} {key}: stored={stored[key]} live={live} ({verdict})"
                )
    return {"lga": lga, "sampled": len(rows), "counts": counts, "examples": examples}


def _drift_rate(counts: dict) -> float:
    """Drift = (mismatch + live_only) / comparable, ignoring both_null."""
    comparable = sum(v for k, v in counts.items() if k != "both_null")
    drift = counts.get("mismatch", 0) + counts.get("live_only", 0)
    return (drift / comparable) if comparable else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate lot_search_index vs live MapServer")
    ap.add_argument("--lga", help="Single LGA (overlay name, e.g. 'BLACKTOWN')")
    ap.add_argument("--all", action="store_true", help="Sample every LGA in the index")
    ap.add_argument("--sample", type=int, default=20, help="Lots sampled per LGA")
    ap.add_argument("--threshold", type=float, default=0.10,
                    help="Drift rate above which the run exits non-zero")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr)
        return 2
    conn = psycopg2.connect(db)
    conn.autocommit = True

    if args.all:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT lga_name FROM lot_search_index WHERE lga_name IS NOT NULL ORDER BY 1")
        lgas = [r[0] for r in cur.fetchall()]
        cur.close()
    elif args.lga:
        lgas = [args.lga.upper()]
    else:
        print("Provide --lga or --all", file=sys.stderr)
        return 2

    worst = 0.0
    for lga in lgas:
        res = validate_lga(conn, lga, args.sample)
        fsr_d = _drift_rate(res["counts"]["fsr"])
        ht_d = _drift_rate(res["counts"]["height"])
        worst = max(worst, fsr_d, ht_d)
        print(f"{lga}: sampled {res['sampled']} | FSR drift {fsr_d:.0%} {res['counts']['fsr']} "
              f"| height drift {ht_d:.0%} {res['counts']['height']}")
        for ex in res["examples"]:
            print(ex)

    conn.close()
    print(f"\nWorst drift: {worst:.0%} (threshold {args.threshold:.0%})")
    return 1 if worst > args.threshold else 0


if __name__ == "__main__":
    sys.exit(main())
