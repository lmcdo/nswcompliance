#!/usr/bin/env python3
"""DQ-88: bring three SEPPs' stored text in line with the law in force, row by row, with history.

prior-art-checked: reuse, not a new method -- the version-history writer is imported from
scripts/dq88_refresh_2026_10_10.py; this applies a reviewed plan to many rows instead of five.

The Biodiversity and Conservation, Planning Systems, and Transport and Infrastructure SEPPs were
loaded from PDFs dated 7 Mar / 11 Jul / 15 Aug 2025 and never registered with the legislation
monitor until 2026-10-05 (DQ-130), so the 2026-09-15 refresh never covered them. The plan
(data/dq88_sepp_refresh_plan_2026-10-10.json) was built by aligning each instrument's in-force
text on those dates with today's (scripts/law_change_diff.py, Fly IP), paragraph by paragraph:
  RETIRE           every law paragraph the row came from is gone from today's text
                   (checked against the WHOLE current instrument, not just the aligned region)
  REPLACE          each paragraph pairs with exactly one current paragraph (>= 60% similar) and
                   the new text is 0.6-1.6x the stored length; new text is today's, verbatim
  REPLACE_PARTIAL  as REPLACE, but some of the row's paragraphs were repealed and are dropped
Rows the plan could not settle (size mismatch, ambiguous location) are not in it.

Each row is refused unless its stored text is still exactly the text the plan was built from.

    python scripts/dq88_sepp_bulk_refresh.py [PLAN.json]            # dry run: rolled back
    python scripts/dq88_sepp_bulk_refresh.py [PLAN.json] --apply
A second plan (data/dq88_sepp_refresh_plan2_2026-10-10.json) holds the rows a reader placed in
today's text by paragraph number; each passed a mechanical check before it was written: a
retirement only where at most 20% of the stored 8-word runs remain anywhere in the law, a
replacement only where the new text is >= 50-60% word-similar and 0.5-2x the stored length.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import psycopg2

sys.path.insert(0, os.path.dirname(__file__))
from dq88_refresh_2026_10_10 import version  # noqa: E402

PLAN = os.path.join(os.path.dirname(__file__), "..", "data", "dq88_sepp_refresh_plan_2026-10-10.json")
SRC = {"Biodiversity": ("epi-2021-0722", "7 Mar 2025"), "Planning Systems": ("epi-2021-0724", "11 Jul 2025"),
       "Transport": ("epi-2021-0732", "15 Aug 2025")}


def run(conn, apply: bool) -> int:
    path = next((x for x in sys.argv[1:] if x.endswith(".json")), PLAN)
    plan = json.load(open(path, encoding="utf-8"))
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    done = {"RETIRE": 0, "REPLACE": 0, "REPLACE_PARTIAL": 0}
    for p in plan:
        epi, since = SRC[p["sepp"]]
        src = f"https://legislation.nsw.gov.au/view/whole/html/inforce/current/{epi}"
        ref = f"Changed between the version in force on {since} and the version in force on 10 Oct 2026."
        cur.execute("SELECT provision_text, is_current FROM regulatory_provisions WHERE id = %s", (p["id"],))
        row = cur.fetchone()
        if row is None or not row[1] or row[0] != p["old_text"]:
            sys.exit(f"{p['id']}: stored text is not what the plan was built from -- refusing")
        if p["action"] == "RETIRE":
            version(cur, p["id"], None, src, ref, "Repealed: no paragraph of this text is in the law in force.", now)
        else:
            why = ("Replaced with the text in force." if p["action"] == "REPLACE"
                   else "Replaced with the text in force; repealed paragraphs dropped.")
            version(cur, p["id"], p["new_text"], src, ref, why, now)
        done[p["action"]] += 1
    print(f"{len(plan)} rows: {done}")
    (conn.commit if apply else conn.rollback)()
    print("COMMITTED" if apply else "ROLLED BACK (dry run)")
    return 0


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))
    load_dotenv()
    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=120000")
    try:
        return run(conn, "--apply" in sys.argv)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
