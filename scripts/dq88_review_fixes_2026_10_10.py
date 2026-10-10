#!/usr/bin/env python3
"""DQ-88: correct the SEPP rows a second review of the 2026-10-10 refresh found wrong, with history.

prior-art-checked: reuse, not a new method -- the plan format and the stale-text refusal are
scripts/dq88_sepp_bulk_refresh.py's, and a row with no history goes through the same
dq88_refresh_2026_10_10.version writer. The only new piece is the next-version writer: five of
these rows were already versioned by that refresh (v1/v2), and provision_versions is unique on
(provision_id, version_number), so they take v3.

What the review found (Sol cross-review of #1250 plus a figure-by-figure check of every served
row against the in-force text, 2026-10-10):
  - the refresh dropped a still-current limb (34927), replaced a definition with an unrelated one
    (42131), and stored three spans that began mid-word (35436, 42118, 44557);
  - it compared rows with the law's CHANGES, so text already out of date in the source PDF was
    never looked at: Transport SEPP Sch 7 cl 2 and cl 4 (45825, 45830, 45832) and the repealed
    ss 2.47, 2.48, 2.102 and 2.122A (43677, 43683, 43685, 44073, 44209);
  - two served table rows carry a scan error, 90mm for the law's 900mm (46345, 46346).
Data: data/dq88_review_fixes_2026-10-10.json (each new text is today's, verbatim).

    python scripts/dq88_review_fixes_2026_10_10.py            # dry run: rolled back
    python scripts/dq88_review_fixes_2026_10_10.py --apply
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import psycopg2

sys.path.insert(0, os.path.dirname(__file__))
from dq88_refresh_2026_10_10 import DETECTED, sha, version  # noqa: E402

PLAN = os.path.join(os.path.dirname(__file__), "..", "data", "dq88_review_fixes_2026-10-10.json")
EPI = {"Biodiversity": "epi-2021-0722", "Planning Systems": "epi-2021-0724", "Transport": "epi-2021-0732"}
REF = "Second review of the 2026-10-10 refresh against the version in force on 10 Oct 2026."


def next_version(cur, pid: int, text_after: str | None, src: str, why: str, now: datetime) -> None:
    """Add one version after the row's latest, close the latest, log the change, update the row."""
    cur.execute("SELECT max(version_number) FROM provision_versions WHERE provision_id = %s", (pid,))
    last = cur.fetchone()[0]
    cur.execute("SELECT id, provision_text FROM provision_versions WHERE provision_id = %s AND version_number = %s",
                (pid, last))
    prev_id, prev_text = cur.fetchone()
    cur.execute("SELECT text_hash FROM regulatory_provisions WHERE id = %s AND is_current FOR UPDATE", (pid,))
    locked = cur.fetchone()
    if locked is None:
        sys.exit(f"{pid}: no longer current -- refusing")
    md5_set = locked[0]
    cur.execute("UPDATE provision_versions SET effective_to = %s WHERE id = %s AND effective_to IS NULL",
                (now, prev_id))
    kind = "deleted" if text_after is None else "modified"
    body = prev_text if text_after is None else text_after
    cur.execute("INSERT INTO provision_versions (provision_id, version_number, provision_text, effective_from, "
                "change_type, change_summary, text_hash, extracted_from_document, extraction_date, extraction_method) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'legislation.nsw.gov.au in-force HTML, verbatim') "
                "RETURNING id", (pid, last + 1, body, now, kind, why, sha(body), src, now))
    new_id = cur.fetchone()[0]
    cur.execute("INSERT INTO provision_change_log (provision_id, version_from, version_to, change_type, fields_changed, "
                "changed_at, triggered_by_document, amendment_reference, change_reason, detected_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (pid, prev_id, new_id, kind, ["is_current"] if text_after is None else ["provision_text"], now, src,
                 REF, why, DETECTED))
    if text_after is None:
        cur.execute("UPDATE regulatory_provisions SET is_current = FALSE, current_version_id = %s, version_count = %s "
                    "WHERE id = %s", (new_id, last + 1, pid))
    else:
        cur.execute("UPDATE regulatory_provisions SET provision_text = %s, current_version_id = %s, version_count = %s, "
                    "text_hash_current = %s, text_hash = %s WHERE id = %s",
                    (text_after, new_id, last + 1, sha(text_after),
                     hashlib.md5(text_after.encode("utf-8")).hexdigest() if md5_set else None, pid))


def run(conn, apply: bool) -> int:
    plan = json.load(open(PLAN, encoding="utf-8"))
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    done = {"RETIRE": 0, "REPLACE": 0}
    for p in plan:
        src = f"https://legislation.nsw.gov.au/view/whole/html/inforce/current/{EPI[p['sepp']]}"
        cur.execute("SELECT provision_text, is_current FROM regulatory_provisions WHERE id = %s", (p["id"],))
        row = cur.fetchone()
        if row is None or not row[1] or row[0] != p["old_text"]:
            sys.exit(f"{p['id']}: stored text is not what the plan was built from -- refusing")
        cur.execute("SELECT count(*) FROM provision_versions WHERE provision_id = %s", (p["id"],))
        if cur.fetchone()[0]:
            next_version(cur, p["id"], p["new_text"], src, p["why"], now)
        else:
            version(cur, p["id"], p["new_text"], src, REF, p["why"], now)
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
