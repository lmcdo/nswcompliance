#!/usr/bin/env python3
"""
DCP Post-Commit Validation
==========================
Runs after dcp-commit.yml to verify provisions are correctly stored and
accessible. Designed to catch silent failures that look like a successful
commit but result in bad data in production.

Checks:
  1. PDF page citations — all pdf_page values within actual PDF page count
  2. Enrichment completeness — no NULL v2_is_actionable after enrichment
  3. Duplicate detection — no ref_number with both is_current and !is_current rows
     for the same chapter (indicates failed soft-delete of legacy provisions)
  4. API smoke test — provisions endpoint returns results for the council
  5. Golden provisions — known ref_numbers survived the update (optional, if
     golden file exists at scripts/golden_provisions/<council>.json)

Usage:
    python3 scripts/dcp_post_commit_check.py --council inner_west
    python3 scripts/dcp_post_commit_check.py --council waverley --no-api
    python3 scripts/dcp_post_commit_check.py --council ashfield --verify-url https://verify.plotdetect.com.au

Exit codes:
    0 = all checks passed
    1 = one or more checks failed
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import boto3
import pdfplumber
import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL         = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
R2_ACCOUNT_ID        = os.environ.get("R2_ACCOUNT_ID", "")
R2_BUCKET_NAME       = os.environ.get("R2_BUCKET_NAME", "")
R2_ACCESS_KEY_ID     = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
TELEGRAM_BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID     = os.environ.get("TELEGRAM_CHAT_ID", "")

R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Canonical slug → LGA slug used in the provisions API lga param
COUNCIL_LGA_MAP: dict[str, str] = {
    "inner_west":  "inner_west",
    "marrickville": "marrickville",
    "leichhardt":  "leichhardt",
    "ashfield":    "ashfield",
    "waverley":    "waverley",
    "ku_ring_gai": "ku_ring_gai",
}


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def send_telegram(msg: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Check 1: PDF page citations
# ---------------------------------------------------------------------------

def check_pdf_page_citations(
    council: str,
    conn: psycopg2.extensions.connection,
) -> tuple[bool, list[str]]:
    """
    For each chapter with needs_extraction=FALSE (just committed), download
    the chapter PDF from R2 and check that all stored pdf_page values are
    within the PDF's actual page count.
    Returns (passed, issues).
    """
    issues: list[str] = []

    if not all([R2_ACCOUNT_ID, R2_BUCKET_NAME, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]):
        return True, ["[SKIP] R2 credentials not set — skipping PDF page check"]

    s3 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, chapter_key, r2_current_path, page_start, page_end
        FROM dcp_chapter_registry
        WHERE council = %s
          AND needs_extraction = FALSE
          AND r2_current_path IS NOT NULL
        ORDER BY chapter_key
        """,
        (council,),
    )
    chapters = cur.fetchall()

    if not chapters:
        issues.append(f"[WARN] No committed chapters found for council={council}")
        cur.close()
        return True, issues

    for chapter_id, chapter_key, r2_path, db_page_start, db_page_end in chapters:
        print(f"  Checking PDF citations: [{council}/{chapter_key}]")

        # 1a. Get max pdf_page stored in DB for this chapter
        cur.execute(
            """
            SELECT MAX(pdf_page), MIN(pdf_page), COUNT(*)
            FROM regulatory_provisions
            WHERE source_council = %s
              AND source_chapter_key = %s
              AND is_current = TRUE
            """,
            (council, chapter_key),
        )
        row = cur.fetchone()
        if not row or row[2] == 0:
            issues.append(f"  [{chapter_key}] No is_current provisions found after commit")
            continue

        max_page, min_page, provision_count = row

        # 1b. Download PDF from R2, check actual page count
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = Path(tmpdir) / f"{chapter_key}.pdf"
            try:
                s3.download_file(R2_BUCKET_NAME, r2_path, str(pdf_path))
            except Exception as exc:
                issues.append(f"  [{chapter_key}] R2 download failed: {exc}")
                continue

            try:
                with pdfplumber.open(pdf_path) as pdf:
                    actual_pages = len(pdf.pages)
            except Exception as exc:
                issues.append(f"  [{chapter_key}] pdfplumber failed: {exc}")
                continue

        # 1c. Compare
        if max_page > actual_pages:
            issues.append(
                f"  [{chapter_key}] CITATION ERROR: max pdf_page={max_page} "
                f"exceeds PDF page count={actual_pages} "
                f"({provision_count} provisions, pages {min_page}–{max_page})"
            )
        else:
            print(
                f"    OK — {provision_count} provisions, "
                f"pages {min_page}–{max_page} within {actual_pages}-page PDF"
            )

    cur.close()
    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Check 2: Enrichment completeness
# ---------------------------------------------------------------------------

