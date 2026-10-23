"""v7 step 6: a council list page that is not the list must go red, never become "yesterday".

Real fixture: Canterbury Bankstown's DCP list as read 2026-10-22 (70 links). Known-wrong cases: a
homepage or error page that still has a few links, a page of the same size with other links, and a
list page that redirects to the council homepage.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from hub_scrapers import HubScrapeError  # noqa: E402
from hub_scrapers.inner_west import check_not_redirected  # noqa: E402
from verifyops_links import link_entries  # noqa: E402
from verifyops_record import Recorder, shrank  # noqa: E402

FX = json.loads((ROOT / "tests" / "fixtures" / "verifyops" / "canterbury_bankstown_list_2026-10-22.json")
                .read_text(encoding="utf-8"))
GOOD = link_entries(FX["discovered"])
NOW = datetime(2026, 10, 23, tzinfo=timezone.utc)


def _links(n, prefix="https://www.cbcity.nsw.gov.au/other/"):
    return link_entries([{"url": f"{prefix}{i}.pdf", "label": f"x{i}"} for i in range(n)])


def test_fixture_is_the_real_list():
    assert len(GOOD) == 70


def test_same_list_is_not_an_anomaly():
    assert shrank(GOOD, GOOD) is False


def test_first_scan_is_not_an_anomaly():
    assert shrank(None, GOOD[:3]) is False
    assert shrank([], GOOD[:3]) is False


def test_homepage_with_a_few_of_the_links_is_an_anomaly():
    assert shrank(GOOD, GOOD[:3]) is True


def test_half_kept_is_the_line():
    assert shrank(GOOD, GOOD[:35]) is False      # exactly half kept
    assert shrank(GOOD, GOOD[:34]) is True


def test_same_size_page_with_other_links_is_an_anomaly():
    assert shrank(GOOD, _links(70)) is True


def test_new_links_added_is_not_an_anomaly():
    assert shrank(GOOD, GOOD + _links(10)) is False


class _Conn:
    def cursor(self):
        raise AssertionError("dry run: no database")


def _rec(previous):
    rec = Recorder(_Conn(), dry_run=True, mode="daily")
    rec.previous_list = lambda council, page_url=None: previous
    return rec


def test_anomaly_is_recorded_and_not_saved_as_ok():
    rec = _rec(GOOD)
    sent = []
    homepage = [{"url": d["url"], "label": d.get("label")} for d in FX["discovered"][:3]]
    lines = rec.council_list_checked("canterbury_bankstown", FX["hub_url"], homepage, FX["held"],
                                     probe=lambda u: None, send=sent.append, now=NOW)
    assert lines == [] and sent == []
    (row,) = rec._councils
    assert row[2] == "anomaly"
    assert "not saved as the list" in row[7]


def test_good_list_is_still_ok():
    rec = _rec(GOOD)
    rec.council_list_checked("canterbury_bankstown", FX["hub_url"], FX["discovered"], FX["held"],
                             probe=lambda u: None, send=lambda t: None, now=NOW)
    assert rec._councils[0][2] == "ok"


def test_previous_list_is_asked_for_this_page():
    seen = []
    rec = Recorder(_Conn(), dry_run=True, mode="daily")
    rec.previous_list = lambda council, page_url=None: seen.append((council, page_url)) or GOOD
    rec.council_list_checked("canterbury_bankstown", FX["hub_url"], FX["discovered"], FX["held"],
                             probe=lambda u: None, send=lambda t: None, now=NOW)
    assert seen == [("canterbury_bankstown", FX["hub_url"])]


# ── redirect off the page ───────────────────────────────────────────────────────────────────────

PAGE = "https://www.thehills.nsw.gov.au/Building-and-Development/Development-Controls/Development-Control-Plans"


@pytest.mark.parametrize("final", [
    PAGE, PAGE + "/", PAGE.replace("https://www.", "https://"), PAGE.lower(),
    PAGE.replace("https://", "http://"), PAGE + "?page=1", None,
])
def test_not_a_move(final):
    check_not_redirected(PAGE, final)


@pytest.mark.parametrize("final", [
    "https://www.thehills.nsw.gov.au/",                                   # council homepage
    "https://www.thehills.nsw.gov.au/Search?q=dcp",                       # search page
    "https://www.thehills.nsw.gov.au/Building-and-Development/Development-Controls",  # parent page
    "https://www.example-cdn.com/Building-and-Development/Development-Controls/Development-Control-Plans",
])
def test_a_move_is_an_error(final):
    with pytest.raises(HubScrapeError, match="redirected off the page"):
        check_not_redirected(PAGE, final)


def test_every_reader_checks_for_a_redirect():
    for f in (ROOT / "scripts" / "hub_scrapers").glob("*.py"):
        src = f.read_text(encoding="utf-8")
        if "def scrape_" in src and "resp = " in src:
            assert src.count("check_not_redirected(hub_url, resp.url)") == 1, f.name
