#!/usr/bin/env python3
"""
Confirm or reject auto-detected DCP chapters.

Auto-detected chapters are discovered by r2_monitor.py during hub scrapes
and inserted with is_active=FALSE, registration_status='auto_detected'.
This CLI lets you review them and either:
  - confirm (download PDF, upload to R2, activate for monitoring)
  - reject (mark as rejected so they don't re-appear)

Usage:
    python scripts/confirm_chapter.py --list
    python scripts/confirm_chapter.py --confirm <id> [--extract]
    python scripts/confirm_chapter.py --confirm <id> --spatial
    python scripts/confirm_chapter.py --confirm <id> --inert
    python scripts/confirm_chapter.py --reject <id>
    python scripts/confirm_chapter.py --reject-all

Exit codes:
    0 = success
    1 = error
"""

import argparse
import hashlib
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

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]
R2_ACCOUNT_ID = os.environ["R2_ACCOUNT_ID"]
R2_BUCKET_NAME = os.environ["R2_BUCKET_NAME"]
R2_ACCESS_KEY_ID = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
R2_PUBLIC_BASE = "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "application/pdf,*/*",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
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


def list_pending(conn) -> list[dict]:
    """List all auto-detected chapters pending review."""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, council, chapter_key, chapter_label, council_url, created_at
        FROM dcp_chapter_registry
        WHERE registration_status = 'auto_detected'
        ORDER BY council, created_at
    """)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    return rows


def confirm_chapter(
    conn, chapter_id: int, extract: bool, spatial: bool, inert: bool,
) -> int:
    """Download PDF, upload to R2, and activate a chapter."""
    cur = conn.cursor()
    cur.execute(
        """SELECT id, council, dcp_name, chapter_key, chapter_label, council_url,
                  council_page_url, registration_status
           FROM dcp_chapter_registry WHERE id = %s""",
        (chapter_id,),
    )
    row = cur.fetchone()
    cur.close()

    if not row:
        print(f"ERROR: No chapter with id={chapter_id}")
        return 1

    cols = ["id", "council", "dcp_name", "chapter_key", "chapter_label",
            "council_url", "council_page_url", "registration_status"]
    ch = dict(zip(cols, row))

    if ch["registration_status"] != "auto_detected":
        print(f"Chapter {chapter_id} is not auto_detected (status: {ch['registration_status']})")
        return 1

    council = ch["council"]
    key = ch["chapter_key"]
    url = ch["council_url"]

    print(f"Confirming: {council}/{key}")
    print(f"  Label: {ch['chapter_label']}")
    print(f"  URL:   {url}")

    # Download PDF
    print("\n  Downloading PDF...")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=90, allow_redirects=True)
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "")
        if "pdf" not in ct.lower() and not url.lower().endswith(".pdf"):
            print(f"  ERROR: Not a PDF (Content-Type: {ct})")
            return 1
    except Exception as exc:
        print(f"  ERROR downloading: {exc}")
        return 1

    content = resp.content
    content_hash = sha256(content)
    content_len = len(content)
    etag = resp.headers.get("ETag")
    last_mod = resp.headers.get("Last-Modified")
    print(f"  Downloaded: {content_len:,} bytes  SHA-256: {content_hash[:20]}...")

    # Upload to R2
    r2_path = f"source-pdfs/dcps/{council}/v1.0-baseline/{key}.pdf"
    r2_public = R2_PUBLIC_BASE + r2_path
    print(f"  Uploading to R2: {r2_path}")
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
        # Verify upload
        obj = s3.get_object(Bucket=R2_BUCKET_NAME, Key=r2_path)
        verify_hash = sha256(obj["Body"].read())
        if verify_hash != content_hash:
            print(f"  CRITICAL: R2 upload verification FAILED")
            return 1
        print(f"  Uploaded and verified")
    except Exception as exc:
        print(f"  ERROR uploading to R2: {exc}")
        return 1

    # Update registry
    now = datetime.now(timezone.utc)
    needs_extraction = extract and not spatial and not inert
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE dcp_chapter_registry SET
            is_active = TRUE,
            registration_status = 'confirmed',
            r2_current_path = %s,
            r2_version_label = 'v1.0-baseline',
            r2_public_pdf_url = %s,
            content_hash = %s,
            url_content_length = %s,
            url_etag = %s,
            url_last_modified = %s,
            url_last_checked = %s,
            url_last_changed = %s,
            needs_extraction = %s,
            is_spatial = %s,
            is_inert = %s,
            check_failures = 0,
            updated_at = NOW()
        WHERE id = %s
        """,
        (
            r2_path, r2_public, content_hash, content_len,
            etag, last_mod, now, now,
            needs_extraction, spatial, inert,
            chapter_id,
        ),
    )
    conn.commit()
    cur.close()

    mode = (
        "spatial — no extraction" if spatial else
        "inert (cover/ToC) — silent" if inert else
        "queued for extraction" if extract else
        "monitoring only"
    )
    print(f"\n  Confirmed: {council}/{key} ({mode})")

    send_telegram(
        f"DCP chapter confirmed [{council}]\n"
        f"{ch['chapter_label']}\n"
        f"Key: {key} | {mode}"
    )

    if extract:
        print(f"\n  NEXT: python scripts/dcp_extract_changed.py --council {council}")

    return 0


def reject_chapter(conn, chapter_id: int) -> int:
    """Mark a chapter as rejected."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE dcp_chapter_registry SET registration_status = 'rejected', updated_at = NOW() WHERE id = %s AND registration_status = 'auto_detected' RETURNING chapter_key, council",
        (chapter_id,),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    if not row:
        print(f"No auto_detected chapter with id={chapter_id}")
        return 1
    print(f"Rejected: {row[1]}/{row[0]}")
    return 0


def reject_all(conn) -> int:
    """Reject all auto-detected chapters."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE dcp_chapter_registry SET registration_status = 'rejected', updated_at = NOW() WHERE registration_status = 'auto_detected' RETURNING id"
    )
    count = cur.rowcount
    conn.commit()
    cur.close()
    print(f"Rejected {count} auto-detected chapter(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Review auto-detected DCP chapters")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List pending auto-detected chapters")
    group.add_argument("--confirm", type=int, metavar="ID", help="Confirm chapter by ID")
    group.add_argument("--reject", type=int, metavar="ID", help="Reject chapter by ID")
    group.add_argument("--reject-all", action="store_true", help="Reject all auto-detected chapters")

    parser.add_argument("--extract", action="store_true", help="Queue for provision extraction")
    parser.add_argument("--spatial", action="store_true", help="Spatial/map doc — track but don't extract")
    parser.add_argument("--inert", action="store_true", help="Cover/ToC — silent tracking only")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    if args.list:
        rows = list_pending(conn)
        conn.close()
        if not rows:
            print("No auto-detected chapters pending review.")
            return 0
        print(f"\n{len(rows)} auto-detected chapter(s) pending review:\n")
        for r in rows:
            age = (datetime.now(timezone.utc) - r["created_at"].replace(tzinfo=timezone.utc)).days
            print(f"  ID {r['id']:>5}  {r['council']:<20}  {r['chapter_label'][:50]}")
            print(f"          {r['council_url']}")
            print(f"          detected {age}d ago")
            print()
        print("Actions:")
        print("  python scripts/confirm_chapter.py --confirm <ID> --extract")
        print("  python scripts/confirm_chapter.py --confirm <ID> --spatial")
        print("  python scripts/confirm_chapter.py --reject <ID>")
        return 0

    if args.confirm:
        result = confirm_chapter(conn, args.confirm, args.extract, args.spatial, args.inert)
        conn.close()
        return result

    if args.reject is not None:
        result = reject_chapter(conn, args.reject)
        conn.close()
        return result

    if args.reject_all:
        result = reject_all(conn)
        conn.close()
        return result

    return 0


if __name__ == "__main__":
    sys.exit(main())
