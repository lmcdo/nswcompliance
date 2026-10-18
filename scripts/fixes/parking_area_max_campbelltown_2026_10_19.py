#!/usr/bin/env python3
# prior-art-checked: one-off move of two rows; no existing script writes parking_area_max
# (the type is new in migration 115).
"""Move Campbelltown 3.6.1.4 (rows 254/255) from car_parking to parking_area_max.

The clause (Part 3 p21) caps the UNDERCOVER PARKING AREA of a dwelling house at 18 m2
(1-2 bedrooms) and 36 m2 (3+ bedrooms). The rows held it as 1 and 2 spaces/dwelling,
numbers the clause never states, so they were hidden (needs_review).

Steps, all guarded:
  1. back up both rows to data/db_rollback_backups/;
  2. apply migrations/115 if the CHECK does not yet name parking_area_max;
  3. rewrite the rows in the council's own words, label 3.6.1.4, page 21 (still hidden);
  4. prove each on the PDF page (citation_proof.prove_label) AND find its number on a p21
     line that also names its bedroom count; only then clear needs_review.
Dry run by default. --apply does 1-3 (rows stay hidden). --show does 4, and must wait until
the structured-controls route that knows parking_area_max is DEPLOYED: the old route files an
unknown type under "Other" as a minimum (">= 18 m2"), the inverse of the clause. Then run
  python scripts/dcp_setback_citation_status.py --council campbelltown --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

CHAPTER = "campbelltown-dcp-part3-low-medium"
LEAD = ("A dwelling house shall be provided with an undercover car parking area which is "
        "restricted to a maximum of: ")
ROWS = {
    254: {"value": 18, "condition": "1-2 bedrooms",
          "text": LEAD + "i) 18 m2 for 1 – 2 bedroom dwellings; and",
          "page_line": r"^18 m ?2\s+for 1 – 2 bedroom"},
    255: {"value": 36, "condition": "3 or more bedrooms",
          "text": LEAD + "ii) 36 m2 for dwellings proposing 3 or more bedrooms.",
          "page_line": r"^36 m ?2\s+for dwellings proposing 3 or more"},
}
PAGE = 21
REF = "3.6.1.4"
REASON = ("2026-10-19: moved car_parking -> parking_area_max (migration 115). PDF p21 3.6.1.4 caps "
          "the undercover parking AREA; it states no number of spaces. Number re-found on p21 and "
          "label proven before needs_review was cleared.")


def proof(readings) -> dict[int, str]:
    """Why each row may NOT be shown; an empty dict means every row passed."""
    import citation_proof as cp
    bad = {}
    for rid, r in ROWS.items():
        v = cp.prove_label(REF, r["text"], readings, PAGE)["status"]
        lines = [ln.text for cl in readings for ln in cl.lines if ln.page == PAGE]
        found = any(re.search(r["page_line"], t) for t in lines)
        if v != "proven" or not found or str(r["value"]) not in r["text"]:
            bad[rid] = f"label {v}, number line found={found}"
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="back up, migrate, move (stay hidden)")
    ap.add_argument("--show", action="store_true", help="clear needs_review after the proof")
    args = ap.parse_args()

    import boto3
    import psycopg2
    import psycopg2.extras
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parents[2] / ".env")  # a worktree reads the main checkout's .env
    import dq_probe_section_code_not_in_source as probe

    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET statement_timeout = '30000'")
    cur.execute("SELECT * FROM dcp_setback_controls WHERE id = ANY(%s) AND lga = 'campbelltown' "
                "AND source_chapter_key = %s AND is_current ORDER BY id", (list(ROWS), CHAPTER))
    before = cur.fetchall()
    if len(before) != len(ROWS):
        print(f"expected {len(ROWS)} rows, found {len(before)} -- nothing written")
        return 1

    cur.execute("SELECT r2_current_path FROM dcp_chapter_registry WHERE council = 'campbelltown' "
                "AND chapter_key = %s AND is_active", (CHAPTER,))
    r2 = cur.fetchone()["r2_current_path"]
    s3 = boto3.client(
        "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    readings = probe.chapter_lines(s3, os.environ["R2_BUCKET_NAME"], r2,
                                   Path(tempfile.gettempdir()) / "dq111_lines")
    bad = proof(readings)
    print("proof:", bad or "both rows proven on p21 with their number")
    if bad:
        return 1
    if args.show:
        cur.execute("UPDATE dcp_setback_controls SET needs_review = FALSE, reviewed_at = now(), "
                    "review_reason = %s WHERE id = ANY(%s) AND control_type = 'parking_area_max' "
                    "AND pdf_page = %s AND section_ref = %s AND is_current",
                    (REASON, list(ROWS), PAGE, REF))
        assert cur.rowcount == len(ROWS), cur.rowcount
        conn.commit()
        print(f"shown {len(ROWS)} rows; now run dcp_setback_citation_status.py --council campbelltown --apply")
        return 0
    if not args.apply:
        print("DRY RUN -- nothing written")
        return 0

    stamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    backup = ROOT / "data" / "db_rollback_backups" / f"campbelltown_parking_area_pre_{stamp}.json"
    backup.write_text(json.dumps([dict(r) for r in before], default=str, indent=2), encoding="utf-8")
    print("backup:", backup)

    cur.execute("SELECT pg_get_constraintdef(oid) d FROM pg_constraint "
                "WHERE conname = 'control_type_canonical'")
    if "'parking_area_max'" not in cur.fetchone()["d"]:
        cur.execute((ROOT / "migrations" / "115_parking_area_max_control_type.sql")
                    .read_text(encoding="utf-8").replace("BEGIN;", "").replace("COMMIT;", ""))
        conn.commit()
        print("applied migration 115")

    for rid, r in ROWS.items():
        cur.execute(
            "UPDATE dcp_setback_controls SET control_type = 'parking_area_max', value_min = %s, "
            "value_max = NULL, unit = 'm2', condition = %s, source_text = %s, section_ref = %s, "
            "pdf_page = %s, extraction_method = 'manual_curation' "
            "WHERE id = %s AND lga = 'campbelltown' AND control_type = 'car_parking' AND is_current",
            (r["value"], r["condition"], r["text"], REF, PAGE, rid))
        assert cur.rowcount == 1, rid
    conn.commit()
    print(f"moved {len(ROWS)} rows, still hidden; after the route is deployed run --show")
    return 0


if __name__ == "__main__":
    sys.exit(main())
