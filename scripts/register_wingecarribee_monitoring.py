#!/usr/bin/env python3
"""Register Wingecarribee in the VerifyOpsBot monitoring system.

prior-art-checked: data-registration only, following the existing registry
conventions (dcp_chapter_registry rows as per the ku_ring_gai baseline pattern,
instrument_registry rows as per the 23 monitored LEPs). No new monitoring
logic — r2_monitor / legislation_monitor / dcp_watchdog pick these up on
their existing schedules.

What this wires up (and why each piece):
1. dcp_chapter_registry: the three town-plan PDFs (Bowral/Mittagong/Moss Vale,
   as amended 2015) with SHA-256 baselines + R2 upload — r2_monitor then
   hash-watches them weekly and Telegram-alerts on change.
2. dcp_setback_controls.source_chapter_key -> 'wingecarribee-bowral-town-plan'
   for the 32 numeric rows — closes the dcp_watchdog "blind spot" check AND
   makes a source-PDF change auto-flag the rows needs_review (and a clean run
   refresh last_verified_at). The Bowral copy is the reference document; the
   values were verified identical across all three plans (Phase-0), and the
   other two plans are registered for change detection in their own right.
3. instrument_registry: wingecarribee_lep_2010 (epi-2010-0245) — the
   legislation_monitor then watches the LEP that backs the land-use table
   and the upzoning tool's permissibility panel.

The DCP 2026 consolidation needs no separate watch: when it commences, the
town-plan PDFs/URLs will change or vanish, which is exactly what r2_monitor
alerts on.

Usage:
    python scripts/register_wingecarribee_monitoring.py --pdf-dir=<dir> --dry-run
    python scripts/register_wingecarribee_monitoring.py --pdf-dir=<dir>
"""
import hashlib
import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

DRY_RUN = "--dry-run" in sys.argv

# Exact planURLs from the Planning Portal /dcp endpoint (verified 2026-07-14 —
# NB the irregular double-spaces are real; hand-built URLs 404).
S3 = "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/_R15"
CHAPTERS = [
    {
        "chapter_key": "wingecarribee-bowral-town-plan",
        "chapter_label": "Bowral Town Plan (as amended 23 Sep 2015)",
        "council_url": f"{S3}/Wingecarribee%20DCP%202010%20-%20Bowral%20Town%20Plan%20-%20as%20amended%2023%20Sep%202015.pdf",
        "local_pdf": "bowral_town_plan.pdf",
    },
    {
        "chapter_key": "wingecarribee-mittagong-town-plan",
        "chapter_label": "Mittagong Town Plan (as amended 17 Jun 2015)",
        "council_url": f"{S3}/Wingecarribee%20DCP%202010%20-%20Mittagong%20Town%20Plan%20-%20as%20amended%20%2017%20Jun%202015.pdf",
        "local_pdf": "mittagong_town_plan.pdf",
    },
    {
        "chapter_key": "wingecarribee-moss-vale-town-plan",
        "chapter_label": "Moss Vale Town Plan (as amended 17 Jun 2015)",
        "council_url": f"{S3}/Wingecarribee%20DCP%202010%20-%20Moss%20Vale%20Town%20Plan%20-%20as%20amended%2017%20Jun%202015.pdf",
        "local_pdf": "mossvale_town_plan.pdf",
    },
]
REFERENCE_CHAPTER_KEY = "wingecarribee-bowral-town-plan"

LEP_ROW = {
    "instrument_type": "lep",
    "instrument_key": "wingecarribee_lep_2010",
    "instrument_label": "Wingecarribee Local Environmental Plan 2010",
    "council": "wingecarribee",
    "legislation_url": "https://legislation.nsw.gov.au/view/html/inforce/current/epi-2010-0245",
}


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def upload_to_r2(local_path: str, key: str) -> str:
    import boto3

    r2_path = f"source-pdfs/dcps/wingecarribee/v1.0-baseline/{key}.pdf"
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )
    client.upload_file(local_path, os.environ["R2_BUCKET_NAME"], r2_path)
    return r2_path


