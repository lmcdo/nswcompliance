"""
Cumberland City Council hub page scraper.

Cumberland runs Drupal. PDF links follow the pattern:
    /sites/default/files/inline-files/{filename}.pdf

DCP 2021, Parts A–G plus precinct-specific F1–F4.
"""

import re
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .inner_west import HubScrapeError, _match_by_label, _match_by_filename, _slug

BASE = "https://www.cumberland.nsw.gov.au"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "text/html,*/*",
}


def scrape_cumberland(
    hub_url: str,
    expected_keys: set[str],
    timeout: int = 30,
    expected_labels: dict[str, str] | None = None,
) -> list[dict]:
    """Scrape Cumberland DCP hub page for PDF links."""
    resp = requests.get(hub_url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    if resp.status_code != 200:
        raise HubScrapeError(f"Hub page returned HTTP {resp.status_code}: {hub_url}")

    soup = BeautifulSoup(resp.content, "lxml")
    results = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a", href=True):
        href: str = a["href"]

        # Cumberland Drupal pattern: /sites/default/files/inline-files/*.pdf
        if "/sites/default/files/" not in href:
            continue
        if not href.lower().endswith(".pdf"):
            continue

        full_url = urljoin(BASE, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        raw_label = a.get_text(" ", strip=True)
        label = re.sub(r"\s*\(PDF[^)]*\)", "", raw_label).strip()
        if not label:
            label = PurePosixPath(urlparse(full_url).path).stem

        # Match by label first, fallback to filename
        chapter_key = None
        if expected_labels:
            chapter_key = _match_by_label(label, expected_labels)

        if chapter_key is None:
            filename = PurePosixPath(urlparse(full_url).path).stem
            # Strip cumberland prefix for cleaner matching
            cleaned = re.sub(
                r"^cumberland[\s_-]*(dcp)?[\s_-]*",
                "",
                filename,
                flags=re.IGNORECASE,
            ).strip("- _")
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
            f"No PDF links found on Cumberland hub page: {hub_url}"
        )

    return results
