"""The Woollahra scraper must not offer a repealed chapter as the chapter's current URL.

REAL FINDING, 2026-09-13. 19 of Woollahra's 27 active registry chapters pointed into
the council's /development-control-plans/repealed-dcps/ archive. #1079 made extraction
REJECT those sources; it did not say how the registry got there. This is how:

  1. The council's rules page lists the in-force chapter AND, lower down, every
     superseded version, in a repealed-dcps folder under the same DCP path.
  2. An archived file name still carries the chapter name, so the scraper matched it
     to the same chapter_key as the in-force link.
  3. r2_monitor.diff_urls builds {chapter_key: link}. The LAST link per key wins, and
     the archive comes last -- so the monthly monitor recorded a "URL migration" into
     the archive and wrote it to dcp_chapter_registry.council_url.

A registry re-point on its own would be undone by the next monitor run. These tests
drive the real scraper loop and the real diff_urls over a page shaped like Woollahra's.

The page HTML is a fixture, but every URL in it was copied from the live registry or
the council's page on 2026-09-13, not invented.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# r2_monitor reads its R2 settings at import. Without these the diff_urls tests pass or
# fail depending on which test file happened to import it first in the same run.
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
    os.environ.setdefault(_k, "test")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import hub_scrapers.woollahra as w  # noqa: E402

KEY = "chapter-b1-residential-precincts"
BASE = "https://www.woollahra.nsw.gov.au"
CURRENT = ("/files/assets/public/v/1/plans-policies-publications/development-control-plans/"
           "chapter-b1-residential-precincts.pdf")
REPEALED = ("/files/assets/public/v/1/plans-policies-publications/development-control-plans/"
            "repealed-dcps/woollahra-dcp-2015-repealed-7-december-2020-chapter_b1_residential_precincts.pdf")
# A repealed file that does NOT sit under /development-control-plans/ -- the D2 case.
REPEALED_ELSEWHERE = ("/files/assets/public/v/1/building-and-development/documents/"
                      "repealed-31-may-2024-chapter-d2-mixed-use-centres.pdf")

PAGE = f"""<html><body>
<h2>Development Control Plan 2015</h2>
<a href="{CURRENT}">Chapter B1 - Residential Precincts (PDF 2.1MB)</a>
<h2>Repealed DCPs</h2>
<a href="{REPEALED}">Chapter B1 Residential Precincts - repealed 7 December 2020 (PDF)</a>
</body></html>"""


def _scrape(monkeypatch, page=PAGE, keys=frozenset({KEY})):
    resp = MagicMock(status_code=200, content=page.encode("utf-8"))
    monkeypatch.setattr(w.requests, "get", lambda *a, **k: resp)
    # The scraper asks for lxml, which CI's test requirements do not install. The stdlib
    # parser builds the same <a> list for this markup, so the real loop is still what runs.
    monkeypatch.setattr(w, "BeautifulSoup", lambda content, _parser: BeautifulSoup(content, "html.parser"))
    return w.scrape_woollahra(BASE + "/Building-and-development/Development-rules", set(keys))


def _import_diff_urls():
    saved = {k: sys.modules.get(k) for k in ("boto3", "botocore", "botocore.exceptions", "dotenv")}
    for k in saved:
        sys.modules[k] = MagicMock()
    try:
        import r2_monitor
        return r2_monitor.diff_urls
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


# ---------------------------------------------------------------------------
# 1. The end-to-end shape: page -> scraper -> diff_urls
# ---------------------------------------------------------------------------

def test_the_monitor_sees_no_migration_when_the_registry_already_holds_the_current_url(monkeypatch):
    diff_urls = _import_diff_urls()
    discovered = _scrape(monkeypatch)
    diff = diff_urls(discovered, [{"chapter_key": KEY, "council_url": BASE + CURRENT}], None)
    assert diff.url_migrated == [], f"the monitor would re-point {KEY} to {diff.url_migrated}"
    assert diff.url_same == [KEY]


def test_without_the_filter_the_same_page_migrates_into_the_archive(monkeypatch):
    """Proves the test above can fail: with both links offered, diff_urls keeps the last
    one, and records the in-force URL as having moved to the repealed file."""
    diff_urls = _import_diff_urls()
    monkeypatch.setattr(w, "is_repealed_link", lambda url, label: False)
    discovered = _scrape(monkeypatch)
    diff = diff_urls(discovered, [{"chapter_key": KEY, "council_url": BASE + CURRENT}], None)
    assert diff.url_migrated == [(KEY, BASE + CURRENT, BASE + REPEALED)]


def test_a_registry_already_pointing_at_the_archive_is_moved_back(monkeypatch):
    """The repair direction: once the scraper stops offering the archive, a chapter still
    pointing into it is reported as migrating to the in-force file."""
    diff_urls = _import_diff_urls()
    discovered = _scrape(monkeypatch)
    diff = diff_urls(discovered, [{"chapter_key": KEY, "council_url": BASE + REPEALED}], None)
    assert diff.url_migrated == [(KEY, BASE + REPEALED, BASE + CURRENT)]


# ---------------------------------------------------------------------------
# 2. The rule itself, with its confusable negatives
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,label", [
    (BASE + REPEALED, "Chapter B1"),
    (BASE + REPEALED_ELSEWHERE, "Chapter D2"),
    (BASE + CURRENT, "Repealed 7 December 2020 - Chapter B1"),
    (BASE + "/x/repealed%5Fdcps/chapter.pdf", ""),   # an encoded separator
])
def test_repealed_links_are_recognised(url, label):
    assert w.is_repealed_link(url, label)


@pytest.mark.parametrize("url,label", [
    (BASE + CURRENT, "Chapter B1 - Residential Precincts"),
    (BASE + "/files/notrepealedstuff/chapter-e1.pdf", "Chapter E1"),  # letters, not a token
    (BASE + CURRENT, None),
])
def test_in_force_links_are_not(url, label):
    assert not w.is_repealed_link(url, label)


def test_the_council_misnamed_d5_file_does_not_capture_d4(monkeypatch):
    """With the archive gone, the page's D5 link -- which the council labels "Double Bay
    Centre" but names chapter-d5-edgecliff-centre.pdf -- is the closest file-name match
    for the D4 Edgecliff chapter. The monitor passes the registry's chapter labels, and a
    label match wins, so D4 must stay on its own file. Labels copied from the registry
    and the page, 2026-09-13."""
    d4 = "/files/assets/public/v/3/plans-policies-publications/development-control-plans/chapter-d4-edgecliff-centre.pdf"
    d5 = "/files/assets/public/v/5/plans-policies-publications/development-control-plans/chapter-d5-edgecliff-centre.pdf"
    page = (f'<a href="{d4}">Chapter D4 - Edgecliff Centre</a>'
            f'<a href="{d5}">Chapter D5 - Double Bay Centre</a>')
    labels = {"chapter-d4-edgecliff-centre": "Chapter D4 – Edgecliff Centre",
              "chapter-d5-double-bay-centre": "Chapter D5 - Double Bay Centre"}
    resp = MagicMock(status_code=200, content=page.encode("utf-8"))
    monkeypatch.setattr(w.requests, "get", lambda *a, **k: resp)
    monkeypatch.setattr(w, "BeautifulSoup", lambda content, _parser: BeautifulSoup(content, "html.parser"))
    found = {d["chapter_key"]: d["url"]
             for d in w.scrape_woollahra(BASE + "/x", set(labels), expected_labels=labels)}
    assert found["chapter-d4-edgecliff-centre"] == BASE + d4
    assert found["chapter-d5-double-bay-centre"] == BASE + d5


def test_the_scraper_and_the_extraction_reject_share_one_definition():
    """Two copies of a guard drift. If either pattern changes, change both."""
    import dcp_extract_changed as dx
    assert w._REPEALED.pattern == dx._REPEALED_PATH.pattern
    assert w._REPEALED.flags == dx._REPEALED_PATH.flags
