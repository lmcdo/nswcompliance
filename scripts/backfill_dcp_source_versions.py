# prior-art-checked: four sweeps 2026-11-18. (1) DB: provision_versions / provision_change_log / dcp_monitor_chapter_results hold rule-text
# versions and daily outcomes, none holds which SOURCE FILE was held when; dcp_chapter_registry keeps only the current path. (2) Frontend: nothing
# reads source-file history. (3) Python: r2_monitor.py writes each new version to a new R2 path and never deletes (r2_path_for_version), but records
# no ledger; no script lists the bucket by date. (4) Plans: ce-dated-archive-PLAN-2026-11-18.md (approved by the owner 2026-11-18).
"""Backfill dcp_source_versions from the R2 listing: one 'stored' row per council PDF, dated by the object's LastModified.

Usage:
    python scripts/backfill_dcp_source_versions.py            # dry run: counts, dates, nothing written
    python scripts/backfill_dcp_source_versions.py --apply    # write the rows (idempotent: UNIQUE (r2_key, event))

captured_at is when OUR copy was stored, not when the council published it. Run migration 126 first.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Iterable, Optional

PREFIX = "source-pdfs/dcps/"
BATCH = 200


def parse_key(key: str) -> Optional[dict]:
    """source-pdfs/dcps/{council}/{version}/{chapter}.pdf -> parts, else None (never guess a shape)."""
    if not key.startswith(PREFIX) or not key.lower().endswith(".pdf"):
        return None
    parts = key.split("/")
    if len(parts) != 5:
        return None
    council, version, fname = parts[2], parts[3], parts[4]
    chapter = fname[:-4]
    if not (council and version and chapter):
        return None
    return {"council": council, "version_label": version, "chapter_key": chapter}


def rows_from_objects(objs: Iterable[dict]) -> tuple[list[tuple], list[str]]:
    """Build insert tuples from R2 list entries. Returns (rows, skipped_keys); a skipped key is reported, never dropped silently."""
    rows: list[tuple] = []
    skipped: list[str] = []
    for o in objs:
        key = o.get("Key") or ""
        p = parse_key(key)
        lm = o.get("LastModified")
        if p is None or lm is None:
            skipped.append(key)
            continue
        etag = (o.get("ETag") or "").strip('"') or None
        rows.append((p["council"], p["chapter_key"], p["version_label"], key, "stored", o.get("Size"), etag, None, lm, "r2_listing_backfill"))
    return rows, skipped


def _env() -> dict[str, str]:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".env"))
    load_dotenv()
    return dict(os.environ)


def list_objects(env: dict[str, str]) -> list[dict]:
    import boto3

    s3 = boto3.client(
        "s3", endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=env["R2_ACCESS_KEY_ID"], aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"], region_name="auto",
    )
    out: list[dict] = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=env["R2_BUCKET_NAME"], Prefix=PREFIX):
        out += page.get("Contents") or []
    return out


INSERT_SQL = (
    "INSERT INTO dcp_source_versions (council, chapter_key, version_label, r2_key, event, size_bytes, etag, content_hash, captured_at, source) "
    "VALUES %s ON CONFLICT (r2_key, event) DO NOTHING"
)


def insert_rows(cur: Any, rows: list[tuple]) -> None:
    """Insert ledger rows once each: a repeat of the same (file, event) is ignored, never duplicated."""
    from psycopg2.extras import execute_values

    execute_values(cur, INSERT_SQL, rows)


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    env = _env()
    objs = list_objects(env)
    rows, skipped = rows_from_objects(objs)
    dates = sorted(r[8] for r in rows)
    print(f"R2 objects: {len(objs)} | parsed rows: {len(rows)} | skipped (unexpected shape): {len(skipped)}")
    if rows:
        print(f"earliest {dates[0].date()} latest {dates[-1].date()} | chapters {len({(r[0], r[1]) for r in rows})}")
    for k in skipped[:10]:
        print("  skipped:", k)
    if not apply:
        print("DRY RUN: nothing written. Re-run with --apply.")
        return 0
    # prior-art-checked: reuse not viable because this block only moves the ledger insert into the shared insert_rows helper above; the
    # other repo hits (legislation monitor, enrichment pipeline, frontend clients) write unrelated tables and share only generic words.
    import psycopg2

    conn = psycopg2.connect(env["DATABASE_URL"], connect_timeout=20)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30000'")
    before = _count(cur)
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        insert_rows(cur, chunk)
        conn.commit()
        print(f"DONE {min(i + BATCH, len(rows))}/{len(rows)}", flush=True)
    after = _count(cur)
    print(f"ledger rows before {before} after {after} (added {after - before})")
    conn.close()
    return 0


def _count(cur: Any) -> int:
    cur.execute("SELECT count(*) FROM dcp_source_versions")
    return int(cur.fetchone()[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
