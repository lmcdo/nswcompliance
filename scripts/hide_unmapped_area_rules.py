#!/usr/bin/env python3
"""Withhold rules whose own words limit them to an area we have no outline for (stated exception, 2026-10-15).

prior-art-checked: reuse not viable -- derive_precinct_keys.py keys a row only TO an outline; no script sends a row
whose area is unmapped to "no house". Same end state as an unkeyed precinct row (v2_dcp_layer='precinct',
v2_precinct_id NULL, which the route serves to nobody since #1286), reached on purpose and listed.

User decision 2026-10-15: rules for small areas with no map are hidden and listed as "not covered yet", not
served council-wide. Address audit run2 found them served to houses outside the area. Never deletes a row;
backs up every changed row first. The list is data/chapter_scope/not_covered_2026-10-15.json.

    python scripts/hide_unmapped_area_rules.py            # dry run: counts
    python scripts/hide_unmapped_area_rules.py --apply    # backup, then update
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIST = REPO / "data" / "chapter_scope" / "not_covered_2026-10-15.json"
BACKUP_DIR = REPO / "data" / "db_rollback_backups"



def selectors() -> list[dict]:
    return json.loads(LIST.read_text(encoding="utf-8"))["withheld_area_rules"]


def where_for(sel: dict) -> tuple[str, list]:
    """SQL for one selector: a whole chapter, or listed row ids within it. Never an open-ended match."""
    if not sel.get("council") or not sel.get("chapter_key"):
        raise SystemExit(f"[ABORT] selector without council/chapter: {sel}")
    sql, params = "source_council = %s AND source_chapter_key = %s", [sel["council"], sel["chapter_key"]]
    if sel.get("ids"):
        sql += " AND id = ANY(%s)"
        params.append(sel["ids"])
    return sql, params


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = 30000")
        todo = []
        for sel in selectors():
            w, p = where_for(sel)
            cur.execute("SELECT id, v2_dcp_layer, v2_precinct_id FROM regulatory_provisions "
                        "WHERE is_current AND v2_is_actionable "
                        "AND (v2_provision_type IS NULL OR v2_provision_type <> 'TOC') AND " + w, p)
            rows = cur.fetchall()
            if sel.get("expect") is not None and len(rows) != sel["expect"]:
                raise SystemExit(f"[ABORT] {sel['council']}/{sel['chapter_key']}: {len(rows)} rows, list says {sel['expect']}")
            # A precinct row is already off the council-wide list: withheld (no id) or keyed to its outline by a
            # gate rule (e.g. Warringah G1 -> Dee Why). Un-keying the latter would undo that rule.
            # ... unless the entry names an outline that is too wide for these rows ("from_precinct": C-B 6.2 key
            # sites were keyed to the whole city centre): those are taken off it.
            change = [r for r in rows if r[1] != "precinct" or (sel.get("from_precinct") and r[2] == sel["from_precinct"])]
            print(f"  {sel['council']}/{sel['chapter_key']}: served {len(rows)}, to withhold {len(change)}")
            todo += change
        print(f"total to withhold: {len(todo)}")
        if not a.apply or not todo:
            print("dry run: nothing written" if not a.apply else "nothing to change")
            return 0
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        bk = BACKUP_DIR / f"hide_unmapped_area_rules_pre_{datetime.now():%Y-%m-%dT%H%M%S}.json"
        bk.write_text(json.dumps([{"id": i, "v2_dcp_layer": l, "v2_precinct_id": p} for i, l, p in todo]),
                      encoding="utf-8")
        print("backup:", bk)
        cur.execute("UPDATE regulatory_provisions SET v2_dcp_layer = 'precinct', v2_precinct_id = NULL "
                    "WHERE id = ANY(%s) AND is_current", ([t[0] for t in todo],))
        if cur.rowcount != len(todo):
            conn.rollback()
            raise SystemExit(f"[ROLLED BACK] updated {cur.rowcount}, expected {len(todo)}")
        conn.commit()
        print(f"withheld {len(todo)} rows")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
