# prior-art-checked: four sweeps 2026-11-18. (1) DB: spatial_overlays holds 226,114 bushfire rows (instrument_key 'unknown', no council), loaded 2026-04..05 by
# scripts/ingest_spatial_overlays.py --layer bushfire. (2) Frontend: no loader. (3) Python: that script re-writes every feature and deletes what it replaces first, which
# took about 7 minutes per 500 features on this table (days for 227k); this reuses its fetch and row-building helpers but only ADDS features whose id is missing, and deletes
# nothing. (4) Plans: ce-layers-own-copy-SCOPE-2026-11-18.md (owner approved the bushfire refresh 2026-11-18).
"""Add the bush fire prone land areas the state map has and our overlay table lacks. Deletes nothing.

    python scripts/refresh_bushfire_new_areas.py            # dry run: how many are new and how many of ours are gone from the live map
    python scripts/refresh_bushfire_new_areas.py --apply    # inserts the new areas (INSERT ... ON CONFLICT DO NOTHING)

Adding an area can only make a bush fire check stricter, so this is the safe half of a refresh. Areas that are in our table but gone from the live map are only
COUNTED here: removing them is a separate decision (an id may have been re-issued rather than the area removed).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ingest_spatial_overlays as ing  # noqa: E402  (its loader helpers: fetch_page_by_oids, geom_to_multipolygon_wkt)
import psycopg2  # noqa: E402
import requests  # noqa: E402
from psycopg2.extras import execute_values  # noqa: E402

from services.geom_pieces import explode_rows  # noqa: E402

LAYER = "bushfire"
BATCH = 200
MIN_LIVE_AREAS = 100_000   # the layer holds about 227,000; far fewer means the service errored, not that areas were removed
PIECE_OID_BASE = 10 ** 12   # split pieces are keyed base + id * 100000 + n (services/geom_pieces.PIECE_OID_BASE); a piece counts as its original id


def live_ids() -> set[int]:
    url = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire/BFPL/MapServer/0/query"
    j = requests.get(url, params={"where": "1=1", "returnIdsOnly": "true", "f": "json"}, timeout=120).json()
    return set(j.get("objectIds") or [])


def held_ids(cur) -> set[int]:
    cur.execute("SELECT DISTINCT CASE WHEN source_oid >= %s THEN (source_oid - %s) / 100000 ELSE source_oid END FROM spatial_overlays "
                "WHERE layer_type = %s AND source_oid IS NOT NULL", (PIECE_OID_BASE, PIECE_OID_BASE, LAYER))
    return {int(o) for (o,) in cur.fetchall()}


def build_rows(features: list[dict], value_field: str = "d_Category") -> list[tuple]:
    """Overlay rows exactly as the loader builds them for this layer (instrument 'unknown', no council, no currency date)."""
    rows = []
    for f in features:
        props = f.get("properties") or f.get("attributes") or {}
        wkt = ing.geom_to_multipolygon_wkt(f["geometry"]) if f.get("geometry") else None
        oid = props.get("OBJECTID")
        if not wkt or oid is None:
            continue
        raw = props.get(value_field)
        rows.append(("unknown", None, LAYER, str(raw) if raw is not None else None, None, None, oid, wkt))
    return rows


def main(argv: list[str]) -> int:
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    try:
        return _run(argv, conn)
    finally:
        conn.close()


def _run(argv: list[str], conn) -> int:
    apply = "--apply" in argv
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '120000'")
    live, held = live_ids(), held_ids(cur)
    if len(live) < MIN_LIVE_AREAS:
        print(f"STOPPED: the live service returned only {len(live)} area ids (expected over {MIN_LIVE_AREAS}); nothing was compared or written")
        return 1
    new, gone = sorted(live - held), sorted(held - live)
    print(f"live areas {len(live)} | held {len(held)} | NEW (to add) {len(new)} | held but gone from live (NOT touched) {len(gone)}")
    if not apply:
        print("DRY RUN: nothing written. Re-run with --apply.")
        return 0
    added = skipped = 0
    for i in range(0, len(new), BATCH):
        ids = new[i:i + BATCH]
        data = None
        for attempt in range(4):
            try:
                data = ing.fetch_page_by_oids("BFPL", 0, ids, base="Fire")
                break
            except Exception as exc:  # noqa: BLE001
                print(f"    retry {attempt + 1}: {type(exc).__name__}", flush=True)
                time.sleep(5 * (attempt + 1))
        if data is None:
            print(f"STOPPED: batch starting at {i} could not be read; {added} added so far, the rest can be re-run (it only adds what is missing)")
            return 1
        feats = data.get("features") or []
        rows = ing.explode_rows(build_rows(feats), oid_index=6, wkt_index=7) if feats else []
        skipped += len(ids) - len({r[6] for r in build_rows(feats)})
        if rows:
            execute_values(cur, """INSERT INTO spatial_overlays (instrument_key, lga_name, layer_type, value, value_numeric, currency_date, source_oid, geom, synced_at)
                                   VALUES %s ON CONFLICT (instrument_key, layer_type, source_oid) DO NOTHING""", rows,
                           template="(%s, %s, %s, %s, %s, %s, %s, ST_Multi(ST_GeomFromText(%s, 4326)), now())")
            conn.commit()
            added += len(rows)
        print(f"DONE {min(i + BATCH, len(new))}/{len(new)} (rows added {added}, features without geometry skipped {skipped})", flush=True)
    print(f"finished: {added} rows added; held-but-gone {len(gone)} left untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
