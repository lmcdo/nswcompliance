# prior-art-checked: four sweeps 2026-11-19. (1) DB: spatial_overlays holds 232k bushfire rows that measured 2026-11-18 miss about 1 in 10 live lots (existing areas changed shape);
# scripts/refresh_bushfire_new_areas.py only adds missing ids, scripts/ingest_spatial_overlays.py rewrites in place at about 7 minutes per 500 areas (days for 227k). (2) Frontend: no loader.
# (3) Python: this reuses the loader's fetch and row-building helpers and the geometry splitter; it builds a COMPLETE copy in a separate staging table and swaps it in one transaction.
# (4) Plans: ce-layers-own-copy-SCOPE-2026-11-18.md (owner asked for the rebuild "right" 2026-11-19).
"""Rebuild the bush fire prone land layer in spatial_overlays from the state map, safely.

    python scripts/rebuild_bushfire_overlay.py stage     # download every area into spatial_overlays_bushfire_new (resumable; touches nothing live)
    python scripts/rebuild_bushfire_overlay.py verify [--accept-unobtainable=ID,ID]   # staging vs the state map: ids, then hit/clear agreement at random points; prints PASS or FAIL
    python scripts/rebuild_bushfire_overlay.py swap      # ONLY after verify passed: backup the old rows, replace them with the staging rows in ONE transaction

stage can be re-run any number of times: it only fetches ids that are not yet in the staging table. Nothing reads the staging table, so a half-finished stage harms nothing.
swap refuses to run unless the staging table holds every live area id, writes the old rows to data/db_rollback_backups/bushfire_overlay_old_<date>.csv first, and rolls back on any problem.
"""
from __future__ import annotations

import os
import random
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ingest_spatial_overlays as ing  # noqa: E402  (fetch_page_by_oids, geom_to_multipolygon_wkt)
import psycopg2  # noqa: E402
import requests  # noqa: E402
from psycopg2.extras import execute_values  # noqa: E402

from services.geom_pieces import PIECE_OID_BASE as _GP_BASE, explode_rows  # noqa: E402

LAYER = "bushfire"
STAGE = "spatial_overlays_bushfire_new"
LIVE_URL = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire/BFPL/MapServer/0/query"
BATCH = 200
MIN_LIVE_AREAS = 100_000
PIECE_OID_BASE = _GP_BASE   # services/geom_pieces.PIECE_OID_BASE: split pieces are keyed base + id * 100000 + n
SAMPLE_POINTS = 150
MIN_AGREEMENT = 0.99


def connect():
    return psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)


def live_ids() -> set[int]:
    j = requests.get(LIVE_URL, params={"where": "1=1", "returnIdsOnly": "true", "f": "json"}, timeout=120).json()
    ids = set(j.get("objectIds") or [])
    if len(ids) < MIN_LIVE_AREAS:
        raise SystemExit(f"STOPPED: the live service returned only {len(ids)} area ids (expected over {MIN_LIVE_AREAS})")
    return ids


def build_rows(features: list[dict]) -> list[tuple]:
    """Overlay rows exactly as the loader builds them for this layer (instrument 'unknown', no council, no currency date)."""
    rows = []
    for f in features:
        props = f.get("properties") or f.get("attributes") or {}
        wkt = ing.geom_to_multipolygon_wkt(f["geometry"]) if f.get("geometry") else None
        oid = props.get("OBJECTID")
        if not wkt or oid is None:
            continue
        raw = props.get("d_Category")
        rows.append(("unknown", None, LAYER, str(raw) if raw is not None else None, None, None, oid, wkt))
    return rows


MAX_UNSTORABLE = 20   # more than this many missing areas is a failure, not an exception


def unstorable(ids: list[int]) -> list[int]:
    """Of these missing ids, the ones the state service answers for but whose shape cannot be stored (no usable polygon). An id that cannot be fetched is NOT listed."""
    out = []
    for oid in ids[:MAX_UNSTORABLE + 1]:
        try:
            d = ing.fetch_page_by_oids("BFPL", 0, [oid], base="Fire")
        except Exception:  # noqa: BLE001
            continue
        feats = d.get("features") or []
        if feats and not build_rows(feats):
            out.append(oid)
    return out


ACCEPTED: set[int] = set()   # ids a person named on the command line after checking that the state service errors on them every time (recorded in bushfire_copy.json)


def missing_is_acceptable(missing: list[int]) -> tuple[bool, list[int]]:
    """(ok, accepted ids). Missing areas are acceptable only if there are few and each is either proven to have no usable shape or was named by a person as
    unobtainable (the state service errors on it every time). Anything else, or too many, is a failure."""
    if not missing:
        return True, []
    if len(missing) > MAX_UNSTORABLE:
        return False, []
    named = [i for i in missing if i in ACCEPTED]
    rest = [i for i in missing if i not in ACCEPTED]
    bad = unstorable(rest) if rest else []
    return sorted(bad) == sorted(rest), sorted(named + bad)


