"""Fidelity gate grading (2026-09) — DQ-97 follow-up.

Contract under test (anchored to a real false-flag found live: city_of_sydney
section-2-locality-statements, provision 2_1_2, page 11 — text visibly runs
across a page break per its own footer stamps '2.1-4' / '2.1-5'):
  - a confident page match grounds WORDS against a +-1 page window, not just
    the single anchor page, so text that legitimately straddles a page break
    is not falsely flagged as unmatched
  - a genuinely wrong/hallucinated number is still flagged even against the
    wider window (the fix must not weaken the numeric check into a rubber
    stamp — NUMERIC changes stay human-gated by design)
  - an ambiguous (non-confident) page match still falls back to the whole
    chapter, unchanged by this fix

2026-09-07 Sol cross-review (4 HIGH + 1 MEDIUM on the pushed branch) forced a
second pass on the numeric check specifically. Two of the four HIGH findings
are fixed; the other two were attempted and REVERTED after live re-verification
showed the fix caused a worse regression than the risk it closed -- documented
honestly below rather than silently claimed as solved:

  FIXED:
  - citation/caption/heading exclusion is SPAN-based, not value-based -- a
    legitimate 'Figure 10' citation no longer removes every occurrence of the
    digit '10' from the row, only its own matched span (confidence 1.0's
    mechanism is fixed; see the residual note below for why the finding as a
    whole is only partially closed)
  - a citation's own phrase must be independently verified present in the
    WHOLE CHAPTER's text before it is trusted at all -- a hallucinated
    citation (source says 'DS 2.6', extraction says 'DS 2.7') is no longer
    exempted just because it LOOKS like a citation (confidence 0.99, fully closed)
  - numbers are checked against a NARROWER window than words (anchor page +
    caption pages only, not +-1 neighbours) -- an unrelated NEIGHBOURING
    provision's coincidental number can no longer mask a wrong one this way
    (confidence 0.98, the neighbour-page half, fully closed)
  - row-level auto-reject (dcp_extract_changed.py) is scoped to only the
    three near-certain defect reasons; a SIZE heuristic (section_collapsed /
    oversize_new_provision) that could legitimately fire on a genuine
    amendment stays 'pending' for a human (confidence 0.91, fully closed)

  ATTEMPTED AND REVERTED (residual, accepted, documented -- not silently
  claimed fixed): sentence-level source matching (checking a number against
  its best-matching SOURCE SENTENCE rather than the whole window) was built to
  close the remaining half of confidence 1.0/0.98 -- a citation's digit
  coinciding with an unrelated genuinely-wrong value ON THE SAME PAGE. Re-run
  against real production data, it caused a severe regression: real DCP PDFs
  are full of structural extraction messiness naive sentence-splitting cannot
  handle -- unpunctuated TABLE rows (blacktown 6_1_7: an entire multi-hundred-
  word road-width table became one 'sentence') and two-column-interleaved text
  (hornsby 1_2_6: alternating unrelated column fragments produce nonsense
  'sentences'). ashfield/blacktown/georges_river/hornsby all jumped from
  single digits to 15-50%+ flagged. A length guard fixed the table case but
  not the interleaving case, and interleaving is a KNOWN, pre-existing,
  separately-tracked defect class (suspect_reason's preflight_two_column) --
  chasing further guards was diminishing, so the sentence-level mechanism was
  removed entirely rather than shipped half-working. The SAME-PAGE masking
  coincidence (source page independently contains the same digit for an
  unrelated reason) remains open, same as before this session -- see
  TestGroundRowStillAcceptsKnownResidualRisk below.
"""

import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# dcp_fidelity_gate does bare `import dcp_extract_changed` / `import verify_extraction_fidelity`,
# relying on scripts/ being on sys.path (true when run as `python scripts/dcp_fidelity_gate.py`,
# not when loaded via importlib from tests/) -- so scripts/ must be added explicitly here too.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(os.path.dirname(__file__), "..", "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_gate = _load("dcp_fidelity_gate")
_best_page = _gate._best_page
_page_window = _gate._page_window
_number_window = _gate._number_window
_blank = _gate._blank_verified_references
ground_row = _gate.ground_row


