#!/usr/bin/env python3
# prior-art-checked: four sweeps 2026-11-21. (1) DB: nothing stores map-copy age. (2) Frontend: none. (3) Python: scripts/lmr_area/download_map_layers.py makes the copy;
# services/lmr_map_copy.py reads it and stops answering after MAX_AGE_DAYS; no script checks that the copy is still fresh or still agrees with the live maps.
# (4) Plans: ce-layers-own-copy-SCOPE-2026-11-18.md step 3 (monthly refresh + a 50-lot check), approved 2026-11-20.
"""Check our saved state maps: are they fresh and intact, and (with --compare) do they still agree with the live state maps?

    python scripts/lmr_area/check_map_copy.py                 # AGE + INTEGRITY. No network, no database. Exit 1 when a copy is within WARN_DAYS of the reader's limit, or any layer cannot be proven.
    python scripts/lmr_area/check_map_copy.py --compare 50    # also ask the live state maps about 50 random lots; exit 1 on any difference the reader would NOT send to the live map

The age check is what the data-quality ledger runs (DQ-153): it goes red WARN_DAYS before services/lmr_map_copy.py stops using the copy, which is the
reminder to refresh (python scripts/lmr_area/download_map_layers.py --apply, then --compare 50, then a pull request). The compare is part of that refresh.

A difference where the reader flags the point or lot as near a map edge is reported but not a failure: the reader sends those to the live map.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from services import lmr_area_inputs as inp  # noqa: E402
from services import lmr_map_copy as mc  # noqa: E402

WARN_DAYS = 30   # noqa: regulatory-number -- refresh reminder: red 15 days before the reader's 45-day limit, not a planning figure
COMPARED = tuple(inp.COPY_LAYERS)


def age_and_integrity(today: date | None = None, maps_dir: Path = mc.MAPS_DIR) -> tuple[bool, list[str]]:
    """(ok, lines). ok is False when the copy is old, dated in the future, unreadable, or any layer fails its hash or count."""
    today = today or date.today()
    lines: list[str] = []
    try:
        manifest = json.loads((maps_dir / "manifest.json").read_text(encoding="utf-8"))
        read_on = datetime.strptime(str(manifest.get("read_on")), "%Y-%m-%d").date()
    except (OSError, ValueError) as exc:
        return False, [f"RED: manifest unreadable ({exc})"]
    age = (today - read_on).days
    ok = True
    if age < 0:
        ok = False
        lines.append(f"RED: copy read_on {read_on} is in the future")
    elif age >= WARN_DAYS:
        ok = False
        lines.append(f"RED: copy is {age} days old (read {read_on}); the reader stops using it at {mc.MAX_AGE_DAYS} days. Refresh now.")
    else:
        lines.append(f"copy read {read_on}, {age} days old (reader limit {mc.MAX_AGE_DAYS}, reminder at {WARN_DAYS})")
    reader = mc.MapCopy(maps_dir)
    for key, name in mc.COPY_KEYS.items():
        # today=read_on makes the age test pass so this isolates the hash and count proof
        if reader.layer(name, today=read_on) is None:
            ok = False
            lines.append(f"RED: layer {name} ({key}) fails its hash or feature count")
    if ok:
        lines.append(f"all {len(mc.COPY_KEYS)} layers load, hash and count match the manifest")
    return ok, lines


def _sample_lots(n: int, seed: int) -> list[dict]:
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c default_transaction_read_only=on -c statement_timeout=30000")
    try:
        cur = conn.cursor()
        cur.execute("SELECT ST_Y(ST_Centroid(geom)), ST_X(ST_Centroid(geom)), ST_AsGeoJSON(geom) FROM lot_search_index "
                    "TABLESAMPLE SYSTEM (0.01) REPEATABLE (%s) LIMIT %s", (seed, n * 3))
        rows = cur.fetchall()
    finally:
        conn.close()
    out = []
    for lat, lng, gj in rows:
        g = json.loads(gj)
        coords = g["coordinates"][0] if g.get("type") == "Polygon" else (g["coordinates"][0][0] if g.get("type") == "MultiPolygon" else None)  # noqa: bracket-access -- shape just checked
        if coords:
            out.append({"lat": lat, "lng": lng, "rings": [[x, y] for x, y in coords]})
    random.Random(seed).shuffle(out)
    return out[:n]


def compare(n: int, seed: int) -> tuple[bool, list[str]]:
    from concurrent.futures import ThreadPoolExecutor

    lots = _sample_lots(n, seed)
    if len(lots) < n:
        return False, [f"RED: only {len(lots)} lots could be sampled, wanted {n}"]

    def one(lot: dict):
        return [(k, lot, inp._layer(k, lot["lat"], lot["lng"], lot["rings"]), mc.check(k, lot["lat"], lot["lng"], lot["rings"])) for k in COMPARED]

    res = []
    with ThreadPoolExecutor(4) as ex:
        for i, r in enumerate(ex.map(one, lots), 1):
            res.extend(r)
            if i % 10 == 0 or i == len(lots):
                print(f"DONE {i}/{len(lots)}", flush=True)
    agree = edge = live_none = copy_none = 0
    bad: list[str] = []
    for key, lot, live, cp in res:
        if cp is None:
            copy_none += 1
            continue
        for part in ("point", "lot"):
            lv, cv = live.get(part), cp.get(part)
            if lv is None:
                live_none += 1
            elif lv == cv:
                agree += 1
            elif cp.get("near_edge"):
                edge += 1
            else:
                bad.append(f"RED: {key} {part} copy={cv} live={lv} at {lot['lat']:.6f},{lot['lng']:.6f}")
    lines = [f"{len(lots)} lots x {len(COMPARED)} layers: {agree} agree, {edge} differ near an edge (sent to live), "
             f"{live_none} live no answer, {copy_none} copy no answer, {len(bad)} unflagged differences"] + bad[:20]
    return not bad and copy_none == 0, lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", type=int, default=0, metavar="N", help="also compare N random lots with the live state maps")
    ap.add_argument("--seed", type=int, default=int(date.today().strftime("%Y%m%d")))
    a = ap.parse_args()
    ok, lines = age_and_integrity()
    for ln in lines:
        print(ln)
    if a.compare:
        try:
            from dotenv import load_dotenv
            load_dotenv(REPO / ".env")
        except ImportError:
            pass
        ok2, more = compare(a.compare, a.seed)
        for ln in more:
            print(ln)
        ok = ok and ok2
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
