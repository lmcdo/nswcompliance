"""
Generic council hub page scraper.

Works for councils that serve standard HTML pages with PDF links.
Handles common patterns across NSW council CMS platforms.

Used for: Blacktown, Campbelltown, Liverpool, Hornsby, Randwick,
Sutherland, Bayside, Georges River, Northern Beaches, Parramatta.
"""

import re
import time
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .inner_west import HubScrapeError, _match_by_label, _match_by_filename, _slug

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}

# Volume/consolidated PDFs to skip
SKIP_PATTERNS = (
    "full_version", "full version", "consolidated",
    "volume_1", "volume_2", "volume-1", "volume-2",
)


def scrape_generic(
    hub_url: str,
    expected_keys: set[str],
    timeout: int = 30,
    expected_labels: dict[str, str] | None = None,
    council_prefix: str = "",
) -> list[dict]:
    """
    Generic scraper for council hub pages.

    Works with most NSW council CMS platforms. Uses browser-like headers
    to avoid bot protection. Finds all PDF links on the page.

    Args:
        hub_url:         Full URL of the council DCP hub page.
        expected_keys:   Set of chapter_key slugs from dcp_chapter_registry.
        timeout:         HTTP timeout in seconds.
        expected_labels: Optional dict {chapter_key: chapter_label}.
        council_prefix:  Council name prefix to strip from filenames for matching
                         (e.g., "blacktown", "campbelltown").
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    # Some councils require a session cookie from the homepage first
    parsed = urlparse(hub_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    resp = session.get(hub_url, timeout=timeout, allow_redirects=True)

    # Retry once on 403 — sometimes the first request sets cookies
    if resp.status_code == 403:
        time.sleep(2)
        # Try hitting homepage first for cookies
        try:
            session.get(base_url, timeout=timeout, allow_redirects=True)
            time.sleep(1)
        except Exception:
            pass
        resp = session.get(hub_url, timeout=timeout, allow_redirects=True)

    if resp.status_code == 429:
        time.sleep(5)
        resp = session.get(hub_url, timeout=timeout, allow_redirects=True)

    if resp.status_code != 200:
        raise HubScrapeError(f"Hub page returned HTTP {resp.status_code}: {hub_url}")

    soup = BeautifulSoup(resp.content, "lxml")
    results = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a", href=True):
        href: str = a["href"]

        if not href.lower().endswith(".pdf"):
            continue

        full_url = urljoin(base_url, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Skip consolidated/volume PDFs
        fn_lower = full_url.lower()
        if any(skip in fn_lower for skip in SKIP_PATTERNS):
            continue

        raw_label = a.get_text(" ", strip=True)
        label = re.sub(r"\s*\(PDF[^)]*\)", "", raw_label).strip()
        label = re.sub(r"\s*\[\s*\d+(\.\d+)?\s*(KB|MB|GB)\s*\]", "", label, flags=re.IGNORECASE).strip()
        if not label:
            label = PurePosixPath(urlparse(full_url).path).stem

        # Match by label first, fallback to filename
        chapter_key = None
        if expected_labels:
            chapter_key = _match_by_label(label, expected_labels)

        if chapter_key is None:
            filename = PurePosixPath(urlparse(full_url).path).stem
            if council_prefix:
                cleaned = re.sub(
                    rf"^{re.escape(council_prefix)}[\s_-]*(dcp|development[\s_-]*control[\s_-]*plan)?[\s_-]*\d*[\s_-]*",
                    "",
                    filename,
                    flags=re.IGNORECASE,
                ).strip("- _")
            else:
                cleaned = filename
            chapter_key = _match_by_filename(
                cleaned if cleaned else filename, expected_keys
            )

        results.append({
            "chapter_key": chapter_key,
            "url": full_url,
            "label": label,
        })

    if not results:
        raise HubScrapeError(
            f"No PDF links found on hub page: {hub_url}"
        )

    return results


# ── Per-council convenience wrappers ─────────────────────────────

def scrape_blacktown(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "blacktown")

def scrape_campbelltown(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "campbelltown")

def scrape_liverpool(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "liverpool")

def scrape_hornsby(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "hornsby")

def scrape_parramatta(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "parramatta")

def scrape_northern_beaches(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "northern-beaches")

def scrape_randwick(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "randwick")

def scrape_sutherland(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "sutherland")

def scrape_bayside(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "bayside")

def scrape_georges_river(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "georges-river")

def scrape_burwood(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "burwood")

def scrape_camden(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "camden")

def scrape_canada_bay(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "canada-bay")

def scrape_fairfield(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "fairfield")

def scrape_ryde(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "ryde")

def scrape_strathfield(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "strathfield")

def scrape_the_hills(hub_url, expected_keys, timeout=30, expected_labels=None):
    return scrape_generic(hub_url, expected_keys, timeout, expected_labels, "the-hills")