class TestPageWindow:
    """The WORD window: anchor +-1 plus any page a table caption names."""

    def test_includes_neighbours_when_present(self):
        pages = {10: "alpha", 11: "beta", 12: "gamma"}
        assert _page_window(11, pages) == "alpha beta gamma"

    def test_missing_neighbour_is_skipped_not_blank(self):
        pages = {11: "beta", 12: "gamma"}
        assert _page_window(11, pages) == "beta gamma"

    def test_single_page_chapter(self):
        pages = {1: "only page"}
        assert _page_window(1, pages) == "only page"


class TestNumberWindow:
    """The NUMBER window: anchor page ONLY plus caption pages -- deliberately
    narrower than the word window (Sol HIGH 0.98): +-1 neighbours exist for
    word-straddling, and including them for numbers would let an unrelated
    adjacent provision's coincidentally-identical value mask a wrong one."""

    def test_excludes_plain_neighbours_the_word_window_would_include(self):
        pages = {10: "alpha", 11: "beta", 12: "gamma"}
        assert _number_window(11, pages, "no captions here") == "beta"

    def test_still_includes_captioned_pages(self):
        pages = {60: "x", 61: "table one", 62: "y", 63: "table three"}
        text = "**Table 1** (Page 61)\n\n**Table 3** (Page 63)"
        assert _number_window(61, pages, text) == "table one table three"

    def test_page_straddle_false_positive_is_a_documented_accepted_residual(self):
        """Sol cross-review (MEDIUM 0.96, on push): a number that genuinely
        continues onto the next page with no table caption falls outside this
        window -- the CURRENT (imperfect) behaviour, asserted honestly rather
        than silently hidden. See _number_window's docstring for why this is
        the deliberately-chosen side of the trade-off (a flagged-but-correct
        row costs review time; a masked wrong number ships silently)."""
        pages = {11: "beta", 12: "4.5 metres, no caption here"}
        assert "4.5" not in _number_window(11, pages, "no captions here")


class TestGroundRowPageStraddle:
    """Reproduces the real defect: a provision whose distinctive words are
    split across two consecutive pages must ground as fine, not flagged."""

    # Most of the provision's distinctive vocabulary sits on page 11 (enough to win
    # the confident match on its own), but the clause finishes on page 12 — the
    # '2.1-4' -> '2.1-5' continuation pattern from the live case.
    PAGE_11 = ("locality statement heritage conservation landscape setting "
               "streetscape character precinct boundary")
    PAGE_12 = "continues alignment reference below determination unrelated other clause text"
    STRADDLING_TEXT = ("locality statement heritage conservation landscape setting streetscape "
                        "character precinct boundary continues alignment reference below determination")

    def test_straddling_text_grounds_when_confident(self):
        pages = {11: self.PAGE_11, 12: self.PAGE_12}
        result = ground_row(self.STRADDLING_TEXT, "cos__2_1_2", pages)
        assert result["status"] == "grounded"
        assert result["verified_page"] == 11

    def test_same_text_would_have_falsely_flagged_on_single_page(self):
        """Proves the old behaviour was the bug, not a coincidence of this fixture:
        grounding against page 11 alone drops below the 75% word-match threshold."""
        import verify_extraction_fidelity as vf
        prov_words = set(vf._content_words(self.STRADDLING_TEXT))
        single_page_ratio = sum(1 for w in prov_words if w in self.PAGE_11) / len(prov_words)
        assert single_page_ratio < 0.75  # old code would have flagged this

    def test_content_confined_to_one_page_still_grounds(self):
        pages = {5: "car parking rate is one space per dwelling for this precinct",
                  6: "unrelated clause about tree preservation orders"}
        result = ground_row("car parking rate is one space per dwelling for this precinct",
                             "x__5_1", pages)
        assert result["status"] == "grounded"


class TestGroundRowStillCatchesRealErrors:
    def test_hallucinated_number_flags_even_with_wider_window(self):
        pages = {
            11: "front setback is 4.5 metres from the primary road boundary",
            12: "side setback is 1.2 metres for a single storey dwelling",
        }
        # AI wrote 9.9m -- nowhere in the anchor page OR its neighbours.
        text = "front setback is 9.9 metres from the primary road boundary"
        result = ground_row(text, "x__2_1", pages)
        assert result["status"] == "flagged"
        assert "9.9" in result["detail"]

    def test_unrelated_text_flags_not_grounded(self):
        pages = {1: "flood planning level provisions for the low-lying precinct"}
        result = ground_row("bicycle parking requirements for commercial premises",
                             "x__9_9", pages)
        assert result["status"] == "flagged"


