"""The Canterbury-Bankstown scraper must see the chapters behind cb.city short links.

REAL FINDING, 2026-10-21. The council's DCP page links every numbered chapter as
cb.city/DCP7-3, which 301s to the CURRENT version's api/publish URL. The scraper kept
only hrefs ending in .pdf, so it saw the 14 guides and none of the chapters. diff_urls
(the replacement check, #1188/#1189) therefore never saw a chapter's link change:
chapters 1.1, 7.3 and 7.6 had newer versions on the council's site and we held the old
ones. #1188 read the same symptom as "the page never enumerates" the chapters.

Second half: the old 7.3/1.1/11.15 links were reported dead (check_failures 6) because
their host answers HEAD 404 while a GET serves the PDF. head_request now falls back
to a range GET on 404 as well as 405.

prior-art-checked: tests/test_woollahra_scraper_skips_repealed.py is the sibling for
another council's scraper; no Canterbury-Bankstown scraper test existed.

Every URL below was copied from the live page, its redirect, or the registry on
2026-10-21.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME"):
    os.environ.setdefault(_k, "test")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import hub_scrapers.canterbury_bankstown as cb  # noqa: E402

HUB = ("https://www.cbcity.nsw.gov.au/planning-and-building/planning-city/"
       "planning-controls-and-policies/canterbury-bankstown-development-control-plan")
NEW_7_3 = ("https://cbcity-webdocs.azurewebsites.net/api/publish?documentPath=aHR0cHM6Ly9jYmNpdHkuc2hhcmVwb2ludC5jb20v"
           "c2l0ZXMvUGxhbm5pbmctU1AvRENQIEFtZW5kbWVudHMvRENQIC0gV2Vic2l0ZSBEb2N1bWVudHMgLSBDdXJyZW50IHZlcnNpb25zIG9u"
           "IENvdW5jaWwncyB3ZWJzaXRlLzIwMjYuMDQuMjQgLSBEQ1AgMjAyMyAtIEFNRU5ETUVOVCAxNCAtIENoYXB0ZXIgNy4zIC0gQ2l0eSBF"
           "YXN0LnBkZg==&title=2026.04.24%20-%20DCP%202023%20-%20AMENDMENT%2014%20-%20Chapter%207.3%20-%20City%20East.pdf")
OLD_7_3 = ("https://cbcity-webdocs.azurewebsites.net/api/publish?documentPath=aHR0cHM6Ly9jYmNpdHkuc2hhcmVwb2ludC5jb20v"
           "c2l0ZXMvQ09NTVNQVUIvV2Vic2l0ZSBEb2N1bWVudHMvMjAyNi4wMy4zMCAtIERDUCAyMDIzIC0gQU1FTkRNRU5UIDEzIC0gQ2hhcHRl"
           "ciA3LjMgLSBDaXR5IEVhc3QucGRm&title=2026.03.30%20-%20DCP%202023%20-%20AMENDMENT%2013%20-%20Chapter%207.3%20-%20City%20East.pdf")
NEW_7_2 = ("https://webdocs.bankstown.nsw.gov.au/api/publish?documentPath=aHR0cDovL2lzaGFyZS9zaXRlcy9QbGFubmluZy9TUC9E"
           "Q1AgQW1lbmRtZW50cy9EQ1AgLSBXZWJzaXRlIERvY3VtZW50cyAtIEN1cnJlbnQgdmVyc2lvbnMgb24gQ291bmNpbCdzIHdlYnNpdGUv"
           "MjAyNS4wOC4wMSAtIERDUCAyMDIzIC0gQU1FTkRNRU5UIDggLSBDaGFwdGVyIDcuMiAtIENpdHkgV2VzdC5wZGY=&title=2025.08.01"
           "%20-%20DCP%202023%20-%20AMENDMENT%208%20-%20Chapter%207.2%20-%20City%20West.pdf")
NEW_7_6 = ("https://cbcity-webdocs.azurewebsites.net/api/publish?documentPath=aHR0cHM6Ly9jYmNpdHkuc2hhcmVwb2ludC5jb20v"
           "c2l0ZXMvUGxhbm5pbmctU1AvRENQIEFtZW5kbWVudHMvRENQIC0gV2Vic2l0ZSBEb2N1bWVudHMgLSBDdXJyZW50IHZlcnNpb25zIG9u"
           "IENvdW5jaWwncyB3ZWJzaXRlLzIwMjYuMDYuMjIgLSBEQ1AgMjAyMyAtIEFNRU5ETUVOVCAxMyAtIENoYXB0ZXIgNy42IC0gQmVsbW9y"
           "ZSBhbmQgTGFrZW1iYSAtIHdlYnNpdGUucGRm&title=2026.06.22%20-%20DCP%202023%20-%20AMENDMENT%2013%20-%20Chapter"
           "%207.6%20-%20Belmore%20and%20Lakemba%20-%20website.pdf")
REDIRECTS = {"https://cb.city/DCP7-3": NEW_7_3, "https://cb.city/DCP7-2": NEW_7_2}
KEYS = {"chapter-7-2-city-west", "chapter-7-3-city-east", "chapter-11-15-marco-avenue"}
PAGE = f"""<html><body>
<a href="https://cb.city/DCP7-2">Chapter 7.2 - City West</a>
<a href="https://cb.city/DCP7-3">Chapter 7.3 - City East</a>
<a href="https://cb.city/DCP7-6">Chapter 7.6 - Belmore and Lakemba</a>
<a href="https://cb.city/DCP9-9">Chapter 9.9 - no redirect</a>
</body></html>"""


def _resp(status, headers=None, content=b""):
    r = MagicMock()
    r.status_code, r.headers, r.content, r.url = status, headers or {}, content, HUB
    return r


def _patch_network(monkeypatch, redirects=REDIRECTS):
    monkeypatch.setattr(cb.requests, "get", lambda *a, **k: _resp(200, content=PAGE.encode()))
    monkeypatch.setattr(cb.requests, "head", lambda url, **k: (
        _resp(301, {"Location": redirects[url]}) if url in redirects else _resp(404)))


def test_short_links_resolve_to_the_current_version_of_the_right_chapter(monkeypatch):
    _patch_network(monkeypatch)
    found = {d["chapter_key"]: d["url"] for d in cb.scrape_canterbury_bankstown(HUB, KEYS)}
    assert found["chapter-7-3-city-east"] == NEW_7_3
    assert found["chapter-7-2-city-west"] == NEW_7_2  # not swapped with its neighbour


def test_a_short_link_with_no_registry_chapter_is_offered_unmatched(monkeypatch):
    """7.6 is not in this registry, so it is offered unmatched (diff_urls' 'added'),
    never forced onto a key. 9.9 does not redirect, so it is skipped."""
    _patch_network(monkeypatch, {**REDIRECTS, "https://cb.city/DCP7-6": NEW_7_6})
    found = cb.scrape_canterbury_bankstown(HUB, KEYS)
    by_url = {d["url"]: d["chapter_key"] for d in found}
    assert by_url[NEW_7_6] is None
    assert len(found) == 3


def test_chapter_number_match_is_exact():
    assert cb._match_by_chapter_number("7", "3", KEYS) == "chapter-7-3-city-east"
    assert cb._match_by_chapter_number("11", "1", KEYS) is None  # not chapter-11-15-...
    assert cb._match_by_chapter_number("7", "3", KEYS | {"chapter-7-3-city-east-old"}) is None


def test_the_existing_replacement_check_now_sees_the_new_version(monkeypatch):
    """The point of the fix: diff_urls reports 7.3 as moved to its new link."""
    import r2_monitor
    _patch_network(monkeypatch)
    discovered = cb.scrape_canterbury_bankstown(HUB, KEYS)
    diff = r2_monitor.diff_urls(discovered, [{"chapter_key": "chapter-7-3-city-east", "council_url": OLD_7_3}], None)
    assert ("chapter-7-3-city-east", OLD_7_3, NEW_7_3) in diff.url_migrated


def test_head_404_falls_back_to_get(monkeypatch):
    import r2_monitor
    monkeypatch.setattr(r2_monitor.SESSION, "head", lambda *a, **k: _resp(404))
    monkeypatch.setattr(r2_monitor.SESSION, "get", lambda *a, **k: _resp(206, {"Content-Range": "bytes 0-0/3182931", "Content-Type": "application/pdf"}))
    assert r2_monitor.head_request(OLD_7_3)["status"] == 200


def test_a_link_that_is_really_gone_still_fails(monkeypatch):
    import r2_monitor
    monkeypatch.setattr(r2_monitor.SESSION, "head", lambda *a, **k: _resp(404))
    monkeypatch.setattr(r2_monitor.SESSION, "get", lambda *a, **k: _resp(404))
    assert r2_monitor.head_request(OLD_7_3)["status"] == 404


# ── Cross-review 2026-10-21 ───────────────────────────────────────────────────

def test_a_redirect_off_the_councils_document_hosts_is_refused(monkeypatch):
    for bad in ("https://unrelated.example/api/publish?documentPath=x",
                "/api/publish?documentPath=x",
                "http://cbcity-webdocs.azurewebsites.net/api/publish?documentPath=x"):
        monkeypatch.setattr(cb.requests, "head", lambda *a, _b=bad, **k: _resp(301, {"Location": _b}))
        assert cb._resolve_short_link("https://cb.city/DCP7-3", 30) is None, bad


def test_head_404_then_an_html_page_is_still_a_failure(monkeypatch):
    import r2_monitor
    monkeypatch.setattr(r2_monitor.SESSION, "head", lambda *a, **k: _resp(404))
    monkeypatch.setattr(r2_monitor.SESSION, "get", lambda *a, **k: _resp(200, {"Content-Type": "text/html"}))
    assert r2_monitor.head_request(OLD_7_3)["status"] == 404
