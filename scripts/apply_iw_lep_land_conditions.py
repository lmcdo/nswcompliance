"""Write each Inner West LEP 2022 row's land condition to regulatory_provisions.v2_land_condition (DQ-140).

prior-art-checked: no writer of this column exists (migration 109 adds it). The conditions are computed by
enrichment/config/inner_west_lep_land.py `row_conditions`; this script only reads rows, backs them up, and
writes. Dry run by default; --apply writes inside one transaction after a CSV backup.

    python scripts/apply_iw_lep_land_conditions.py            # dry run: counts only
    python scripts/apply_iw_lep_land_conditions.py --apply
Verify: python scripts/dq_probe_live.py --id DQ-140   (0 after)
"""
import argparse
import collections
import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enrichment.config.inner_west_lep_land import row_conditions  # noqa: E402

DOC_RE = '^Inner_West_Local_Environmental_Plan_2022'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    # A worktree has no .env of its own; the repository root's is three levels up.
    for env in (ROOT / '.env', ROOT.parents[2] / '.env'):
        if env.exists():
            load_dotenv(env)
    conn = psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=20)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET statement_timeout = 30000")
    cur.execute(
        "SELECT id, document_id, section_header, ref_number, provision_text, v2_land_condition "
        "FROM regulatory_provisions WHERE is_current AND document_id ~ %s", (DOC_RE,))
    rows = cur.fetchall()
    current = {r['id']: r['v2_land_condition'] for r in rows}
    by_doc = collections.defaultdict(list)
    for r in rows:
        by_doc[r['document_id']].append(r)
    conds = {}
    for doc_rows in by_doc.values():
        conds.update(row_conditions(doc_rows))

    changed = [(rid, c) for rid, c in conds.items() if current[rid] != c]
    print(f'{len(rows)} current rows, {len(conds)} with a land condition, {len(changed)} to write')
    print('by layer:', dict(collections.Counter(c['layer'] for c in conds.values())))
    if not args.apply:
        print('dry run -- nothing written')
        return 0

    stamp = dt.datetime.now().strftime('%Y-%m-%d_%H%M')
    backup = ROOT / 'data' / 'db_rollback_backups' / f'regulatory_provisions_pre_iw_land_condition_{stamp}.csv'
    with backup.open('w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['id', 'v2_land_condition'])
        for rid, _ in changed:
            w.writerow([rid, json.dumps(current[rid]) if current[rid] is not None else ''])
    print('backup:', backup)

    psycopg2.extras.execute_batch(
        cur, "UPDATE regulatory_provisions SET v2_land_condition = %s::jsonb WHERE id = %s AND is_current",
        [(json.dumps(c), rid) for rid, c in changed])
    cur.execute("SELECT count(*) AS n FROM regulatory_provisions WHERE is_current AND document_id ~ %s "
                "AND v2_land_condition IS NOT NULL", (DOC_RE,))
    n = cur.fetchone()['n']
    if n != len(conds):
        conn.rollback()
        print(f'ROLLED BACK: {n} rows carry a condition, expected {len(conds)}')
        return 1
    conn.commit()
    print(f'written: {len(changed)}; rows carrying a condition: {n}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