class TestNonConfidentFallbackUnchanged:
    def test_ambiguous_match_uses_whole_chapter_not_a_window(self):
        """When no single page wins clearly, the fix must not change the
        existing whole-chapter fallback (used for repeated/short/boilerplate
        clauses that appear near-identically on many pages)."""
        pages = {1: "objective clause", 2: "objective clause", 3: "objective clause"}
        page, confident = _best_page({"objective", "clause"}, pages)
        assert confident is False
        result = ground_row("objective clause", "x__1_1", pages)
        assert result["verified_page"] is None
        assert result["status"] == "grounded"


class TestBlankVerifiedReferences:
    """2026-09-07 Sol cross-review (2 HIGH). The earlier design excluded a
    citation's digit VALUE everywhere in the row and trusted the citation's own
    digits unconditionally. This version blanks only the matched SPAN, and only
    once the matched phrase is independently verified present somewhere in the
    chapter's real text (table captions are the one exception, verified by
    construction -- see the function docstring)."""

    def test_table_caption_blanked_unconditionally(self):
        text = "some clause text\n\n**Table 3** (Page 63)\n\n<table>...</table>"
        cleaned = _blank(text, whole_chapter="")
        assert "3" not in cleaned
        assert "63" not in cleaned
        assert "some clause text" in cleaned  # untouched outside the caption span

    def test_page_citation_blanked_only_when_verified(self):
        text = "Comprehensive Inner West DCP 2016 page 123"
        cleaned = _blank(text, whole_chapter="comprehensive inner west dcp 2016 page 123")
        assert "123" not in cleaned

    def test_unverifiable_page_citation_left_alone(self):
        text = "Comprehensive Inner West DCP 2016 page 123"
        cleaned = _blank(text, whole_chapter="nothing matching here at all")
        assert "123" in cleaned

    def test_hallucinated_clause_citation_not_blanked(self):
        """The exact scenario Sol found (confidence 0.99): source says DS 2.7,
        extraction says DS 2.6 -- must NOT be exempted just because it looks
        like a citation. PC2 stays too: a single-digit clause code never
        verifies (_NUM_RE requires 2+ digits or a decimal), so it's always
        conservatively left alone rather than blanked -- by design, not a gap,
        since a lone digit is not confusable with a real measured value."""
        text = "pursuant to clauses PC2 and DS 2.6"
        cleaned = _blank(text, whole_chapter="pursuant to clauses pc2 and ds 2.7")
        assert "2.6" in cleaned  # left alone -- unverifiable
        assert "PC2" in cleaned  # left alone -- single digit never verifies

    def test_masking_scenario_blanks_only_the_citation_occurrence(self):
        """The exact scenario Sol found (confidence 1.0): a legitimate 'Figure
        10' citation must not remove a DIFFERENT, unrelated '10' elsewhere."""
        text = "the maximum height is 10 m, see Figure 10 for the elevation."
        cleaned = _blank(text, whole_chapter="see figure 10 for the elevation diagram")
        assert "10 m" in cleaned  # the standalone measurement survives
        assert "Figure 10" not in cleaned  # only the citation occurrence is gone

    def test_property_number_blanked_only_when_address_verified(self):
        text = "3 metre setback applying to property no.810 Pacific Highway."
        cleaned = _blank(text, whole_chapter="setback applying to property no.810 pacific highway")
        assert "810" not in cleaned
        assert "3 metre" in cleaned

    def test_wrong_property_number_not_blanked(self):
        text = "3 metre setback applying to property no.811 Pacific Highway."
        cleaned = _blank(text, whole_chapter="setback applying to property no.810 pacific highway")
        assert "811" in cleaned

    def test_heading_blanked_only_when_verified(self):
        text = "# D-Part12 55-63 Smith Street Summer Hill\n\nbody text here"
        cleaned = _blank(text, whole_chapter="d-part12 55-63 smith street summer hill other page")
        assert "55-63" not in cleaned
        assert "body text here" in cleaned

    def test_wrong_heading_not_blanked(self):
        """The wrong-site-range scenario Sol found (confidence 0.98): a
        hallucinated address range must not be exempted just for being on the
        first markdown-heading line."""
        text = "# D-Part12 57-63 Smith Street Summer Hill\n\nbody text here"
        cleaned = _blank(text, whole_chapter="d-part12 55-63 smith street summer hill other page")
        assert "57" in cleaned

    def test_no_heading_marker_not_blanked(self):
        text = "front setback is 9.9 metres from the primary road boundary"
        cleaned = _blank(text, whole_chapter="front setback is 4.5 metres from the primary road")
        assert "9.9" in cleaned

    def test_plain_measurement_never_touched(self):
        text = "the minimum rear setback is 4.5 metres from the boundary"
        assert _blank(text, whole_chapter="anything") == text

    def test_no_citations_returns_text_unchanged(self):
        text = "plain body text with no citations at all"
        assert _blank(text, whole_chapter="") == text


