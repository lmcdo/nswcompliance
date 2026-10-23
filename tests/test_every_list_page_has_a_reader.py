"""Every council with a stored DCP list page must have a reader registered.

Real data: the councils with an active council_page_url in dcp_chapter_registry, read 2026-10-24.
Known-wrong case: Wingecarribee, Ku-ring-gai and Wollongong had a stored page and no reader, so run 5
recorded `no_scraper` and their new documents could never be found.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hub_scrapers import HUB_SCRAPERS  # noqa: E402

COUNCILS_WITH_A_LIST_PAGE = [
    "ashfield", "bayside", "blacktown", "burwood", "camden", "campbelltown", "canada_bay",
    "canterbury_bankstown", "city_of_sydney", "cumberland", "fairfield", "georges_river", "hornsby",
    "ku_ring_gai", "leichhardt", "marrickville", "parramatta", "penrith", "randwick", "ryde",
    "strathfield", "sutherland_shire", "the_hills", "the_hills_shire", "waverley", "wingecarribee",
    "wollongong", "woollahra",
]


def test_every_council_with_a_list_page_has_a_reader():
    missing = [c for c in COUNCILS_WITH_A_LIST_PAGE if c not in HUB_SCRAPERS]
    assert missing == []


def test_the_three_added_readers_are_callable():
    for c in ("wingecarribee", "ku_ring_gai", "wollongong"):
        assert callable(HUB_SCRAPERS[c])
