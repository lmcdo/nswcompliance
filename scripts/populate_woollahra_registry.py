#!/usr/bin/env python3
"""
Woollahra DCP 2015 — R2 Upload + Registry Initialisation
==========================================================
Uploads Woollahra DCP 2015 chapter PDFs to Cloudflare R2 and creates
dcp_chapter_registry rows so the extraction pipeline picks them up.

Woollahra publishes per-chapter PDFs (A1, A3, B1–B4, C1–C3, D4, E1–E6).
Heritage chapters (C1 Paddington, C2 Woollahra, C3 Watsons Bay) each have
their own registry row for per-HCA tagging.

Usage:
    python3 scripts/populate_woollahra_registry.py            # upload + register
    python3 scripts/populate_woollahra_registry.py --dry-run  # show plan only
    python3 scripts/populate_woollahra_registry.py --skip-upload  # DB only

Steps before first run:
    1. Download chapter PDFs from the council website (URLs listed below)
       and place them in  woollahra/  at the project root using the filenames below.
    2. Run survey on a few chapters to verify SECTION_RE hit rate:
           python3 scripts/survey_dcp.py woollahra/chapter-b3-general-development.pdf
           python3 scripts/survey_dcp.py woollahra/chapter-c1-paddington-hca.pdf
    3. Run this script (--dry-run first, then live):
           python3 scripts/populate_woollahra_registry.py --dry-run
           python3 scripts/populate_woollahra_registry.py
    4. Extract provisions:
           python3 scripts/dcp_extract_changed.py --council woollahra --dry-run
           python3 scripts/dcp_extract_changed.py --council woollahra

NOTE: D1, D2, D5, D6 chapter URLs still need confirmation from the council website.
      Add their local_filename entries here once URLs are confirmed.
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

WOOLLAHRA_COUNCIL_PAGE = "https://www.woollahra.nsw.gov.au/Building-and-development/Development-rules"
BASE_URL = "https://www.woollahra.nsw.gov.au/files/assets/public"

# ── Chapter definitions ───────────────────────────────────────────────────────
# local_filename: file to place under woollahra/ directory before running
# council_url:    direct PDF download URL from council website
# sort_order:     display order in UI
#
# Download URLs confirmed 2026-03-04.  Version numbers (v/N) may change as
# amendments are published — re-run this script to upload the updated file.

ROOT = Path(__file__).parent.parent / "woollahra"

WOOLLAHRA_CHAPTERS = [
    # ── Part A: Introduction & Definitions ──────────────────────────────────
    {
        "chapter_key":    "chapter-a1-introduction",
        "chapter_label":  "Chapter A1 — Introduction",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-a1-introduction.pdf",
        "council_url":    f"{BASE_URL}/v/13/plans-policies-publications/development-control-plans/woollahra-development-control-plan-2015-chapter-a1-introduction.pdf",
        "sort_order":     1,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "chapter-a3-definitions",
        "chapter_label":  "Chapter A3 — Definitions",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-a3-definitions.pdf",
        "council_url":    f"{BASE_URL}/v/3/plans-policies-publications/development-control-plans/chapter-a3-definitions-23may2025.pdf",
        "sort_order":     2,
        "doc_type":       "dcp",
    },
    # ── Part B: General Residential ─────────────────────────────────────────
    {
        "chapter_key":    "chapter-b1-residential-precincts",
        "chapter_label":  "Chapter B1 — Residential Precincts",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-b1-residential-precincts.pdf",
        "council_url":    f"{BASE_URL}/v/1/plans-policies-publications/development-control-plans/chapter-b1-residential-precincts.pdf",
        "sort_order":     10,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "chapter-b2-neighbourhood-hcas",
        "chapter_label":  "Chapter B2 — Neighbourhood Heritage Conservation Areas",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-b2-neighbourhood-hcas.pdf",
        "council_url":    f"{BASE_URL}/v/2/plans-policies-publications/development-control-plans/chapter-b2-neighbourhood-hcas.pdf",
        "sort_order":     11,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "chapter-b3-general-development",
        "chapter_label":  "Chapter B3 — General Development Controls",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-b3-general-development.pdf",
        "council_url":    f"{BASE_URL}/v/6/plans-policies-publications/development-control-plans/chapter-b3-general-development.pdf",
        "sort_order":     12,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "chapter-b4-housing-accessible-areas",
        "chapter_label":  "Chapter B4 — Housing in Accessible Areas",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-b4-housing-accessible-areas.pdf",
        "council_url":    f"{BASE_URL}/v/1/building-and-development/documents/chapter-b4-housing-in-accessible-areas_2.pdf",
        "sort_order":     13,
        "doc_type":       "dcp",
    },
    # ── Part C: Heritage Conservation Areas ─────────────────────────────────
    {
        "chapter_key":    "chapter-c1-paddington-hca",
        "chapter_label":  "Chapter C1 — Paddington Heritage Conservation Area",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-c1-paddington-hca.pdf",
        "council_url":    f"{BASE_URL}/v/3/plans-policies-publications/development-control-plans/chapter-c1-paddington-hca.pdf",
        "sort_order":     20,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "chapter-c2-woollahra-hca",
        "chapter_label":  "Chapter C2 — Woollahra Heritage Conservation Area",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-c2-woollahra-hca.pdf",
        "council_url":    f"{BASE_URL}/v/3/plans-policies-publications/development-control-plans/chapter-c2-woollahra-hca.pdf",
        "sort_order":     21,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "chapter-c3-watsons-bay-hca",
        "chapter_label":  "Chapter C3 — Watsons Bay Heritage Conservation Area",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-c3-watsons-bay-hca.pdf",
        "council_url":    f"{BASE_URL}/v/3/plans-policies-publications/development-control-plans/chapter-c3-watsons-bay-hca.pdf",
        "sort_order":     22,
        "doc_type":       "dcp",
    },
    # ── Part D: Business & Mixed Use Centres ─────────────────────────────────
    # D3 was repealed Dec 2023.  D1, D2, D5, D6 URLs need confirmation.
    {
        "chapter_key":    "chapter-d4-edgecliff-centre",
        "chapter_label":  "Chapter D4 — Edgecliff Centre",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-d4-edgecliff-centre.pdf",
        "council_url":    f"{BASE_URL}/v/3/plans-policies-publications/development-control-plans/chapter-d4-edgecliff-centre.pdf",
        "sort_order":     30,
        "doc_type":       "dcp",
    },
    # ── Part E: General Controls for All Development ─────────────────────────
    {
        "chapter_key":    "chapter-e1-parking-access",
        "chapter_label":  "Chapter E1 — Parking and Access",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-e1-parking-access.pdf",
        "council_url":    f"{BASE_URL}/v/6/plans-policies-publications/development-control-plans/chapter-e1-parking-and-access-23may2025.pdf",
        "sort_order":     40,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "chapter-e2-stormwater-flood",
        "chapter_label":  "Chapter E2 — Stormwater, Flood and Geotechnical Risk",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-e2-stormwater-flood.pdf",
        "council_url":    f"{BASE_URL}/v/1/plans-policies-publications/development-control-plans/chapter-e2-stormwater-and-flood-risk-management.pdf",
        "sort_order":     41,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "chapter-e3-tree-management",
        "chapter_label":  "Chapter E3 — Tree Management",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-e3-tree-management.pdf",
        "council_url":    f"{BASE_URL}/v/2/plans-policies-publications/development-control-plans/chapter-e3-tree-management.pdf",
        "sort_order":     42,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "chapter-e5-waste-management",
        "chapter_label":  "Chapter E5 — Waste Management",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-e5-waste-management.pdf",
        "council_url":    f"{BASE_URL}/v/1/plans-policies-publications/development-control-plans/chapter_e5_waste_management.pdf",
        "sort_order":     44,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "chapter-e6-sustainability",
        "chapter_label":  "Chapter E6 — Sustainability",
        "dcp_name":       "Woollahra DCP 2015",
        "local_filename": "chapter-e6-sustainability.pdf",
        "council_url":    f"{BASE_URL}/v/2/plans-policies-publications/development-control-plans/chapter_e6_sustainability.pdf",
        "sort_order":     45,
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
        print(f"  Download: {chapter['council_url']}")
        print(f"  Local:    {local_path}")

        if not local_path.exists():
            print(f"  [SKIP] PDF not found — download from URL above and place at local path")
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
        print(f"       See download URLs printed above for each skipped chapter.")
        print(f"       Place PDFs in: {ROOT}")
    print("\nDone.")


if __name__ == "__main__":
    main()
