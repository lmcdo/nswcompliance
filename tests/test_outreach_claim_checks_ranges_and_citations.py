"""The claim 8 and claim 17 wording sub-checks count what the claims are about, and can still fail.

prior-art-checked: tests for two sub-checks already in scripts/outreach_claim_checks.py; the existing file
tests/test_outreach_claim_checks_plan_and_zone.py covers the plan and zone sub-checks, not these two.

The served entries are handed in by replacing served_entries(), so each case states exactly what the serve path
returned.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import outreach_claim_checks as occ  # noqa: E402

PDF = {"ch1": "https://pub-x.r2.dev/source-pdfs/dcps/c/v1/ch1.pdf"}


def _entry(**kw):
    base = {"value_min": 6.0, "value_max": None, "unit": "m", "semantic_type": "front_setback",
            "requirement": "6 m minimum", "clause": "C1.2", "source_text": "Front setback 6m",
            "source_chapter_key": "ch1"}
    base.update(kw)
    return base


def _serve(monkeypatch, *entries, urls=PDF, instruments=None):
    monkeypatch.setattr(occ, "served_entries", lambda: ([("council", e, urls) for e in entries], ""))
    monkeypatch.setattr(occ, "registered_instruments", lambda: {} if instruments is None else instruments)


# ── claim 8: every served NUMBER is cited ──────────────────────────────────────────────────────────

def test_a_number_without_a_pdf_link_fails(monkeypatch):
    _serve(monkeypatch, _entry(source_chapter_key="legacy-key"))
    verdict, detail = occ.every_served_number_is_cited()
    assert verdict == occ.FAIL and "1 of 1" in detail


def test_a_no_set_number_note_is_not_counted_as_a_number(monkeypatch):
    """Confusable negative: "No maximum site coverage specified in the DCP" carries no number to cite."""
    _serve(monkeypatch, _entry(), _entry(value_min=None, value_max=None, source_chapter_key="_external_lep",
                                          requirement="No maximum site coverage specified in the DCP"))
    verdict, detail = occ.every_served_number_is_cited()
    assert verdict == occ.PASS and "0 of 1" in detail


def test_a_number_missing_its_sentence_still_fails(monkeypatch):
    _serve(monkeypatch, _entry(source_text=""))
    assert occ.every_served_number_is_cited()[0] == occ.FAIL


SUTHERLAND_LEP = {"council": frozenset({"epi-2015-0319"})}


def _lep_row(url):
    return (_entry(source_chapter_key="sutherland-lep-2015-schedule-3", clause="LEP 2015 Schedule 3",
                   source_text="A setback from the side boundaries of at least 1.5m"),
            {"sutherland-lep-2015-schedule-3": url})


def test_an_lep_clause_linked_to_the_official_legislation_page_passes(monkeypatch):
    """Sutherland LEP 2015 Sch 3 numbers are published on legislation.nsw.gov.au, not in a council PDF."""
    entry, urls = _lep_row("https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2015-0319#sch.3")
    _serve(monkeypatch, entry, urls=urls, instruments=SUTHERLAND_LEP)
    verdict, detail = occ.every_served_number_is_cited()
    assert verdict == occ.PASS and "0 of 1" in detail


def test_the_legislation_home_page_is_not_a_source_link(monkeypatch):
    """Confusable negative: the right site, but no instrument is opened."""
    entry, urls = _lep_row("https://legislation.nsw.gov.au/")
    _serve(monkeypatch, entry, urls=urls, instruments=SUTHERLAND_LEP)
    assert occ.every_served_number_is_cited()[0] == occ.FAIL


def test_another_councils_lep_on_the_legislation_site_is_not_a_source_link(monkeypatch):
    """Confusable negative: a real instrument view, but Woollahra LEP 2014 (epi-2015-0020) is not this council's."""
    entry, urls = _lep_row("https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2015-0020")
    _serve(monkeypatch, entry, urls=urls, instruments=SUTHERLAND_LEP)
    assert occ.every_served_number_is_cited()[0] == occ.FAIL


class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, *args):
        pass

    def fetchall(self):
        return self.rows


class _FakeConn:
    def __init__(self, rows):
        self.rows = rows

    def cursor(self):
        return _FakeCursor(self.rows)

    def close(self):
        pass


def test_a_longer_registry_id_does_not_register_its_prefix(monkeypatch):
    """Confusable negative: epi-2024-12345 must not make epi-2024-1234 count as registered, while an ordinary
    legislation_url with a section anchor still registers its instrument."""
    rows = [("council", "epi-2024-12345", None),
            ("council", None, "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2015-0319#sch.3")]
    monkeypatch.setattr(occ, "_connect", lambda: _FakeConn(rows))
    assert occ.registered_instruments() == {"council": frozenset({"epi-2015-0319"})}


