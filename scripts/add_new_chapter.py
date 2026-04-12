#!/usr/bin/env python3
"""
Add a new DCP chapter to the registry and optionally queue it for extraction.

Usage:
    python3 scripts/add_new_chapter.py \\
        --url "https://www.innerwest.nsw.gov.au/sites/default/files/..." \\
        --council leichhardt \\
        --key "amendment-7-licensed-premises" \\
        --label "Amendment 7: C4.11 Licensed Premises and Small Bars" \\
        --extract                    # substantive chapter — queue for extraction
        --dry-run                    # preview without writing anything

    python3 scripts/add_new_chapter.py \\
        --url "https://..." \\
        --council marrickville \\
        --key "map-planning-precincts" \\
        --label "Map: Planning Precincts" \\
        --spatial                    # map/boundary doc — track but do not extract

Exit codes:
    0 = success
    1 = error (inputs invalid, download failed, DB write failed)
    2 = chapter_key already exists in registry (idempotent guard — check before re-running)

WHAT IT DOES:
    1. Validates inputs (council slug, URL reachable, PDF content-type)
    2. Downloads PDF with retries + SHA-256 hash
    3. Checks registry: aborts if chapter_key already exists (prevents duplicates)
    4. Uploads to R2: source-pdfs/dcps/{council}/v1.0-baseline/{key}.pdf
    5. Verifies upload by re-fetching from R2 and re-hashing
    6. Inserts row into dcp_chapter_registry (in a transaction — rolls back on any failure)
    7. Sends Telegram notification
    8. If --extract: prints reminder to run extraction pipeline

BULLETPROOFING:
    - Idempotent guard: refuses to add a key that already exists
    - Upload verification: re-fetches from R2 after upload to confirm hash matches
    - Atomic DB insert: wrapped in transaction, rolls back on any failure
    - PDF validation: checks Content-Type before downloading full file
    - Dry-run mode: shows exactly what would happen without writing anything
    - Consistent exit codes with r2_monitor.py and dcp_extract_changed.py
"""

import argparse
import hashlib
import io
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import boto3
import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ── Constants ─────────────────────────────────────────────────────────────────

KNOWN_COUNCILS = {
    "marrickville": {
        "dcp_name": "Marrickville DCP 2011",
        "hub_url": "https://www.innerwest.nsw.gov.au/development-controls-lep-and-dcp/marrickville-development-control-plan-dcp",
    },
    "leichhardt": {
        "dcp_name": "Leichhardt DCP 2013",
        "hub_url": "https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp/leichhardt-dcp/leichhardt-dcp",
    },
    "ashfield": {
        "dcp_name": "Ashfield DCP 2013",
        "hub_url": "https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp/ashfield-dcp/ashfield-dcp",
    },
    "woollahra": {
        "dcp_name": "Woollahra DCP 2015",
        "hub_url": "https://www.woollahra.nsw.gov.au/building_and_development/policies_and_plans/development_control_plans",
    },
    "waverley": {
        "dcp_name": "Waverley DCP 2012",
        "hub_url": "https://www.waverley.nsw.gov.au/council/plans_and_policies/waverley_development_control_plan_2012",
    },
    "ku_ring_gai": {
        "dcp_name": "Ku-ring-gai DCP",
        "hub_url": "https://www.krg.nsw.gov.au/Building-and-development/Planning-controls/Development-Control-Plans",
    },
    "city_of_sydney": {
        "dcp_name": "City of Sydney DCP 2012",
        "hub_url": "https://www.cityofsydney.nsw.gov.au/development/policies-and-controls/development-control-plans",
    },
}

R2_ACCOUNT_ID        = os.environ["R2_ACCOUNT_ID"]
R2_BUCKET_NAME       = os.environ["R2_BUCKET_NAME"]
R2_ACCESS_KEY_ID     = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
DATABASE_URL         = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

