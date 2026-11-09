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
  python scripts/load_project_brief.py picks.jsonl --replace-cells --apply --confirm-production-write --backup-to backup.json

--replace-cells: the file is the WHOLE answer for every (council, zone_group, dev_type, row_type) cell it names. Each such cell's
existing rows are deleted and the file's rows inserted, in one transaction, after the old rows are saved to --backup-to (required to
apply). A cell with no pick is named by a line {"council":..., "zone_group":..., "dev_type":..., "row_type":..., "empty": true}.
Without it the loader only adds or overwrites rank by rank, so it can never remove a weaker old row or empty a cell.

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


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)    # 1.9 is not rank 1 and True is not rank 1: no silent truncation


def _valid_pick(r):
    return bool(r["zone_group"] in ZONES and r["dev_type"] in DEV_TYPES and r["row_type"] in ROW_TYPES
                and _is_int(r["rank"]) and 1 <= r["rank"] <= 5 and r["verdict"] in ("APPLIES", "MIGHT")
                and _is_int(r["provision_id"]) and r["provision_id"] > 0 and r["council"])


def _valid_cell(r):
    # an empty-cell line names a cell and nothing else: one that also carries pick fields would silently drop that pick
    return bool(r["zone_group"] in ZONES and r["dev_type"] in DEV_TYPES and r["row_type"] in ROW_TYPES and r["council"]
                and not any(k in r for k in ("rank", "provision_id", "verdict", "reason")))


def cell_key(r):
    return (r["council"], r["zone_group"], r["dev_type"], r["row_type"])


def read_cells(path):
    """(picks, empty_cells, bad_line_numbers) for --replace-cells: a pick line, or an {"empty": true} line naming a cell with no pick."""
    picks, empties, bad = [], [], []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if r.get("empty") is True:
                    (empties if _valid_cell(r) else bad).append(r if _valid_cell(r) else n)
                else:
                    (picks if _valid_pick(r) else bad).append(r if _valid_pick(r) else n)
            except Exception:
                bad.append(n)
    return picks, empties, bad


def replace_problems(picks, empties):
    """Reasons a replace file cannot be applied as written: ranks must run 1..n inside each cell, a cell cannot be both picked and empty,
    and no cell may be named twice as empty."""
    problems, ranks = [], collections.defaultdict(list)
    for r in picks:
        ranks[cell_key(r)].append(int(r["rank"]))
    for k, rk in ranks.items():
        if sorted(rk) != list(range(1, len(rk) + 1)):
            problems.append("ranks in %s are %s: they must run 1..%d with no gap or repeat" % ("/".join(k), sorted(rk), len(rk)))
    seen = set()
    for e in empties:
        k = cell_key(e)
        if k in ranks:
            problems.append("%s is named empty and also has picks" % "/".join(k))
        if k in seen:
            problems.append("%s is named empty twice" % "/".join(k))
        seen.add(k)
    return problems


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
    ap.add_argument("--replace-cells", action="store_true", help="the file is the whole answer for every cell it names (see the module doc)")
    ap.add_argument("--backup-to", help="where --replace-cells saves the rows it is about to delete (required to apply)")
    a = ap.parse_args()
    writing = a.apply and a.confirm_production_write
    if a.apply and not a.confirm_production_write:
        sys.exit("--apply also needs --confirm-production-write. Nothing written.")
    if a.replace_cells and a.remove_build:
        sys.exit("--replace-cells and --remove-build are separate operations. Nothing written.")
    if writing and a.replace_cells and not a.backup_to:
        sys.exit("--replace-cells --apply also needs --backup-to <file>: the rows it deletes are saved there first. Nothing written.")

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
    if a.replace_cells:
        return _replace_cells(conn, cur, a, writing)
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


