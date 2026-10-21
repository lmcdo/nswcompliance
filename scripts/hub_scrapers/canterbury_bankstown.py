"""
Canterbury Bankstown hub page scraper.

Canterbury Bankstown uses a SharePoint-backed CMS with base64-encoded document
paths served via Azure:
    webdocs.bankstown.nsw.gov.au/api/publish?documentPath={base64}&title={filename}.pdf
    cbcity-webdocs.azurewebsites.net/api/publish?documentPath={base64}&title={filename}.pdf

The title parameter contains the readable filename. Chapter labels are derived
from the title parameter since the link text on the hub page is often just the
PDF filename.
"""

import re
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from .inner_west import HubScrapeError, _match_by_label, _match_by_filename, _slug

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "text/html,*/*",
}

# Patterns that identify CB's document hosting
CB_DOC_HOSTS = ("webdocs.bankstown.nsw.gov.au", "cbcity-webdocs.azurewebsites.net")

# The hub links every numbered chapter through a short link, cb.city/DCP7-3, that
# 301s to the CURRENT version's api/publish URL. Those hrefs do not end in .pdf, so
# they were skipped, and an amendment published under a new filename was never seen:
# on 2026-10-21 chapters 1.1, 7.3 and 7.6 had newer versions on the council's site.
CB_SHORT_LINK = re.compile(r"^https?://cb\.city/DCP(\d+)-(\d+)/?$", re.IGNORECASE)


def _resolve_short_link(href: str, timeout: int) -> str | None:
    """The api/publish URL a cb.city short link redirects to, or None."""
    try:
        resp = requests.head(href, headers=HEADERS, timeout=timeout, allow_redirects=False)
    except requests.RequestException:
        return None
    location = resp.headers.get("Location") if resp.status_code in (301, 302, 303, 307, 308) else None
    return location if location and "api/publish" in location else None


def _match_by_chapter_number(major: str, minor: str, expected_keys: set[str]) -> str | None:
    """The one key named chapter-<major>-<minor>-..., matched exactly.

    Not the fuzzy label match: "Chapter 7.3 - City East" and "Chapter 7.2 - City West"
    share 60% of their words, which that matcher accepts, and a wrong match here would
    swap one chapter's document for another's.
    """
    if not (major and minor and major.isdigit() and minor.isdigit()):
        return None
    prefix = f"chapter-{int(major)}-{int(minor)}-"
    hits = [k for k in expected_keys if k.startswith(prefix)]
    return hits[0] if len(hits) == 1 else None


def _extract_label_from_title(url: str, link_text: str) -> str:
    """Extract a readable chapter label from the CB URL title parameter.

    The title parameter has format like:
        2025.08.01 - DCP 2023 - AMENDMENT 8 - Chapter 3.2 - Parking.pdf
    We extract "Chapter 3.2 - Parking".
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    title = params.get("title", [""])[0]

    if title:
        # Strip date prefix and DCP/Amendment prefix
        # "2025.08.01 - DCP 2023 - AMENDMENT 8 - Chapter 3.2 - Parking.pdf"
        # → "Chapter 3.2 - Parking"
        m = re.search(r"(Chapter\s+\d+\.\d+\s*-\s*.+?)\.pdf$", title, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        # Fallback: strip date and DCP prefix
        cleaned = re.sub(r"^\d{4}\.\d{2}\.\d{2}\s*-\s*DCP\s+\d{4}\s*-\s*AMENDMENT\s+\d+\s*-\s*", "", title)
        cleaned = re.sub(r"\.pdf$", "", cleaned, flags=re.IGNORECASE)
        if cleaned:
            return cleaned.strip()

    return link_text or "Unknown"


def scrape_canterbury_bankstown(
    hub_url: str,
    expected_keys: set[str],
    timeout: int = 30,
    expected_labels: dict[str, str] | None = None,
) -> list[dict]:
    """Scrape Canterbury Bankstown DCP hub page for PDF links."""
    resp = requests.get(hub_url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    if resp.status_code != 200:
        raise HubScrapeError(f"Hub page returned HTTP {resp.status_code}: {hub_url}")

    soup = BeautifulSoup(resp.content, "lxml")
    results = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a", href=True):
        href: str = a["href"]

        short = CB_SHORT_LINK.match(href.strip())
        if short:
            target = _resolve_short_link(href.strip(), timeout)
            if target is None:
                continue
            doc_path = parse_qs(urlparse(target).query).get("documentPath", [""])[0]
            if (doc_path or target) in seen_urls:
                continue
            seen_urls.add(doc_path or target)
            results.append({
                "chapter_key": _match_by_chapter_number(short.group(1), short.group(2), expected_keys),
                "url": target,
                "label": _extract_label_from_title(target, a.get_text(" ", strip=True)),
            })
            continue

        if not href.lower().endswith(".pdf"):
            continue

        # Must be from CB's document hosting
        parsed = urlparse(href)
        if parsed.netloc and parsed.netloc not in CB_DOC_HOSTS:
            # Relative URLs — check if they contain the api/publish pattern
            if "api/publish" not in href:
                continue

        # Build absolute URL
        if href.startswith("http"):
            full_url = href
        else:
            full_url = urljoin(resp.url, href)

        # Deduplicate by documentPath parameter (same doc may appear with different titles)
        params = parse_qs(urlparse(full_url).query)
        doc_path = params.get("documentPath", [""])[0]
        dedup_key = doc_path or full_url
        if dedup_key in seen_urls:
            continue
        seen_urls.add(dedup_key)

        raw_label = a.get_text(" ", strip=True)
        label = _extract_label_from_title(full_url, raw_label)

        chapter_key = None
        if expected_labels:
            chapter_key = _match_by_label(label, expected_labels)
        if chapter_key is None:
            # Use the cleaned label as pseudo-filename for matching
            chapter_key = _match_by_filename(_slug(label), expected_keys)

        results.append({
            "chapter_key": chapter_key,
            "url": full_url,
            "label": label,
        })

    if not results:
        raise HubScrapeError(
            f"No PDF links found on Canterbury Bankstown hub page: {hub_url}"
        )

    return results
