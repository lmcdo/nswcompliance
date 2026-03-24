#!/usr/bin/env python3
"""
Weekly DCP Chapter Monitor
===========================
Polls every council_url in dcp_chapter_registry, detects PDF changes via
content hash, uploads new versions to R2, and flags chapters for re-extraction.

Run this on a weekly schedule (cron, GitHub Actions, or manual).

Usage:
    python3 scripts/r2_monitor.py               # check all active chapters
    python3 scripts/r2_monitor.py --council marrickville
    python3 scripts/r2_monitor.py --dry-run     # report only, no changes
    python3 scripts/r2_monitor.py --force       # re-download all regardless of Content-Length

Exit codes:
    0 = no changes detected
    1 = error during run
    2 = changes detected (triggers downstream pipeline in CI)
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
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

R2_ACCOUNT_ID        = os.environ["R2_ACCOUNT_ID"]
R2_BUCKET_NAME       = os.environ["R2_BUCKET_NAME"]
R2_ACCESS_KEY_ID     = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
DATABASE_URL         = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

R2_ENDPOINT          = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
SOURCE_PDF_PREFIX    = "source-pdfs"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "application/pdf,*/*",
}

SANITY_MAX_CHANGE_PCT = 40  # Alert if >40% of a council's chapters changed in one run

# ── Telegram alerting ────────────────────────────────────────────────────────
def send_telegram(message: str) -> None:
    """Send a Telegram message. Silently no-ops if env vars not set."""
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
        pass  # Never let alerting kill the pipeline


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def head_request(url: str) -> dict:
    """HTTP HEAD to cheaply check Content-Length before downloading."""
    try:
        resp = requests.head(url, headers=HEADERS, timeout=30, allow_redirects=True)
        return {
            "content_length": resp.headers.get("Content-Length"),
            "etag": resp.headers.get("ETag"),
            "last_modified": resp.headers.get("Last-Modified"),
            "status": resp.status_code,
        }
    except Exception as exc:
        return {"error": str(exc), "status": None}


def download_pdf(url: str, retries: int = 3) -> tuple[bytes, dict]:
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
            resp.raise_for_status()
            return resp.content, dict(resp.headers)
        except Exception as exc:
            print(f"    [attempt {attempt}/{retries}] {exc}")
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Failed to download after {retries} attempts: {url}")


def next_version_label(current: str) -> str:
    """Increment version label: v1.0-baseline → v1.1, v1.1 → v1.2, v2.3 → v2.4"""
    import re
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    if current == "v1.0-baseline":
        return f"v1.1-{date_str}"
    m = re.match(r"v(\d+)\.(\d+)", current)
    if m:
        major, minor = int(m.group(1)), int(m.group(2))
        return f"v{major}.{minor + 1}-{date_str}"
    return f"v2.0-{date_str}"


def r2_path_for_version(current_path: str, new_version: str) -> str:
    """
    Given current r2 path like:
      source-pdfs/dcps/marrickville/v1.0-baseline/part2-s10-parking.pdf
    Return new path with updated version segment.
    """
    parts = current_path.split("/")
    # version is the 3rd path segment (index 3 for source-pdfs/dcps/{council}/{version}/...)
    if len(parts) >= 4:
        parts[3] = new_version
    return "/".join(parts)


def run_monitor(
    council_filter: str | None,
    s3,
    conn,
    dry_run: bool = False,
    force: bool = False,
) -> dict:
    """
    Main monitor loop.
    Returns summary dict with counts and list of changed chapters.
    """
    cur = conn.cursor()
    now = datetime.now(timezone.utc)

    # Fetch active chapters with council URLs
    query = """
        SELECT id, council, chapter_key, chapter_label, council_url,
               r2_current_path, r2_version_label,
               content_hash, url_content_length, check_failures
        FROM dcp_chapter_registry
        WHERE is_active = TRUE
          AND council_url IS NOT NULL
    """
    params = []
    if council_filter:
        query += " AND council = %s"
        params.append(council_filter)
    query += " ORDER BY council, sort_order"

    cur.execute(query, params)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    chapters = [dict(zip(cols, row)) for row in rows]

    print(f"Checking {len(chapters)} chapters...")

    results = {
        "checked": 0,
        "changed": [],
        "unchanged": 0,
        "failed": 0,
        "skipped_no_url": 0,
    }

    for chapter in chapters:
        chapter_id   = chapter["id"]
        council      = chapter["council"]
        key          = chapter["chapter_key"]
        label        = chapter["chapter_label"]
        url          = chapter["council_url"]
        r2_path      = chapter["r2_current_path"]
        version      = chapter["r2_version_label"]
        stored_hash  = chapter["content_hash"]
        stored_len   = chapter["url_content_length"]
        failures     = chapter["check_failures"] or 0

        print(f"\n  {council}/{key}")

        try:
            # Step 1: Quick HEAD check on Content-Length
            head = head_request(url)
            if head.get("status") not in (200, 206):
                raise RuntimeError(f"HEAD returned HTTP {head.get('status')}: {url}")

            remote_len = head.get("content_length")
            if remote_len:
                remote_len = int(remote_len)

            # Skip full download only if BOTH Content-Length AND ETag match stored values.
            # Content-Length alone is not reliable — some councils serve different PDFs
            # at the same byte count. Requiring both signals reduces false-negative risk.
            stored_etag = chapter.get("url_etag")
            new_etag_head = head.get("etag")
            content_length_match = (
                not force
                and stored_hash
                and remote_len
                and stored_len
                and remote_len == stored_len
            )
            etag_match = (
                stored_etag
                and new_etag_head
                and stored_etag == new_etag_head
            )
            if content_length_match and etag_match:
                print(f"    [unchanged] Content-Length + ETag both match stored")
                cur.execute(
                    "UPDATE dcp_chapter_registry SET url_last_checked=%s, check_failures=0 WHERE id=%s",
                    (now, chapter_id),
                )
                if not dry_run:
                    conn.commit()
                results["unchanged"] += 1
                results["checked"] += 1
                continue
            elif content_length_match and not etag_match:
                # Content-Length matches but ETag differs or absent — download and hash anyway
                print(f"    Content-Length unchanged but ETag mismatch/absent — downloading for hash check")

            # Step 2: Full download + hash comparison
            print(f"    Downloading for hash check...")
            content, resp_headers = download_pdf(url)
            new_hash = sha256(content)
            new_len = len(content)
            new_etag = resp_headers.get("ETag")
            new_lm = resp_headers.get("Last-Modified")

            if new_hash == stored_hash:
                print(f"    [unchanged] Hash matches stored ({new_hash[:16]}...)")
                cur.execute(
                    """
                    UPDATE dcp_chapter_registry
                    SET url_last_checked=%s, url_content_length=%s,
                        url_etag=%s, url_last_modified=%s, check_failures=0
                    WHERE id=%s
                    """,
                    (now, new_len, new_etag, new_lm, chapter_id),
                )
                if not dry_run:
                    conn.commit()
                results["unchanged"] += 1
                results["checked"] += 1
                continue

            # ── CHANGE DETECTED ──────────────────────────────────────────────
            print(f"    [CHANGED] {stored_hash[:16] if stored_hash else 'NEW'} → {new_hash[:16]}")
            print(f"    Old size: {stored_len or '?':,}  New size: {new_len:,}")

            new_version = next_version_label(version or "v1.0-baseline")
            new_r2_path = r2_path_for_version(r2_path or f"source-pdfs/dcps/{council}/v1.0-baseline/{key}.pdf", new_version)

            if not dry_run:
                # Upload new version to R2
                s3.put_object(
                    Bucket=R2_BUCKET_NAME,
                    Key=new_r2_path,
                    Body=content,
                    ContentType="application/pdf",
                )
                print(f"    Uploaded → r2://{R2_BUCKET_NAME}/{new_r2_path}")

                # Update registry
                cur.execute(
                    """
                    UPDATE dcp_chapter_registry
                    SET r2_current_path=%s, r2_version_label=%s,
                        content_hash=%s, url_content_length=%s,
                        url_etag=%s, url_last_modified=%s,
                        url_last_checked=%s, url_last_changed=%s,
                        needs_extraction=TRUE, check_failures=0
                    WHERE id=%s
                    """,
                    (
                        new_r2_path, new_version,
                        new_hash, new_len,
                        new_etag, new_lm,
                        now, now,
                        chapter_id,
                    ),
                )
                conn.commit()
            else:
                print(f"    [dry-run] would upload to r2://{R2_BUCKET_NAME}/{new_r2_path}")

            results["changed"].append({
                "council": council,
                "chapter_key": key,
                "chapter_label": label,
                "old_hash": stored_hash,
                "new_hash": new_hash,
                "new_version": new_version,
                "r2_path": new_r2_path,
            })
            results["checked"] += 1

        except Exception as exc:
            print(f"    [ERROR] {exc}")
            new_failures = failures + 1
            cur.execute(
                "UPDATE dcp_chapter_registry SET url_last_checked=%s, check_failures=%s WHERE id=%s",
                (now, new_failures, chapter_id),
            )
            if not dry_run:
                conn.commit()
            results["failed"] += 1

        time.sleep(0.3)  # polite delay

    cur.close()
    return results


def sanity_check(results: dict, total_chapters: int) -> list[str]:
    """
    Return list of warnings if the change volume looks suspicious.
    A large fraction of chapters changing at once usually means a full DCP restructure,
    not routine amendments — flag for human review.
    """
    warnings = []
    n_changed = len(results["changed"])
    if total_chapters > 0:
        pct = (n_changed / total_chapters) * 100
        if pct > SANITY_MAX_CHANGE_PCT:
            warnings.append(
                f"WARNING: {n_changed}/{total_chapters} chapters changed ({pct:.0f}%). "
                f"This may indicate a full DCP restructure — review before re-extraction."
            )
    return warnings


def main():
    parser = argparse.ArgumentParser(description="Weekly DCP chapter change monitor")
    parser.add_argument("--council", help="Filter to specific council")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing to DB or R2")
    parser.add_argument("--force", action="store_true", help="Re-download all even if Content-Length unchanged")
    args = parser.parse_args()

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
    print(f"DCP Chapter Monitor — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if args.dry_run:
        print("DRY RUN")
    print("=" * 60)

    try:
        results = run_monitor(args.council, s3, conn, args.dry_run, args.force)
    finally:
        conn.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    n_changed = len(results["changed"])
    print(f"\n{'='*60}")
    print("MONITOR SUMMARY")
    print(f"{'='*60}")
    print(f"  Checked   : {results['checked']}")
    print(f"  Unchanged : {results['unchanged']}")
    print(f"  Changed   : {n_changed}")
    print(f"  Failed    : {results['failed']}")

    # ── Persistent-failure alert ─────────────────────────────────────────────
    # Warn about chapters that have failed repeatedly — these need investigation.
    if results["failed"] > 0:
        print(f"\n  {results['failed']} chapter(s) had download errors.")
        print("  Chapters with check_failures >= 3 should be investigated.")

    # ── Sanity check ─────────────────────────────────────────────────────────
    warnings = sanity_check(results, results["checked"] + results["unchanged"])
    for w in warnings:
        print(f"\n  {w}")

    # ── Telegram notifications ───────────────────────────────────────────────
    # Always notify so we have proof the pipeline ran (or didn't run cleanly).
    total_checked = results["checked"] + results["unchanged"]

    if results["failed"] > 0 and n_changed == 0:
        # BUG FIX: previously this branch exited 0 — looked like "all clear"
        # when actually nothing was successfully checked. Now exits 1 to fail CI.
        msg = (
            f"DCP Monitor ERROR\n"
            f"{results['failed']}/{total_checked} chapters failed to check.\n"
            f"No changes detected but run was not clean — investigate download errors."
        )
        print(f"\n  ERROR: {results['failed']} chapters failed with no changes detected.")
        print("  This is not a clean 'all current' result — run should be investigated.")
        send_telegram(msg)
        sys.exit(1)

    if n_changed > 0:
        print(f"\n  Changed chapters (queued for re-extraction):")
        for c in results["changed"]:
            print(f"    [{c['council']}] {c['chapter_key']} → {c['new_version']}")
            print(f"      {c['r2_path']}")

        chapters_list = "\n".join(
            f"  [{c['council']}] {c['chapter_key']} -> {c['new_version']}"
            for c in results["changed"]
        )
        warn_text = ("\n" + "\n".join(warnings)) if warnings else ""
        fail_text = f"\n  {results['failed']} chapter(s) failed to check." if results["failed"] else ""
        send_telegram(
            f"DCP Monitor: {n_changed} chapter(s) changed\n"
            f"{chapters_list}{fail_text}{warn_text}\n\n"
            f"Review file will be generated — approve before provisions go live."
        )

        print(f"\n  Next step: run the extraction pipeline on changed chapters.")
        print(f"  Chapters flagged with needs_extraction=TRUE in dcp_chapter_registry.")

        if results["failed"] > 0:
            sys.exit(1)
        sys.exit(2)  # exit code 2 = changes detected (CI trigger)
    else:
        send_telegram(
            f"DCP Monitor: no changes ({results['checked']} chapters checked)"
        )
        print("\n  No changes detected. All chapters are current.")
        sys.exit(0)


if __name__ == "__main__":
    main()
