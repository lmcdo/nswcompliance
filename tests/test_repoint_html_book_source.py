"""A council plan published as an ePlanning book, and the guards on rendering it.

Northern Beaches serves Warringah DCP 2011 from a URL ending "as amended 7 May 2016.pdf"
on an immutable bucket, so its hash can never change and every freshness check reads green
while telling us nothing. The council is on amendment 23 (Part G10, commenced 15 September
2025) and publishes the plan only as an online book.

These tests are pure: no browser, no network, no database. They pin the things that decide
whether a render is allowed to replace a council's source — the targeting table and the
refusal thresholds — because the failure mode is silent: a challenge page renders happily
and would otherwise be stored as the plan.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _module():
    """Import the script without running it (it has no import-time side effects)."""
    path = ROOT / "scripts" / "repoint_html_book_source.py"
    spec = importlib.util.spec_from_file_location("repoint_html_book_source", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["repoint_html_book_source"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestWhatItWillTouch:
    def test_only_registered_html_books_are_targets(self):
        """The table is the whole allow-list: a council absent from it cannot be
        re-pointed by a typo in --council."""
        m = _module()
        assert ("northern_beaches", "warringah-dcp-2011-full") in m.HTML_BOOK_SOURCES
        assert len(m.HTML_BOOK_SOURCES) == 1, (
            "a new entry needs its own evidence that the export carries the whole plan")

    def test_the_target_url_is_the_councils_own_export(self):
        m = _module()
        url = m.HTML_BOOK_SOURCES[("northern_beaches", "warringah-dcp-2011-full")]
        assert url.startswith("https://eservices.northernbeaches.nsw.gov.au/")
        # children=true is what makes the export the WHOLE book rather than one node;
        # without it the render is a contents page, which is what a browser print of the
        # book's index produced (1 page, no controls).
        assert "children=true" in url and "page=book" in url

    def test_it_does_not_point_at_the_draft_plan(self):
        """The draft Northern Beaches DCP was on exhibition to 30 August 2026 and is not
        law. Sourcing from it would serve controls that are not in force — worse than the
        stale copy this replaces."""
        m = _module()
        for url in m.HTML_BOOK_SOURCES.values():
            assert "yoursay" not in url.lower()
            assert "draft" not in url.lower()


class TestItRefusesAnythingThatIsNotThePlan:
    def test_the_size_floor_rejects_a_challenge_page(self):
        """The real render is ~23 MB over 273 pages; an error or challenge screen is
        orders of magnitude smaller, and storing one would replace a council's plan with
        a login prompt."""
        m = _module()
        assert m.MIN_RENDER_BYTES >= 2_000_000

    def test_the_floor_is_below_the_measured_render(self):
        """Guards the guard: a floor above the real document would refuse every run and
        the re-point would silently never happen."""
        m = _module()
        assert m.MIN_RENDER_BYTES < 23_567_910, "measured render, 2026-09-18"
