"""
City of Sydney hub page scraper.

PDF links follow the pattern:
    /-/media/corporate/files/publications/development-control-plans/{filename}.pdf

The hub page lists all sections of Sydney DCP 2012.
"""

import re
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .inner_west import HubScrapeError, _match_by_label, _match_by_filename, _slug

BASE = "https://www.cityofsydney.nsw.gov.au"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "text/html,*/*",
}


def scrape_city_of_sydney(
    hub_url: str,
    expected_keys: set[str],
    timeout: int = 30,
    expected_labels: dict[str, str] | None = None,
) -> list[dict]:
    """Scrape City of Sydney DCP hub page for PDF links."""
    resp = requests.get(hub_url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    if resp.status_code != 200:
        raise HubScrapeError(f"Hub page returned HTTP {resp.status_code}: {hub_url}")

    soup = BeautifulSoup(resp.content, "lxml")
    results = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a", href=True):
        href: str = a["href"]

        # Strip query params before extension check — City of Sydney appends
        # ?download=true to PDF hrefs, which breaks .endswith(".pdf").
        href_path = href.split("?")[0]
        if not href_path.lower().endswith(".pdf"):
            continue

        # City of Sydney uses /-/media/ pattern for DCP documents
        if "/-/media/" not in href and "/files/" not in href:
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
            f"No PDF links found on City of Sydney hub page: {hub_url}"
        )

    return results