def check_enrichment_completeness(
    council: str,
    conn: psycopg2.extensions.connection,
) -> tuple[bool, list[str]]:
    """
    After enrichment, no provision that was set to NULL (pending enrichment) should
    remain NULL for v2_is_actionable. If enrichment ran cleanly, all NULL-actionable
    provisions from this council will have been classified.
    """
    issues: list[str] = []
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE source_council = %s
          AND is_current = TRUE
          AND v2_is_actionable IS NULL
        """,
        (council,),
    )
    null_count = cur.fetchone()[0]

    cur.execute(
        """
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE source_council = %s
          AND is_current = TRUE
        """,
        (council,),
    )
    total = cur.fetchone()[0]

    cur.close()

    if null_count > 0:
        pct = 100 * null_count / total if total > 0 else 0
        issues.append(
            f"  ENRICHMENT INCOMPLETE: {null_count}/{total} ({pct:.1f}%) "
            f"provisions have NULL v2_is_actionable — enrichment pipeline may not have run"
        )
    else:
        print(f"    OK — all {total} provisions have v2_is_actionable set")

    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Check 3: Duplicate detection
# ---------------------------------------------------------------------------

def check_duplicates(
    council: str,
    conn: psycopg2.extensions.connection,
) -> tuple[bool, list[str]]:
    """
    Detect ref_numbers that appear as both is_current=TRUE and is_current=FALSE
    for the same council. This indicates the soft-delete did not retire the old
    provisions (typically the legacy NULL source_chapter_key gap).

    Note: same ref_number across different chapter_keys is expected (e.g.
    section numbers restart per chapter). We group by (ref_number, source_chapter_key)
    where is_current=FALSE rows have NULL chapter key (legacy).
    """
    issues: list[str] = []
    cur = conn.cursor()

    # Case 1: duplicate is_current=TRUE (two live versions of same provision)
    cur.execute(
        """
        SELECT ref_number, source_chapter_key, COUNT(*) as n
        FROM regulatory_provisions
        WHERE source_council = %s
          AND is_current = TRUE
        GROUP BY ref_number, source_chapter_key
        HAVING COUNT(*) > 1
        ORDER BY n DESC
        LIMIT 20
        """,
        (council,),
    )
    live_dupes = cur.fetchall()
    if live_dupes:
        dupe_lines = "\n".join(
            f"    ref={r} chapter={c or 'NULL'} count={n}"
            for r, c, n in live_dupes
        )
        issues.append(
            f"  DUPLICATE LIVE PROVISIONS ({len(live_dupes)} ref_numbers):\n{dupe_lines}"
        )
    else:
        print(f"    OK — no duplicate is_current=TRUE provisions")

    # Case 2: ref_number appears as is_current=TRUE in new chapter AND is_current=FALSE
    # with source_chapter_key=NULL (legacy unretired provisions)
    cur.execute(
        """
        SELECT COUNT(DISTINCT ref_number)
        FROM regulatory_provisions old
        WHERE old.source_council = %s
          AND old.is_current = FALSE
          AND old.source_chapter_key IS NULL
          AND EXISTS (
              SELECT 1
              FROM regulatory_provisions new
              WHERE new.source_council = old.source_council
                AND new.ref_number = old.ref_number
                AND new.is_current = TRUE
                AND new.source_chapter_key IS NOT NULL
          )
        """,
        (council,),
    )
    ghost_count = cur.fetchone()[0]
    if ghost_count > 0:
        issues.append(
            f"  LEGACY NULL GHOST PROVISIONS: {ghost_count} ref_numbers have "
            f"is_current=FALSE rows with source_chapter_key=NULL alongside live "
            f"is_current=TRUE rows — soft-delete of legacy provisions may be incomplete"
        )
    else:
        print(f"    OK — no unretired legacy NULL provisions detected")

    cur.close()
    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Check 4: API smoke test
# ---------------------------------------------------------------------------

def check_api_smoke(
    council: str,
    verify_url: str,
) -> tuple[bool, list[str]]:
    """
    Hit the /api/provisions endpoint with lga=<council> and verify we get
    a non-empty result set. This confirms the DB write is visible through
    the API layer (cache warmed, connection pool healthy).
    """
    issues: list[str] = []
    lga_slug = COUNCIL_LGA_MAP.get(council, council)
    endpoint = f"{verify_url.rstrip('/')}/api/provisions"

    try:
        resp = requests.get(
            endpoint,
            params={"lga": lga_slug, "limit": "5", "q": ""},
            timeout=15,
        )
    except Exception as exc:
        issues.append(f"  API smoke test failed (network): {exc}")
        return False, issues

    if resp.status_code != 200:
        issues.append(
            f"  API returned HTTP {resp.status_code} for lga={lga_slug} — "
            f"body: {resp.text[:200]}"
        )
        return False, issues

    try:
        data = resp.json()
    except Exception:
        issues.append(f"  API returned non-JSON response: {resp.text[:200]}")
        return False, issues

    # The provisions endpoint returns either {provisions: [...]} or {results: [...]}
    provisions = data.get("provisions") or data.get("results") or []
    count = data.get("total") or data.get("count") or len(provisions)

    if count == 0:
        issues.append(
            f"  API returned 0 provisions for lga={lga_slug} — "
            f"data may not be visible through the API layer"
        )
    else:
        print(f"    OK — API returned {count} provisions for lga={lga_slug}")

    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Check 5: Golden provisions regression
# ---------------------------------------------------------------------------

def check_golden_provisions(
    council: str,
    conn: psycopg2.extensions.connection,
) -> tuple[bool, list[str]]:
    """
    If a golden file exists at scripts/golden_provisions/<council>.json,
    verify all listed ref_numbers exist in is_current=TRUE provisions.

    Golden file format:
        [
            {"ref_number": "B1.4.1", "section_header": "Waste Storage"},
            ...
        ]
    """
    issues: list[str] = []
    golden_dir = Path(__file__).parent / "golden_provisions"
    golden_file = golden_dir / f"{council}.json"

    if not golden_file.exists():
        print(f"    SKIP — no golden file at {golden_file}")
        return True, []

    try:
        golden = json.loads(golden_file.read_text(encoding="utf-8"))
    except Exception as exc:
        issues.append(f"  Could not read golden file: {exc}")
        return False, issues

    if not golden:
        return True, []

    ref_numbers = [g["ref_number"] for g in golden]
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ref_number
        FROM regulatory_provisions
        WHERE source_council = %s
          AND is_current = TRUE
          AND ref_number = ANY(%s)
        """,
        (council, ref_numbers),
    )
    found = {row[0] for row in cur.fetchall()}
    cur.close()

    missing = [r for r in ref_numbers if r not in found]
    if missing:
        issues.append(
            f"  GOLDEN REGRESSION: {len(missing)}/{len(ref_numbers)} known provisions "
            f"missing after update: {', '.join(missing[:10])}"
            + (" ..." if len(missing) > 10 else "")
        )
    else:
        print(f"    OK — all {len(ref_numbers)} golden provisions present")

    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="DCP post-commit validation checks")
    parser.add_argument("--council", required=True, help="Council slug (e.g. waverley)")
    parser.add_argument(
        "--verify-url",
        default=os.environ.get("VERIFY_APP_URL", "https://verify.plotdetect.com.au"),
        help="Base URL of the Verify app (for API smoke test)",
    )
    parser.add_argument("--no-api", action="store_true", help="Skip API smoke test")
    args = parser.parse_args()

    council = args.council
    all_issues: list[str] = []
    all_passed = True

    print(f"\nDCP Post-Commit Validation — council={council}")
    print("=" * 60)

    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)

    # 1. PDF page citations
    print("\n[1] PDF page citations")
    passed, issues = check_pdf_page_citations(council, conn)
    if not passed:
        all_passed = False
        all_issues.extend(issues)
    for issue in issues:
        print(issue)

    # 2. Enrichment completeness
    print("\n[2] Enrichment completeness")
    passed, issues = check_enrichment_completeness(council, conn)
    if not passed:
        all_passed = False
        all_issues.extend(issues)
    for issue in issues:
        print(issue)

    # 3. Duplicate detection
    print("\n[3] Duplicate detection")
    passed, issues = check_duplicates(council, conn)
    if not passed:
        all_passed = False
        all_issues.extend(issues)
    for issue in issues:
        print(issue)

    # 4. API smoke test
    if not args.no_api:
        print(f"\n[4] API smoke test ({args.verify_url})")
        passed, issues = check_api_smoke(council, args.verify_url)
        if not passed:
            all_passed = False
            all_issues.extend(issues)
        for issue in issues:
            print(issue)
    else:
        print("\n[4] API smoke test — SKIPPED (--no-api)")

    # 5. Golden provisions
    print("\n[5] Golden provisions regression")
    passed, issues = check_golden_provisions(council, conn)
    if not passed:
        all_passed = False
        all_issues.extend(issues)
    for issue in issues:
        print(issue)

    conn.close()

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        summary = f"DCP post-commit check PASSED — council={council}"
        print(f"RESULT: {summary}")
        send_telegram(summary)
        sys.exit(0)
    else:
        summary_lines = [f"DCP post-commit check FAILED — council={council}"]
        summary_lines.extend(all_issues)
        full_summary = "\n".join(summary_lines)
        print(f"RESULT: FAILED\n" + "\n".join(all_issues))
        send_telegram(full_summary[:4000])  # Telegram max message length ~4096
        sys.exit(1)


if __name__ == "__main__":
    main()