def _replace_cells(conn, cur, a, writing):
    """--replace-cells: the file is the whole answer for each cell it names. Dry run unless writing; writing saves the old rows first.

    prior-art-checked: extends this loader, the only writer of project_brief_rows; the files the guard listed (delete_orphaned_provisions,
    enrichment/pipeline, add_new_chapter, legislation_monitor) write other tables, and none can empty a brief cell or save its old rows.
    """
    picks, empties, bad = read_cells(a.file)
    print("lines read: %d picks, %d empty-cell markers, %d invalid lines %s" % (len(picks), len(empties), len(bad), bad[:10]))
    if bad:
        sys.exit("invalid lines: a replace must not run on a partly read file. Nothing written.")
    if not picks and not empties:
        sys.exit("nothing to replace")
    problems = replace_problems(picks, empties)
    if problems:
        sys.exit("cannot apply as written:\n  " + "\n  ".join(problems) + "\nNothing written.")

    # every pick must exist, be current + actionable and belong to its council: a pick that fails would empty its cell
    ids = sorted({int(r["provision_id"]) for r in picks})
    ok_ids = {}
    for i in range(0, len(ids), 5000):
        cur.execute("SELECT id, source_council FROM regulatory_provisions WHERE id = ANY(%s) AND is_current AND v2_is_actionable", (ids[i:i + 5000],))
        ok_ids.update({r[0]: r[1] for r in cur.fetchall()})
    unfit = [r for r in picks if ok_ids.get(int(r["provision_id"])) != r["council"]]
    if unfit:
        sys.exit("%d picks name a clause that is missing, not current, or from another council (first: %s). A replace would empty their cells. Nothing written."
                 % (len(unfit), unfit[0]))

    keys = sorted({cell_key(r) for r in picks} | {cell_key(e) for e in empties})
    cur.execute("SELECT id, council, zone_group, dev_type, row_type, rank, provision_id, verdict, reason, build_id, built_at FROM project_brief_rows "
                "WHERE (council, zone_group, dev_type, row_type) IN %s ORDER BY council, zone_group, dev_type, row_type, rank", (tuple(keys),))
    cols = [d[0] for d in cur.description]
    old = cur.fetchall()
    print("cells to replace: %d (%d with picks, %d empty) | existing rows to delete: %d | rows to insert: %d" % (len(keys), len(keys) - len(empties), len(empties), len(old), len(picks)))
    print("by council (existing -> new):", {c: "%d -> %d" % (sum(1 for o in old if o[1] == c), sum(1 for p in picks if p["council"] == c)) for c in sorted({k[0] for k in keys})})

    build_id = "strict-picks-" + datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    if not writing:
        print("DRY RUN: would replace %d cells as build %s. Nothing written." % (len(keys), build_id))
        return
    # the old rows are saved before anything is deleted; a short file stops the run
    saved = [dict(zip(cols, [str(v) if hasattr(v, "isoformat") else v for v in row])) for row in old]
    with open(a.backup_to, "w", encoding="utf-8") as fh:
        json.dump(saved, fh, ensure_ascii=False, indent=1)
    with open(a.backup_to, encoding="utf-8") as fh:
        if len(json.load(fh)) != len(old):
            sys.exit("the backup did not save every row. Nothing deleted.")
    print("backup saved:", a.backup_to, "(%d rows)" % len(old))
    try:
        cur.execute("SET LOCAL statement_timeout = '60000'")
        cur.execute("DELETE FROM project_brief_rows WHERE (council, zone_group, dev_type, row_type) IN %s", (tuple(keys),))
        if cur.rowcount != len(old):
            raise RuntimeError("deleted %d rows but the backup holds %d" % (cur.rowcount, len(old)))
        for i in range(0, len(picks), BATCH):
            chunk = picks[i:i + BATCH]
            args = b",".join(cur.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s,%s)", (
                r["council"], r["zone_group"], r["dev_type"], r["row_type"], int(r["rank"]), int(r["provision_id"]), r["verdict"], (r.get("reason") or "")[:200], build_id)) for r in chunk)
            cur.execute(b"INSERT INTO project_brief_rows (council,zone_group,dev_type,row_type,rank,provision_id,verdict,reason,build_id) VALUES " + args)
        cur.execute("SELECT count(*) FROM project_brief_rows WHERE (council, zone_group, dev_type, row_type) IN %s", (tuple(keys),))
        n = cur.fetchone()[0]
        if n != len(picks):
            raise RuntimeError("after the swap the cells hold %d rows, expected %d" % (n, len(picks)))
        conn.commit()
        print("committed build %s: deleted %d, inserted %d" % (build_id, len(old), len(picks)))
    except Exception:
        conn.rollback()
        raise


if __name__ == "__main__":
    main()
