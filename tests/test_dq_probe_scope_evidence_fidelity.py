"""Tests for the scope_evidence fidelity probe.

prior-art-checked: tests/test_scope_evidence_declared.py asserts that a
declaration CARRIES a sentence; this file tests the machinery that asks whether
the sentence is TRUE. No existing test imports
scripts/dq_probe_scope_evidence_fidelity.py. Swept 2026-10-03.

WHY THE PURE FUNCTIONS GET THE ATTENTION
----------------------------------------
Every bug the probe had on its first run was in them, and each one made it
report a correct quote as MISSING or a false one as fine:

  * `loose()` STRIPPED accents instead of folding them, so Waverley Part D2's
    "café" became "caf" and a correct quote failed.
  * `spans()` harvested any long single-quoted run, which picked up our own
    prose split on an apostrophe ("Penrith's own introductory Part" ->
    "s own introductory Part") and picked up section headings quoted in order
    to say a chapter does NOT have one.
  * `resolve()` must never guess: two candidate chapters has to mean None,
    because attaching a council's sentence to the wrong chapter is worse than
    leaving it unchecked.

A probe that cries wolf gets switched off, so its precision is the thing under
test, not its plumbing.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "dq_probe_scope_evidence_fidelity",
    ROOT / "scripts" / "dq_probe_scope_evidence_fidelity.py")
probe = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(probe)


class TestLooseFoldsRatherThanStrips:
    def test_an_accent_folds_to_its_base_letter(self):
        """The bug that reported Waverley Part D2's correct quote as MISSING.

        The PDF prints "café"; the config quotes "cafe". Stripping the accent
        turned the document's word into "caf" and the two could never match.
        """
        assert probe.loose("café or restaurant") == probe.loose("cafe or restaurant")

    def test_curly_quotes_and_dashes_do_not_decide_a_verdict(self):
        assert probe.loose("Council’s requirements — all land") == \
               probe.loose("Council's requirements -- all land")

    def test_line_breaks_and_double_spaces_collapse(self):
        assert probe.loose("applies to\n  all   land") == "applies to all land"

    def test_the_words_still_have_to_match(self):
        """Loose on punctuation, STRICT on words. A paraphrase must not pass."""
        assert probe.loose("applies to all land") != probe.loose("applies to some land")


class TestSpansOnlyTakesPromises:
    def test_a_verbatim_span_is_taken(self):
        ev = "Section 1.1, verbatim: 'This Part applies to all land within the LGA.' Therefore ALL."
        assert probe.spans(ev) == ["This Part applies to all land within the LGA."]

    def test_a_page_cited_span_is_taken(self):
        """12 of Waverley's 22 claims use this form rather than `verbatim:`, so
        dropping it reported real page-cited quotations as UNPARSED."""
        ev = "'This Part applies to any type of low density development' (PDF p167) names no zone."
        assert probe.spans(ev) == ["This Part applies to any type of low density development"]

    def test_our_own_prose_split_on_an_apostrophe_is_NOT_taken(self):
        """The first version read this as a claim about the document.

        "Penrith's own introductory Part, which would carry the plan-level
        sentence, is not in dcp_chapter_registry" has two apostrophes in it, and
        everything between them was asserted against the PDF.
        """
        ev = ("Penrith's own introductory Part, which would carry the plan-level sentence, "
              "is not in dcp_chapter_registry, so the inherited sentence cannot be quoted.")
        assert probe.spans(ev) == []

    def test_a_heading_quoted_to_say_it_is_ABSENT_is_not_taken(self):
        """Several entries record that a chapter carries NO such section. The
        probe used to demand the absent thing be present."""
        ev = ("NO land-application clause exists. All 84 pages were read and the Part carries "
              "no 'land to which this Part applies' section anywhere in it.")
        assert probe.spans(ev) == []

    def test_a_short_fragment_is_not_a_quotation(self):
        """Under MIN_SPAN it would match almost any planning document."""
        ev = "verbatim: 'applies to land'"
        assert probe.spans(ev) == []

    def test_the_same_span_is_not_counted_twice(self):
        ev = ("verbatim: 'This Part applies to all land within the LGA.' and again "
              "'This Part applies to all land within the LGA.' (PDF p7)")
        assert len(probe.spans(ev)) == 1


class TestCheckSpan:
    HAY = probe.loose("Section 1.1 Land to which this Part applies. This Part of the DCP "
                      "applies to all land within the Blacktown Local Government Area zoned "
                      "for residential purposes under Blacktown LEP 2015.")

    def test_a_present_span_passes(self):
        good, bad = probe.check_span("applies to all land within the Blacktown Local "
                                     "Government Area", self.HAY)
        assert good and bad == ""

    def test_an_absent_span_fails_and_names_itself(self):
        good, bad = probe.check_span("applies to all land within the Penrith Local "
                                     "Government Area", self.HAY)
        assert not good
        assert "Penrith" in bad

    def test_an_abridged_span_is_checked_PIECEWISE_not_waved_through(self):
        """An ellipsis must not become permission. Every fragment of 20+
        characters still has to be in the document."""
        good, _ = probe.check_span(
            "Land to which this Part applies ... zoned for residential purposes", self.HAY)
        assert good
        bad_good, bad_frag = probe.check_span(
            "Land to which this Part applies ... zoned for INDUSTRIAL purposes", self.HAY)
        assert not bad_good
        assert "INDUSTRIAL" in bad_frag.upper()


class TestResolveNeverGuesses:
    REG = {
        "blacktown": [{"key": "blacktown-dcp-2015-part-c", "url": "u", "pages": 91},
                      {"key": "part-a-car-parking", "url": "u", "pages": 20}],
        "waverley": [{"key": "waverley-dcp-2022", "url": "u", "pages": 473},
                     {"key": "something-small", "url": "u", "pages": 4}],
        "ku_ring_gai": [{"key": "section-a-part-2-site-analysis", "url": "u", "pages": 6},
                        {"key": "section-b-part-19-heritage", "url": "u", "pages": 59}],
        "ambiguous": [{"key": "part-1-alpha", "url": "u", "pages": 5},
                      {"key": "part-1-beta", "url": "u", "pages": 5}],
    }

    def test_an_exact_chapter_key_resolves(self):
        got = probe.resolve("blacktown", "blacktown_dcp_2015_part_c", "chapter_topics", self.REG)
        assert got["key"] == "blacktown-dcp-2015-part-c"

    def test_a_parts_config_takes_the_single_whole_dcp_document(self):
        """Waverley's part keys are single letters against ONE PDF. This must
        come before the substring rule or 'A' matches most chapter keys."""
        got = probe.resolve("waverley", "A", "parts", self.REG)
        assert got["key"] == "waverley-dcp-2022"

    def test_a_section_prefixed_registry_key_resolves_by_unique_substring(self):
        """Ku-ring-gai configs key 'part_2_site_analysis' while the registry
        says 'section-a-part-2-site-analysis'."""
        got = probe.resolve("ku_ring_gai", "part_2_site_analysis", "chapter_topics", self.REG)
        assert got["key"] == "section-a-part-2-site-analysis"

    def test_two_candidates_resolve_to_NOTHING(self):
        """The whole point. UNRESOLVED is a reported state; a guess is not."""
        assert probe.resolve("ambiguous", "part_1", "chapter_topics", self.REG) is None

    def test_an_unknown_council_resolves_to_nothing(self):
        assert probe.resolve("nowhere", "anything", "chapter_topics", self.REG) is None

    def test_the_warringah_slug_override_is_present(self):
        """COUNCIL_CONFIGS keys this council by the PLAN name and the registry by
        the COUNCIL name. Without the override every Warringah entry reports
        UNRESOLVED and the probe looks clean while checking nothing."""
        assert probe.COUNCIL_SLUG_OVERRIDE["warringah"] == "northern_beaches"


@pytest.mark.database
class TestAgainstTheRealRegistry:
    """The one real-layer check: the probe's single query against live data.

    Skips without an explicit opt-in, because conftest_mocks.py stubs psycopg2
    and a mocked cursor would hand this a MagicMock and "pass" on nonsense.
    """

    @pytest.fixture(autouse=True)
    def _require_real_db(self):
        if not os.environ.get("PYTEST_REAL_DB"):
            pytest.skip("needs PYTEST_REAL_DB=1 and DATABASE_URL (see .claude/rules/testing-and-qa.md)")

    def test_the_registry_query_returns_chapters_with_urls(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import dq_db
        with dq_db.session() as conn:
            reg = probe.load_registry(conn.cursor())
        assert reg, "load_registry returned nothing — the query or the table moved"
        # Rows with no public PDF are excluded on purpose: an entry pointing at
        # one is UNRESOLVED rather than clean.
        for council, chapters in reg.items():
            for chapter in chapters:
                assert chapter["url"], f"{council}/{chapter['key']} has no URL but was returned"

    def test_a_known_council_resolves_to_a_real_chapter(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import dq_db
        with dq_db.session() as conn:
            reg = probe.load_registry(conn.cursor())
        got = probe.resolve("northern_beaches", "B", "parts", reg)
        assert got and "warringah" in got["key"]
