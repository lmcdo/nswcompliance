#!/usr/bin/env python3
"""Revert ONE re-copied state-law row to its backed-up text, label and citation status, as a new version.

prior-art-checked: dq88_refresh_2026_10_10.version writes only v1/v2 (a first change); a row already at v2 needs v3.
Used 2026-10-17 for row 45999, whose schedule had been chosen by the withdrawn neighbour-label tie-break.

    python scripts/revert_row_from_backup.py 45999 data/db_rollback_backups/sepp_marker_blind_pre_2026-10-17T164627.json \
        --expect-ref "Schedule 12, section 28"            # dry run
    ... --apply                                           # backup, then write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state_law_proof import ROOT, connect  # noqa: E402

BACKUPS = ROOT / "data" / "db_rollback_backups"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("id", type=int)
    ap.add_argument("backup")
    ap.add_argument("--expect-ref", required=True, help="the row's CURRENT ref_number; refuses if it differs")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    prior = [x for x in json.loads(Path(a.backup).read_text(encoding="utf-8")) if x["id"] == a.id]
    if len(prior) != 1:
        print(f"REFUSING: {a.id} is not in {a.backup}")
        return 1
    b = prior[0]
    conn = connect()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 30000")
    cur.execute("SELECT provision_text, ref_number, citation_status, citation_source_path, version_count, "
                "current_version_id, text_hash, text_hash_current, source_council FROM regulatory_provisions "
                "WHERE id = %s AND is_current", (a.id,))
    row = cur.fetchone()
    if row is None or row[1] != a.expect_ref or row[8] is not None:
        print(f"REFUSING: {a.id} is not current state law with ref_number {a.expect_ref!r} (found {row and row[1]!r})")
        return 1
    cur.execute("SELECT max(version_number) FROM provision_versions WHERE provision_id = %s", (a.id,))
    vmax = cur.fetchone()[0] or 0
    print(f"{a.id}: {row[1]!r} -> {b['ref_number']!r}; citation {row[2]!r} -> {b['citation_status']!r}; "
          f"text {len(row[0])} -> {len(b['provision_text'])} chars; new version {vmax + 1}")
    if not a.apply:
        print("DRY RUN -- nothing written. Re-run with --apply.")
        return 0
    back = BACKUPS / f"revert_{a.id}_pre_{datetime.now():%Y-%m-%dT%H%M%S_%f}.json"
    back.write_text(json.dumps({"id": a.id, "provision_text": row[0], "ref_number": row[1], "citation_status": row[2],
                                "citation_source_path": row[3], "version_count": row[4], "current_version_id": row[5],
                                "text_hash": row[6], "text_hash_current": row[7]}, indent=1, default=str),
                    encoding="utf-8")
    print(f"backup: {back.relative_to(ROOT)}")
    conn.rollback()
    conn.autocommit = True
    cur.execute("SET default_transaction_read_only = off")
    conn.autocommit = False
    now = datetime.now(timezone.utc)
    old = b["provision_text"]
    why = ("Reverted: the row's schedule was chosen from neighbouring row labels, and row order is not document "
           "order (cross-review 2026-10-17).")
    cur.execute("SELECT id FROM provision_versions WHERE provision_id = %s ORDER BY version_number DESC LIMIT 1", (a.id,))
    prev = cur.fetchone()
    cur.execute("INSERT INTO provision_versions (provision_id, version_number, provision_text, effective_from, "
                "change_type, change_summary, text_hash, extraction_date, extraction_method) "
                "VALUES (%s, %s, %s, %s, 'modified', %s, %s, %s, 'revert to the backed-up text') RETURNING id",
                (a.id, vmax + 1, old, now, why, hashlib.sha256(old.encode()).hexdigest(), now))
    vnew = cur.fetchone()[0]
    cur.execute("INSERT INTO provision_change_log (provision_id, version_from, version_to, change_type, fields_changed, "
                "changed_at, change_reason, detected_by) VALUES (%s, %s, %s, 'modified', %s, %s, %s, %s)",
                (a.id, prev[0] if prev else None, vnew, ["provision_text", "ref_number", "citation_status"], now, why,
                 "revert_row_from_backup.py"))
    cur.execute("UPDATE regulatory_provisions SET provision_text = %s, ref_number = %s, citation_status = %s, "
                "citation_source_path = %s, citation_checked_at = NULL, current_version_id = %s, version_count = %s, "
                "text_hash_current = %s WHERE id = %s AND is_current AND ref_number = %s",
                (old, b["ref_number"], b["citation_status"], b["citation_source_path"], vnew, vmax + 1,
                 hashlib.sha256(old.encode()).hexdigest(), a.id, a.expect_ref))
    if cur.rowcount != 1:
        conn.rollback()
        print("ROLLED BACK: the row changed under us")
        return 1
    conn.commit()
    print(f"reverted {a.id} (version {vmax + 1})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
