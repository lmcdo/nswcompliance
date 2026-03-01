#!/usr/bin/env python3
"""
Woollahra DCP 2015 — R2 Upload + Registry Initialisation
==========================================================
Uploads Woollahra DCP 2015 chapter PDFs to Cloudflare R2 and creates
dcp_chapter_registry rows so the extraction pipeline picks them up.

Woollahra publishes per-chapter PDFs (Parts A–G, ~15 chapters).
Heritage chapters (C1 Paddington, C2 Woollahra, C3 Watsons Bay) have
separate registry rows for per-HCA tagging.

Usage:
    python3 scripts/populate_woollahra_registry.py            # upload + register
    python3 scripts/populate_woollahra_registry.py --dry-run  # show plan only
    python3 scripts/populate_woollahra_registry.py --skip-upload  # DB only

TODO before first run:
    1. Download chapter PDFs from Woollahra council website:
       https://www.woollahra.nsw.gov.au/Building-and-development/Development-rules/dcps-background
    2. Place PDFs in woollahra/ directory at project root (names below)
    3. Fill in WOOLLAHRA_COUNCIL_PAGE with confirmed URL
    4. Confirm chapter URLs per chapter (or leave as placeholder)
    5. Run: python3 scripts/survey_dcp.py woollahra/{chapter}.pdf
       to verify SECTION_RE hit rate before extracting

Chapter keys follow kebab-case: part-a-intro, part-b-general, part-c1-paddington-hca, etc.
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

R2_ENDPOINT       = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
SOURCE_PDF_PREFIX = "source-pdfs"
VERSION_LABEL     = "v1.0-baseline"
COUNCIL           = "woollahra"

WOOLLAHRA_COUNCIL_PAGE = "https://www.woollahra.nsw.gov.au/Building-and-development/Development-rules/dcps-background"

# ── Chapter definitions ───────────────────────────────────────────────────────
# local_filename: filename under woollahra/ directory (place PDFs there before running)
# council_url:    direct PDF download URL from council website (<FILL_IN> = placeholder)
# sort_order:     display order

ROOT = Path(__file__).parent.parent / "woollahra"

WOOLLAHRA_CHAPTERS = [
    {
        "chapter_key":   "part-a-intro",
        "chapter_label": "Part A — Introduction",
        "dcp_name":      "Woollahra DCP 2015",
        "local_filename": "part-a-intro.pdf",
        "council_url":   "<FILL_IN>",
        "sort_order":    1,
        "doc_type":      "dcp",
    },
    {
        "chapter_key":   "part-b-general",
        "chapter_label": "Part B — General Provisions",
        "dcp_name":      "Woollahra DCP 2015",
        "local_filename": "part-b-general.pdf",
        "council_url":   "<FILL_IN>",
        "sort_order":    2,
        "doc_type":      "dcp",
    },
    {
        "chapter_key":   "part-c-heritage",
        "chapter_label": "Part C — Heritage Conservation Areas (General)",
        "dcp_name":      "Woollahra DCP 2015",
        "local_filename": "part-c-heritage.pdf",
        "council_url":   "<FILL_IN>",
        "sort_order":    3,
        "doc_type":      "dcp",
    },
    {
        "chapter_key":   "part-c1-paddington-hca",
        "chapter_label": "Part C1 — Paddington Heritage Conservation Area",
        "dcp_name":      "Woollahra DCP 2015",
        "local_filename": "part-c1-paddington-hca.pdf",
        "council_url":   "<FILL_IN>",
        "sort_order":    4,
        "doc_type":      "dcp",
    },
    {
        "chapter_key":   "part-c2-woollahra-hca",
        "chapter_label": "Part C2 — Woollahra Heritage Conservation Area",
        "dcp_name":      "Woollahra DCP 2015",
        "local_filename": "part-c2-woollahra-hca.pdf",
        "council_url":   "<FILL_IN>",
        "sort_order":    5,
        "doc_type":      "dcp",
    },
    {
        "chapter_key":   "part-c3-watsons-bay-hca",
        "chapter_label": "Part C3 — Watsons Bay Heritage Conservation Area",
        "dcp_name":      "Woollahra DCP 2015",
        "local_filename": "part-c3-watsons-bay-hca.pdf",
        "council_url":   "<FILL_IN>",
        "sort_order":    6,
        "doc_type":      "dcp",
    },
    {
        "chapter_key":   "part-d-business",
        "chapter_label": "Part D — Business and Commercial Development",
        "dcp_name":      "Woollahra DCP 2015",
        "local_filename": "part-d-business.pdf",
        "council_url":   "<FILL_IN>",
        "sort_order":    7,
        "doc_type":      "dcp",
    },
    {
        "chapter_key":   "part-e-parking",
        "chapter_label": "Part E — Parking and Transport",
        "dcp_name":      "Woollahra DCP 2015",
        "local_filename": "part-e-parking.pdf",
        "council_url":   "<FILL_IN>",
        "sort_order":    8,
        "doc_type":      "dcp",
    },
    {
        "chapter_key":   "part-f-residential",
        "chapter_label": "Part F — Residential Development",
        "dcp_name":      "Woollahra DCP 2015",
        "local_filename": "part-f-residential.pdf",
        "council_url":   "<FILL_IN>",
        "sort_order":    9,
        "doc_type":      "dcp",
    },
    {
        "chapter_key":   "part-g-landscaping",
        "chapter_label": "Part G — Landscaping, Trees, and Open Space",
        "dcp_name":      "Woollahra DCP 2015",
        "local_filename": "part-g-landscaping.pdf",
        "council_url":   "<FILL_IN>",
        "sort_order":    10,
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
    parser = argparse.ArgumentParser(description="Populate Woollahra DCP registry")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-upload", action="store_true", help="DB only, assume PDFs already in R2")
    parser.add_argument("--chapter", help="Process only this chapter_key (for incremental updates)")
    args = parser.parse_args()

    chapters = WOOLLAHRA_CHAPTERS
    if args.chapter:
        chapters = [c for c in chapters if c["chapter_key"] == args.chapter]
        if not chapters:
            print(f"[ERROR] Unknown chapter_key: {args.chapter}")
            sys.exit(1)

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
    print("Woollahra DCP Registry Population")
    if args.dry_run:
        print("DRY RUN")
    print("=" * 60)

    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    skipped = 0

    for chapter in chapters:
        local_path = ROOT / chapter["local_filename"]
        chapter_key = chapter["chapter_key"]

        print(f"\n[{COUNCIL}/{chapter_key}]")
        print(f"  Local: {local_path}")

        if not local_path.exists():
            print(f"  [SKIP] PDF not found — place at path above then re-run")
            skipped += 1
            continue

        content = local_path.read_bytes()
        content_hash = sha256(content)
        content_length = len(content)
        print(f"  Read {content_length:,} bytes, SHA-256: {content_hash[:16]}...")

        r2_path = r2_key(COUNCIL, VERSION_LABEL, chapter_key)

        if not args.skip_upload:
            upload_to_r2(s3, content, r2_path, dry_run=args.dry_run)

        upsert_registry(cur, {
            "council":            COUNCIL,
            "dcp_name":           chapter["dcp_name"],
            "doc_type":           chapter["doc_type"],
            "chapter_key":        chapter_key,
            "chapter_label":      chapter["chapter_label"],
            "sort_order":         chapter["sort_order"],
            "council_url":        chapter["council_url"],
            "council_page_url":   WOOLLAHRA_COUNCIL_PAGE,
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

    if skipped:
        print(f"\n[WARN] {skipped} chapter(s) skipped (PDFs missing).")
        print(f"       Download from: {WOOLLAHRA_COUNCIL_PAGE}")
    print("\nDone.")


if __name__ == "__main__":
    main()