class TestGroundRowCitationFindingsEndToEnd:
    """End-to-end reproductions of Sol's findings through the full ground_row
    pipeline. The hallucinated-citation finding (confidence 0.99) is fully
    closed by _blank_verified_references's phrase-verification. The masking
    finding (confidence 1.0) is only PARTIALLY closed -- span-based blanking
    stops a citation from removing every occurrence of its digit value, but
    the SAME-PAGE coincidence Sol's exact scenario describes (source
    independently contains the digit for an unrelated reason) remains open,
    same as before this session: see the module docstring's 'ATTEMPTED AND
    REVERTED' note for why a sentence-level fix was tried, found to regress
    real production data severely (unpunctuated tables, two-column
    interleaving), and removed rather than shipped half-working."""

    def test_hallucinated_citation_still_flags_end_to_end(self):
        pages = {1: "pursuant to clauses pc2 and ds 2.7, the wall height applies."}
        text = "# X\n\npursuant to clauses PC2 and DS 2.6, the wall height applies."
        result = ground_row(text, "x__1_1", pages)
        assert result["status"] == "flagged"
        assert "2.6" in result["detail"]

    def test_genuinely_correct_row_with_legitimate_citation_still_grounds(self):
        """The fix must not become so strict it starts flagging correct rows
        just because they happen to contain a citation."""
        pages = {11: ("the maximum height is 8 m in this precinct. "
                      "see figure 10 for the elevation diagram.")}
        text = ("the maximum height is 8 m in this precinct. "
                "see Figure 10 for the elevation diagram.")
        result = ground_row(text, "x__1_1", pages)
        assert result["status"] == "grounded"

    def test_masking_scenario_is_a_documented_accepted_residual_not_silently_hidden(self):
        """Confirms the HONEST state after reverting sentence-level matching:
        this specific coincidence (a legitimate citation's digit + an unrelated
        genuinely-wrong value sharing the same page) still grounds. This is a
        real, known gap -- documented in the module docstring and QA report,
        not silently claimed fixed. If this test starts failing (status
        becomes 'flagged'), a future fix closed the gap for real; update this
        test's assertion and the docstring together rather than leaving them
        to contradict each other."""
        pages = {
            11: ("the maximum height is 8 m in this precinct. "
                 "see figure 10 for the elevation diagram."),
            12: "unrelated content about landscaping requirements setback controls fencing.",
        }
        text = ("the maximum height is 10 m in this precinct. "
                "see Figure 10 for the elevation diagram.")
        result = ground_row(text, "x__1_1", pages)
        assert result["status"] == "grounded"  # accepted residual, see docstring above