def main():
    pdf_dir = None
    for a in sys.argv[1:]:
        if a.startswith("--pdf-dir="):
            pdf_dir = a.split("=", 1)[1]
    if not pdf_dir:
        print("Pass --pdf-dir=<dir containing the three town plan PDFs>")
        sys.exit(1)

    db_url = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
    if not db_url:
        print("No SUPABASE_DB_URL/DATABASE_URL set")
        sys.exit(1)
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    for ch in CHAPTERS:
        local = os.path.join(pdf_dir, ch["local_pdf"])
        if not os.path.exists(local):
            print(f"MISSING local PDF: {local}")
            sys.exit(1)
        digest = sha256_of(local)
        print(f"{ch['chapter_key']}: sha256={digest[:16]}... size={os.path.getsize(local):,}")

        cur.execute(
            "SELECT id FROM dcp_chapter_registry WHERE council='wingecarribee' AND chapter_key=%s",
            (ch["chapter_key"],),
        )
        if cur.fetchone():
            print("  SKIP (already registered)")
            continue
        if DRY_RUN:
            print("  DRY-RUN: would upload to R2 + insert registry row")
            continue

        r2_path = upload_to_r2(local, ch["chapter_key"])
        print(f"  uploaded: {r2_path}")
        cur.execute(
            """
            INSERT INTO dcp_chapter_registry
              (council, dcp_name, doc_type, chapter_key, chapter_label,
               council_url, r2_current_path, r2_version_label, content_hash,
               is_active, needs_extraction, is_spatial, is_inert,
               registration_status, notes)
            VALUES ('wingecarribee', 'Wingecarribee DCP 2010', 'dcp', %s, %s,
                    %s, %s, 'v1.0-baseline', %s,
                    TRUE, FALSE, FALSE, FALSE,
                    'confirmed',
                    'Town plan monitored for the numeric setback controls (insert_wingecarribee_setbacks.py). Values identical across the three town plans (Phase-0, 2026-07-14). The DCP 2026 consolidation will surface here as a URL/hash change.')
            """,
            (ch["chapter_key"], ch["chapter_label"], ch["council_url"], r2_path, digest),
        )
        print("  registry row inserted")

    # Link the 32 numeric rows to the reference chapter (closes the watchdog
    # blind-spot check; enables change-triggered needs_review + last_verified_at).
    if DRY_RUN:
        cur.execute(
            "SELECT COUNT(*) FROM dcp_setback_controls WHERE lga='wingecarribee' AND source_chapter_key IS NULL"
        )
        print(f"DRY-RUN: would link {cur.fetchone()[0]} control rows to {REFERENCE_CHAPTER_KEY}")
    else:
        cur.execute(
            """
            UPDATE dcp_setback_controls
            SET source_chapter_key = %s
            WHERE lga = 'wingecarribee' AND source_chapter_key IS NULL
            """,
            (REFERENCE_CHAPTER_KEY,),
        )
        print(f"linked {cur.rowcount} control rows to {REFERENCE_CHAPTER_KEY}")

    # LEP watch for the land-use table / upzoning permissibility panel.
    cur.execute(
        "SELECT id FROM instrument_registry WHERE instrument_key=%s",
        (LEP_ROW["instrument_key"],),
    )
    if cur.fetchone():
        print("LEP already registered")
    elif DRY_RUN:
        print(f"DRY-RUN: would register {LEP_ROW['instrument_key']}")
    else:
        cur.execute(
            """
            INSERT INTO instrument_registry
              (instrument_type, instrument_key, instrument_label, council,
               legislation_url, needs_review, check_failures, is_active, notes)
            VALUES (%s, %s, %s, %s, %s, FALSE, 0, TRUE,
                    'Backs lep_land_use_table (scrape 2026-07-14) and the upzoning tool permissibility panel.')
            """,
            (LEP_ROW["instrument_type"], LEP_ROW["instrument_key"],
             LEP_ROW["instrument_label"], LEP_ROW["council"], LEP_ROW["legislation_url"]),
        )
        print(f"registered {LEP_ROW['instrument_key']}")

    if not DRY_RUN:
        conn.commit()
    conn.close()
    print(f"\nDone. dry_run={DRY_RUN}")


if __name__ == "__main__":
    main()
