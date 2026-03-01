#!/usr/bin/env python3
"""
Ku-ring-gai DCP — R2 Upload + Registry Initialisation
======================================================
Uploads Ku-ring-gai DCP PDFs to Cloudflare R2 and creates dcp_chapter_registry
rows so the extraction pipeline picks them up.

Ku-ring-gai has multiple numbered topic-DCPs (structurally distinct from
single-DCP LGAs). Each DCP is a separate chapter. Topic is encoded in the
DCP name/number, not in section headers within PDFs.

Known DCPs (confirm from council website before running):
- Principal DCP: General controls
- DCP 28: Signs and Advertising
- DCP 31: Access and Mobility
- DCP 38: Residential Design
- DCP 40: Demolition and Site Waste Management
- DCP 43: Car Parking
- DCP 46: Exempt and Complying Development
- DCP 47: Water Management
- DCP 48: Medium Density Housing

Usage:
    python3 scripts/populate_ku_ring_gai_registry.py            # upload + register
    python3 scripts/populate_ku_ring_gai_registry.py --dry-run  # show plan only
    python3 scripts/populate_ku_ring_gai_registry.py --skip-upload  # DB only

TODO before first run:
    1. Download DCP PDFs from Ku-ring-gai council website:
       https://www.krg.nsw.gov.au/Planning-and-development/Planning-policies-and-guidelines/Ku-ring-gai-Development-Control-Plan
    2. Place PDFs in ku-ring-gai/ directory at project root
    3. Run survey_dcp.py on principal DCP and one topic DCP
    4. Confirm heritage location (likely in Principal DCP)
    5. Fill in council_url per DCP once confirmed
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
COUNCIL           = "ku_ring_gai"

KU_RING_GAI_COUNCIL_PAGE = "https://www.krg.nsw.gov.au/Planning-and-development/Planning-policies-and-guidelines/Ku-ring-gai-Development-Control-Plan"

ROOT = Path(__file__).parent.parent / "ku-ring-gai"

KU_RING_GAI_CHAPTERS = [
    {
        "chapter_key":    "principal-dcp",
        "chapter_label":  "Ku-ring-gai DCP — Principal DCP (General Controls)",
        "dcp_name":       "Ku-ring-gai DCP",
        "local_filename": "principal-dcp.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     1,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "dcp-28-signs",
        "chapter_label":  "DCP 28 — Signs and Advertising",
        "dcp_name":       "Ku-ring-gai DCP",
        "local_filename": "dcp-28-signs.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     2,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "dcp-31-access",
        "chapter_label":  "DCP 31 — Access and Mobility",
        "dcp_name":       "Ku-ring-gai DCP",
        "local_filename": "dcp-31-access.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     3,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "dcp-38-residential",
        "chapter_label":  "DCP 38 — Residential Design",
        "dcp_name":       "Ku-ring-gai DCP",
        "local_filename": "dcp-38-residential.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     4,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "dcp-40-demolition-waste",
        "chapter_label":  "DCP 40 — Demolition and Site Waste Management",
        "dcp_name":       "Ku-ring-gai DCP",
        "local_filename": "dcp-40-demolition-waste.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     5,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "dcp-43-car-parking",
        "chapter_label":  "DCP 43 — Car Parking",
        "dcp_name":       "Ku-ring-gai DCP",
        "local_filename": "dcp-43-car-parking.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     6,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "dcp-46-exempt-complying",
        "chapter_label":  "DCP 46 — Exempt and Complying Development",
        "dcp_name":       "Ku-ring-gai DCP",
        "local_filename": "dcp-46-exempt-complying.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     7,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "dcp-47-water",
        "chapter_label":  "DCP 47 — Water Management",
        "dcp_name":       "Ku-ring-gai DCP",
        "local_filename": "dcp-47-water.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     8,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "dcp-48-medium-density",
        "chapter_label":  "DCP 48 — Medium Density Housing",
        "dcp_name":       "Ku-ring-gai DCP",
        "local_filename": "dcp-48-medium-density.pdf",
        "council_url":    "<FILL_IN>",
        "sort_order":     9,
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
    parser = argparse.ArgumentParser(description="Populate Ku-ring-gai DCP registry")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-upload", action="store_true", help="DB only, assume PDFs already in R2")
    parser.add_argument("--chapter", help="Process only this chapter_key (for incremental updates)")
    args = parser.parse_args()

    chapters = KU_RING_GAI_CHAPTERS
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
    print("Ku-ring-gai DCP Registry Population")
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
            "council_page_url":   KU_RING_GAI_COUNCIL_PAGE,
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
        print(f"\n[WARN] {skipped} DCP(s) skipped (PDFs missing).")
        print(f"       Download from: {KU_RING_GAI_COUNCIL_PAGE}")
    print("\nDone.")


if __name__ == "__main__":
    main()
