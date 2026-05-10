"""
Penrith City Council hub page scraper.

Penrith uses a standard council CMS. PDF links follow the pattern:
    /images/{path}/{filename}.pdf
    /images/documents/building-development/planning-zoning/planning-controls/{filename}.pdf

DCP 2014 with Parts A–F, plus precinct-specific E1–E18.
Some links point to Google Drive or NSW Planning Portal (external).
"""

import re
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .inner_west import HubScrapeError, _match_by_label, _match_by_filename, _slug

BASE = "https://www.penrithcity.nsw.gov.au"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "text/html,*/*",
}

# Skip volume downloads (full consolidated PDFs) — we track per-part
SKIP_PATTERNS = ("volume_1", "volume_2", "volume-1", "volume-2")


def scrape_penrith(
    hub_url: str,
    expected_keys: set[str],
    timeout: int = 30,
    expected_labels: dict[str, str] | None = None,
) -> list[dict]:
    """Scrape Penrith DCP hub page for PDF links."""
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

        # Accept local PDFs (/images/) and external (drive.google.com, planningportal)
        is_local = href.startswith("/images/") or href.startswith("/Images/")
        is_external = "drive.google.com" in href or "planningportal.nsw.gov.au" in href
        if not is_local and not is_external:
            continue

        full_url = urljoin(BASE, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Skip volume downloads
        fn_lower = full_url.lower()
        if any(skip in fn_lower for skip in SKIP_PATTERNS):
            continue

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
            # Strip Penrith/DCP prefix for cleaner matching
            cleaned = re.sub(
                r"^(penrith[\s_-]*(city)?[\s_-]*)?(dcp[\s_-]*2014[\s_-]*)?",
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
            f"No PDF links found on Penrith hub page: {hub_url}"
        )

    return results