class TestPageWindowFollowsTableCaptions:
    """2026-09-07: blacktown 10_4_3_1 is three stitched tables from real pages
    61/62/63 (each stamped by dcp_extract_changed.py's own caption); _best_page's
    word-overlap heuristic anchored on 61, and a bare +-1 window (60-62) missed 63
    even though the row's OWN caption already states it. Using that caption is
    exact, not another heuristic widening."""

    def test_word_window_extends_to_a_captioned_page_outside_neighbours(self):
        pages = {60: "unrelated", 61: "table one content", 62: "table two content",
                  63: "225mm above finished ground"}
        text = "flood controls\n\n**Table 1** (Page 61)\n\n**Table 3** (Page 63)"
        window = _page_window(61, pages, text)
        assert "225mm" in window

    def test_no_captions_falls_back_to_plain_neighbours(self):
        pages = {10: "a", 11: "b", 12: "c", 20: "should not appear"}
        assert _page_window(11, pages, "no captions here") == "a b c"

    def test_end_to_end_real_shape_grounds_the_flood_row(self):
        """Reproduces the actual defect (verified live against the real Blacktown
        10_4_3_1 PDF, which now grounds too): a row whose real values (200mm, 225mm)
        sit on a caption-named page the +-1 window alone would miss. Page text is
        lowercase throughout -- matching _page_text_for_chapter's own _norm(), which
        always lowercases; grounding is case-sensitive, so a mixed-case fixture here
        would falsely fail regardless of the fix."""
        part_a = ("flood related development controls f1 f2 f3 garage floor level "
                  "natural ground level annual exceedance probability flood level")
        part_b = "f9 the height difference minus 200 mm 225mm above finished ground"
        pages = {
            60: "unrelated preceding page content about setbacks driveways street "
                "frontage landscaping fencing",
            61: part_a,
            62: "unrelated filler page landscaping requirements fencing controls "
                "parking allocation bicycle",
            63: part_b,
        }
        text = ("# 10.4.3.1 land use by vulnerability to flooding\n\n" + part_a + "\n\n"
                "**Table 1** (Page 61)\n\n**Table 3** (Page 63)\n\n" + part_b)
        result = ground_row(text, "blacktown__10_4_3_1", pages)
        assert result["status"] == "grounded"
        assert result["verified_page"] == 61


class TestHeadingExclusionRequiresRealHeading:
    """2026-09-07 regression: the first heading-exclusion draft used text.splitlines()[0]
    unconditionally, so a single-line row with NO separate heading line had its own
    (and only) content line treated as "the heading" and fully exempted from checking --
    a genuinely wrong number in a heading-less row would have silently passed. Real
    rows are always built as "# {heading}\\n\\n{content}" (dcp_extract_changed.py), so
    requiring the first line to start with '#' is both correct and the guard against
    this collapsing back in."""

    def test_single_line_row_without_heading_marker_is_still_checked(self):
        pages = {1: "front setback is 4.5 metres from the primary road boundary"}
        # No leading '#' -- this must NOT be treated as a heading line.
        text = "front setback is 9.9 metres from the primary road boundary"
        result = ground_row(text, "x__1_1", pages)
        assert result["status"] == "flagged"
        assert "9.9" in result["detail"]

    def test_real_heading_line_numbers_are_still_excluded(self):
        # Lowercase page text -- matches _page_text_for_chapter's _norm(), which always
        # lowercases; a running header repeating the precinct name is what let the real
        # Ashfield D-Part12 rows ground on word-match alone (only the numbers were flagged).
        pages = {1: "d-part12 55-63 smith street summer hill the design controls "
                    "for this precinct address building form"}
        text = ("# D-Part12 55-63 Smith Street Summer Hill\n\n"
                 "the design controls for this precinct address building form")
        result = ground_row(text, "x__12_1", pages)
        assert result["status"] == "grounded"


class TestGateChapterScopesToActionableRows:
    """2026-09-07: measured live that only 2,662 of 5,660 pending rows across all
    9 councils sit in a chapter with existing live+actionable content AND are
    themselves actionable text (not an introduction/definitions/boilerplate
    section) -- the rest was being graded (spending real R2/CPU time) for
    content that could never become served regulatory data even once approved.
    gate_chapter now skips non-actionable rows entirely (ungraded, not flagged,
    not touched); main()'s chapter query defaults to live+actionable chapters
    only (see TestMainScopesToLiveChapters below for that half)."""

    @staticmethod
    def _run_gate_chapter(rows, pages):
        """rows: list of (id, ref_number, new_text). Mocks the cursor and the
        real R2/pdfplumber fetch so this stays a fast, offline unit test."""
        from unittest.mock import MagicMock, patch
        cur = MagicMock()
        cur.fetchall.return_value = rows
        with patch.object(_gate.vf, "_page_text_for_chapter", return_value=pages):
            g, f, s = _gate.gate_chapter(cur, s3=None, council="x", chapter_key="y", r2_path="z")
        return g, f, s, cur

    def test_non_actionable_row_is_skipped_not_graded(self):
        rows = [(1, "x__intro", "# Introduction\n\nThis Part provides additional "
                                  "objectives and controls for development.")]
        g, f, s, cur = self._run_gate_chapter(rows, pages={1: "anything"})
        assert (g, f, s) == (0, 0, 1)
        # skipped rows must never be written back -- ungraded means untouched
        update_calls = [c for c in cur.execute.call_args_list if "UPDATE" in c.args[0]]
        assert update_calls == []

    def test_actionable_row_is_still_graded_and_written(self):
        rows = [(1, "x__1_1", "front setback is 4.5 metres from the primary road boundary")]
        pages = {1: "front setback is 4.5 metres from the primary road boundary"}
        g, f, s, cur = self._run_gate_chapter(rows, pages)
        assert (g, f, s) == (1, 0, 0)
        update_calls = [c for c in cur.execute.call_args_list if "UPDATE" in c.args[0]]
        assert len(update_calls) == 1
        assert update_calls[0].args[1][0] == "grounded"

    def test_mixed_batch_counts_each_bucket_correctly(self):
        rows = [
            (1, "x__intro", "# Introduction\n\nThis Part provides additional objectives."),
            (2, "x__1_1", "front setback is 4.5 metres from the primary road boundary"),
            (3, "x__1_2", "front setback is 9.9 metres from the primary road boundary"),
        ]
        pages = {1: "front setback is 4.5 metres from the primary road boundary"}
        g, f, s, cur = self._run_gate_chapter(rows, pages)
        assert (g, f, s) == (1, 1, 1)


