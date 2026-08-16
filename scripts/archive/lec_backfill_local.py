"""
LEC Decision Backfill — local script.

Runs from your machine (residential IP, not blocked by AustLII).
Scrapes NSWLEC1 (Class 1 merit appeals) for years 2020–2025,
extracts structured data via Claude Haiku, saves JSON to ./lec-data/.

Usage:
    cd compliance-engine
    pip install httpx anthropic
    python scripts/lec_backfill_local.py
    python scripts/lec_backfill_local.py --start 2020 --end 2025
    python scripts/lec_backfill_local.py --year 2024

Output:
    lec-data/decisions/{year}/{case_id}.json   — one file per decision
    lec-data/state.json                        — seen IDs + progress

Low-confidence extractions are saved with confidence=low and flagged in
lec-data/review_queue.txt for manual verification before training.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import httpx
from anthropic import Anthropic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(__file__).parent.parent / "lec-data"
STATE_FILE = OUTPUT_DIR / "state.json"
REVIEW_QUEUE = OUTPUT_DIR / "review_queue.txt"
CONSECUTIVE_404_LIMIT = 30
REQUEST_DELAY = 0.6  # seconds between AustLII requests (≤ 1.5 req/sec)

AUSTLII_HEADERS = {
    "User-Agent": "Mozilla/5.0 (research/lec-collection; contact: plotdetect.com.au)",
    "Accept": "text/html,application/xhtml+xml",
}

# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_ids": [], "last_checked": None}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ── AustLII ───────────────────────────────────────────────────────────────────

def case_id_from_url(url: str) -> str:
    m = re.search(r"NSWLEC1/(\d+)/(\d+)\.html", url, re.IGNORECASE)
    return f"NSWLEC1-{m.group(1)}-{m.group(2)}" if m else url


def html_to_text(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                          ("&nbsp;", " "), ("&quot;", '"')]:
        text = text.replace(entity, char)
    text = re.sub(r"&#\d+;", " ", text)
    return re.sub(r"\s{3,}", "\n\n", text).strip()


def probe_year(client: httpx.Client, year: int, seen_ids: set[str]) -> list[tuple[str, str]]:
    """
    Return list of (canonical_url, fetch_url) for unseen decisions in a year.

    AustLII's static paths redirect (302) to /cgi-bin/viewdoc/... which blocks HEAD.
    We treat 302 as "exists" and record the redirect destination for fetching.
    """
    links = []
    consecutive_404 = 0
    n = 1

    # Client without redirect following for probing
    probe_client = httpx.Client(
        headers=AUSTLII_HEADERS,
        timeout=15,
        follow_redirects=False,
    )

    with probe_client:
        while consecutive_404 < CONSECUTIVE_404_LIMIT:
            url = f"https://www.austlii.edu.au/au/cases/nsw/NSWLEC1/{year}/{n}.html"
            case_id = case_id_from_url(url)

            if case_id in seen_ids:
                consecutive_404 = 0
                n += 1
                time.sleep(REQUEST_DELAY)
                continue

            try:
                resp = probe_client.head(url)
                status = resp.status_code
            except Exception as exc:
                logger.warning("Network error: %s — %s", url, exc)
                status = 404

            if status in (200, 302):
                # 302 = redirect to viewdoc CGI = decision exists
                fetch_url = str(resp.headers.get("location", url))
                if not fetch_url.startswith("http"):
                    fetch_url = "https://www.austlii.edu.au" + fetch_url
                links.append((url, fetch_url))
                consecutive_404 = 0
                sys.stdout.write(f"\r  Year {year}: found {len(links)} decisions (checking {n})...")
                sys.stdout.flush()
            elif status == 404:
                consecutive_404 += 1
            else:
                logger.warning("HTTP %s: %s", status, url)
                consecutive_404 += 1

            n += 1
            time.sleep(REQUEST_DELAY)

    print()
    return links


def fetch_html(client: httpx.Client, fetch_url: str) -> str:
    """Fetch decision HTML — uses the viewdoc URL directly (GET works, HEAD doesn't)."""
    resp = client.get(fetch_url)
    resp.raise_for_status()
    return resp.text


# ── Extraction ────────────────────────────────────────────────────────────────

EXTRACTION_PROMPT = """\
You are extracting structured data from a NSW Land and Environment Court (LEC) \
Class 1 appeal judgment.

Case ID: {case_id}

Return ONLY a valid JSON object — no markdown fences, no prose:

{{
  "case_ref": "<citation e.g. [2024] NSWLEC 1 123, or empty string>",
  "judgment_date": "<ISO date YYYY-MM-DD, or empty string>",
  "property_address": "<street address if mentioned, otherwise empty string>",
  "lga": "<council or LGA name if mentioned, otherwise empty string>",
  "application_type": "<dwelling-house | dual-occupancy | multi-dwelling | subdivision | commercial | industrial | mixed-use | other>",
  "council_refusal_grounds": ["<refusal ground 1>"],
  "outcome": "<exactly one of: appellant_won | council_won | settled | remitted | unknown>",
  "appeal_grounds": ["<ground raised by appellant>"],
  "key_swing_factors": ["<factor that most influenced the outcome>"],
  "confidence": "<high if outcome clearly stated in ORDERS section; low if inferred>"
}}

Rules:
- ORDERS section is at the end. Appeal upheld/allowed → appellant_won. Dismissed → council_won.
- confidence=high only when you found and read the ORDERS section.
- Empty string or empty array if a field cannot be determined.

Judgment text (first 6000 chars):
{text}"""


def extract(anthropic: Anthropic, text: str, case_id: str, source_url: str) -> dict | None:
    try:
        msg = anthropic.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(case_id=case_id, text=text[:6000]),
            }],
        )
        result = json.loads(msg.content[0].text.strip())
        result["source_url"] = source_url
        result.setdefault("case_ref", case_id)
        return result
    except Exception as exc:
        logger.warning("Extraction failed for %s: %s", case_id, exc)
        return None


