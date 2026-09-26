#!/usr/bin/env python3
# prior-art-checked: the digest is the database's own report_audit_trail_digest (migration 078),
# the one definition the insert trigger also uses; nothing else reads report_audit_trail's chain.
"""Verify the report audit trail's hash chain: no row edited, deleted or inserted out of order.

Every row's row_hash must equal report_audit_trail_digest(row, prev_hash), and every prev_hash
must equal the row_hash of the row before it (by chain_seq). An edited row fails its own digest;
a deleted row breaks the next row's link; an unchained row has no chain_seq.

Read-only. Exit 0 = intact, 1 = broken (the rows are named), 2 = could not check.

  python scripts/verify_audit_chain.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECK_SQL = """
WITH o AS (
    SELECT r AS rec, r.id, r.chain_seq, r.prev_hash, r.row_hash,
           lag(r.row_hash) OVER (ORDER BY r.chain_seq) AS expected_prev
    FROM report_audit_trail r
)
SELECT id, chain_seq,
       CASE WHEN chain_seq IS NULL THEN 'not chained'
            WHEN prev_hash IS DISTINCT FROM expected_prev THEN 'link broken (row deleted or inserted)'
            ELSE 'content changed' END
FROM o
WHERE chain_seq IS NULL
   OR prev_hash IS DISTINCT FROM expected_prev
   OR row_hash IS DISTINCT FROM report_audit_trail_digest(rec, prev_hash)
ORDER BY chain_seq NULLS FIRST
"""

#: Deleting the newest row breaks no later link; the tail checkpoint (migration 078) catches it.
TAIL_SQL = """
SELECT t.chain_seq, t.row_hash, last.chain_seq, last.row_hash
FROM report_audit_trail_tail t
LEFT JOIN LATERAL (SELECT chain_seq, row_hash FROM report_audit_trail
                   ORDER BY chain_seq DESC LIMIT 1) last ON true
"""


def tail_problem(row) -> str | None:
    """None when the newest row is the one the checkpoint names. Pure."""
    if row is None:
        return "no tail checkpoint"
    t_seq, t_hash, last_seq, last_hash = row
    if (t_seq, t_hash) != (last_seq, last_hash):
        return f"newest row is chain_seq={last_seq}, checkpoint says {t_seq}: rows removed from the end"
    return None


def main() -> int:
    try:
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
        conn.set_session(readonly=True, autocommit=True)
    except Exception as exc:  # noqa: BLE001
        print(f"UNREACHABLE: {exc}")
        return 2
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        cur.execute("SELECT count(*) FROM report_audit_trail")
        total = cur.fetchone()[0]
        cur.execute(CHECK_SQL)
        bad = cur.fetchall()
        cur.execute(TAIL_SQL)
        tail = tail_problem(cur.fetchone()) if total else None
    except Exception as exc:  # noqa: BLE001 -- e.g. migration 078 not applied: cannot check
        print(f"COULD NOT CHECK: {exc}")
        return 2
    finally:
        conn.close()
    if bad or tail:
        print(f"BROKEN: {len(bad)} of {total} audit rows fail the chain" + (f"; {tail}" if tail else ""))
        for rid, seq, why in bad[:20]:
            print(f"  chain_seq={seq} id={rid}: {why}")
        return 1
    print(f"INTACT: {total} audit rows, chain verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
