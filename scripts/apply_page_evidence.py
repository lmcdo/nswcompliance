#!/usr/bin/env python3
# prior-art-checked: write shape and backup are dcp_page_repair.write / backup (migration 079
# columns, nothing new); this adds only the evidence-file gate in front of them.
"""Apply a verified data/page_evidence_<date>.jsonl to regulatory_provisions. DRY RUN by default.

Refuses (exit 1, writes nothing) unless, for EVERY line:
  * scripts/verify_page_evidence.py passes on the file (run first, as a subprocess);
  * the row still exists, is current, and md5(provision_text) equals the recorded md5;
  * the row is still unproven (page_check not on_page/moved) -- someone else's verdict stands;
  * its chapter PDF is still the registry's current one (page_source_path target).
--apply then writes a rollback CSV (data/db_rollback_backups/), writes through
dcp_page_repair.write (pdf_page, page_range, printed_page_label, page_check, page_source_path,
page_checked_at) and fails if the rowcount differs from the number of lines.

  python scripts/apply_page_evidence.py data/page_evidence_2026-10-17.jsonl            # dry run
  python scripts/apply_page_evidence.py data/page_evidence_2026-10-17.jsonl --apply
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def preflight(recs: list, rows: dict) -> list:
    """Reasons the file must not be applied. Pure."""
    bad = []
    for r in recs:
        cur = rows.get(r["id"])
        if cur is None:
            bad.append((r["id"], "row not current/served any more"))
        elif cur["md5"] != r["provision_text_md5"]:
            bad.append((r["id"], "provision_text changed (md5)"))
        elif r["plan"].get("id") != r["id"]:
            bad.append((r["id"], "plan id differs from the record id"))
        elif cur["page_check"] in ("on_page", "moved"):
            bad.append((r["id"], f"already {cur['page_check']}"))
        elif cur["r2_current_path"] != r["pdf_path"]:
            bad.append((r["id"], "chapter PDF is no longer the pinned one"))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    ap.add_argument("jsonl")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    recs = [json.loads(x) for x in Path(args.jsonl).read_text(encoding="utf-8").splitlines() if x.strip()]
    if not recs:
        print("no lines")
        return 1
    if len({r["id"] for r in recs}) != len(recs):
        print("duplicate ids in the file")
        return 1
    # --db: the evidence span must be THIS row's own words, not just a valid phrase from the PDF.
    v = subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_page_evidence.py"), args.jsonl, "--db"])
    if v.returncode != 0:
        print("REFUSED: the evidence does not verify.")
        return 1

    import dcp_page_repair as dpr
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parents[2] / ".env")
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    try:
        conn.cursor().execute("SET statement_timeout = '30000'")
        if not dpr.has_079(conn):
            print("page_check column missing -- migration 079 not applied.")
            return 1
        ids = [r["id"] for r in recs]
        cur = conn.cursor()
        cur.execute(dpr.SERVED_SQL + " AND rp.id = ANY(%s)", (ids,))
        cols = [d[0] for d in cur.description]
        allrows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.execute("SELECT id, md5(provision_text) FROM regulatory_provisions WHERE is_current AND id = ANY(%s)", (ids,))
        md5 = dict(cur.fetchall())
        rows = {x["id"]: {**x, "md5": md5.get(x["id"])} for x in allrows}
        bad = preflight(recs, rows)
        for i, why in bad[:20]:
            print(f"REFUSED id={i}: {why}")
        if bad:
            print(f"REFUSED: {len(bad)} of {len(recs)} lines no longer match the database.")
            return 1
        todo = [r["plan"] for r in recs]
        print(f"{len(todo)} rows to write: " + ", ".join(
            f"{k}={sum(1 for r in recs if r['verdict'] == k)}" for k in ("on_page", "moved")))
        if not args.apply:
            print("DRY RUN -- nothing written.")
            return 0
        saved = dpr.backup(allrows, set(ids))
        print(f"backup: {saved}")
        n = dpr.write(conn, todo)
        print(f"WROTE {n} rows.")
        if n != len(todo):
            print(f"ROWCOUNT MISMATCH: wrote {n}, expected {len(todo)} -- restore from the backup.")
            return 1
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