# ── Storage ───────────────────────────────────────────────────────────────────

def store(year: int, case_id: str, decision: dict) -> None:
    dest = OUTPUT_DIR / "decisions" / str(year)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{case_id}.json").write_text(json.dumps(decision, indent=2))


def flag_for_review(case_id: str, outcome: str, source_url: str) -> None:
    with open(REVIEW_QUEUE, "a") as f:
        f.write(f"{case_id}\t{outcome}\t{source_url}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(start_year: int, end_year: int) -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY not set. Export it first:\n  export ANTHROPIC_API_KEY=sk-...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    seen_ids = set(state["seen_ids"])
    anthropic = Anthropic(api_key=api_key)

    total_stored = 0
    total_skipped = 0
    total_errors = 0
    total_low_conf = 0

    with httpx.Client(headers=AUSTLII_HEADERS, timeout=20, follow_redirects=True) as client:
        for year in range(start_year, end_year + 1):
            logger.info("=== Year %s ===", year)

            new_urls = probe_year(client, year, seen_ids)
            already_seen = sum(
                1 for n in range(1, 500)
                if case_id_from_url(
                    f"https://www.austlii.edu.au/au/cases/nsw/NSWLEC1/{year}/{n}.html"
                ) in seen_ids
            )
            logger.info("Year %s: %s new, ~%s already seen", year, len(new_urls), len(seen_ids))

            year_stored = 0
            year_errors = 0

            for url, fetch_url in new_urls:
                case_id = case_id_from_url(url)
                try:
                    html = fetch_html(client, fetch_url)
                    time.sleep(REQUEST_DELAY)

                    text = html_to_text(html)
                    decision = extract(anthropic, text, case_id, url)

                    if decision:
                        store(year, case_id, decision)
                        seen_ids.add(case_id)
                        year_stored += 1

                        if decision.get("confidence") == "low":
                            flag_for_review(case_id, decision.get("outcome", "unknown"), url)
                            total_low_conf += 1
                            logger.warning("Low confidence — flagged: %s", case_id)
                        else:
                            logger.info("Stored: %s | %s | %s",
                                        case_id,
                                        decision.get("outcome", "?"),
                                        decision.get("lga", "?"))
                    else:
                        year_errors += 1

                except Exception as exc:
                    logger.warning("Failed %s: %s", case_id, exc)
                    year_errors += 1

                time.sleep(REQUEST_DELAY)

            # Save state after each year
            state["seen_ids"] = list(seen_ids)
            save_state(state)

            logger.info("Year %s done — stored: %s, errors: %s", year, year_stored, year_errors)
            total_stored += year_stored
            total_skipped += already_seen
            total_errors += year_errors

    logger.info("=== Complete ===")
    logger.info("Stored: %s | Skipped: %s | Errors: %s | Low-confidence: %s",
                total_stored, total_skipped, total_errors, total_low_conf)
    if total_low_conf:
        logger.info("Review queue: %s", REVIEW_QUEUE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LEC decision backfill — local scraper")
    parser.add_argument("--start", type=int, default=2020, help="First year (default: 2020)")
    parser.add_argument("--end", type=int, default=2025, help="Last year (default: 2025)")
    parser.add_argument("--year", type=int, help="Single year (overrides --start/--end)")
    args = parser.parse_args()

    if args.year:
        run(args.year, args.year)
    else:
        run(args.start, args.end)