def staged_ids(cur) -> set[int]:
    """Original area ids held in staging. A complex area is stored split into pieces keyed PIECE_OID_BASE + id * 100000 + n, so those count as the original id."""
    cur.execute(f"SELECT DISTINCT CASE WHEN source_oid >= %s THEN (source_oid - %s) / 100000 ELSE source_oid END FROM {STAGE}", (PIECE_OID_BASE, PIECE_OID_BASE))
    return {int(o) for (o,) in cur.fetchall()}


def _fetch_small(ids: list[int]):
    """Features for a few ids, one try each of two, or None. Used only when the full batch failed."""
    for attempt in range(2):
        try:
            return ing.fetch_page_by_oids("BFPL", 0, ids, base="Fire").get("features") or []
        except Exception:  # noqa: BLE001
            time.sleep(3)
    return None


def stage() -> int:
    live = live_ids()
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '120000'")
        cur.execute(f"""CREATE TABLE IF NOT EXISTS {STAGE} (
            instrument_key text, lga_name text, layer_type text, value text, value_numeric double precision, currency_date date,
            source_oid bigint, geom geometry(MultiPolygon, 4326), synced_at timestamptz DEFAULT now(),
            UNIQUE (instrument_key, layer_type, source_oid))""")
        cur.execute(f"CREATE INDEX IF NOT EXISTS {STAGE}_geom_idx ON {STAGE} USING gist (geom)")
        conn.commit()
        todo = sorted(live - staged_ids(cur))
        print(f"live areas {len(live)} | already staged {len(live) - len(todo)} | to fetch {len(todo)}", flush=True)
        done = 0
        for i in range(0, len(todo), BATCH):
            ids = todo[i:i + BATCH]
            data = None
            for attempt in range(5):
                try:
                    data = ing.fetch_page_by_oids("BFPL", 0, ids, base="Fire")
                    break
                except Exception as exc:  # noqa: BLE001
                    print(f"    retry {attempt + 1}: {type(exc).__name__}", flush=True)
                    time.sleep(8 * (attempt + 1))
            feats = None
            if data is not None:
                feats = data.get("features") or []
            else:   # a batch the service cannot answer (large or complex shapes): try 20 at a time, then one at a time
                feats = []
                for j in range(0, len(ids), 20):
                    part = _fetch_small(ids[j:j + 20])
                    if part is None:
                        for one in ids[j:j + 20]:
                            single = _fetch_small([one])
                            if single is None:
                                print(f"    area {one}: the service would not return it", flush=True)
                            else:
                                feats += single
                    else:
                        feats += part
            got = {(f.get("properties") or f.get("attributes") or {}).get("OBJECTID") for f in feats}
            absent = [i for i in ids if i not in got]
            if absent and data is not None:   # the service answered but left some ids out (it can reply with an empty list for a batch it could not serve): retry those smaller
                for j in range(0, len(absent), 20):
                    part = _fetch_small(absent[j:j + 20])
                    if part is None:
                        for one in absent[j:j + 20]:
                            single = _fetch_small([one])
                            if single:
                                feats += single
                    else:
                        feats += part
            rows = explode_rows(build_rows(feats), oid_index=6, wkt_index=7)
            for attempt in range(4):   # the database connection can drop on a long run: reconnect and retry the same batch (the insert ignores repeats)
                try:
                    if rows:
                        execute_values(cur, f"""INSERT INTO {STAGE} (instrument_key, lga_name, layer_type, value, value_numeric, currency_date, source_oid, geom, synced_at)
                                                VALUES %s ON CONFLICT (instrument_key, layer_type, source_oid) DO NOTHING""", rows,
                                       template="(%s, %s, %s, %s, %s, %s, %s, ST_Multi(ST_GeomFromText(%s, 4326)), now())")
                        conn.commit()
                    break
                except psycopg2.OperationalError as exc:
                    print(f"    database connection lost ({type(exc).__name__}); reconnecting", flush=True)
                    try:
                        conn.close()
                    except Exception:  # noqa: BLE001
                        pass
                    time.sleep(10 * (attempt + 1))
                    conn = connect()
                    cur = conn.cursor()
                    cur.execute("SET statement_timeout = '120000'")
            else:
                print("STOPPED: the database did not come back; re-run stage to resume", flush=True)
                return 1
            done += len(ids)
            print(f"DONE {done}/{len(todo)}", flush=True)
        missing = len(live - staged_ids(cur))
        print(f"finished this run: {missing} live areas still not staged (re-run stage to fill them; areas the service returns no shape for stay missing)")
        return 0
    finally:
        conn.close()


def _hit_live(lat: float, lng: float):
    p = {"geometry": f"{lng},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
         "returnCountOnly": "true", "f": "json"}
    for _ in range(3):
        try:
            j = requests.post(LIVE_URL, data=p, timeout=30).json()
            if "count" in j:
                return j["count"] > 0
        except Exception:  # noqa: BLE001
            time.sleep(2)
    return None


