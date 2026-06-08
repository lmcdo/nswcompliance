#!/usr/bin/env python3
"""
Weekly DCP Chapter Monitor
===========================
For each council, scrapes the hub page (council_page_url) to re-discover
current PDF URLs, then hash-checks changed/new URLs and uploads to R2.

This approach survives council CMS migrations — URLs are re-discovered
weekly from the hub page rather than assumed stable in the registry.

Usage:
    python3 scripts/r2_monitor.py               # check all active chapters
    python3 scripts/r2_monitor.py --council marrickville
    python3 scripts/r2_monitor.py --dry-run     # report only, no changes
    python3 scripts/r2_monitor.py --force       # re-download all regardless of Content-Length
    python3 scripts/r2_monitor.py --reseed      # update council_url for all chapters from hub scrape

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
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import boto3
import psycopg2
import requests
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Hub scrapers — keyed by council slug
# Councils not listed fall back to per-chapter council_url checking
sys.path.insert(0, str(Path(__file__).parent))
try:
    from hub_scrapers import HUB_SCRAPERS, HubScrapeError
except ImportError:
    HUB_SCRAPERS = {}
    HubScrapeError = Exception


class WAFBlockError(Exception):
    """Raised when a 403 indicates WAF/access denial, not a content issue.
    Should not increment check_failures — it's an infrastructure problem, not data."""
    pass


@dataclass
class DiffResult:
    url_same:     list[str] = field(default_factory=list)   # chapter_keys: URL unchanged
    url_migrated: list[tuple] = field(default_factory=list) # (key, old_url, new_url)
    removed:      list[str] = field(default_factory=list)   # keys in registry, not on hub
    added:        list[dict] = field(default_factory=list)  # {url, label} on hub, no key match
    count_ok:     bool = True

load_dotenv(Path(__file__).parent.parent / ".env")

R2_ACCOUNT_ID        = os.environ["R2_ACCOUNT_ID"]
R2_BUCKET_NAME       = os.environ["R2_BUCKET_NAME"]
R2_ACCESS_KEY_ID     = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
DATABASE_URL         = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

R2_ENDPOINT          = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
R2_PUBLIC_BASE       = "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/"
SOURCE_PDF_PREFIX    = "source-pdfs"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "application/pdf,*/*",
}

SANITY_MAX_CHANGE_PCT = 40  # Alert if >40% of a council's chapters changed in one run

# ── Shared session for connection pooling ────────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ── Adaptive delay tracking ──────────────────────────────────────────────────
_domain_delays: dict[str, float] = {}  # domain → current delay in seconds
DEFAULT_DELAY = 2.0
MAX_DELAY = 60.0


def _get_domain(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url).netloc


def adaptive_delay(url: str) -> None:
    """Sleep for the current adaptive delay for this URL's domain."""
    domain = _get_domain(url)
    delay = _domain_delays.get(domain, DEFAULT_DELAY)
    time.sleep(delay)


def _backoff(url: str) -> None:
    """Increase delay for this domain after a rate-limit or error."""
    domain = _get_domain(url)
    current = _domain_delays.get(domain, DEFAULT_DELAY)
    _domain_delays[domain] = min(current * 2, MAX_DELAY)


def _decay(url: str) -> None:
    """Decrease delay for this domain after a success."""
    domain = _get_domain(url)
    current = _domain_delays.get(domain, DEFAULT_DELAY)
    _domain_delays[domain] = max(current * 0.8, DEFAULT_DELAY)

