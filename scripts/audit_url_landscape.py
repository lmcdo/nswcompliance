#!/usr/bin/env python3
"""
DCP URL Landscape Audit
=======================
Tests every active chapter URL in dcp_chapter_registry and produces a
structured report on:

  - HTTP status (live / dead / redirect)
  - Headers served: Content-Length, ETag, Last-Modified
  - Fast-path eligibility (can monitor skip full download?)
  - Response time
  - Content-Length drift (remote vs stored)
  - Per-council aggregates
  - CMS fingerprint (URL pattern → inferred platform)

This informs two decisions:
  1. Is direct URL polling reliable enough without hub scraping?
  2. What is the real weekly bandwidth/time cost at scale?

Usage:
    python scripts/audit_url_landscape.py
    python scripts/audit_url_landscape.py --council ku_ring_gai
    python scripts/audit_url_landscape.py --active-only   (default)
    python scripts/audit_url_landscape.py --include-inactive
    python scripts/audit_url_landscape.py --output reports/url-audit-{date}.txt

Exit codes:
    0 = all URLs live
    1 = some URLs dead or errored
"""

import argparse
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-audit)"
    ),
    "Accept": "application/pdf,*/*",
}

TIMEOUT = 20  # seconds per HEAD request
POLITE_DELAY = 1.5  # seconds between requests — audit is less frequent than monitor


# ── CMS fingerprinting ────────────────────────────────────────────────────────

def fingerprint_cms(url: str) -> str:
    """
    Infer council CMS platform from URL pattern.
    Informational only — helps group councils by platform for scraper planning.
    """
    if not url:
        return "unknown"
    parsed = urlparse(url)
    path = parsed.path.lower()
    host = parsed.netloc.lower()

    if "/sites/default/files/" in path:
        return "drupal"
    if "/ArticleDocuments/" in url or "articledocuments" in path:
        return "squiz-matrix-old"  # Inner West pre-migration pattern
    if "/files/assets/" in path or "/files/sharedassets/" in path:
        return "squiz-matrix"
    if "legislation.nsw.gov.au" in host or "austlii.edu.au" in host:
        return "nsw-legislation"
    if "planningportal.nsw.gov.au" in host:
        return "nsw-planning-portal"
    if "/development/" in path and ".pdf" in path:
        return "generic-council"
    if "/documents/" in path or "/document/" in path:
        return "generic-council"
    if "/media/" in path:
        return "generic-council"
    if "amazonaws.com" in host or "s3." in host:
        return "s3-hosted"
    if "cloudfront.net" in host:
        return "cloudfront-cdn"
    return "unknown"


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class URLResult:
    council: str
    chapter_key: str
    chapter_label: str
    url: str
    cms: str

    # HTTP result
    status: int | None = None
    error: str | None = None
    response_ms: int = 0
    redirect_count: int = 0
    final_url: str | None = None

    # Headers
    content_length_remote: int | None = None
    content_length_stored: int | None = None
    etag: str | None = None
    last_modified: str | None = None

    # Flags
    is_active: bool = True
    is_spatial: bool = False
    is_inert: bool = False
    check_failures: int = 0

    @property
    def is_live(self) -> bool:
        return self.status is not None and 200 <= self.status < 400

    @property
    def is_dead(self) -> bool:
        return self.status is not None and self.status >= 400

    @property
    def has_content_length(self) -> bool:
        return self.content_length_remote is not None

    @property
    def has_etag(self) -> bool:
        return self.etag is not None and self.etag != ""

    @property
    def fast_path_eligible(self) -> bool:
        """Can the monitor skip full download? Requires BOTH CL and ETag."""
        return self.has_content_length and self.has_etag

    @property
    def cl_only_eligible(self) -> bool:
        """Content-Length present but no ETag — monitor still does full download."""
        return self.has_content_length and not self.has_etag

    @property
    def content_length_drifted(self) -> bool:
        """Remote CL differs from stored — amendment candidate."""
        if self.content_length_remote and self.content_length_stored:
            return self.content_length_remote != self.content_length_stored
        return False

    @property
    def redirected(self) -> bool:
        return self.final_url is not None and self.final_url != self.url


