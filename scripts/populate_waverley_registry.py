#!/usr/bin/env python3
"""
Waverley DCP 2022 — R2 Upload + Registry Initialisation
=========================================================
Uploads the Waverley DCP 2022 (Amendment 5) PDF to Cloudflare R2 and
creates the dcp_chapter_registry row so the extraction pipeline picks it up.

Waverley publishes one combined PDF (not per-chapter), so there is a single
registry row for the full document.

Usage:
    python3 scripts/populate_waverley_registry.py            # upload + register
    python3 scripts/populate_waverley_registry.py --dry-run  # show plan only
    python3 scripts/populate_waverley_registry.py --skip-upload  # DB only

TODO before first run:
    1. Confirm the live Waverley DCP PDF URL from waverley.nsw.gov.au
       (search "Development Control Plan 2022" under Planning & Building)
    2. Replace WAVERLEY_COUNCIL_URL below with the confirmed URL
"""

import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import boto3
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

R2_ACCOUNT_ID        = os.environ["R2_ACCOUNT_ID"]
R2_BUCKET_NAME       = os.environ["R2_BUCKET_NAME"]
R2_ACCESS_KEY_ID     = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
DATABASE_URL         = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

R2_ENDPOINT        = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
SOURCE_PDF_PREFIX  = "source-pdfs"
VERSION_LABEL      = "v1.0-baseline"

# ── Fill in the live Waverley DCP URL before running ─────────────────────────
# Check: https://www.waverley.nsw.gov.au/planning/development-control-plans
WAVERLEY_COUNCIL_URL = "https://www.waverley.nsw.gov.au/media/documents/building_and_development/dcp/WDCP_2022_updated.pdf"
WAVERLEY_COUNCIL_PAGE = "https://www.waverley.nsw.gov.au/planning/development-control-plans"

WAVERLEY_CHAPTERS = [
    {
        "chapter_key":   "waverley-dcp-2022",
        "chapter_label": "Waverley DCP 2022 (Full — Amendment 5)",
        "dcp_name":      "Waverley DCP 2022",
        "local_path":    Path(__file__).parent.parent / "waverley" / "Waverley_DCP_2022_Full_Version_Amendment5.pdf",
        "council_url":   WAVERLEY_COUNCIL_URL,
        "sort_order":    1,
        "doc_type":      "dcp",
    },
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def r2_key(council: str, version: str, chapter_key: str) -> str:
    return f"{SOURCE_PDF_PREFIX}/dcps/{council}/{version}/{chapter_key}.pdf"


def upload_to_r2(s3, content: bytes, key: str, dry_run: bool = False) -> None:
    if dry_run:
        print(f"  [dry-run] would upload → r2://{R2_BUCKET_NAME}/{key}")
        return
    s3.put_object(Bucket=R2_BUCKET_NAME, Key=key, Body=content)
    print(f"  Uploaded → r2://{R2_BUCKET_NAME}/{key} ({len(content):,} bytes)")


def upsert_registry(cur, row: dict, dry_run: bool = False) -> None:
    if dry_run:
        print(f"  [dry-run] would upsert: {row['council']}/{row['chapter_key']}")
        return
    cur.execute(
        """
        INSERT INTO dcp_chapter_registry (
            council, dcp_name, doc_type, chapter_key, chapter_label, sort_order,
            council_url, council_page_url,
            r2_current_path, r2_version_label,
            content_hash, url_content_length,
            url_last_checked, url_last_changed,
            is_active, needs_extraction
        ) VALUES (
            %(council)s, %(dcp_name)s, %(doc_type)s, %(chapter_key)s, %(chapter_label)s, %(sort_order)s,
            %(council_url)s, %(council_page_url)s,
            %(r2_current_path)s, %(r2_version_label)s,
            %(content_hash)s, %(url_content_length)s,
            %(url_last_checked)s, %(url_last_changed)s,
            TRUE, TRUE
        )
        ON CONFLICT (council, chapter_key) DO UPDATE SET
            dcp_name             = EXCLUDED.dcp_name,
            chapter_label        = EXCLUDED.chapter_label,
            sort_order           = EXCLUDED.sort_order,
            council_url          = EXCLUDED.council_url,
            council_page_url     = EXCLUDED.council_page_url,
            r2_current_path      = EXCLUDED.r2_current_path,
            r2_version_label     = EXCLUDED.r2_version_label,
            content_hash         = EXCLUDED.content_hash,
            url_content_length   = EXCLUDED.url_content_length,
            url_last_checked     = EXCLUDED.url_last_checked,
            needs_extraction     = TRUE,
            updated_at           = NOW()
        """,
        row,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate Waverley DCP registry")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-upload", action="store_true", help="DB only, assume PDF already in R2")
    args = parser.parse_args()

    if WAVERLEY_COUNCIL_URL == "<FILL_IN_LIVE_URL>":
        print("[WARN] WAVERLEY_COUNCIL_URL is not set — fill in the live URL before running.")
        print("       Continuing anyway (council_url will be stored as placeholder).")

    s3 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    print("=" * 60)
    print("Waverley DCP Registry Population")
    if args.dry_run:
        print("DRY RUN")
    print("=" * 60)

    cur = conn.cursor()
    now = datetime.now(timezone.utc)

    for chapter in WAVERLEY_CHAPTERS:
        local_path: Path = chapter["local_path"]
        chapter_key = chapter["chapter_key"]

        print(f"\n[waverley/{chapter_key}]")
        print(f"  Local: {local_path}")

        if not local_path.exists():
            print(f"  [ERROR] Local PDF not found: {local_path}")
            print(f"  Place the PDF at the path above and re-run.")
            continue

        content = local_path.read_bytes()
        content_hash = sha256(content)
        content_length = len(content)
        print(f"  Read {content_length:,} bytes, SHA-256: {content_hash[:16]}...")

        r2_path = r2_key("waverley", VERSION_LABEL, chapter_key)

        if not args.skip_upload:
            upload_to_r2(s3, content, r2_path, dry_run=args.dry_run)

        upsert_registry(cur, {
            "council":            "waverley",
            "dcp_name":           chapter["dcp_name"],
            "doc_type":           chapter["doc_type"],
            "chapter_key":        chapter_key,
            "chapter_label":      chapter["chapter_label"],
            "sort_order":         chapter["sort_order"],
            "council_url":        chapter["council_url"],
            "council_page_url":   WAVERLEY_COUNCIL_PAGE,
            "r2_current_path":    r2_path,
            "r2_version_label":   VERSION_LABEL,
            "content_hash":       content_hash,
            "url_content_length": content_length,
            "url_last_checked":   now,
            "url_last_changed":   now,
        }, dry_run=args.dry_run)

        if not args.dry_run:
            conn.commit()
            print(f"  [OK] Registry row upserted — needs_extraction=TRUE")

    cur.close()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
