#!/usr/bin/env python3
"""DQ-88 2026-11-25: bring served SEPP rows in line with the law in force, row by row, with history.

prior-art-checked: reuse, not a new method -- the version-history writer is imported from
scripts/dq88_refresh_2026_10_10.py (it gained two optional arguments); this applies a reviewed plan.

The plan (data/dq88_law_refresh_plan_2026-11-25.json) was built by taking each stored row that holds wording
the law has since removed (an 8-word run that was in the old law and is nowhere in today's) and placing it in
today's text of the whole instrument (read in Chrome on legislation.nsw.gov.au, which refuses scripts from this PC):
  REPLACE  (proved in the same transaction: migration 113) today's text, word for word, is the row's own span: at least 90% of the row's words match, anchored at
           both ends, 0.85-1.25x the stored length, and no removed wording is left in it
  RETIRE   at most 30% of the row's wording is anywhere in today's law, so the row states law that no longer exists
Rows the plan could not place safely are not in it; they stay flagged for a person (DQ-88).

Each row is refused unless its stored text is still exactly the text the plan was built from.

    python scripts/dq88_apply_law_refresh.py [PLAN.json]            # dry run: rolled back
    python scripts/dq88_apply_law_refresh.py [PLAN.json] --apply
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import psycopg2

sys.path.insert(0, os.path.dirname(__file__))
from dq88_refresh_2026_10_10 import version  # noqa: E402

PLAN = os.path.join(os.path.dirname(__file__), "..", "data", "dq88_law_refresh_plan_2026-11-25.json")
DETECTED = "paragraph comparison of in-force text on legislation.nsw.gov.au, placed by word alignment (scripts/dq88_apply_law_refresh.py)"
ACTIONS = ("REPLACE", "RETIRE")
# The document_id of each instrument's stored rows: a plan row whose id belongs to another instrument is refused.
DOC_LIKE = {"housing": "%Housing%", "exempt": "%Exempt%Complying%", "industry": "%Industry%Employment%", "planning": "%Planning%Systems%",
            "transport": "%Transport%Infrastructure%", "biodiversity": "%Biodiversity%"}


def run(conn, apply: bool, path: str = PLAN) -> int:
    plan = json.load(open(path, encoding="utf-8"))
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    done = {a: 0 for a in ACTIONS}
    for p in plan:
        if p["action"] not in ACTIONS:
            sys.exit(f"{p['id']}: unknown action {p['action']!r} -- refusing")
        if p["action"] == "REPLACE" and not p.get("new_text"):
            sys.exit(f"{p['id']}: REPLACE with no new text -- refusing")
        if p["action"] == "REPLACE" and p.get("verbatim_in_law") is not True:
            sys.exit(f"{p['id']}: REPLACE not marked as checked word for word against the law in force -- refusing")
        src = f"https://legislation.nsw.gov.au/view/whole/html/inforce/current/{p['epi']}"
        ref = f"Changed between the version in force on {p['baseline']} and the version in force on 25 Nov 2026."
        if p["sepp"] not in DOC_LIKE:
            sys.exit(f"{p['id']}: unknown instrument {p['sepp']!r} -- refusing")
        # FOR UPDATE: the row stays locked from this check through version(), so nobody can edit it in between.
        cur.execute("SELECT provision_text, is_current, document_id ILIKE %s FROM regulatory_provisions WHERE id = %s FOR UPDATE",
                    (DOC_LIKE[p["sepp"]], p["id"]))
        row = cur.fetchone()
        if row is None or not row[1] or row[0] != p["old_text"]:
            sys.exit(f"{p['id']}: stored text is not what the plan was built from -- refusing")
        if not row[2]:
            sys.exit(f"{p['id']}: the row does not belong to {p['sepp']} -- refusing")
        note = "Text as stored before the 2026-11-25 refresh from the law in force."
        if p["action"] == "RETIRE":
            version(cur, p["id"], None, src, ref, "Retired: the law in force no longer contains this wording.", now, note, DETECTED)
        else:
            version(cur, p["id"], p["new_text"], src, ref, "Replaced with the text in force, word for word.", now, note, DETECTED)
            # Migration 113 (DQ-145): new state-law text is served only with its proof, in the same transaction. The text was checked
            # to be inside the whole instrument in force; a new source path and time are required or the proof is voided.
            cur.execute("UPDATE regulatory_provisions SET citation_status = 'proven', citation_source_path = %s, citation_checked_at = %s WHERE id = %s",
                        (src + "#in-force-2026-11-25", now, p["id"]))
        done[p["action"]] += 1
    print(f"{len(plan)} rows: {done}")
    (conn.commit if apply else conn.rollback)()
    print("COMMITTED" if apply else "ROLLED BACK (dry run)")
    return 0


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))
    load_dotenv()
    path = next((x for x in sys.argv[1:] if x.endswith(".json")), PLAN)
    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=120000")
    try:
        return run(conn, "--apply" in sys.argv, path)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
