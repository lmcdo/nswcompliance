#!/usr/bin/env python3
"""Stop serving state-law rows whose text is not the law's words (user decision 2026-10-16, option 1).

prior-art-checked: reuse not viable -- hide_unmapped_area_rules.py withholds AREA rules by moving them to an
unkeyed precinct layer; these rows are wrong WORDS, not wrong area, so they leave the served set instead
(v2_is_actionable = FALSE). Never deletes; is_current is untouched, so the row stays as history.

The list is data/state_law_paraphrase_2026-10-16.json from scripts/state_law_proof2.py: under half of the row's
5-word runs occur anywhere in the instrument in force today or at the row's own date (e.g. 'Parking spaces must
remain the same'). Some are law fragments rather than summaries; they come back one by one once read.

    python scripts/withhold_state_paraphrase.py            # dry run
    python scripts/withhold_state_paraphrase.py --apply    # backup, then update
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIST = ROOT / "data" / "state_law_paraphrase_2026-10-16.json"
BACKUP_DIR = ROOT / "data" / "db_rollback_backups"


def listed_ids(path: Path = LIST) -> list[int]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    ids = sorted({int(r["id"]) for r in rows if r.get("id") is not None})
    if not ids:
        raise SystemExit("[ABORT] the list is empty")
    return ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--list", default=str(LIST), help="paraphrase list JSON (default: the state-law list)")
    ap.add_argument("--council", default=None,
                    help="rows of this council (registry LEP rows, e.g. inner_west); default state-law rows only")
    a = ap.parse_args()
    import psycopg2
    ids = listed_ids(Path(a.list))
    who, wp = (("source_council = %s", [a.council]) if a.council else ("source_council IS NULL", []))
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = 30000")
        cur.execute("SELECT id, v2_is_actionable FROM regulatory_provisions WHERE id = ANY(%s) AND is_current"
                    f" AND {who}", [ids] + wp)
        rows = cur.fetchall()
        served = [r for r in rows if r[1]]
        if len(rows) != len(ids):
            # a mistyped --council or a stale list matches fewer rows and would otherwise "succeed" doing nothing
            raise SystemExit(f"[ABORT] {len(ids)} listed but {len(rows)} current rows match ({who}); check --council/--list")
        print(f"listed {len(ids)} | current state rows {len(rows)} | still served {len(served)}")
        if not a.apply or not served:
            print("dry run: nothing written" if not a.apply else "nothing to change")
            return 0
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        # council + microseconds: per-council runs in the same second overwrote each other's backup (2026-10-17)
        bk = BACKUP_DIR / f"withhold_{a.council or 'state'}_pre_{datetime.now():%Y-%m-%dT%H%M%S_%f}.json"
        bk.write_text(json.dumps([{"id": i, "v2_is_actionable": v} for i, v in served]), encoding="utf-8")
        cur.execute("UPDATE regulatory_provisions SET v2_is_actionable = FALSE WHERE id = ANY(%s) AND is_current"
                    f" AND {who} AND v2_is_actionable", [[r[0] for r in served]] + wp)
        if cur.rowcount != len(served):
            conn.rollback()
            raise SystemExit(f"[ROLLED BACK] updated {cur.rowcount}, expected {len(served)}")
        conn.commit()
        print(f"withheld {cur.rowcount}; backup {bk}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
