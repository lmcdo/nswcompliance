#!/usr/bin/env python3
# prior-art-checked: the verdict is scripts/citation_proof.prove_citation_any, and the served
# rows and cached page lines are the DQ-111 probe's own (dq_probe_section_code_not_in_source:
# SERVED_SQL, chapter_lines). Nothing here re-decides a citation; it only stores the verdict.
"""Store, per served DCP rule, whether its clause number is printed on the council's page.

WHY
---
Served clause numbers were written by the AI extractor and never checked (DQ-111). Until
each is fixed, the serving layer must show the page instead of an unproven number. This
writes regulatory_provisions.citation_status (migration 076), which the serving layer reads.

WHAT IT DOES
------------
For every served DCP rule: proven | imprecise | not_proven | unjudged | text_not_found, or
no_source when the chapter's PDF cannot be read. Only rows whose verdict CHANGED are written.
Dry run by default; --apply writes. Runs after every publish and nightly.

USAGE
-----
  python scripts/dcp_citation_status.py                 # dry run, all councils
  python scripts/dcp_citation_status.py --council ashfield --apply
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

STATUSES = ("proven", "imprecise", "not_proven", "unjudged", "text_not_found", "no_source")
BATCH = 500


def plan_updates(verdicts: dict[int, str], current: dict[int, str | None]) -> list[tuple[int, str]]:
    """(id, status) for every row whose verdict differs from what is stored. Pure."""
    bad = {v for v in verdicts.values() if v not in STATUSES}
    if bad:
        raise ValueError(f"unknown citation status {sorted(bad)}")
    return sorted((i, v) for i, v in verdicts.items() if current.get(i) != v)


def _judge_chapter(args) -> dict[int, str]:
    """Verdicts for one PDF's rows. Runs in a worker process."""
    r2_path, rows, cache_dir = args
    import boto3
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import citation_proof as cp
    import dq_probe_section_code_not_in_source as probe
    s3 = boto3.client(
        "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    try:
        readings = probe.chapter_lines(s3, os.environ["R2_BUCKET_NAME"], r2_path, Path(cache_dir))
    except Exception as e:  # noqa: BLE001 -- a missing PDF is a verdict, not a crash
        print(f"  no source for {r2_path}: {str(e)[:80]}", flush=True)
        return {rid: "no_source" for rid, _ref, _text, _pages in rows}
    return {rid: cp.prove_citation_any(ref, text, readings, (pages or [None])[0])["status"]
            for rid, ref, text, pages in rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    ap.add_argument("--council", help="Only this council.")
    ap.add_argument("--apply", action="store_true", help="Write. Without it nothing changes.")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cache-dir", default=str(Path(tempfile.gettempdir()) / "dq111_lines"))
    args = ap.parse_args()

    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import dq_probe_section_code_not_in_source as probe

    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        _total, rows = probe.fetch_served(conn, args.council)
        by_pdf = defaultdict(list)
        for rid, _co, _chk, ref, r2_path, text, pages in rows:
            by_pdf[r2_path].append((rid, ref, text, pages))
        Path(args.cache_dir).mkdir(parents=True, exist_ok=True)
        verdicts: dict[int, str] = {}
        jobs = [(p, rs, args.cache_dir) for p, rs in by_pdf.items()]
        with ProcessPoolExecutor(max_workers=max(1, args.workers)) as ex:
            for got in ex.map(_judge_chapter, jobs):
                verdicts.update(got)
        cur.execute("SELECT id, citation_status FROM regulatory_provisions WHERE id = ANY(%s)",
                    (list(verdicts),))
        current = dict(cur.fetchall())
        todo = plan_updates(verdicts, current)
        print(f"scope: {args.council or 'all councils'}  rules: {len(verdicts)}")
        for k, n in Counter(verdicts.values()).most_common():
            print(f"  {n:6}  {k}")
        print(f"  {len(todo):6}  to write (verdict changed)")
        if not args.apply:
            print("DRY RUN -- nothing written. Re-run with --apply.")
            return 0
        for i in range(0, len(todo), BATCH):
            chunk = todo[i:i + BATCH]
            cur.execute(
                "UPDATE regulatory_provisions p SET citation_status = v.s, citation_checked_at = now() "
                "FROM unnest(%s::bigint[], %s::text[]) AS v(id, s) WHERE p.id = v.id AND p.is_current",
                ([t[0] for t in chunk], [t[1] for t in chunk]))
            conn.commit()
        print(f"WROTE {len(todo)} verdicts.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
