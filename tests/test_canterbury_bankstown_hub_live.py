"""The Canterbury-Bankstown scraper against the council's REAL hub page.

The fixture tests in test_cb_scraper_follows_short_links.py prove the logic; this
proves the page still has the shape that logic expects. If the council stops using
cb.city short links, the fixture tests stay green and this one goes red.

prior-art-checked: no live test for any hub scraper existed.

Run with `PYTEST_REAL_HTTP=1 pytest -m integration tests/test_canterbury_bankstown_hub_live.py -o addopts=`.
Without PYTEST_REAL_HTTP=1, conftest_mocks stubs `requests`, so this skips and says so.
"""
import os
import sys
from collections import Counter
from pathlib import Path

import pytest

for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
    os.environ.setdefault(_k, "test")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

HUB = ("https://www.cbcity.nsw.gov.au/planning-and-building/planning-city/"
       "planning-controls-and-policies/canterbury-bankstown-development-control-plan")
# Keys as the registry holds them (dcp_chapter_registry, 2026-10-21).
KEYS = {"chapter-1-1-introduction-and-administration", "chapter-7-2-city-west",
        "chapter-7-3-city-east", "chapter-7-6-belmore-and-lakemba", "chapter-11-15-marco-avenue"}


@pytest.mark.integration
def test_live_hub_exposes_every_numbered_chapter_through_a_short_link():
    if os.environ.get("PYTEST_REAL_HTTP") != "1":
        pytest.skip("requests is stubbed by conftest_mocks; set PYTEST_REAL_HTTP=1")
    import requests
    import hub_scrapers.canterbury_bankstown as cb
    try:
        found = cb.scrape_canterbury_bankstown(HUB, KEYS)
    except (requests.RequestException, cb.HubScrapeError) as exc:
        pytest.skip(f"council hub page not reachable from here: {exc}")
    matched = [d["chapter_key"] for d in found if d["chapter_key"]]
    assert set(matched) == KEYS, f"short links no longer resolve for: {sorted(KEYS - set(matched))}"
    assert not [k for k, n in Counter(matched).items() if n > 1], "a key matched twice"
    assert all("api/publish" in d["url"] for d in found if d["chapter_key"])
