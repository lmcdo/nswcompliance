# prior-art-checked: four sweeps 2026-11-19. (1) DB: lot_search_index.bushfire_prone (3,126,418 lots, 584,867 true, built from the 2026-04 bushfire overlay by scripts/build_lot_search_index.py step 7). (2) Frontend: reads the flag only. (3) Python: build_lot_search_index.py recomputes per council inside a full index rebuild, too slow and too broad for one flag; this recomputes ONE flag, same centroid-in-polygon rule, and writes only lots whose flag changes. (4) Plans: ce-layers-own-copy-SCOPE-2026-11-18.md.
"""Recompute lot_search_index.bushfire_prone from the rebuilt bushfire overlay. Same rule as the index builder: the lot centroid is inside a bush fire prone area.

    python scripts/rebuild_lot_bushfire_flag.py plan                  # lots per worker, nothing written
    python scripts/rebuild_lot_bushfire_flag.py run --worker 0 --of 3 # one worker; safe to stop and re-run (it resumes from its saved position)

Only lots whose flag CHANGES are written, and each one's old value is appended to a CSV in data/db_rollback_backups/ BEFORE the update, so it can be put back.
Progress prints after every batch. Lots are visited in lotidstring order, one worker per share of the first-character groups.
"""
from __future__ import annotations

import csv
import os
import sys
import time
from datetime import date
from pathlib import Path

import psycopg2

BATCH = 2000
ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / "data" / "db_rollback_backups"
STATE_DIR = Path(os.environ.get("CLAUDE_JOB_DIR", str(ROOT / "data"))) / "tmp"

_SQL_PAGE = "SELECT lotidstring FROM lot_search_index WHERE left(lotidstring, 1) = %s AND lotidstring > %s ORDER BY lotidstring LIMIT %s"
_SQL_COMPARE = """
    SELECT lsi.lotidstring, lsi.bushfire_prone, (h.hit IS TRUE) AS new_flag
    FROM lot_search_index lsi
    LEFT JOIN LATERAL (SELECT TRUE AS hit FROM spatial_overlays so
                       WHERE so.layer_type = 'bushfire' AND ST_Intersects(so.geom, ST_Centroid(lsi.geom)) LIMIT 1) h ON TRUE
    WHERE lsi.lotidstring = ANY(%s)"""


def connect():
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5)
    conn.cursor().execute("SET statement_timeout = '100000'")
    return conn


def changed_lots(rows: list[tuple]) -> list[tuple]:
    """(lotidstring, old, new) rows whose flag differs. A NULL old flag counts as False, so NULL -> False is not a change."""
    return [(lot, old, new) for lot, old, new in rows if bool(old) != bool(new)]


def first_char_groups(cur) -> list[tuple[str, int]]:
    cur.execute("SELECT left(lotidstring, 1) AS c, count(*) FROM lot_search_index GROUP BY 1 ORDER BY 1")
    return [(c, n) for c, n in cur.fetchall() if c is not None]


def split_groups(groups: list[tuple[str, int]], workers: int) -> list[list[str]]:
    """Greedy split of the first-character groups so each worker gets about the same number of lots."""
    out: list[list[str]] = [[] for _ in range(workers)]
    load = [0] * workers
    for c, n in sorted(groups, key=lambda g: -g[1]):
        i = load.index(min(load))
        out[i].append(c)
        load[i] += n
    return out


_SQL_KEYSET = "SELECT lotidstring FROM lot_search_index WHERE lotidstring > %s AND lotidstring < %s ORDER BY lotidstring LIMIT %s"


def keep_ids(ids: list[str], skip: str, only: str = "") -> list[str]:
    """Lots whose first character is not in `skip` (those groups belong to other workers); if `only` is given, just the lots whose first character is in it."""
    return [i for i in ids if i[:1] not in skip and (not only or i[:1] in only)]