def test_an_unreadable_instrument_registry_is_unknown_not_a_pass(monkeypatch):
    entry, urls = _lep_row("https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2015-0319#sch.3")
    _serve(monkeypatch, entry, urls=urls)
    monkeypatch.setattr(occ, "registered_instruments", lambda: None)
    assert occ.every_served_number_is_cited()[0] == occ.UNKNOWN


def test_a_council_hub_page_or_a_look_alike_host_is_still_not_a_source_link(monkeypatch):
    """Confusable negatives: a DCP hub page lists documents rather than being one, and a host that merely starts
    with the legislation site's name is someone else's site."""
    urls = {"hub": "https://www.sutherlandshire.nsw.gov.au/plan-and-build/Planning-considerations/development-control-plan-dcp",
            "fake": "https://legislation.nsw.gov.au.example.com/view/whole/html/inforce/current/epi-2015-0319"}
    _serve(monkeypatch, _entry(source_chapter_key="hub"), _entry(source_chapter_key="fake"), urls=urls)
    verdict, detail = occ.every_served_number_is_cited()
    assert verdict == occ.FAIL and "2 of 2" in detail


# ── claim 17: a range is not a maximum, and a number keeps its unit ────────────────────────────────

def test_a_range_printed_as_a_maximum_the_plan_does_not_state_fails(monkeypatch):
    _serve(monkeypatch, _entry(semantic_type="rear_setback", value_min=3.0, value_max=6.0,
                               requirement="3 m minimum; 6 m maximum",
                               source_text="Table 3 Setback Requirements: rear 3m to 6m by lot width"))
    verdict, detail = occ.no_range_printed_as_a_maximum()
    assert verdict == occ.FAIL and "set: 1" in detail


def test_a_maximum_the_councils_sentence_states_passes(monkeypatch):
    """Confusable negative: canada_bay's "Minimum 1, maximum 2 car parking spaces" really sets a maximum."""
    _serve(monkeypatch, _entry(semantic_type="car_parking", value_min=1.0, value_max=2.0, unit="spaces/dwelling",
                               requirement="1 spaces/dwelling minimum; 2 spaces/dwelling maximum",
                               source_text="Minimum 1, maximum 2 car parking spaces (Table C-B)"))
    assert occ.no_range_printed_as_a_maximum()[0] == occ.PASS


def test_a_maximum_the_councils_sentence_denies_fails(monkeypatch):
    """Cross-review 2026-09-14: 'no maximum applies' names the word, so a bare search passed a printed maximum."""
    _serve(monkeypatch, _entry(semantic_type="rear_setback", value_min=3.0, value_max=6.0,
                               requirement="3 m minimum; 6 m maximum",
                               source_text="Minimum setback varies from 3m to 6m; no maximum applies"))
    verdict, detail = occ.no_range_printed_as_a_maximum()
    assert verdict == occ.FAIL and "set: 1" in detail


def test_a_number_printed_in_metres_when_its_unit_is_spaces_fails(monkeypatch):
    """The 2026-09-14 case: every number printed as metres, so a parking rate read '1 m minimum'."""
    _serve(monkeypatch, _entry(semantic_type="car_parking", value_min=1.0, unit="spaces/dwelling",
                               requirement="1 m minimum", source_text="1 space per dwelling"))
    verdict, detail = occ.no_range_printed_as_a_maximum()
    assert verdict == occ.FAIL and "own: 1" in detail


def test_the_serve_paths_wording_passes_both_parts():
    """The real wording function, not a copy: what it prints for these rows satisfies the check."""
    import conveyancing_db as cdb

    cases = [
        ("rear_setback", 3.0, 6.0, "m", "rear 3m to 6m by lot width"),
        ("car_parking", 1.0, 2.0, "spaces/dwelling", "Minimum 1, maximum 2 car parking spaces"),
        ("car_parking", 1.0, None, "spaces/dwelling", "1 space per dwelling"),
        ("max_site_coverage", 60.0, None, "%", "Maximum site coverage of 60%"),
    ]
    entries = []
    for semantic, vmin, vmax, unit, text in cases:
        entries.append(_entry(semantic_type=semantic, value_min=vmin, value_max=vmax, unit=unit, source_text=text,
                              requirement=cdb.requirement_text(semantic, vmin, vmax, unit, text)))
    original = occ.served_entries
    occ.served_entries = lambda: ([("council", e, PDF) for e in entries], "")
    try:
        verdict, detail = occ.no_range_printed_as_a_maximum()
    finally:
        occ.served_entries = original
    assert verdict == occ.PASS, detail
