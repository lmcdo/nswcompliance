#!/usr/bin/env python3
"""
Ku-ring-gai DCP — R2 Upload + Registry Initialisation
======================================================
Uploads Ku-ring-gai DCP (adopted March 2024) per-Part PDFs to Cloudflare R2
and creates dcp_chapter_registry rows so the extraction pipeline picks them up.

Structure: 3 sections (A/B/C) with ~24 Parts. Excludes cover pages, reference
maps, appendices, and the 15 site-specific precinct PDFs (Part 14A-14O) which
can be added later.

Source: https://www.krg.nsw.gov.au/Development/Planning-controls/Development-Control-Plan

Usage:
    python3 scripts/populate_ku_ring_gai_registry.py            # upload + register
    python3 scripts/populate_ku_ring_gai_registry.py --dry-run  # show plan only
    python3 scripts/populate_ku_ring_gai_registry.py --skip-upload  # DB only
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

KU_RING_GAI_COUNCIL_PAGE = "https://www.krg.nsw.gov.au/Development/Planning-controls/Development-Control-Plan"

ROOT = Path(__file__).parent.parent / "ku-ring-gai"

_BASE = "https://www.krg.nsw.gov.au/files/assets/public"

KU_RING_GAI_CHAPTERS = [
    # ── Part 1: Introduction ──────────────────────────────────────────────
    {
        "chapter_key":    "part-1-introduction",
        "chapter_label":  "Part 1 — Introduction, Preliminary and Dictionary",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "part-1-introduction.pdf",
        "council_url":    f"{_BASE}/v/4/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/part-1-introduction-preliminary-dictionary.pdf",
        "sort_order":     1,
        "doc_type":       "dcp",
    },
    # ── Section A: Residential & General ─────────────────────────────────
    {
        "chapter_key":    "section-a-part-2-site-analysis",
        "chapter_label":  "Section A Part 2 — Site Analysis",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-a-part-2-site-analysis.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-a-part-2-site-analysis.pdf",
        "sort_order":     2,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-a-part-3-subdivision",
        "chapter_label":  "Section A Part 3 — Land Consolidation and Subdivision",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-a-part-3-subdivision.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-a-part-3-land-consolidation-and-subdivision.pdf",
        "sort_order":     3,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-a-part-4-dwelling-houses",
        "chapter_label":  "Section A Part 4 — Dwelling Houses",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-a-part-4-dwelling-houses.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-a-part-4-dwelling-houses.pdf",
        "sort_order":     4,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-a-part-4-1-secondary-dwellings",
        "chapter_label":  "Section A Part 4.1 — Secondary Dwellings",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-a-part-4-1-secondary-dwellings.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-a-part-4.1-secondary-dwellings.pdf",
        "sort_order":     5,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-a-part-5-dual-occupancy",
        "chapter_label":  "Section A Part 5 — Dual Occupancy",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-a-part-5-dual-occupancy.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-a-part-5-dual-occupancy.pdf",
        "sort_order":     6,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-a-part-6-multi-dwelling",
        "chapter_label":  "Section A Part 6 — Multi-Dwelling Housing",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-a-part-6-multi-dwelling.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-a-part-6-multi-dwelling-housing.pdf",
        "sort_order":     7,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-a-part-7-residential-flat-buildings",
        "chapter_label":  "Section A Part 7 — Residential Flat Buildings",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-a-part-7-residential-flat-buildings.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-a-part-7-residential-flat-buildings.pdf",
        "sort_order":     8,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-a-part-8-mixed-use",
        "chapter_label":  "Section A Part 8 — Mixed Use Development",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-a-part-8-mixed-use.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-a-part-8-mixed-use-development.pdf",
        "sort_order":     9,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-a-part-9-non-residential",
        "chapter_label":  "Section A Part 9 — Non-Residential and Office Buildings",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-a-part-9-non-residential.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-a-part-9-non-residential-and-office-buildings.pdf",
        "sort_order":     10,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-a-part-12-signage",
        "chapter_label":  "Section A Part 12 — Signage and Advertising",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-a-part-12-signage.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-a-part-12-signage-and-advertising.pdf",
        "sort_order":     11,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-a-part-13-trees",
        "chapter_label":  "Section A Part 13 — Tree and Vegetation Preservation",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-a-part-13-trees.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-a-part-13-tree-and-vegetation-preservation.pdf",
        "sort_order":     12,
        "doc_type":       "dcp",
    },
    # ── Section B: Character Areas & Environmental ────────────────────────
    {
        "chapter_key":    "section-b-part-15-contamination",
        "chapter_label":  "Section B Part 15 — Land Contamination",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-b-part-15-contamination.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-b-part-15-land-contamination.pdf",
        "sort_order":     13,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-b-part-16-bushfire",
        "chapter_label":  "Section B Part 16 — Bushfire Risk",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-b-part-16-bushfire.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-b-part-16-bushfire-risk.pdf",
        "sort_order":     14,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-b-part-17-riparian",
        "chapter_label":  "Section B Part 17 — Riparian Lands",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-b-part-17-riparian.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-b-part-17-reparian-lands.pdf",
        "sort_order":     15,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-b-part-18-biodiversity",
        "chapter_label":  "Section B Part 18 — Biodiversity",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-b-part-18-biodiversity.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-b-part-18-biodiversity.pdf",
        "sort_order":     16,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-b-part-19-heritage",
        "chapter_label":  "Section B Part 19 — Heritage Items and Conservation Areas",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-b-part-19-heritage.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-b-part-19-heritage-items-and-heritage-conservation-areas.pdf",
        "sort_order":     17,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-b-part-20-rail-roads",
        "chapter_label":  "Section B Part 20 — Development near Rail Corridors and Busy Roads",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-b-part-20-rail-roads.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-b-part-20-development-near-rail-corridors-and-busy-roads.pdf",
        "sort_order":     18,
        "doc_type":       "dcp",
    },
    # ── Section C: Design & Technical Standards ───────────────────────────
    {
        "chapter_key":    "section-c-part-21-site-design",
        "chapter_label":  "Section C Part 21 — General Site Design",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-c-part-21-site-design.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-c-part-21-general-site-design.pdf",
        "sort_order":     19,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-c-part-22-parking",
        "chapter_label":  "Section C Part 22 — General Access and Parking",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-c-part-22-parking.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-c-part-22-general-access-and-parking.pdf",
        "sort_order":     20,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-c-part-23-building-design",
        "chapter_label":  "Section C Part 23 — General Building Design and Sustainability",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-c-part-23-building-design.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-c-part-23-general-building-design-and-sustainability.pdf",
        "sort_order":     21,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-c-part-24-water",
        "chapter_label":  "Section C Part 24 — Water Management",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-c-part-24-water.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-c-part-24-water-management.pdf",
        "sort_order":     22,
        "doc_type":       "dcp",
    },
    {
        "chapter_key":    "section-c-part-25-waste",
        "chapter_label":  "Section C Part 25 — Waste Management",
        "dcp_name":       "Ku-ring-gai DCP 2024",
        "local_filename": "section-c-part-25-waste.pdf",
        "council_url":    f"{_BASE}/v/1/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-c-part-25-waste-management.pdf",
        "sort_order":     23,
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
