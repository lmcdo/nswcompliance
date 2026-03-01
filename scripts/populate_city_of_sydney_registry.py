#!/usr/bin/env python3
"""
City of Sydney DCP 2012 — R2 Upload + Registry Initialisation
==============================================================
Uploads City of Sydney DCP 2012 section PDFs to Cloudflare R2 and creates
dcp_chapter_registry rows so the extraction pipeline picks them up.

City of Sydney publishes per-section PDFs (6 sections):
- Section 1: Introduction (~10 pages)
- Section 2: Locality Statements — 75 HCAs (~12.88 MB, largest section)
- Section 3: General Provisions
- Section 4: Development Types
- Section 5: Specific Areas / Precincts
- Section 6: Schedules / Appendices

Scale note: Section 2 is the main HCA coverage. Run survey_dcp.py on it
before registering to verify SECTION_RE hit rate (expected: page_ranges fallback).

Usage:
    python3 scripts/populate_city_of_sydney_registry.py            # upload + register
    python3 scripts/populate_city_of_sydney_registry.py --dry-run  # show plan only
    python3 scripts/populate_city_of_sydney_registry.py --skip-upload  # DB only

TODO before first run:
    1. Download section PDFs from City of Sydney DCP 2012 page:
       https://www.cityofsydney.nsw.gov.au/development-control-plans/sydney-dcp-2012
    2. Place PDFs in city-of-sydney/ directory at project root
    3. Run survey_dcp.py on section-2 (largest, most complex)
    4. Fill in council_url per section once confirmed
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
COUNCIL           = "city_of_sydney"

CITY_OF_SYDNEY_COUNCIL_PAGE = "https://www.cityofsydney.nsw.gov.au/development-control-plans/sydney-dcp-2012"

ROOT = Path(__file__).parent.parent / "city-of-sydney"

CITY_OF_SYDNEY_CHAPTERS = [
    {
        "chapter_key":    "section-1-introduction",
        "chapter_label":  "Section 1 — Introduction and General Provisions",
        "dcp_name":       "Sydney DCP 2012",
        "local_filename": "section-1-introduction.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     1,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-2-locality-statements",
        "chapter_label":  "Section 2 — Locality Statements (Heritage Conservation Areas)",
        "dcp_name":       "Sydney DCP 2012",
        "local_filename": "section-2-locality-statements.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     2,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-3-general-provisions",
        "chapter_label":  "Section 3 — General Provisions",
        "dcp_name":       "Sydney DCP 2012",
        "local_filename": "section-3-general-provisions.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     3,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-4-development-types",
        "chapter_label":  "Section 4 — Development Types",
        "dcp_name":       "Sydney DCP 2012",
        "local_filename": "section-4-development-types.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     4,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-5-specific-areas",
        "chapter_label":  "Section 5 — Specific Areas / Precincts",
        "dcp_name":       "Sydney DCP 2012",
        "local_filename": "section-5-specific-areas.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     5,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-6-schedules",
        "chapter_label":  "Section 6 — Schedules and Appendices",
        "dcp_name":       "Sydney DCP 2012",
        "local_filename": "section-6-schedules.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     6,
        "doc_type":       "dcp",
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
    parser = argparse.ArgumentParser(description="Populate City of Sydney DCP registry")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-upload", action="store_true", help="DB only, assume PDFs already in R2")
    parser.add_argument("--chapter", help="Process only this chapter_key (for incremental updates)")
    args = parser.parse_args()

    chapters = CITY_OF_SYDNEY_CHAPTERS
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
    print("City of Sydney DCP Registry Population")
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
            "council_page_url":   CITY_OF_SYDNEY_COUNCIL_PAGE,
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
        print(f"\n[WARN] {skipped} section(s) skipped (PDFs missing).")
        print(f"       Download from: {CITY_OF_SYDNEY_COUNCIL_PAGE}")
    print("\nDone.")


if __name__ == "__main__":
    main()
