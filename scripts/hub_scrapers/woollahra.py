"""
Woollahra Council hub page scraper.

Woollahra runs Drupal. DCP PDF links follow the pattern:
    /files/assets/public/v/1/plans-policies-publications/development-control-plans/{filename}.pdf

The hub page also contains LEP documents — filter to DCP-related PDFs only.
"""

import re
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .inner_west import HubScrapeError, _match_by_label, _match_by_filename, _slug

BASE = "https://www.woollahra.nsw.gov.au"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "text/html,*/*",
}

# Only match PDFs in the DCP subdirectory — skip LEP, heritage, etc.
DCP_PATH_PATTERN = "/development-control-plans/"


def scrape_woollahra(
    hub_url: str,
    expected_keys: set[str],
    timeout: int = 30,
    expected_labels: dict[str, str] | None = None,
) -> list[dict]:
    """Scrape Woollahra DCP hub page for PDF links."""
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

        # Filter to DCP documents only
        if DCP_PATH_PATTERN not in href.lower():
            # Also accept if the filename matches a known chapter key
            # (some pages link directly without the DCP subdirectory)
            filename = PurePosixPath(urlparse(href).path).stem.lower()
            if not any(k in filename for k in ("chapter", "dcp", "part")):
                continue

        full_url = urljoin(BASE, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

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
            f"No DCP PDF links found on Woollahra hub page: {hub_url}"
        )

    return results
