"""
Hub page scrapers — one per council CMS pattern.

Each scraper takes a hub page URL and a set of known chapter_keys,
and returns a list of discovered chapters:
    [{"chapter_key": str | None, "url": str, "label": str}]

chapter_key is None when no match is found (new/unknown chapter).

HUB_SCRAPERS maps council slug → scraper function.
Councils with no entry fall back to per-chapter URL checking.
"""

from .inner_west import scrape_inner_west, HubScrapeError
from .city_of_sydney import scrape_city_of_sydney
from .woollahra import scrape_woollahra
from .canterbury_bankstown import scrape_canterbury_bankstown

# council slug (matches dcp_chapter_registry.council) → scraper function
HUB_SCRAPERS: dict = {
    # Inner West (Drupal — /sites/default/files/)
    "marrickville":          scrape_inner_west,
    "leichhardt":            scrape_inner_west,
    "ashfield":              scrape_inner_west,
    # City of Sydney (/-/media/corporate/files/)
    "city_of_sydney":        scrape_city_of_sydney,
    # Woollahra (Drupal — /files/assets/public/)
    "woollahra":             scrape_woollahra,
    # Canterbury Bankstown (SharePoint/Azure — api/publish?documentPath=base64)
    "canterbury_bankstown":  scrape_canterbury_bankstown,
}

__all__ = ["HUB_SCRAPERS", "HubScrapeError"]