def run_keyset(name: str, lo: str, hi: str, skip: str, only: str = "") -> int:
    """Walk lots in index order between lo and hi (exclusive) with plain keyset paging, which the index serves in about 0.3 s. The group workers' paging used
    left(lotidstring, 1) = c, which cannot use the index and took over 60 s. Lots in the `skip` groups are left to the group workers."""
    conn = connect()
    cur = conn.cursor()
    state = STATE_DIR / f"lot_bushfire_flag_keyset_{name}.pos"
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    pos = state.read_text(encoding="utf-8").strip() if state.exists() else lo
    backup = BACKUP_DIR / f"lot_bushfire_flag_old_{date.today():%Y%m%d}_{name}.csv"
    total = changed = 0
    t0 = time.time()
    size = BATCH
    print(f"{time.strftime('%H:%M:%S')} keyset worker {name}: from {pos!r} to {hi!r}, skipping groups {skip!r}", flush=True)
    with open(backup, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        while True:
            try:
                cur.execute(_SQL_KEYSET, (pos, hi, size))
                page = [r[0] for r in cur.fetchall()]
                if not page:
                    break
                ids = keep_ids(page, skip, only)
                diff = []
                if ids:
                    cur.execute(_SQL_COMPARE, (ids,))
                    diff = changed_lots(cur.fetchall())
                    if diff:
                        for lot, old, new in diff:
                            w.writerow([lot, old, new])
                        fh.flush()
                        os.fsync(fh.fileno())
                        cur.execute("UPDATE lot_search_index lsi SET bushfire_prone = v.new_flag FROM (SELECT unnest(%s::text[]) AS lot, unnest(%s::boolean[]) AS new_flag) v WHERE lsi.lotidstring = v.lot",
                                    ([d[0] for d in diff], [d[2] for d in diff]))
                conn.commit()
            except psycopg2.Error as exc:
                if isinstance(exc, psycopg2.errors.QueryCanceled):
                    size = max(1, size // 4)
                print(f"{time.strftime('%H:%M:%S')} keyset {name}: {type(exc).__name__} after lot {pos!r}, {total} checked; retrying with batch size {size}", flush=True)
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(10)
                conn = connect()
                cur = conn.cursor()
                continue
            pos = page[-1]
            size = min(BATCH, size * 2)
            total += len(ids)
            changed += len(diff)
            state.write_text(pos, encoding="utf-8")
            print(f"{time.strftime('%H:%M:%S')} DONE keyset {name}: at {pos!r}, {total} lots checked, {changed} flags changed, {round(time.time() - t0)} s", flush=True)
    print(f"finished keyset {name}: {total} lots checked, {changed} flags changed", flush=True)
    conn.close()
    return 0


def plan() -> int:
    conn = connect()
    groups = first_char_groups(conn.cursor())
    for w in (3,):
        parts = split_groups(groups, w)
        counts = dict(groups)
        print({i: (p, sum(counts[c] for c in p)) for i, p in enumerate(parts)})
    conn.close()
    return 0


def run(worker: int, of: int) -> int:
    conn = connect()
    cur = conn.cursor()
    mine = sorted(split_groups(first_char_groups(cur), of)[worker])
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = STATE_DIR / f"lot_bushfire_flag_worker{worker}of{of}.pos"
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"lot_bushfire_flag_old_{date.today():%Y%m%d}_w{worker}.csv"
    done = {}
    if state.exists():
        for line in state.read_text(encoding="utf-8").splitlines():
            c, _, last = line.partition("\t")
            done[c] = last
    total = changed = 0
    size = BATCH
    print(f"{time.strftime('%H:%M:%S')} worker {worker} of {of} starting: groups {mine}, resuming {done or 'from the start'}", flush=True)
    t0 = time.time()
    with open(backup, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        for c in mine:
            lo = done.get(c, c)                      # exclusive lower bound: the last lot finished in this group
            if lo == "DONE":
                continue
            while True:
                try:
                    cur.execute(_SQL_PAGE, (c, lo, size))
                    ids = [r[0] for r in cur.fetchall()]
                    if not ids:
                        break
                    cur.execute(_SQL_COMPARE, (ids,))
                    rows = cur.fetchall()
                    diff = changed_lots(rows)
                    if diff:
                        for lot, old, new in diff:   # the old value is on disk BEFORE the update
                            w.writerow([lot, old, new])
                        fh.flush()
                        os.fsync(fh.fileno())
                        cur.execute("UPDATE lot_search_index lsi SET bushfire_prone = v.new_flag FROM (SELECT unnest(%s::text[]) AS lot, unnest(%s::boolean[]) AS new_flag) v WHERE lsi.lotidstring = v.lot",
                                    ([d[0] for d in diff], [d[2] for d in diff]))
                    conn.commit()
                except psycopg2.Error as exc:
                    if isinstance(exc, psycopg2.errors.QueryCanceled):   # a batch too heavy for the time limit: retry it smaller, down to one lot
                        size = max(1, size // 4)
                    print(f"{time.strftime('%H:%M:%S')} worker {worker}: {type(exc).__name__} at group {c!r} after lot {lo!r}, {total} lots done so far; retrying with batch size {size}", flush=True)
                    try:
                        conn.close()
                    except Exception:  # noqa: BLE001
                        pass
                    time.sleep(10)
                    conn = connect()
                    cur = conn.cursor()
                    continue
                lo = ids[-1]
                size = min(BATCH, size * 2)                  # recover the batch size after a heavy stretch
                total += len(ids)
                changed += len(diff)
                done[c] = lo
                state.write_text("".join(f"{k}\t{v}\n" for k, v in done.items()), encoding="utf-8")
                print(f"{time.strftime('%H:%M:%S')} DONE worker {worker}: group {c!r} {total} lots checked, {changed} flags changed, {round(time.time() - t0)} s, batch {size}", flush=True)
            done[c] = "DONE"
            state.write_text("".join(f"{k}\t{v}\n" for k, v in done.items()), encoding="utf-8")
    print(f"finished worker {worker}: {total} lots checked, {changed} flags changed", flush=True)
    conn.close()
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["plan"]:
        sys.exit(plan())
    if args[:1] == ["keyset"]:
        def opt(k, d=""):
            return args[args.index(k) + 1] if k in args else d
        sys.exit(run_keyset(opt("--name"), opt("--lo"), opt("--hi", "􏿿"), opt("--skip"), opt("--only")))
    if args[:1] == ["run"]:
        wk = int(args[args.index("--worker") + 1]) if "--worker" in args else 0
        of = int(args[args.index("--of") + 1]) if "--of" in args else 1
        sys.exit(run(wk, of))
    print(__doc__)
    sys.exit(2)