# ── Telegram alerting ────────────────────────────────────────────────────────
def send_telegram(message: str) -> None:
    """Send a Telegram message. Logs to stdout for Railway visibility."""
    token   = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[telegram] skipped — no token or chat_id")
        return
    original_len = len(message)
    if original_len > 4000:
        message = message[:3950] + "\n\n… (truncated — full output in Railway logs)"
    print(f"[telegram] sending message ({original_len} chars, truncated={original_len > 4000})")
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        if resp.ok:
            print(f"[telegram] sent OK ({resp.status_code})")
        else:
            print(f"[telegram] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        print(f"[telegram] send failed: {exc}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def head_request(url: str) -> dict:
    """HTTP HEAD to cheaply check Content-Length before downloading.
    Falls back to a range-0 GET if HEAD returns 405 (some council APIs
    only support GET — e.g. Canterbury Bankstown webdocs).
    """
    try:
        resp = SESSION.head(url, timeout=30, allow_redirects=True)
        if resp.status_code == 405:
            # Server doesn't support HEAD — try GET with Range header
            # to avoid downloading the full file just for metadata.
            resp = SESSION.get(
                url, timeout=30, allow_redirects=True,
                headers={**SESSION.headers, "Range": "bytes=0-0"},
                stream=True,
            )
            resp.close()
            # Range request returns 206; some servers ignore Range and return 200
            status = 200 if resp.status_code in (200, 206) else resp.status_code
            return {
                "content_length": resp.headers.get("Content-Length"),
                "etag": resp.headers.get("ETag"),
                "last_modified": resp.headers.get("Last-Modified"),
                "status": status,
            }
        return {
            "content_length": resp.headers.get("Content-Length"),
            "etag": resp.headers.get("ETag"),
            "last_modified": resp.headers.get("Last-Modified"),
            "status": resp.status_code,
        }
    except Exception as exc:
        return {"error": str(exc), "status": None}


def download_pdf(url: str, retries: int = 3) -> tuple[bytes, requests.structures.CaseInsensitiveDict]:
    for attempt in range(1, retries + 1):
        try:
            resp = SESSION.get(url, timeout=60, allow_redirects=True)
            if resp.status_code == 429:
                _backoff(url)
                delay = _domain_delays.get(_get_domain(url), DEFAULT_DELAY)
                print(f"    [429 rate-limited] backing off {delay:.0f}s")
                time.sleep(delay)
                continue
            if resp.status_code == 403:
                _backoff(url)
                raise WAFBlockError(f"HTTP 403 Forbidden (WAF/access denied): {url}")
            resp.raise_for_status()
            _decay(url)
            # Verify Content-Type is PDF — guards against HTML error pages
            # being hashed as "changes" (QA pattern bug #7).
            ct = resp.headers.get("Content-Type", "")
            if ct and "pdf" not in ct.lower() and "octet-stream" not in ct.lower():
                raise RuntimeError(
                    f"Expected PDF but got Content-Type: {ct} — "
                    f"server may have returned an error page: {url}"
                )
            # Return resp.headers directly (CaseInsensitiveDict) — do NOT convert to dict().
            # dict() loses case-insensitivity; servers/CDNs may send 'etag' (lowercase)
            # while the code looks up 'ETag', causing None to be stored every run.
            return resp.content, resp.headers
        except requests.exceptions.HTTPError as exc:
            print(f"    [attempt {attempt}/{retries}] {exc}")
            if attempt < retries:
                time.sleep(2 * attempt)
        except (RuntimeError, WAFBlockError):
            raise  # Don't retry 403/WAF blocks or content-type errors
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


def diff_urls(
    discovered: list[dict],
    stored: list[dict],
    hub_expected_count: int | None,
) -> DiffResult:
    """
    Diff hub-discovered chapters against registry-stored chapters.

    Args:
        discovered: list of {chapter_key, url, label} from hub scraper
                    chapter_key may be None for unrecognised PDFs
        stored:     list of registry rows {chapter_key, council_url, ...}
        hub_expected_count: baseline chapter count for anomaly gate (None = skip gate)

    Returns DiffResult with categorised changes.
    """
    result = DiffResult()

    # Anomaly gate: abort if scrape returned < 80% of expected
    if hub_expected_count and len(discovered) < hub_expected_count * 0.8:
        result.count_ok = False
        return result

    discovered_by_key = {d["chapter_key"]: d for d in discovered if d["chapter_key"]}
    unmatched = [d for d in discovered if d["chapter_key"] is None]
    stored_by_key = {s["chapter_key"]: s for s in stored}

    for key, stored_ch in stored_by_key.items():
        if key not in discovered_by_key:
            result.removed.append(key)
        elif discovered_by_key[key]["url"] != stored_ch["council_url"]:
            result.url_migrated.append((key, stored_ch["council_url"], discovered_by_key[key]["url"]))
        else:
            result.url_same.append(key)

    result.added = unmatched  # hub PDFs with no matching chapter_key
    return result


def _update_instrument_currency(conn, council: str, dry_run: bool) -> None:
    """Update instrument_currency.verified_at for a council's DCP after a clean run."""
    if dry_run:
        return
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO instrument_currency (council, instrument_key, instrument_label, instrument_type, verified_at)
        VALUES (%s, 'dcp', %s, 'dcp', NOW())
        ON CONFLICT (council, instrument_key) DO UPDATE
            SET verified_at = NOW(), updated_at = NOW()
        """,
        (council, f"{council.title()} DCP"),
    )
    conn.commit()
    cur.close()


def _slugify(label: str) -> str:
    """Convert a chapter label to a URL-safe slug for chapter_key."""
    import re as _re
    slug = label.lower().strip()
    slug = _re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:80]


# ── Chapter classification ──────────────────────────────────────────────────
import re as _re

_CLASSIFY_RULES: list[tuple[str, str]] = [
    # Order matters: first match wins. Most specific patterns first.
    (r"(^sheet\s+\d|map$|map\s|frontage.+map|height.+map|setback.+map|"
     r"signage.+map|lane.+map|link.+map|priority.+map|stormwater.+map|"
     r"trading.+map|open\s+space.+map|colonnades.+map|contributions.+map|"
     r"sound\s+management$|domain\s+setback)", "spatial"),
    (r"^repealed", "repealed"),
    (r"(^table\s+of\s+contents|^preliminary|^document\s+information|"
     r"^section\s+1\s.*preliminary)", "inert"),
    (r"(guide\b|manual\b|character\s+statement|waste\s+design)", "guide"),
    (r"(^chapter\s+[A-Za-z]?\d|^part\s+\d|^section\s+\d)", "text"),
]

_CLASSIFY_COMPILED = [(_re.compile(pat, _re.IGNORECASE), cat) for pat, cat in _CLASSIFY_RULES]


def classify_chapter(label: str) -> str:
    """Classify a chapter label into a category.

    Returns one of: spatial, repealed, inert, guide, text, unknown.
    Conservative — ambiguous labels return 'unknown' for manual review.
    """
    for pattern, category in _CLASSIFY_COMPILED:
        if pattern.search(label.strip()):
            return category
    return "unknown"


# Categories that are auto-handled (no pending review needed)
_AUTO_HANDLE = {
    "spatial":  {"registration_status": "confirmed", "is_active": True,  "is_spatial": True,  "is_inert": False},
    "repealed": {"registration_status": "rejected",  "is_active": False, "is_spatial": False, "is_inert": False},
    "inert":    {"registration_status": "confirmed", "is_active": True,  "is_spatial": False, "is_inert": True},
}


def _auto_register_chapter(
    conn, council: str, council_chapters: list[dict], item: dict, hub_url: str | None,
) -> dict:
    """Insert an auto-detected chapter, classifying it on insert.

    Auto-handled categories (spatial, repealed, inert) go straight to their
    final state. Text/guide/unknown stay as auto_detected for manual review.

    Returns {"category": str, "action": "registered"|"auto_handled"|"skipped"}
    for digest aggregation. Never sends individual Telegram messages.
    """
    label = item["label"]
    url = item["url"]
    slug = _slugify(label)

    if not slug:
        return {"category": "unknown", "action": "skipped"}

    category = classify_chapter(label)

    # Deduplicate: skip if this slug already exists for the council
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM dcp_chapter_registry WHERE council = %s AND chapter_key = %s",
        (council, slug),
    )
    if cur.fetchone():
        cur.close()
        print(f"    [auto-reg] {slug} already in registry — skipping")
        return {"category": category, "action": "skipped"}

    dcp_name = council_chapters[0].get("dcp_name", f"{council.title()} DCP")

    auto = _AUTO_HANDLE.get(category)
    if auto:
        # Auto-handle: insert directly into final state
        cur.execute(
            """
            INSERT INTO dcp_chapter_registry (
                council, dcp_name, doc_type, chapter_key, chapter_label,
                council_url, council_page_url,
                is_active, is_spatial, is_inert,
                needs_extraction, registration_status, detected_category,
                check_failures, created_at, updated_at
            ) VALUES (
                %s, %s, 'dcp', %s, %s,
                %s, %s,
                %s, %s, %s,
                FALSE, %s, %s,
                0, NOW(), NOW()
            )
            """,
            (
                council, dcp_name, slug, label, url, hub_url,
                auto["is_active"], auto["is_spatial"], auto["is_inert"],
                auto["registration_status"], category,
            ),
        )
        conn.commit()
        cur.close()
        print(f"    [auto-{category}] {slug}")
        return {"category": category, "action": "auto_handled"}
    else:
        # Pending review: text, guide, unknown
        cur.execute(
            """
            INSERT INTO dcp_chapter_registry (
                council, dcp_name, doc_type, chapter_key, chapter_label,
                council_url, council_page_url,
                is_active, needs_extraction, registration_status, detected_category,
                check_failures, created_at, updated_at
            ) VALUES (
                %s, %s, 'dcp', %s, %s,
                %s, %s,
                FALSE, FALSE, 'auto_detected', %s,
                0, NOW(), NOW()
            )
            """,
            (council, dcp_name, slug, label, url, hub_url, category),
        )
        conn.commit()
        cur.close()
        print(f"    [pending-{category}] {slug}")
        return {"category": category, "action": "registered"}


def _send_discovery_digest(
    council: str,
    discovered_count: int,
    previous_count: int | None,
    registration_results: list[dict],
    hub_alerts: list[str],
) -> None:
    """Send a single Telegram digest for all discoveries on a council.

    Format designed for copy-paste into Claude — structured, parseable,
    actionable.
    """
    if not registration_results and not hub_alerts:
        return

    # Aggregate by category and action
    by_cat: dict[str, dict[str, int]] = {}
    for r in registration_results:
        cat = r["category"]
        action = r["action"]
        by_cat.setdefault(cat, {"registered": 0, "auto_handled": 0, "skipped": 0})
        by_cat[cat][action] += 1

    pending_count = sum(
        c["registered"] for c in by_cat.values()
    )
    auto_count = sum(
        c["auto_handled"] for c in by_cat.values()
    )
    skipped_count = sum(
        c["skipped"] for c in by_cat.values()
    )

    # Only send if there's something actionable
    new_total = pending_count + auto_count
    if new_total == 0 and not hub_alerts:
        return

    lines = [f"DCP Discovery [{council}]"]

    # Hub PDF count delta
    if previous_count is not None:
        delta = discovered_count - previous_count
        if delta != 0:
            sign = "+" if delta > 0 else ""
            lines.append(f"Hub: {discovered_count} PDFs ({sign}{delta} since last run)")
        else:
            lines.append(f"Hub: {discovered_count} PDFs (unchanged)")
    else:
        lines.append(f"Hub: {discovered_count} PDFs (first scan)")

    # Category breakdown
    if new_total > 0:
        parts = []
        for cat in ["text", "guide", "unknown", "spatial", "repealed", "inert"]:
            if cat not in by_cat:
                continue
            counts = by_cat[cat]
            n = counts["registered"] + counts["auto_handled"]
            if n == 0:
                continue
            if cat in _AUTO_HANDLE:
                parts.append(f"{n} {cat} (auto)")
            else:
                parts.append(f"{n} {cat}")
        lines.append("New: " + ", ".join(parts))

    # Anomaly flags
    total_new = pending_count + auto_count
    if total_new > 30:
        spatial_n = by_cat.get("spatial", {}).get("auto_handled", 0)
        unknown_n = by_cat.get("unknown", {}).get("registered", 0)
        if spatial_n == 0 and total_new > 30:
            lines.append("! 0 spatial — unusual for a large DCP, check classification")
        if total_new > 0 and unknown_n / max(total_new, 1) > 0.3:
            lines.append(f"! {unknown_n} unknown ({unknown_n*100//max(total_new,1)}%) — may need new patterns")

    # URL migrations / removals from hub_alerts
    for alert in hub_alerts:
        lines.append(alert)

    # Action line
    if pending_count > 0:
        lines.append(f"Review: confirm_chapter.py --list --council {council}")

    send_telegram("\n".join(lines))


def run_monitor(
    council_filter: str | None,
    s3,
    conn,
    dry_run: bool = False,
    force: bool = False,
    reseed: bool = False,
) -> dict:
    """
    Main monitor loop.
    Returns summary dict with counts and list of changed chapters.
    """
    cur = conn.cursor()
    now = datetime.now(timezone.utc)

    # Fetch active chapters including hub page URL and expected count
    query = """
        SELECT id, council, dcp_name, chapter_key, chapter_label, council_url,
               council_page_url, hub_expected_count, hub_last_pdf_count,
               r2_current_path, r2_version_label,
               content_hash, url_content_length, url_etag, check_failures,
               COALESCE(is_spatial, FALSE) AS is_spatial,
               COALESCE(is_inert, FALSE) AS is_inert
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
    cur.close()

    # Group by council for hub-scrape approach
    by_council: dict[str, list[dict]] = defaultdict(list)
    for ch in chapters:
        by_council[ch["council"]].append(ch)

    print(f"Checking {len(chapters)} chapters across {len(by_council)} councils...")

    results = {
        "checked": 0,
        "changed": [],
        "unchanged": 0,
        "failed": 0,
        "skipped_no_url": 0,
        "hub_alerts": [],
        "waf_blocked": [],
    }

    for council, council_chapters in by_council.items():
        hub_url = council_chapters[0].get("council_page_url")
        hub_expected = council_chapters[0].get("hub_expected_count")
        hub_last_count = council_chapters[0].get("hub_last_pdf_count")
        scraper = HUB_SCRAPERS.get(council)

        # ── Hub scrape (if scraper registered and hub URL available) ───────────
        if scraper and hub_url:
            print(f"\n[{council}] Scraping hub page...")
            expected_keys = {ch["chapter_key"] for ch in council_chapters}
            expected_labels = {
                ch["chapter_key"]: ch["chapter_label"]
                for ch in council_chapters
                if ch.get("chapter_label")
            }
            try:
                discovered = scraper(hub_url, expected_keys, expected_labels=expected_labels)
                previous_count = council_chapters[0].get("hub_last_pdf_count")
                print(f"  Hub returned {len(discovered)} PDF links (previous: {previous_count or 'first scan'})")

                diff = diff_urls(discovered, council_chapters, hub_expected)

                if not diff.count_ok:
                    msg = (
                        f"DCP Monitor: hub scrape anomaly [{council}]\n"
                        f"Returned {len(discovered)} links, expected ~{hub_expected}.\n"
                        f"Possible scrape failure or hub page restructure. Skipping council."
                    )
                    print(f"  ABORT: {msg}")
                    send_telegram(msg)
                    results["hub_alerts"].append(msg)
                    results["failed"] += len(council_chapters)
                    continue

                # Collect digest items for this council
                council_hub_alerts = []
                registration_results = []

                # URL migrations — update registry and proceed to hash check
                for key, old_url, new_url in diff.url_migrated:
                    print(f"  [URL MIGRATED] {key}\n    {old_url}\n    → {new_url}")
                    if not dry_run:
                        cur2 = conn.cursor()
                        cur2.execute(
                            "UPDATE dcp_chapter_registry SET council_url = %s WHERE council = %s AND chapter_key = %s",
                            (new_url, council, key),
                        )
                        conn.commit()
                        cur2.close()
                    # Update the in-memory chapter dict so hash check uses new URL
                    for ch in council_chapters:
                        if ch["chapter_key"] == key:
                            ch["council_url"] = new_url
                    council_hub_alerts.append(f"URL migrated: {key}")
                    results["hub_alerts"].append(f"URL migration: {council}/{key}")

                # Removed chapters
                for key in diff.removed:
                    chapter_is_inert = next(
                        (ch.get("is_inert", False) for ch in council_chapters if ch["chapter_key"] == key),
                        False,
                    )
                    if chapter_is_inert:
                        print(f"  [INERT-REMOVED] {key} — not matched on hub, inert chapter, no alert")
                        continue
                    print(f"  [REMOVED] {key}")
                    council_hub_alerts.append(f"Removed from hub: {key}")
                    results["hub_alerts"].append(f"removed: {council}/{key}")

                # New/unmatched chapters — classify and auto-handle where possible.
                for item in diff.added:
                    print(f"  [NEW] {item['label']}  {item['url']}")
                    if not dry_run:
                        try:
                            reg_result = _auto_register_chapter(conn, council, council_chapters, item, hub_url)
                            registration_results.append(reg_result)
                        except Exception as exc:
                            print(f"    [auto-reg ERROR] {exc}")
                            conn.rollback()

                # Update hub_last_pdf_count for delta tracking
                if not dry_run:
                    cur2 = conn.cursor()
                    cur2.execute(
                        """UPDATE dcp_chapter_registry
                           SET hub_last_pdf_count = %s
                           WHERE council = %s AND council_page_url IS NOT NULL AND is_active = TRUE""",
                        (len(discovered), council),
                    )
                    conn.commit()
                    cur2.close()

                # Send single digest for this council (replaces per-chapter Telegram)
                _send_discovery_digest(
                    council, len(discovered), previous_count,
                    registration_results, council_hub_alerts,
                )

                # If reseed mode: update council_url for all matched chapters
                if reseed and not dry_run:
                    discovered_map = {d["chapter_key"]: d["url"] for d in discovered if d["chapter_key"]}
                    cur2 = conn.cursor()
                    updated = 0
                    for key, url in discovered_map.items():
                        cur2.execute(
                            "UPDATE dcp_chapter_registry SET council_url = %s WHERE council = %s AND chapter_key = %s AND council_url != %s",
                            (url, council, key, url),
                        )
                        updated += cur2.rowcount
                    conn.commit()
                    cur2.close()
                    print(f"  [reseed] Updated {updated} council_url values for {council}")

            except HubScrapeError as exc:
                msg = f"DCP Monitor: hub scrape failed [{council}]: {exc}"
                print(f"  HUB ERROR: {exc}")
                send_telegram(msg)
                results["hub_alerts"].append(msg)
                results["failed"] += len(council_chapters)
                continue

        # ── Per-chapter hash check ─────────────────────────────────────────────
        council_changed = 0
        council_failed = 0  # failures for THIS council only — used for currency update
        cur = conn.cursor()
        for chapter in council_chapters:
            chapter_id  = chapter["id"]
            ch_council  = chapter["council"]
            key         = chapter["chapter_key"]
            label       = chapter["chapter_label"]
            url         = chapter["council_url"]
            r2_path     = chapter["r2_current_path"]
            version     = chapter["r2_version_label"]
            stored_hash = chapter["content_hash"]
            stored_len  = chapter["url_content_length"]
            failures    = chapter["check_failures"] or 0
            is_spatial  = chapter.get("is_spatial", False)
            is_inert    = chapter.get("is_inert", False)

            print(f"\n  {ch_council}/{key}")

            try:
                # Step 1: Quick HEAD check on Content-Length
                head = head_request(url)
                head_status = head.get("status")
                if head_status == 403:
                    # WAF/access denied — don't count as check_failure (not a content issue).
                    # Log and skip, but don't increment the failure counter.
                    print(f"    [WAF] HTTP 403 — access denied, skipping (not counted as failure)")
                    _backoff(url)
                    results["failed"] += 1
                    council_failed += 1
                    adaptive_delay(url)
                    continue
                if head_status == 429:
                    _backoff(url)
                    delay = _domain_delays.get(_get_domain(url), DEFAULT_DELAY)
                    print(f"    [429] rate-limited on HEAD — backing off {delay:.0f}s, retrying")
                    time.sleep(delay)
                    head = head_request(url)
                    head_status = head.get("status")
                    if head_status == 429:
                        print(f"    [429] still rate-limited after backoff — skipping")
                        adaptive_delay(url)
                        continue
                if head_status not in (200, 206):
                    raise RuntimeError(f"HEAD returned HTTP {head_status}: {url}")

                remote_len = head.get("content_length")
                if remote_len:
                    remote_len = int(remote_len)

                # Fast-path: skip full download if ETag matches stored value.
                # ETag alone is sufficient — it is designed for this purpose and is
                # served reliably by Drupal and Squiz Matrix (98% of registered chapters).
                #
                # We do NOT require Content-Length to also match because servers may
                # serve Content-Length as the compressed size (gzip) while the monitor
                # stores len(content) = decompressed size — these will never match for
                # gzip responses even when the file is unchanged.
                stored_etag = chapter.get("url_etag")
                new_etag_head = head.get("etag")
                etag_match = (
                    not force
                    and stored_hash
                    and stored_etag
                    and new_etag_head
                    and stored_etag == new_etag_head
                )
                if etag_match:
                    print(f"    [unchanged] ETag match — skipping download")
                    cur.execute(
                        "UPDATE dcp_chapter_registry SET url_last_checked=%s, check_failures=0 WHERE id=%s",
                        (now, chapter_id),
                    )
                    # Mark linked control rows as verified current
                    cur.execute(
                        "UPDATE dcp_setback_controls SET last_verified_at=%s "
                        "WHERE source_chapter_key=%s AND lga=%s AND is_current=TRUE",
                        (now, key, ch_council),
                    )
                    if not dry_run:
                        conn.commit()
                    results["unchanged"] += 1
                    results["checked"] += 1
                    adaptive_delay(url)
                    continue
                elif stored_etag and not new_etag_head:
                    print(f"    Stored ETag but server no longer serving one — downloading for hash check")
                elif not stored_etag:
                    # No stored ETag yet (first run, or server didn't serve one previously)
                    pass

                # Step 2: Full download + hash comparison
                print(f"    Downloading for hash check...")
                content, resp_headers = download_pdf(url)
                new_hash = sha256(content)
                # Store the HEAD Content-Length (not len(content)) so future HEAD
                # fast-path comparisons use the same value the server reports.
                # Servers may gzip responses, making len(content) != Content-Length.
                new_len = remote_len if remote_len else len(content)
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
                    # Mark linked control rows as verified current
                    cur.execute(
                        "UPDATE dcp_setback_controls SET last_verified_at=%s "
                        "WHERE source_chapter_key=%s AND lga=%s AND is_current=TRUE",
                        (now, key, ch_council),
                    )
                    if not dry_run:
                        conn.commit()
                    results["unchanged"] += 1
                    results["checked"] += 1
                    continue

                # ── CHANGE DETECTED ──────────────────────────────────────────
                print(f"    [CHANGED] {stored_hash[:16] if stored_hash else 'NEW'} → {new_hash[:16]}")
                old_size = f"{stored_len:,}" if stored_len else "?"
                print(f"    Old size: {old_size}  New size: {new_len:,}")

                new_version = next_version_label(version or "v1.0-baseline")
                new_r2_path = r2_path_for_version(
                    r2_path or f"source-pdfs/dcps/{ch_council}/v1.0-baseline/{key}.pdf",
                    new_version,
                )

                if not dry_run:
                    s3.put_object(
                        Bucket=R2_BUCKET_NAME,
                        Key=new_r2_path,
                        Body=content,
                        ContentType="application/pdf",
                    )
                    print(f"    Uploaded → r2://{R2_BUCKET_NAME}/{new_r2_path}")
                    new_public_url = R2_PUBLIC_BASE + new_r2_path
                    # Spatial/inert chapters: hash-tracked but never trigger extraction
                    cur.execute(
                        """
                        UPDATE dcp_chapter_registry
                        SET r2_current_path=%s, r2_version_label=%s,
                            r2_public_pdf_url=%s,
                            content_hash=%s, url_content_length=%s,
                            url_etag=%s, url_last_modified=%s,
                            url_last_checked=%s, url_last_changed=%s,
                            needs_extraction=%s, check_failures=0
                        WHERE id=%s
                        """,
                        (
                            new_r2_path, new_version,
                            new_public_url,
                            new_hash, new_len,
                            new_etag, new_lm,
                            now, now,
                            not is_spatial and not is_inert,
                            chapter_id,
                        ),
                    )
                    # Flag linked numeric control rows for review
                    flagged = cur.execute(
                        """
                        UPDATE dcp_setback_controls
                        SET needs_review = TRUE,
                            review_reason = 'chapter_pdf_changed',
                            reviewed_at = NULL
                        WHERE source_chapter_key = %s
                          AND lga = %s
                          AND is_current = TRUE
                          AND needs_review = FALSE
                        """,
                        (key, ch_council),
                    )
                    flagged_count = cur.rowcount
                    if flagged_count > 0:
                        print(f"    [CONTROLS] Flagged {flagged_count} numeric control rows for review")
                    conn.commit()
                    if is_spatial:
                        if stored_hash:
                            # Only alert on genuine changes, not first-time baseline
                            send_telegram(
                                f"DCP spatial amendment detected — {ch_council}/{key}\n"
                                f"{label}\n"
                                f"Map or boundary document changed. Manual review required.\n"
                                f"{url}"
                            )
                            print(f"    [SPATIAL] Telegram alert sent — manual review required")
                        else:
                            print(f"    [SPATIAL] First baseline stored — no alert")
                    elif is_inert:
                        print(f"    [INERT] Hash updated silently — cover/ToC, no alert")
                else:
                    print(f"    [dry-run] would upload to r2://{R2_BUCKET_NAME}/{new_r2_path}")

                if not is_inert:
                    results["changed"].append({
                        "council": ch_council,
                        "chapter_key": key,
                        "chapter_label": label,
                        "old_hash": stored_hash,
                        "new_hash": new_hash,
                        "new_version": new_version,
                        "r2_path": new_r2_path,
                    })
                    council_changed += 1
                results["checked"] += 1

            except WAFBlockError as exc:
                # 403 WAF/access denial — skip without incrementing check_failures.
                # Infrastructure problem (CDN blocking GH Actions IP), not a data issue.
                print(f"    [WAF-BLOCKED] {exc}")
                cur.execute(
                    "UPDATE dcp_chapter_registry SET url_last_checked=%s WHERE id=%s",
                    (now, chapter_id),
                )
                if not dry_run:
                    conn.commit()
                council_failed += 1
                results["failed"] += 1
                results["waf_blocked"].append({
                    "council": ch_council,
                    "chapter_key": key,
                    "label": label,
                    "url": url,
                })

            except Exception as exc:
                print(f"    [ERROR] {exc}")
                new_failures = failures + 1
                cur.execute(
                    "UPDATE dcp_chapter_registry SET url_last_checked=%s, check_failures=%s WHERE id=%s",
                    (now, new_failures, chapter_id),
                )
                if not dry_run:
                    conn.commit()
                council_failed += 1
                results["failed"] += 1

            adaptive_delay(url)  # per-domain adaptive delay (default 2s, backs off on 429)

        # Update instrument_currency for this council if all its chapters passed.
        # Use council_failed (not results["failed"]) — the global counter is cumulative
        # across all councils, so a failure in council A would otherwise block verified_at
        # updates for all subsequently-processed councils even if they had zero failures.
        if council_changed == 0 and council_failed == 0:
            _update_instrument_currency(conn, council, dry_run)
            print(f"\n  [{council}] instrument_currency updated — verified_at=NOW()")

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


def reseed_hashes(conn, council_filter: str | None, dry_run: bool, delay: float = 5.0) -> None:
    """
    Re-download all active chapters and update stored content_hash, url_etag,
    url_content_length, and check_failures without triggering extraction.

    Use after a CMS migration invalidates stored ETags/Content-Lengths, causing
    the normal monitor to think every chapter has changed.

    Does NOT:
      - Set needs_extraction = TRUE (provisions are already extracted)
      - Upload to R2 (R2 copies are already correct)
      - Send Telegram alerts
    """
    cur = conn.cursor()
    now = datetime.now(timezone.utc)

    query = """
        SELECT id, council, chapter_key, council_url, content_hash, url_etag
        FROM dcp_chapter_registry
        WHERE is_active = TRUE AND council_url IS NOT NULL
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
    cur.close()

    print(f"\nReseeding hashes for {len(chapters)} chapters (delay={delay}s)...\n")

    updated = 0
    skipped = 0
    failed = 0

    for chapter in chapters:
        chapter_id = chapter["id"]
        council = chapter["council"]
        key = chapter["chapter_key"]
        url = chapter["council_url"]
        stored_hash = chapter["content_hash"]
        stored_etag = chapter["url_etag"]

        print(f"  {council}/{key}", end="", flush=True)

        try:
            content, resp_headers = download_pdf(url)
            new_hash = sha256(content)
            new_etag = resp_headers.get("ETag")
            new_lm = resp_headers.get("Last-Modified")
            # Use Content-Length from response if available, else len(content)
            remote_len = resp_headers.get("Content-Length")
            new_len = int(remote_len) if remote_len else len(content)

            changed = new_hash != stored_hash or new_etag != stored_etag

            if not changed:
                print(f"  [ok] hash+etag match")
                skipped += 1
            else:
                hash_changed = "hash" if new_hash != stored_hash else ""
                etag_changed = "etag" if new_etag != stored_etag else ""
                diff = "+".join(filter(None, [hash_changed, etag_changed]))
                print(f"  [reseed] {diff} updated")

                if not dry_run:
                    cur2 = conn.cursor()
                    cur2.execute(
                        """
                        UPDATE dcp_chapter_registry
                        SET content_hash=%s, url_etag=%s, url_content_length=%s,
                            url_last_modified=%s, url_last_checked=%s, check_failures=0
                        WHERE id=%s
                        """,
                        (new_hash, new_etag, new_len, new_lm, now, chapter_id),
                    )
                    conn.commit()
                    cur2.close()
                updated += 1

        except Exception as exc:
            print(f"  [ERROR] {exc}")
            failed += 1

        time.sleep(delay)

    print(f"\n{'='*60}")
    print(f"RESEED SUMMARY")
    print(f"{'='*60}")
    print(f"  Updated  : {updated}")
    print(f"  Unchanged: {skipped}")
    print(f"  Failed   : {failed}")
    if dry_run:
        print(f"  (dry-run — no DB writes)")


def main():
    parser = argparse.ArgumentParser(description="Weekly DCP chapter change monitor")
    parser.add_argument("--council", help="Filter to specific council")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing to DB or R2")
    parser.add_argument("--force", action="store_true", help="Re-download all even if Content-Length unchanged")
    parser.add_argument("--reseed", action="store_true", help="Update council_url for all chapters from hub scrape (run once after CMS migration)")
    parser.add_argument("--reseed-hashes", action="store_true", help="Re-download all chapters and update stored hashes/ETags without triggering extraction (run after CMS migration invalidates ETags)")
    parser.add_argument("--delay", type=float, default=None, help="Override default inter-request delay in seconds (default: 2.0, reseed-hashes: 5.0)")
    args = parser.parse_args()

    # Set default delay based on mode
    if args.delay is not None:
        _domain_delays.clear()  # will use args.delay as base
        global DEFAULT_DELAY
        DEFAULT_DELAY = args.delay

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
    if args.reseed_hashes:
        print("RESEED HASHES MODE — updating stored hashes/ETags, no extraction triggers")
    print("=" * 60)

    if args.reseed_hashes:
        try:
            reseed_hashes(conn, args.council, args.dry_run, delay=args.delay or 5.0)
        finally:
            conn.close()
        sys.exit(0)

    try:
        results = run_monitor(args.council, s3, conn, args.dry_run, args.force, args.reseed)
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

    # ── WAF-blocked digest ──────────────────────────────────────────────────
    n_waf = len(results["waf_blocked"])
    if n_waf > 0:
        waf_by_council: dict[str, list[dict]] = {}
        for w in results["waf_blocked"]:
            waf_by_council.setdefault(w["council"], []).append(w)
        lines = []
        for waf_council, items in sorted(waf_by_council.items()):
            lines.append(f"\n  [{waf_council}] ({len(items)} chapters)")
            for item in items:
                lines.append(f"    {item['chapter_key']}")
                lines.append(f"    {item['url']}")
        waf_detail = "\n".join(lines)
        send_telegram(
            f"DCP Monitor: {n_waf} chapter(s) WAF-blocked — manual download required\n"
            f"{waf_detail}\n\n"
            f"Open URLs in browser to check for changes.\n"
            f"If changed: python scripts/manual_verify.py --council X --chapter Y --file path.pdf"
        )

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