class TestChaptersQueryScopesToLiveChapters:
    """Behavioural (not source-grep) test of the other half of the same fix:
    chapters_query() -- the function main() actually calls, and the same one
    tests/test_dcp_fidelity_gate_real_db.py runs against the real database --
    must default to a live+actionable-only filter, with an explicit opt-out.
    Never silently drops rows, only skips grading them until asked."""

    @staticmethod
    def _main_src():
        src = open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                                "dcp_fidelity_gate.py"), encoding="utf-8").read()
        start = src.index("def main()")
        return src[start:]

    def test_include_backlog_flag_exists(self):
        assert "--include-backlog" in self._main_src()

    def test_default_query_filters_on_live_actionable(self):
        sql, params = _gate.chapters_query("blacktown", None, include_backlog=False)
        assert "rp.is_current" in sql and "rp.v2_is_actionable" in sql
        assert params == ["blacktown"]

    def test_include_backlog_omits_the_filter(self):
        sql, _ = _gate.chapters_query("blacktown", None, include_backlog=True)
        assert "regulatory_provisions" not in sql

    def test_chapter_filter_still_applies_params_in_order(self):
        sql, params = _gate.chapters_query("ashfield", "chapter-d-precinct-guidelines",
                                            include_backlog=False)
        assert "q.chapter_key=%s" in sql
        assert params == ["ashfield", "chapter-d-precinct-guidelines"]

    def test_is_active_required_regardless_of_include_backlog(self):
        """Sol cross-review (MEDIUM 0.99, on push): a retired/superseded registry
        entry must never be graded -- unconditionally, not just when scoping to
        live+actionable content. --include-backlog widens what counts as
        'relevant', it does not resurrect a chapter the registry itself has
        retired."""
        for include_backlog in (False, True):
            sql, _ = _gate.chapters_query("blacktown", None, include_backlog=include_backlog)
            assert "reg.is_active" in sql, f"include_backlog={include_backlog}"

    def test_skipped_count_is_reported_not_silently_dropped(self):
        assert "non-actionable rows skipped, not graded" in self._main_src()