def verify() -> int:
    live = live_ids()
    conn = connect()
    try:
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '120000'")
        have = staged_ids(cur)
        missing = len(live - have)
        extra = len(have - live)
        print(f"ids: live {len(live)} | staged {len(have)} | live not staged {missing} | staged not live {extra}")
        cur.execute("SELECT ST_Y(ST_PointOnSurface(geom)), ST_X(ST_PointOnSurface(geom)) FROM lot_search_index TABLESAMPLE SYSTEM (0.05) LIMIT 1500")
        pts = cur.fetchall()
        # a third of the sample is drawn from the areas themselves, so hits are well represented
        cur.execute(f"SELECT ST_Y(ST_PointOnSurface(geom)), ST_X(ST_PointOnSurface(geom)) FROM {STAGE} TABLESAMPLE SYSTEM (0.2) LIMIT 400")
        pts_hit = cur.fetchall()
        random.Random(19).shuffle(pts)
        random.Random(19).shuffle(pts_hit)
        sample = pts[: SAMPLE_POINTS * 2 // 3] + pts_hit[: SAMPLE_POINTS // 3]
        agree = compared = own_hit_live_clear = own_clear_live_hit = 0
        for lat, lng in sample:
            live_hit = _hit_live(lat, lng)
            if live_hit is None:
                continue
            cur.execute(f"SELECT EXISTS (SELECT 1 FROM {STAGE} WHERE ST_Intersects(geom, ST_SetSRID(ST_Point(%s, %s), 4326)))", (lng, lat))
            mine = cur.fetchone()[0]
            compared += 1
            agree += mine == live_hit
            own_hit_live_clear += bool(mine) and not live_hit
            own_clear_live_hit += (not mine) and bool(live_hit)
        rate = agree / compared if compared else 0.0
        print(f"points: compared {compared} | agree {agree} ({rate:.1%}) | staged HIT but live clear {own_hit_live_clear} | staged CLEAR but live HIT {own_clear_live_hit}")
        miss_ok, bad = missing_is_acceptable(sorted(live - have))
        if bad:
            print(f"live areas not staged and accepted (no usable shape, or named as unobtainable): {bad}")
        ok = miss_ok and extra == 0 and compared >= 100 and rate >= MIN_AGREEMENT and own_clear_live_hit == 0
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        conn.close()


BACKUP_DIR = Path(__file__).resolve().parent.parent / "data" / "db_rollback_backups"


def backup_to_file(cur) -> tuple[str, int]:
    """Write every current bushfire row (with its shape as EWKT) to a CSV file on this machine BEFORE anything is deleted, and return (path, row count).
    A file, not a second table: the database server's disk is the scarce resource (a table copy ran it out of space on 2026-11-19)."""
    import csv

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"bushfire_overlay_old_{date.today():%Y%m%d}.csv"
    n = 0
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["instrument_key", "lga_name", "layer_type", "value", "value_numeric", "currency_date", "source_oid", "geom_ewkt", "synced_at"])
        cur2 = cur.connection.cursor(name="bf_backup")   # server-side cursor: rows stream, nothing is held in memory
        cur2.itersize = 2000
        cur2.execute("SELECT instrument_key, lga_name, layer_type, value, value_numeric, currency_date, source_oid, ST_AsEWKT(geom), synced_at "
                     "FROM spatial_overlays WHERE layer_type = %s", (LAYER,))
        for row in cur2:
            w.writerow(row)
            n += 1
        cur2.close()
    return str(path), n


def swap() -> int:
    live = live_ids()
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '900000'")
        have = staged_ids(cur)
        miss_ok, _bad = missing_is_acceptable(sorted(live - have))
        if not miss_ok or have - live:
            print(f"REFUSED: staging does not match the live id list (live not staged {len(live - have)}, staged not live {len(have - live)}); run stage and verify first")
            return 1
        backup, n_backup = backup_to_file(cur)
        cur.execute("DELETE FROM spatial_overlays WHERE layer_type = %s", (LAYER,))
        n_del = cur.rowcount
        cur.execute(f"""INSERT INTO spatial_overlays (instrument_key, lga_name, layer_type, value, value_numeric, currency_date, source_oid, geom, synced_at)
                        SELECT instrument_key, lga_name, layer_type, value, value_numeric, currency_date, source_oid, geom, synced_at FROM {STAGE}""")
        n_ins = cur.rowcount
        if n_del != n_backup or n_ins < (len(live) - MAX_UNSTORABLE) * 0.99:
            conn.rollback()
            print(f"ROLLED BACK: deleted {n_del} (backup {n_backup}), inserted {n_ins} (live areas {len(live)})")
            return 1
        conn.commit()
        print(f"SWAPPED: removed {n_del} old rows (kept in the file {backup}), inserted {n_ins} rows from {STAGE}")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    for arg in sys.argv[2:]:
        if arg.startswith("--accept-unobtainable="):
            ACCEPTED.update(int(x) for x in arg.split("=", 1)[1].split(",") if x.strip())
    fn = {"stage": stage, "verify": verify, "swap": swap}.get(cmd)
    if fn is None:
        sys.exit("usage: rebuild_bushfire_overlay.py stage | verify | swap")
    sys.exit(fn())
