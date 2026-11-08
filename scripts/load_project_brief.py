#!/usr/bin/env python3
"""Load the precomputed project brief rows into project_brief_rows (migration 123).

prior-art-checked: no existing loader writes project_brief_rows. Follows the house pattern of the other loaders:
DRY-RUN BY DEFAULT, one build_id per load (so a bad load can be removed with --remove-build), batched inserts,
every provision id checked against regulatory_provisions before anything is written.

Input: a JSONL file, one row per line:
  {"council": "hornsby", "zone_group": "R2", "dev_type": "dual_occupancy", "row_type": "front_setback",
   "rank": 1, "provision_id": 262216, "verdict": "MIGHT", "reason": "..."}

Usage
  python scripts/load_project_brief.py briefs.jsonl                      # dry run: validates and prints counts, writes nothing
  python scripts/load_project_brief.py briefs.jsonl --apply --confirm-production-write
  python scripts/load_project_brief.py --remove-build <build_id> --apply --confirm-production-write

This is a PRODUCTION WRITE when applied. It needs the owner's go; the migration (123_project_brief_rows.sql) must already be applied.
"""
import argparse
import collections
import datetime
import json
import os
import sys

ZONES = {"R2", "R3", "R4", "B", "ANY"}  # noqa: zone-codes -- the brief build's own group labels (project_brief_rows.zone_group)
DEV_TYPES = {"dwelling_house", "dual_occupancy", "secondary_dwelling", "multi_dwelling_housing", "residential_flat_building", "shop_top_housing"}
ROW_TYPES = {"front_setback", "side_setback", "rear_setback", "secondary_street_setback", "car_parking", "landscaping_min",
             "deep_soil_min", "private_open_space", "max_site_coverage", "max_height"}
BATCH = 500


def read_rows(path):
    rows, bad = [], []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                ok = (r["zone_group"] in ZONES and r["dev_type"] in DEV_TYPES and r["row_type"] in ROW_TYPES
                      and 1 <= int(r["rank"]) <= 5 and r["verdict"] in ("APPLIES", "MIGHT") and int(r["provision_id"]) > 0 and r["council"])
            except Exception:
                ok = False
            (rows if ok else bad).append(r if ok else n)
    return rows, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--confirm-production-write", action="store_true")
    ap.add_argument("--remove-build")
    a = ap.parse_args()
    writing = a.apply and a.confirm_production_write
    if a.apply and not a.confirm_production_write:
        sys.exit("--apply also needs --confirm-production-write. Nothing written.")

    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        _run(conn, a, writing)
    finally:
        conn.close()


def _run(conn, a, writing):
    conn.set_session(readonly=not writing)
    cur = conn.cursor()
    cur.execute("SELECT current_database()")
    print("database:", cur.fetchone()[0], "| mode:", "WRITE" if writing else "dry run (read-only)")
    cur.execute("SELECT to_regclass('public.project_brief_rows')")
    if cur.fetchone()[0] is None:
        sys.exit("project_brief_rows does not exist: migration 123 has not been applied. Nothing to do.")

    if a.remove_build:
        cur.execute("SELECT count(*) FROM project_brief_rows WHERE build_id = %s", (a.remove_build,))
        n = cur.fetchone()[0]
        print("rows in build %s: %d" % (a.remove_build, n))
        if writing:
            cur.execute("DELETE FROM project_brief_rows WHERE build_id = %s", (a.remove_build,))
            conn.commit(); print("removed", n)
        return

    if not a.file:
        sys.exit("give the JSONL file")
    rows, bad = read_rows(a.file)
    print("rows read: %d valid, %d invalid lines %s" % (len(rows), len(bad), bad[:10]))
    if not rows:
        sys.exit("nothing valid to load")

    # every provision must exist and be current + actionable, and belong to the row's council
    ids = sorted({int(r["provision_id"]) for r in rows})
    ok_ids = {}
    for i in range(0, len(ids), 5000):
        cur.execute("SELECT id, source_council FROM regulatory_provisions WHERE id = ANY(%s) AND is_current AND v2_is_actionable", (ids[i:i + 5000],))
        ok_ids.update({r[0]: r[1] for r in cur.fetchall()})
    keep = [r for r in rows if ok_ids.get(int(r["provision_id"])) == r["council"]]
    print("rows whose clause exists, is current and belongs to the council: %d of %d" % (len(keep), len(rows)))
    seen, dup = set(), 0
    uniq = []
    for r in keep:
        k = (r["council"], r["zone_group"], r["dev_type"], r["row_type"], int(r["rank"]))
        if k in seen:
            dup += 1; continue
        seen.add(k); uniq.append(r)
    print("duplicate keys dropped: %d | rows to load: %d" % (dup, len(uniq)))
    per = collections.Counter(r["council"] for r in uniq)
    print("by council:", dict(per))

    build_id = "applies-when-" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    if not writing:
        print("DRY RUN: would insert %d rows as build %s. Nothing written." % (len(uniq), build_id)); return
    try:
        cur.execute("SET LOCAL statement_timeout = '60000'")
        for i in range(0, len(uniq), BATCH):
            chunk = uniq[i:i + BATCH]
            args = b",".join(cur.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s,%s)", (
                r["council"], r["zone_group"], r["dev_type"], r["row_type"], int(r["rank"]), int(r["provision_id"]), r["verdict"], (r.get("reason") or "")[:200], build_id)) for r in chunk)
            cur.execute(b"INSERT INTO project_brief_rows (council,zone_group,dev_type,row_type,rank,provision_id,verdict,reason,build_id) VALUES " + args +
                        b" ON CONFLICT (council,zone_group,dev_type,row_type,rank) DO UPDATE SET provision_id=EXCLUDED.provision_id, verdict=EXCLUDED.verdict, reason=EXCLUDED.reason, build_id=EXCLUDED.build_id, built_at=now()")
            print("DONE %d/%d" % (min(i + BATCH, len(uniq)), len(uniq)), flush=True)
        conn.commit()
        print("committed build", build_id)
    except Exception:
        conn.rollback(); raise


if __name__ == "__main__":
    main()