class TestStraddleRescue:
    """_straddle_grounded — the fix for the gate's dominant false-alarm class.

    Measured 2026-09-09 against the live queue: of 433 flagged rows, 428 were a
    clause straddling a page break (the number sits on the next page, outside
    _number_window's deliberately narrow anchor-page scope) and 5 were real.
    A 1.2% true-positive rate made the human queue unworkable, so nothing was
    reviewed at all — the opposite of the safety this gate exists to provide.

    Widening the window would reinstate the masking bug _number_window's own
    docstring documents, so the rescue requires the number to bring its own
    surrounding words with it. These four cases are real production strings and
    pin both directions.
    """

    RULE_11_5 = (
        "Create a consistent 3 storey (11.5 metres) street wall that is built "
        "parallel to the street alignment of Pacific Highway."
    )

    def test_rescues_a_clause_that_continues_on_another_page(self):
        # ku_ring_gai St Ives: the chapter PDF really does carry this phrase.
        st_ives = (
            "BUILT FORM ... consistent 3 storey (11.5 metres) street wall that is built "
            "55 57 59 18 parallel to the street alignment of Mona Vale Road ..."
        )
        assert _gate._straddle_grounded("11.5", self.RULE_11_5, st_ives) is True

    def test_still_flags_a_value_the_chapter_never_states(self):
        # ku_ring_gai Gordon: PDF says "3 storey street wall" with NO metric, and
        # contains neither "11.5" nor "consistent 3 storey". The 11.5 was carried
        # across from St Ives by extraction — a real, served-facing error, and the
        # only genuine defect in all 433 flagged rows.
        gordon = (
            "BUILT FORM Objectives Controls 1 To maintain a consistent street wall height "
            "with reference to existing buildings. - 3 storey street wall - 2m upper level "
            "setback above street wall height"
        )
        assert _gate._straddle_grounded("11.5", self.RULE_11_5, gordon) is False

    def test_does_not_reinstate_the_masking_bug(self):
        # The reason numbers were narrowed to the anchor page in the first place:
        # an unrelated, coincidentally-identical value must not ground this one.
        rule = "The maximum building height is 9.9 metres above natural ground level."
        unrelated = (
            "Deep soil zones must be a minimum of 9.9 square metres in area for corner "
            "allotments."
        )
        assert _gate._straddle_grounded("9.9", rule, unrelated) is False

    def test_rescues_a_number_inside_ordinary_prose(self):
        rule = "uses to ensure 24 hour activity and surveillance of the streetscape."
        next_page = (
            "... mix of commercial and residential uses above active ground floor uses to "
            "ensure 24 hour activity and surveillance of the streetscape. Sydney DCP 2012"
        )
        assert _gate._straddle_grounded("24", rule, next_page) is True

    def test_empty_and_missing_inputs_are_safe(self):
        assert _gate._straddle_grounded("", "text", "chapter") is False
        assert _gate._straddle_grounded("5", "", "chapter") is False
        assert _gate._straddle_grounded("5", "text", "") is False

    def test_a_shorter_number_is_not_grounded_by_a_longer_one(self):
        """Sol HIGH 0.99: a bare substring search made the rescue reintroduce
        the very masking bug this module exists to prevent. A rule saying '5
        metres' must NOT ground against a chapter saying '15 metres', even
        though every surrounding word is identical."""
        rule = "The minimum setback is 5 metres from the front boundary."
        chapter = "The minimum setback is 15 metres from the front boundary."
        assert _gate._straddle_grounded("5", rule, chapter) is False

    def test_a_number_is_not_grounded_by_a_decimal_containing_it(self):
        assert _gate._straddle_grounded("5", "a 5 metre wall", "a 11.5 metre wall") is False

    def test_the_same_number_still_grounds_against_itself(self):
        rule = "The minimum setback is 5 metres from the front boundary."
        assert _gate._straddle_grounded("5", rule, rule) is True

    def test_a_number_ending_a_sentence_still_grounds(self):
        assert _gate._straddle_grounded("6", "must be set back 6.", "the wall must be set back 6.") is True

    def test_a_thousands_separated_value_is_a_different_number(self):
        """Sol HIGH 0.97, second round: digit/decimal boundaries alone still let
        '500' match inside '1,500', so a rule stating a 500 sqm minimum lot size
        grounded against a chapter stating 1,500 sqm -- three times the control,
        marked source-verified."""
        assert _gate._straddle_grounded(
            "500",
            "The minimum lot size is 500 square metres",
            "The minimum lot size is 1,500 square metres",
        ) is False

    def test_a_number_starting_a_thousands_group_is_not_that_number(self):
        assert _gate._straddle_grounded(
            "5", "a 5 metre setback applies", "a 5,000 metre setback applies"
        ) is False

    def test_a_signed_value_is_not_the_unsigned_one(self):
        assert _gate._straddle_grounded(
            "5", "a 5 metre setback applies", "a -5 metre setback applies"
        ) is False

    def test_a_comma_in_ordinary_prose_still_grounds(self):
        """The guard must reject thousands separators without rejecting a number
        that merely follows a comma in a list."""
        text = "sizes of 3, 5 and 7 metres apply"
        assert _gate._straddle_grounded("5", text, text) is True
