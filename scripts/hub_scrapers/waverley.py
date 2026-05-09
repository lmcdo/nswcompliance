"""
Waverley Council hub page scraper.

Waverley runs Squiz Matrix. DCP PDF links follow two patterns:
    /media/documents/building_and_development/dcp/dcp_2022/{filename}.pdf
    /__data/assets/pdf_file/{id}/{filename}.pdf

The hub page lists individual DCP parts (A through F) plus the full
consolidated version. We skip full-version PDFs to avoid duplicates.
"""

import re
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .inner_west import HubScrapeError, _match_by_label, _match_by_filename, _slug

BASE = "https://www.waverley.nsw.gov.au"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "text/html,*/*",
}

# Skip full consolidated DCP PDFs — we track per-part instead
SKIP_PATTERNS = ("full_version", "full version", "amendment_5", "amendment_6")


def scrape_waverley(
    hub_url: str,
    expected_keys: set[str],
    timeout: int = 30,
    expected_labels: dict[str, str] | None = None,
) -> list[dict]:
    """Scrape Waverley DCP hub page for PDF links."""
    resp = requests.get(hub_url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    if resp.status_code != 200:
        raise HubScrapeError(f"Hub page returned HTTP {resp.status_code}: {hub_url}")

    soup = BeautifulSoup(resp.content, "lxml")
    results = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a", href=True):
        href: str = a["href"]

        if not href.lower().endswith(".pdf"):
            continue

        full_url = urljoin(BASE, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Skip full consolidated version PDFs
        url_lower = full_url.lower()
        if any(skip in url_lower for skip in SKIP_PATTERNS):
            continue

        raw_label = a.get_text(" ", strip=True)
        label = re.sub(r"\s*\(PDF[^)]*\)", "", raw_label).strip()
        if not label:
            label = PurePosixPath(urlparse(full_url).path).stem

        chapter_key = None
        if expected_labels:
            chapter_key = _match_by_label(label, expected_labels)
        if chapter_key is None:
            filename = PurePosixPath(urlparse(full_url).path).stem
            chapter_key = _match_by_filename(filename, expected_keys)

        results.append({
            "chapter_key": chapter_key,
            "url": full_url,
            "label": label,
        })

    if not results:
        raise HubScrapeError(
            f"No PDF links found on Waverley hub page: {hub_url}"
        )

    return results