R2_ENDPOINT   = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
R2_PUBLIC_BASE = "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "application/pdf,*/*",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def send_telegram(message: str) -> None:
    token   = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
    except Exception:
        pass


def validate_url_is_pdf(url: str) -> dict:
    """
    HEAD request to confirm URL is reachable and returns a PDF.
    Returns dict with status, content_length, etag, last_modified.
    Raises RuntimeError if not PDF or not reachable.
    """
    try:
        resp = requests.head(url, headers=HEADERS, timeout=30, allow_redirects=True)
    except Exception as exc:
        raise RuntimeError(f"HEAD request failed: {exc}")

    if resp.status_code not in (200, 206):
        raise RuntimeError(f"HEAD returned HTTP {resp.status_code}: {url}")

    ct = resp.headers.get("Content-Type", "")
    if "pdf" not in ct.lower() and not url.lower().endswith(".pdf"):
        raise RuntimeError(
            f"URL does not appear to be a PDF (Content-Type: {ct}).\n"
            f"If you're sure, check the URL manually: {url}"
        )

    return {
        "content_length": int(resp.headers["Content-Length"]) if resp.headers.get("Content-Length") else None,
        "etag": resp.headers.get("ETag"),
        "last_modified": resp.headers.get("Last-Modified"),
        "status": resp.status_code,
    }


def download_pdf(url: str, retries: int = 3) -> tuple[bytes, dict]:
    """Download PDF with retries. Returns (content, response_headers)."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=90, allow_redirects=True)
            resp.raise_for_status()
            ct = resp.headers.get("Content-Type", "")
            if "pdf" not in ct.lower() and not url.lower().endswith(".pdf"):
                raise RuntimeError(f"Download returned non-PDF content type: {ct}")
            return resp.content, dict(resp.headers)
        except Exception as exc:
            print(f"    [attempt {attempt}/{retries}] {exc}")
            if attempt < retries:
                time.sleep(3 * attempt)
    raise RuntimeError(f"Failed to download after {retries} attempts: {url}")


def verify_r2_upload(s3, bucket: str, key: str, expected_hash: str) -> None:
    """
    Re-fetch the uploaded object from R2 and verify its hash matches.
    Raises RuntimeError if hash doesn't match (upload corruption).
    """
    obj = s3.get_object(Bucket=bucket, Key=key)
    content = obj["Body"].read()
    actual_hash = sha256_bytes(content)
    if actual_hash != expected_hash:
        raise RuntimeError(
            f"R2 upload verification FAILED.\n"
            f"  Expected: {expected_hash}\n"
            f"  Got:      {actual_hash}\n"
            f"  The uploaded file is corrupt — do NOT proceed with extraction."
        )


def next_sort_order(conn, council: str) -> int:
    """Return MAX(sort_order) + 10 for the council, or 1000 if none set."""
    cur = conn.cursor()
    cur.execute(
        "SELECT MAX(sort_order) FROM dcp_chapter_registry WHERE council = %s",
        (council,),
    )
    row = cur.fetchone()
    cur.close()
    if row and row[0] is not None:
        return row[0] + 10
    return 1000


def preflight_schema_check(conn) -> list[str]:
    """
    Verify all columns the INSERT relies on actually exist in dcp_chapter_registry.
    Returns list of missing column names (empty = all present).
    """
    required_columns = {
        "council", "dcp_name", "doc_type", "chapter_key", "chapter_label", "sort_order",
        "council_url", "council_page_url",
        "r2_current_path", "r2_version_label", "r2_public_pdf_url",
        "content_hash", "url_content_length", "url_etag", "url_last_modified",
        "url_last_checked", "url_last_changed",
        "is_active", "needs_extraction", "is_spatial", "is_inert",
        "created_at", "updated_at",
    }
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'dcp_chapter_registry'
          AND table_schema = 'public'
    """)
    present = {row[0] for row in cur.fetchall()}
    cur.close()
    return sorted(required_columns - present)


def increment_hub_expected_count(conn, council: str, dry_run: bool) -> int | None:
    """
    Increment hub_expected_count for the council after a chapter is added.
    Returns the new count, or None if the column doesn't exist / count was NULL.
    """
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE dcp_chapter_registry
        SET hub_expected_count = hub_expected_count + 1
        WHERE council = %s AND hub_expected_count IS NOT NULL
        RETURNING hub_expected_count
        """,
        (council,),
    )
    row = cur.fetchone()
    if not dry_run:
        conn.commit()
    cur.close()
    return row[0] if row else None


def check_existing(conn, council: str, key: str) -> dict | None:
    """Return existing registry row for council+key, or None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, chapter_label, is_active, needs_extraction FROM dcp_chapter_registry "
        "WHERE council = %s AND chapter_key = %s",
        (council, key),
    )
    row = cur.fetchone()
    cur.close()
    if row:
        return {"id": row[0], "label": row[1], "is_active": row[2], "needs_extraction": row[3]}
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add a new DCP chapter to the registry and optionally queue for extraction."
    )
    parser.add_argument("--url",     required=True, help="Council PDF URL")
    parser.add_argument("--council", required=True, help="Council slug: marrickville | leichhardt | ashfield")
    parser.add_argument("--key",     required=True, help="Stable chapter_key slug (e.g. 'amendment-7-licensed-premises')")
    parser.add_argument("--label",   required=True, help="Human-readable chapter label")
    parser.add_argument("--extract", action="store_true",
                        help="Substantive chapter — set needs_extraction=TRUE to queue for provision extraction")
    parser.add_argument("--spatial", action="store_true",
                        help="Map or spatial document — track for changes but never extract provisions")
    parser.add_argument("--inert", action="store_true",
                        help="Cover page, ToC, or other non-provision PDF — track hash silently, no extraction, no alert")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without writing anything")
    args = parser.parse_args()

    dry_run   = args.dry_run
    council   = args.council.lower().strip()
    key       = args.key.lower().strip().replace(" ", "-")
    now       = datetime.now(timezone.utc)

    print("=" * 60)
    print(f"add_new_chapter — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    if dry_run:
        print("DRY RUN — no changes will be written")
    print("=" * 60)

    # ── Input validation ──────────────────────────────────────────────────────
    print("\n[1/7] Validating inputs...")

    if council not in KNOWN_COUNCILS:
        print(f"ERROR: Unknown council '{council}'. Known: {', '.join(KNOWN_COUNCILS)}")
        return 1

    mode_flags = sum([args.extract, args.spatial, args.inert])
    if mode_flags > 1:
        print("ERROR: --extract, --spatial, and --inert are mutually exclusive.")
        print("  --extract = substantive chapter with development controls")
        print("  --spatial = map or boundary document, never extracted, Telegram alert on change")
        print("  --inert   = cover page / ToC, never extracted, fully silent on change")
        return 1

    council_info = KNOWN_COUNCILS[council]
    dcp_name     = council_info["dcp_name"]
    hub_url      = council_info["hub_url"]
    r2_path      = f"source-pdfs/dcps/{council}/v1.0-baseline/{key}.pdf"
    r2_public    = R2_PUBLIC_BASE + r2_path

    print(f"  Council   : {council} ({dcp_name})")
    print(f"  Key       : {key}")
    print(f"  Label     : {args.label}")
    print(f"  URL       : {args.url}")
    print(f"  R2 path   : {r2_path}")
    print(f"  Extract   : {args.extract}")
    print(f"  Spatial   : {args.spatial}")

    # ── URL validation ────────────────────────────────────────────────────────
    print("\n[2/7] Validating URL (HEAD request)...")
    try:
        head_info = validate_url_is_pdf(args.url)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"  HTTP {head_info['status']} OK")
    if head_info["content_length"]:
        print(f"  Content-Length: {head_info['content_length']:,} bytes")

    # ── Connect + pre-flight schema check ─────────────────────────────────────
    print("\n[3/7] Checking registry for existing entry...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    missing_cols = preflight_schema_check(conn)
    if missing_cols:
        print(f"ERROR: dcp_chapter_registry is missing required columns: {missing_cols}")
        print("  The schema may be out of date. Check migrations and re-run.")
        conn.close()
        return 1

    existing = check_existing(conn, council, key)
    if existing:
        print(f"  ABORT: chapter_key '{key}' already exists in registry (id={existing['id']})")
        print(f"  Label: {existing['label']}")
        print(f"  is_active: {existing['is_active']} | needs_extraction: {existing['needs_extraction']}")
        print()
        print("  If you want to update an existing chapter, use r2_monitor.py --force instead.")
        print("  If the key is wrong, re-run with a different --key.")
        conn.close()
        return 2
    print("  No existing entry — safe to add.")

    # ── Download PDF ──────────────────────────────────────────────────────────
    print("\n[4/7] Downloading PDF...")
    try:
        content, resp_headers = download_pdf(args.url)
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        conn.close()
        return 1

    content_hash = sha256_bytes(content)
    content_len  = len(content)
    etag         = resp_headers.get("ETag")
    last_mod     = resp_headers.get("Last-Modified")

    print(f"  Downloaded: {content_len:,} bytes")
    print(f"  SHA-256   : {content_hash}")
    if etag:
        print(f"  ETag      : {etag}")

    # ── Upload to R2 ──────────────────────────────────────────────────────────
    print("\n[5/7] Uploading to R2...")
    if dry_run:
        print(f"  [dry-run] would upload to r2://{R2_BUCKET_NAME}/{r2_path}")
    else:
        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=R2_ENDPOINT,
                aws_access_key_id=R2_ACCESS_KEY_ID,
                aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                region_name="auto",
            )
            s3.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=r2_path,
                Body=content,
                ContentType="application/pdf",
            )
            print(f"  Uploaded → r2://{R2_BUCKET_NAME}/{r2_path}")

            # ── Verify upload ─────────────────────────────────────────────────
            print("\n[6/7] Verifying upload (re-fetching from R2 to confirm hash)...")
            try:
                verify_r2_upload(s3, R2_BUCKET_NAME, r2_path, content_hash)
                print(f"  Verified — hash matches: {content_hash[:20]}...")
            except RuntimeError as exc:
                print(f"  CRITICAL: {exc}")
                print("  Upload aborted — not inserting into registry.")
                conn.close()
                return 1

        except Exception as exc:
            print(f"ERROR uploading to R2: {exc}")
            conn.close()
            return 1

    # ── Insert into registry ──────────────────────────────────────────────────
    print("\n[7/7] Inserting into dcp_chapter_registry...")
    sort_order = next_sort_order(conn, council)
    needs_extraction = args.extract and not args.spatial and not args.inert

    if dry_run:
        print(f"  [dry-run] would INSERT:")
        print(f"    council            = {council}")
        print(f"    dcp_name           = {dcp_name}")
        print(f"    chapter_key        = {key}")
        print(f"    chapter_label      = {args.label}")
        print(f"    council_url        = {args.url}")
        print(f"    council_page_url   = {hub_url}")
        print(f"    r2_current_path    = {r2_path}")
        print(f"    r2_version_label   = v1.0-baseline")
        print(f"    content_hash       = {content_hash}")
        print(f"    url_content_length = {content_len}")
        print(f"    needs_extraction   = {needs_extraction}")
        print(f"    is_spatial         = {args.spatial}")
        print(f"    is_inert           = {args.inert}")
        print(f"    sort_order         = {sort_order}")
        print(f"  [dry-run] would increment hub_expected_count for {council}")
    else:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO dcp_chapter_registry (
                    council, dcp_name, doc_type, chapter_key, chapter_label, sort_order,
                    council_url, council_page_url,
                    r2_current_path, r2_version_label, r2_public_pdf_url,
                    content_hash, url_content_length, url_etag, url_last_modified,
                    url_last_checked, url_last_changed,
                    is_active, needs_extraction, is_spatial, is_inert,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, 'dcp', %s, %s, %s,
                    %s, %s,
                    %s, 'v1.0-baseline', %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    TRUE, %s, %s, %s,
                    NOW(), NOW()
                )
                RETURNING id
                """,
                (
                    council, dcp_name, key, args.label, sort_order,
                    args.url, hub_url,
                    r2_path, r2_public,
                    content_hash, content_len, etag, last_mod,
                    now, now,
                    needs_extraction, args.spatial, args.inert,
                ),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            print(f"  Inserted — id={new_id}")
            # Increment hub_expected_count so the anomaly gate stays accurate
            new_count = increment_hub_expected_count(conn, council, dry_run=False)
            if new_count:
                print(f"  hub_expected_count updated → {new_count}")

        except Exception as exc:
            conn.rollback()
            print(f"ERROR inserting into registry: {exc}")
            conn.close()
            return 1

    conn.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    if dry_run:
        print("DRY RUN COMPLETE — no changes written")
    else:
        print("SUCCESS")
    print(f"  {council}/{key}")
    print(f"  {args.label}")
    print(f"  Hash: {content_hash}")
    if args.spatial:
        print("  Spatial document — will be hash-tracked, not extracted. Telegram alert on change.")
    elif args.inert:
        print("  Inert document (cover/ToC) — hash-tracked, no extraction, fully silent on change.")
    elif args.extract:
        print("  needs_extraction=TRUE — queued for provision extraction.")
        print()
        print("  NEXT STEP: Run the extraction pipeline:")
        print(f"    python3 scripts/dcp_extract_changed.py --council {council}")
        print()
        print("  Then verify provisions were produced:")
        print(f"""    SELECT source_chapter_key, COUNT(*) FILTER (WHERE is_current) AS current_provisions
    FROM regulatory_provisions
    WHERE source_council = '{council}' AND source_chapter_key = '{key}'
    GROUP BY 1;""")
    else:
        print("  Registered for monitoring only (no extraction scheduled).")
        print("  Re-run with --extract if this chapter contains development controls.")
    print("=" * 60)

    if not dry_run:
        mode = (
            "spatial document — no extraction"  if args.spatial else
            "inert (cover/ToC) — silent tracking" if args.inert else
            "queued for extraction"              if args.extract else
            "monitoring only"
        )
        send_telegram(
            f"New DCP chapter registered [{council}]\n"
            f"{args.label}\n"
            f"{args.url}\n"
            f"Key: {key} | {mode}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