# ── HTTP audit ────────────────────────────────────────────────────────────────

def audit_url(chapter: dict) -> URLResult:
    url = chapter.get("council_url") or ""
    result = URLResult(
        council=chapter["council"],
        chapter_key=chapter["chapter_key"],
        chapter_label=chapter.get("chapter_label") or "",
        url=url,
        cms=fingerprint_cms(url),
        content_length_stored=chapter.get("url_content_length"),
        is_active=chapter.get("is_active", True),
        is_spatial=chapter.get("is_spatial", False),
        is_inert=chapter.get("is_inert", False),
        check_failures=chapter.get("check_failures") or 0,
    )

    if not url:
        result.error = "no URL registered"
        return result

    start = time.monotonic()
    try:
        resp = requests.head(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        result.status = resp.status_code
        result.response_ms = elapsed_ms
        result.redirect_count = len(resp.history)
        if resp.history:
            result.final_url = resp.url

        cl = resp.headers.get("Content-Length")
        result.content_length_remote = int(cl) if cl and cl.isdigit() else None
        result.etag = resp.headers.get("ETag")
        result.last_modified = resp.headers.get("Last-Modified")

    except requests.exceptions.Timeout:
        result.error = f"timeout (>{TIMEOUT}s)"
        result.response_ms = TIMEOUT * 1000
    except requests.exceptions.ConnectionError as exc:
        result.error = f"connection error: {exc}"
    except Exception as exc:
        result.error = f"unexpected: {exc}"

    return result


# ── Reporting ─────────────────────────────────────────────────────────────────

STATUS_ICON = {
    True: "OK",
    False: "DEAD",
    None: "ERR",
}


def print_report(results: list[URLResult], out=sys.stdout) -> None:
    def p(s=""): print(s, file=out)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    p(f"{'='*70}")
    p(f"DCP URL Landscape Audit — {now}")
    p(f"{'='*70}")

    # ── Per-URL detail ────────────────────────────────────────────────────────
    by_council = defaultdict(list)
    for r in results:
        by_council[r.council].append(r)

    for council, rows in sorted(by_council.items()):
        p(f"\n{'─'*70}")
        p(f"  {council.upper()}  ({len(rows)} chapters)")
        p(f"{'─'*70}")

        for r in rows:
            if r.error:
                status_str = f"ERR  [{r.error}]"
            elif r.is_dead:
                status_str = f"DEAD [{r.status}]"
            elif r.is_live:
                status_str = f"OK   [{r.status}] {r.response_ms}ms"
            else:
                status_str = f"???  [{r.status}]"

            flags = []
            if r.is_spatial:      flags.append("spatial")
            if r.is_inert:        flags.append("inert")
            if r.check_failures:  flags.append(f"failures={r.check_failures}")
            if r.redirected:      flags.append(f"redirected→{urlparse(r.final_url).netloc}")
            if r.content_length_drifted:
                flags.append(f"CL-DRIFT stored={r.content_length_stored} remote={r.content_length_remote}")

            hdrs = []
            hdrs.append(f"CL={'Y' if r.has_content_length else 'N'}")
            hdrs.append(f"ETag={'Y' if r.has_etag else 'N'}")
            hdrs.append(f"LM={'Y' if r.last_modified else 'N'}")
            fast = "FAST-PATH" if r.fast_path_eligible else ("CL-ONLY" if r.cl_only_eligible else "FULL-DL")

            flag_str = f"  [{', '.join(flags)}]" if flags else ""
            p(f"  {status_str:<28}  {fast:<9}  {' '.join(hdrs)}  {r.chapter_key}{flag_str}")
            p(f"    cms={r.cms}  {r.url[:80]}")

    # ── Council aggregates ────────────────────────────────────────────────────
    p(f"\n{'='*70}")
    p("COUNCIL SUMMARY")
    p(f"{'='*70}")
    p(f"  {'Council':<22} {'Total':>5} {'Live':>5} {'Dead':>5} {'Err':>5}  {'CL%':>5} {'ETag%':>5} {'FastP%':>6}  {'AvgMS':>6}  CMS")

    all_live = all_dead = all_err = 0
    for council, rows in sorted(by_council.items()):
        live   = sum(1 for r in rows if r.is_live)
        dead   = sum(1 for r in rows if r.is_dead)
        err    = sum(1 for r in rows if r.error)
        cl_pct = int(100 * sum(1 for r in rows if r.has_content_length) / len(rows))
        et_pct = int(100 * sum(1 for r in rows if r.has_etag) / len(rows))
        fp_pct = int(100 * sum(1 for r in rows if r.fast_path_eligible) / len(rows))
        live_rows = [r for r in rows if r.response_ms > 0 and r.is_live]
        avg_ms = int(sum(r.response_ms for r in live_rows) / len(live_rows)) if live_rows else 0
        cms_set = {r.cms for r in rows}
        p(f"  {council:<22} {len(rows):>5} {live:>5} {dead:>5} {err:>5}  {cl_pct:>4}% {et_pct:>4}% {fp_pct:>5}%  {avg_ms:>5}ms  {', '.join(sorted(cms_set))}")
        all_live += live; all_dead += dead; all_err += err

    p(f"{'─'*70}")
    total = len(results)
    p(f"  {'TOTAL':<22} {total:>5} {all_live:>5} {all_dead:>5} {all_err:>5}")

    # ── Key findings ──────────────────────────────────────────────────────────
    p(f"\n{'='*70}")
    p("KEY FINDINGS")
    p(f"{'='*70}")

    dead = [r for r in results if r.is_dead or r.error]
    if dead:
        p(f"\n  DEAD / ERRORED URLs ({len(dead)}):")
        for r in dead:
            p(f"    [{r.council}] {r.chapter_key}")
            p(f"      {r.url}")
            p(f"      Status: {r.status}  Error: {r.error}")

    cl_drift = [r for r in results if r.content_length_drifted]
    if cl_drift:
        p(f"\n  CONTENT-LENGTH DRIFT — possible amendments ({len(cl_drift)}):")
        for r in cl_drift:
            p(f"    [{r.council}] {r.chapter_key}  stored={r.content_length_stored} remote={r.content_length_remote}")

    high_failures = [r for r in results if r.check_failures >= 2]
    if high_failures:
        p(f"\n  HIGH FAILURE COUNT (>=2 consecutive):")
        for r in high_failures:
            p(f"    [{r.council}] {r.chapter_key}  failures={r.check_failures}")

    no_etag = [r for r in results if r.is_live and not r.has_etag]
    p(f"\n  FAST-PATH ANALYSIS:")
    fast_path = sum(1 for r in results if r.fast_path_eligible)
    cl_only   = sum(1 for r in results if r.cl_only_eligible)
    full_dl   = sum(1 for r in results if r.is_live and not r.has_content_length and not r.has_etag)
    p(f"    FAST-PATH (CL+ETag, skip download) : {fast_path}/{total} ({int(100*fast_path/total)}%)")
    p(f"    CL-ONLY (still full download)      : {cl_only}/{total} ({int(100*cl_only/total)}%)")
    p(f"    FULL-DOWNLOAD (no headers)         : {full_dl}/{total} ({int(100*full_dl/total)}%)")
    p(f"")
    if fast_path == 0:
        p(f"    *** ETag not served by any council. Monitor downloads ALL PDFs every run.")
        p(f"        At {total} chapters × ~3s avg = ~{total*3//60}min download time per weekly run.")
        p(f"        At 100 LGAs × 15 chapters = 1500 chapters × ~3s = ~{1500*3//60}min.")
    elif fast_path < total * 0.5:
        p(f"    *** ETag rarely served. Most chapters require full download each run.")

    redirected = [r for r in results if r.redirected]
    if redirected:
        p(f"\n  REDIRECTED URLs ({len(redirected)}) — stored URL may need updating:")
        for r in redirected:
            p(f"    [{r.council}] {r.chapter_key}")
            p(f"      From: {r.url[:70]}")
            p(f"      To:   {r.final_url[:70]}")

    cms_counts = defaultdict(int)
    for r in results:
        cms_counts[r.cms] += 1
    p(f"\n  CMS LANDSCAPE ({total} chapters):")
    for cms, count in sorted(cms_counts.items(), key=lambda x: -x[1]):
        p(f"    {cms:<30} {count:>3} chapters")

    p(f"\n{'='*70}")
    p("MONITORING IMPLICATIONS")
    p(f"{'='*70}")
    has_hub_scraper = {"marrickville", "leichhardt", "ashfield"}
    no_scraper = sorted({r.council for r in results if r.council not in has_hub_scraper and r.council != "state"})
    if no_scraper:
        p(f"\n  Councils with registered URLs but NO hub scraper:")
        for c in no_scraper:
            rows_c = [r for r in results if r.council == c]
            cms_types = {r.cms for r in rows_c}
            p(f"    {c:<25} {len(rows_c)} chapters   cms={', '.join(sorted(cms_types))}")
        p(f"\n  These {len(no_scraper)} councils use direct URL polling (fallback path).")
        p(f"  If any URL goes dead, alert fires after 3 consecutive weekly failures (~3 weeks).")

    p()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Audit all registered DCP chapter URLs")
    parser.add_argument("--council", help="Filter to specific council slug")
    parser.add_argument("--include-inactive", action="store_true",
                        help="Include is_active=FALSE rows (default: active only)")
    parser.add_argument("--output", help="Write report to file (in addition to stdout)")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    query = """
        SELECT council, chapter_key, chapter_label, council_url,
               url_content_length, url_etag, check_failures,
               is_active, is_spatial, is_inert
        FROM dcp_chapter_registry
        WHERE council_url IS NOT NULL
    """
    params = []
    if not args.include_inactive:
        query += " AND is_active = TRUE"
    if args.council:
        query += " AND council = %s"
        params.append(args.council)
    query += " ORDER BY council, sort_order"

    cur.execute(query, params)
    cols = [d[0] for d in cur.description]
    chapters = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()

    print(f"Auditing {len(chapters)} active chapter URLs...", flush=True)
    print(f"(HEAD requests only — no full downloads)", flush=True)
    print()

    results = []
    for i, ch in enumerate(chapters, 1):
        key = f"{ch['council']}/{ch['chapter_key']}"
        print(f"  [{i:>3}/{len(chapters)}] {key:<55}", end="", flush=True)
        result = audit_url(ch)
        if result.error:
            print(f"ERR  {result.error}")
        elif result.is_dead:
            print(f"DEAD [{result.status}]")
        else:
            fast = "FAST" if result.fast_path_eligible else ("CL" if result.cl_only_eligible else "FULL")
            print(f"OK   [{result.status}] {result.response_ms}ms  {fast}")
        results.append(result)

        if i < len(chapters):
            time.sleep(POLITE_DELAY)

    print()

    # Print to stdout
    print_report(results)

    # Optionally write to file
    if args.output:
        out_path = args.output.replace("{date}", datetime.now().strftime("%Y-%m-%d"))
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            print_report(results, out=f)
        print(f"\nReport written to: {out_path}")

    # Exit 1 if any dead/errored
    dead = [r for r in results if r.is_dead or r.error]
    sys.exit(1 if dead else 0)


if __name__ == "__main__":
    main()
