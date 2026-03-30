"""
Inner West Council hub page scraper.

Inner West runs Drupal. PDF links follow the pattern:
    /sites/default/files/{date}/{filename}.pdf

Covers marrickville, leichhardt, and ashfield — same CMS, same pattern.
"""

import re
import time
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = "https://www.innerwest.nsw.gov.au"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "text/html,*/*",
}


class HubScrapeError(Exception):
    """Raised when a hub page cannot be scraped or yields no usable links."""


def scrape_inner_west(
    hub_url: str,
    expected_keys: set[str],
    timeout: int = 30,
    expected_labels: dict[str, str] | None = None,
) -> list[dict]:
    """
    Scrape an Inner West DCP hub page and return discovered PDF chapters.

    Args:
        hub_url:         Full URL of the council DCP hub page.
        expected_keys:   Set of chapter_key slugs from dcp_chapter_registry.
        timeout:         HTTP timeout in seconds.
        expected_labels: Optional dict {chapter_key: chapter_label} for
                         label-based matching (preferred over filename matching).

    Returns:
        List of dicts: {"chapter_key": str|None, "url": str, "label": str}
        chapter_key is None for PDFs that don't match any known key (new chapters).

    Raises:
        HubScrapeError: if the page returns non-200 or yields 0 PDF links.
    """
    resp = requests.get(hub_url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    if resp.status_code == 429:
        time.sleep(5)
        resp = requests.get(hub_url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    if resp.status_code != 200:
        raise HubScrapeError(f"Hub page returned HTTP {resp.status_code}: {hub_url}")

    soup = BeautifulSoup(resp.content, "lxml")
    results = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a", href=True):
        href: str = a["href"]

        # Match Inner West Drupal PDF pattern
        if "/sites/default/files/" not in href:
            continue
        if not href.lower().endswith(".pdf"):
            continue

        # Normalise to absolute URL
        full_url = urljoin(BASE, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Strip file size suffix from label: "Table of Contents\xa0 (PDF, 397.63KB)" → "Table of Contents"
        raw_label = a.get_text(" ", strip=True)
        label = re.sub(r"\s*\(PDF[^)]*\)", "", raw_label).strip()
        if not label:
            label = PurePosixPath(urlparse(full_url).path).stem

        # Match by label first (most reliable), fall back to filename
        if expected_labels:
            chapter_key = _match_by_label(label, expected_labels)
        else:
            chapter_key = None

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
            f"No PDF links found on hub page (pattern /sites/default/files/*.pdf): {hub_url}"
        )

    return results


def _match_by_label(hub_label: str, expected_labels: dict[str, str]) -> str | None:
    """
    Match a hub page link label against known chapter_label values.

    Strategy:
      1. Exact normalised match
      2. One contains the other (longer is in shorter)
      3. Word overlap >= 0.6

    Returns the best matching chapter_key, or None.
    """
    norm_hub = _slug(hub_label)
    best_key = None
    best_score = 0.0

    for key, stored_label in expected_labels.items():
        norm_stored = _slug(stored_label)

        if norm_hub == norm_stored:
            return key

        if norm_stored in norm_hub or norm_hub in norm_stored:
            score = len(norm_stored) / max(len(norm_hub), 1)
            if score > best_score:
                best_score = score
                best_key = key
            continue

        hub_words = set(norm_hub.split("-")) - {"the", "a", "and", "of", "in", "for", "with"}
        stored_words = set(norm_stored.split("-")) - {"the", "a", "and", "of", "in", "for", "with"}
        if hub_words and stored_words:
            overlap = len(hub_words & stored_words) / len(hub_words | stored_words)
            if overlap >= 0.55 and overlap > best_score:
                best_score = overlap
                best_key = key

    return best_key


def _match_by_filename(filename: str, expected_keys: set[str]) -> str | None:
    """
    Fuzzy-match a PDF filename stem to a known chapter_key.
    Strips common council name prefixes before matching.
    """
    # Strip council name prefixes that dominate and reduce signal
    cleaned = re.sub(
        r"^(marrickville|leichhardt|ashfield|inner[\s-]west)\s*(dcp|development[\s-]control[\s-]plan)[\s-]*\d*[\s-]*",
        "",
        filename,
        flags=re.IGNORECASE,
    ).strip("- ")

    norm_fn = _slug(cleaned) if cleaned else _slug(filename)
    best_key = None
    best_score = 0.0

    for key in expected_keys:
        norm_key = _slug(key)

        if norm_fn == norm_key:
            return key

        if norm_key in norm_fn or norm_fn in norm_key:
            score = len(norm_key) / max(len(norm_fn), 1)
            if score > best_score:
                best_score = score
                best_key = key
            continue

        fn_words = set(norm_fn.split("-")) - {"the", "a", "and", "of", "in", "for", "with", "s", "nov", "22", "23"}
        key_words = set(norm_key.split("-"))
        if fn_words and key_words:
            overlap = len(fn_words & key_words) / len(fn_words | key_words)
            if overlap >= 0.5 and overlap > best_score:
                best_score = overlap
                best_key = key

    return best_key


def _slug(text: str) -> str:
    """Normalise text to a comparable slug: lowercase, alphanumeric + hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
