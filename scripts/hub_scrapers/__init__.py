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
from .waverley import scrape_waverley
from .cumberland import scrape_cumberland
from .penrith import scrape_penrith
from .generic import (
    scrape_blacktown, scrape_campbelltown, scrape_liverpool,
    scrape_hornsby, scrape_parramatta, scrape_northern_beaches,
    scrape_randwick, scrape_sutherland, scrape_bayside, scrape_georges_river,
    scrape_burwood, scrape_camden, scrape_canada_bay, scrape_fairfield,
    scrape_ryde, scrape_strathfield, scrape_the_hills,
)

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
    # Waverley (Squiz Matrix — /media/documents/ + /__data/assets/)
    "waverley":              scrape_waverley,
    # Cumberland (Drupal — /sites/default/files/inline-files/)
    "cumberland":            scrape_cumberland,
    # Penrith (standard CMS — /images/)
    "penrith":               scrape_penrith,
    # Generic scraper councils (browser-like headers for bot protection)
    "blacktown":             scrape_blacktown,
    "campbelltown":          scrape_campbelltown,
    "liverpool":             scrape_liverpool,
    "hornsby":               scrape_hornsby,
    "parramatta":            scrape_parramatta,
    "northern_beaches":      scrape_northern_beaches,
    "randwick":              scrape_randwick,
    "sutherland":            scrape_sutherland,
    "bayside":               scrape_bayside,
    "georges_river":         scrape_georges_river,
    # New LGAs (May 2026)
    "burwood":               scrape_burwood,
    "camden":                scrape_camden,
    "canada_bay":            scrape_canada_bay,
    "fairfield":             scrape_fairfield,
    "ryde":                  scrape_ryde,
    "strathfield":           scrape_strathfield,
    "the_hills":             scrape_the_hills,
    "the_hills_shire":       scrape_the_hills,
    # ⚠ The REGISTRY slug is `sutherland_shire`; this module was written as
    # `sutherland`. Without this alias scrape_sutherland is unreachable, so the
    # council never gets a hub scrape and never discovers a new document -- the
    # same miss `the_hills_shire` above was added for, overlooked here.
    # Measured 2026-09-27: sutherland_shire had url_last_checked NULL on every row.
    # Fixing the alias alone changes nothing visible; it surfaces the hub's 403,
    # which is why it lands together with the fall-through fix in r2_monitor.
    "sutherland_shire":      scrape_sutherland,
}

__all__ = ["HUB_SCRAPERS", "HubScrapeError"]
