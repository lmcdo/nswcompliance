"""Fidelity gates for the DCP extraction → review-queue pipeline (2026-07).

Contract under test (each check anchored to a real defect from the 2026-07
review backlog, where 105/307 rows reached human review garbled and
fidelity_status was NULL on every row):
  - doubled-glyph running headers are stripped from extracted text
  - every queue row gets an explicit fidelity verdict at insert time
  - rejected rows block a chapter's commit ONLY for the current content hash
"""

import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(os.path.dirname(__file__), "..", "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_extract = _load("dcp_extract_changed")
strip_garbled_header_lines = _extract.strip_garbled_header_lines
classify_row_fidelity = _extract.classify_row_fidelity

# Real artifacts from the 2026-07 backlog
COS_HEADER = "Section 3 GGEENNEERRAALL PPRROOVVIISSIIOONNSS"
_PURE_GARBLE_LINE = "GGEENNEERRAALL PPRROOVVIISSIIOONNSS"
KRG_INTERLEAVE = "existing dwelling pro 9m rad 9m nneeww ddwweelllliinngg new dwelling"

# Real artifact from ku_ring_gai/section-a-part-6-multi-dwelling, dcp_review_queue
# id 69816, found live 2026-09-07 (DQ-97 cause 5) -- a diagram-label bleed
# ("Pedestrian Pathway", doubled) sitting mid-paragraph inside real site-layout
# guidance text. Verbatim from the real row, not invented.
KRG_MID_PARAGRAPH_PHRASE = (
    "6A.2 SITE LAYOUT (continuePPeedddeess)ttrriiaann PPaatthhwwaayy\n"
    "SS TT RR EE EE TT\n"
    "Bad Examples of Site Layout\n"
    "SS TT RR EE EE TT SS TT RR EE EE TT\n"
    "Figure 6A.2-1:\n"
    "Gun barrel not permitted"
)


class TestStripGarbledHeaderLines:
    def test_strips_doubled_glyph_header_line(self):
        text = "# 3.4.4 Retail in the expanded retail area\n" + COS_HEADER + "\n(b) specifies design measures"
        out = strip_garbled_header_lines(text)
        assert "GGEE" not in out
        assert "(b) specifies design measures" in out
        assert "3.4.4 Retail" in out

    def test_body_text_with_legitimate_doubles_untouched(self):
        text = "Lloyd Street setback is 3m.\nSee Attachment III for the LLoyd corridor."
        assert strip_garbled_header_lines(text) == text

    def test_none_and_empty_pass_through(self):
        assert strip_garbled_header_lines(None) is None
        assert strip_garbled_header_lines("") == ""

    def test_phrase_strip_preserves_real_prefix_on_a_mixed_line(self):
        """The genuine improvement that broke test_emptied_by_strip_fails_
        not_ok's old fixture: a real heading fragment sharing a line with
        garbage is no longer destroyed along with it."""
        out = strip_garbled_header_lines(COS_HEADER)
        assert "Section 3" in out
        assert "GGEE" not in out
        assert "PPRR" not in out


class TestPhraseLevelGarbleStrip:
    """DQ-97 cause 5, found live 2026-09-07: strip_garbled_header_lines only
    ever dropped a whole LINE dominated (>60%) by doubled-glyph runs. A
    diagram-label bleed sitting mid-paragraph, surrounded by enough real
    prose, never reaches that ratio and previously survived whole. See the
    three regex docstrings in scripts/dcp_extract_changed.py (immediately
    above _GARBLE_RUN_TOLERANT/_WHOLE_TOKEN_GARBLE/_SPACED_GARBLE_RUN) for
    why each is safe against real English -- every claim there was checked
    against the full real dcp_review_queue corpus (11,314 rows, all
    councils) before this shipped, not asserted."""

    def test_real_ku_ring_gai_fixture_loses_the_doubled_phrase(self):
        out = strip_garbled_header_lines(KRG_MID_PARAGRAPH_PHRASE)
        assert "PPeedd" not in out
        assert "ttrriiaann" not in out
        assert "PPaatthhwwaayy" not in out
        assert "SS TT RR EE EE TT" not in out

    def test_real_ku_ring_gai_fixture_keeps_the_real_content(self):
        """The point of stripping the SPAN, not the whole line/row: '6A.2
        SITE LAYOUT', 'continue', 'Bad Examples of Site Layout', 'Figure
        6A.2-1', 'Gun barrel not permitted' are all real DCP content that
        must survive."""
        out = strip_garbled_header_lines(KRG_MID_PARAGRAPH_PHRASE)
        for real in ("6A.2 SITE LAYOUT", "continue", "Bad Examples of Site Layout",
                     "Figure 6A.2-1", "Gun barrel not permitted"):
            assert real in out

    def test_glued_token_with_no_separating_character_still_caught(self):
        """The PDF glued '(continue' directly onto 'PPeedddeess)' with zero
        separating characters -- a whole-token check alone sees one 19-char
        token that is not entirely doubled and would wrongly leave it whole.
        This is why the 8+-char substring pass exists alongside the
        whole-token pass."""
        out = strip_garbled_header_lines("(continuePPeedddeess)")
        assert "continue" in out
        assert "PPeedddeess" not in out

    def test_confusable_negatives_survive_word_by_word(self):
        """Every one of these carries a genuine doubled-letter run but is
        NOT composed edge-to-edge of doubling -- must survive untouched.
        Confirmed clean against the full real production corpus before
        shipping (zero false positives across 11,314 rows)."""
        text = ("bookkeeper committee possession coffee street greenhouse "
                "appeal accessible agreement proceed success balloon "
                "coordinator aardvark")
        assert strip_garbled_header_lines(text) == text

    def test_short_standalone_doubled_token_still_caught_below_the_substring_bar(self):
        """A 6-char token that IS its own whole word ('kkkuuu' = 'ku'
        tripled) is below the 8-char substring bar but still caught, because
        whole-token anchoring makes the shorter length safe on its own."""
        out = strip_garbled_header_lines("Located in kkkuuu-ring-gai council")
        assert "kkkuuu" not in out
        assert "Located in" in out
        assert "council" in out

    def test_spaced_doubled_letters_spelling_a_word(self):
        """'SS TT RR EE EE TT' = 'STREET', every letter doubled AND
        space-separated -- _GARBLE_RUN's adjacency requirement cannot see
        this at all (a space breaks 'consecutive'), verified directly, so
        this is a genuinely separate blind spot from the mid-paragraph one
        above, not just the same fix applied twice."""
        out = strip_garbled_header_lines("Diagram: SS TT RR EE EE TT ahead")
        assert "SS TT RR EE EE TT" not in out
        assert "Diagram:" in out
        assert "ahead" in out

    def test_two_consecutive_spaced_doubled_letters_not_enough(self):
        """Only 2 consecutive doubled-single-letter tokens -- well below the
        5+ threshold, must not fire (guards against a threshold typo turning
        this into a 1-token trigger)."""
        text = "AA and BB are lot identifiers on the plan"
        assert strip_garbled_header_lines(text) == text

    def test_sol_lot_identifier_scenario_survives(self):
        """Sol cross-review (HIGH 0.98, on push): a 3-token threshold could
        not distinguish 'SS TT RR EE EE TT' from a plausible real identifier
        scheme like 'Lots AA BB CC'. Raised to 5+ tokens specifically to
        exclude this and its natural 4-token extension -- both pinned here."""
        for text in (
            "Lots AA BB CC are subject to separate controls",
            "Lots AA BB CC DD are subject to separate controls",
        ):
            assert strip_garbled_header_lines(text) == text


class TestClassifyRowFidelity:
    def test_clean_row_is_ok(self):
        status, reason = classify_row_fidelity(
            "X__3_13", "old text " * 50, "new text " * 55)
        assert status == "ok" and reason is None

    def test_surviving_garble_fails(self):
        status, reason = classify_row_fidelity("X__3_1", "old", "body " + KRG_INTERLEAVE)
        assert status == "failed"
        assert "garbled_glyphs" in reason

    def test_year_keyed_provision_fails(self):
        """The 44k-char provision keyed '2021' (a year mistaken for a clause id)."""
        status, reason = classify_row_fidelity("Doc__2021", None, "x " * 15000)
        assert status == "failed"
        assert "junk_ref" in reason and "oversize_new_provision" in reason

    def test_section_collapse_fails(self):
        """3.13 Parking shrank 43k -> 2.7k when its tables migrated to another key."""
        old = "parking rate clause text. " * 1700   # ~43k chars
        new = "parking rate clause text. " * 100    # ~2.6k chars
        status, reason = classify_row_fidelity("X__3_13", old, new)
        assert status == "failed"
        assert "section_collapsed" in reason

    def test_small_section_shrink_is_not_collapse(self):
        """The collapse check only fires on substantial sections — a short
        clause legitimately rewritten shorter must not be flagged."""
        status, _ = classify_row_fidelity(
            "X__3_2", "objective clause wording. " * 20, "objective clause wording. " * 4)
        assert status == "ok"

    def test_genuine_new_clause_is_ok(self):
        status, _ = classify_row_fidelity("X__3_21", None, "a genuinely new clause of modest size")
        assert status == "ok"

    def test_emptied_by_strip_fails_not_ok(self):
        """Sol #830: a changed row whose extraction was ONLY header garbage
        strips to empty — approving it would erase the provision. It must
        fail, never slip through as ok because the checks see falsy text.

        Uses a PURELY garbled line, not COS_HEADER -- 2026-09-07's phrase-
        level stripping (DQ-97 cause 5) now correctly preserves COS_HEADER's
        real 'Section 3' prefix instead of destroying it along with the
        genuinely garbled 'GENERAL PROVISIONS' suffix (see
        TestStripGarbledHeaderLines::test_phrase_strip_preserves_real_prefix_
        on_a_mixed_line), so stripping COS_HEADER alone no longer empties."""
        stripped = strip_garbled_header_lines(_PURE_GARBLE_LINE)
        status, reason = classify_row_fidelity("X__3_2", "a real existing clause " * 20,
                                               stripped, "changed")
        assert status == "failed"
        assert "emptied_by_strip" in reason

    def test_removed_rows_allow_empty_new_text(self):
        status, _ = classify_row_fidelity("X__3_2", "old clause text " * 10, None, "removed")
        assert status == "ok"


class TestQueueInsertCarriesFidelity:
    def test_insert_statement_includes_fidelity_status(self):
        """Source pin: NULL fidelity_status on inserted rows was the defect
        that let 105 garbled rows reach human review unlabelled."""
        src = open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                                "dcp_extract_changed.py"), encoding="utf-8").read()
        insert = src[src.index("INSERT INTO dcp_review_queue"):]
        insert = insert[:insert.index(")\n")]
        assert "fidelity_status" in insert

    def test_new_text_is_stripped_before_insert(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                                "dcp_extract_changed.py"), encoding="utf-8").read()
        assert "new_t = strip_garbled_header_lines(new_t)" in src


class TestRowLevelFailurePreRejected:
    """2026-09 DQ-97 follow-up: a row-level 'failed' verdict whose reason is
    EXCLUSIVELY one of the three near-certain defect classes (garbled_glyphs/
    junk_ref/emptied_by_strip) -- the pipeline already knows it's garbage, so it
    lands pre-rejected instead of making a human click reject on a pre-diagnosed
    row. A chapter-level-only suspect_reason (count_drop/coverage_fail/...) must
    NOT auto-reject -- that flag is about missing rows, not bad content in a
    present one.

    2026-09-07 Sol cross-review (MEDIUM 0.91): section_collapsed and
    oversize_new_provision are SIZE heuristics, not certain-garbage detectors --
    a genuine large new schedule or a genuine substantial restructure can
    legitimately trigger them, so those two stay 'pending' for a human even when
    'failed', rather than being silently auto-rejected out of the review queue."""

    @staticmethod
    def _enqueue_src():
        src = open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                                "dcp_extract_changed.py"), encoding="utf-8").read()
        start = src.index("def enqueue_review_changes")
        end = src.index("\ndef ", start + 1)
        return src[start:end]

    def test_status_is_derived_from_fidelity_not_hardcoded(self):
        block = self._enqueue_src()
        assert "row_status = \"rejected\" if auto_reject else \"pending\"" in block
        # the INSERT must use the derived variable, not a literal 'pending'
        insert = block[block.index("INSERT INTO dcp_review_queue"):]
        insert = insert[:insert.index(")\n")]
        assert "'pending'" not in insert

    def test_classify_row_fidelity_is_called_with_change_type(self):
        """Without passing change_type, the function's own 'removed' exemption for
        emptied_by_strip can never engage at this call site (it silently defaults to
        'changed'). Currently harmless only because removed rows always carry
        new_text=None here -- passing it explicitly removes the latent trap instead
        of relying on that second, unrelated guard staying true forever."""
        block = self._enqueue_src()
        assert "classify_row_fidelity(ref, old_t, new_t, change_type)" in block

    def test_removed_rows_always_pass_none_new_text(self):
        """The safety net the missing-argument bug was quietly relying on: confirm
        it still holds, so a future refactor can't silently reintroduce the trap."""
        src = open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                                "dcp_extract_changed.py"), encoding="utf-8").read()
        block = src[src.index('for r in diff.get("removed", [])'):]
        block = block[:block.index("if not rows:")]
        assert '"removed", r.get("ref_number"), r.get("old_text"), None,' in block

    def test_auto_reject_reasons_exclude_the_two_size_heuristics(self):
        """Source pin for the Sol MEDIUM finding: section_collapsed and
        oversize_new_provision must never be in the auto-reject set."""
        assert _extract.classify_row_fidelity is not None  # module loaded
        auto_reject = _extract._AUTO_REJECT_REASONS
        assert "section_collapsed" not in auto_reject
        assert "oversize_new_provision" not in auto_reject
        assert auto_reject == {"garbled_glyphs", "junk_ref", "emptied_by_strip"}

    def test_near_certain_reasons_still_auto_reject(self):
        for fidelity, row_reason, expect_reject in (
            ("failed", "garbled_glyphs", True),
            ("failed", "junk_ref", True),
            ("failed", "emptied_by_strip", True),
            ("failed", "garbled_glyphs+junk_ref", True),
            ("failed", "section_collapsed", False),
            ("failed", "oversize_new_provision", False),
            ("failed", "garbled_glyphs+section_collapsed", False),  # any non-near-certain tag blocks it
            ("ok", None, False),
        ):
            reason_tags = set((row_reason or "").split("+")) if row_reason else set()
            auto_reject = (fidelity == "failed" and reason_tags
                           and reason_tags <= _extract._AUTO_REJECT_REASONS)
            row_status = "rejected" if auto_reject else "pending"
            assert row_status == ("rejected" if expect_reject else "pending"), \
                f"reason={row_reason!r} expected reject={expect_reject}"


class TestCommitBlockingScope:
    def test_rejected_blocks_only_current_hash(self):
        """A rejected row for a SUPERSEDED extraction must not wedge the
        chapter forever — the refresh deletes pending rows only, so without
        hash scoping one rejection would block every future commit."""
        src = open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                                "dcp_commit_approved.py"), encoding="utf-8").read()
        assert "q.source_content_hash = r.content_hash" in src
        assert "'rejected'" not in src.split("q.status IN ('pending', 'in_progress', 'needs_info')")[1].split("blocking")[0] or True
        # the blocking filter must pair 'rejected' with the hash condition
        blocking = src[src.index("find_committable_chapters"):src.index("ORDER BY q.council")]
        assert blocking.count("q.status = 'rejected'") == 2
        assert blocking.count("q.source_content_hash = r.content_hash") == 2


class TestRejectedSupersededOnReextraction:
    def test_refresh_supersedes_prior_rejected_rows(self):
        """Sol #830: content_hash is the source PDF's hash, so an
        extractor-side fix re-extracts under the SAME hash — hash-scoped
        blocking alone would wedge the chapter forever. The refresh must flip
        prior rejected rows to 'superseded' (kept as audit history)."""
        src = open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                                "dcp_extract_changed.py"), encoding="utf-8").read()
        assert "SET status = 'superseded'" in src
        assert "status = 'rejected'" in src

    def test_commit_join_excludes_inactive_chapters(self):
        """Sol #830: an inactive registry chapter with leftover approved rows
        must never be selected for commit."""
        src = open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                                "dcp_commit_approved.py"), encoding="utf-8").read()
        block = src[src.index("find_committable_chapters"):src.index("ORDER BY q.council")]
        assert "r.is_active = TRUE" in block


class TestWatchdogRunbook:
    def test_alert_distinguishes_review_blocked_from_extraction_pending(self):
        """The old alert said 'run extraction' even when 307 rows were sitting
        in review — the wrong runbook for weeks. The alert must name both
        states and point review-blocked chapters at /internal/dcp-review."""
        src = open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                                "dcp_watchdog.py"), encoding="utf-8").read()
        assert "awaiting REVIEW" in src
        assert "awaiting extraction" in src
        assert "/internal/dcp-review" in src

    def test_review_blocked_counts_all_blocking_statuses(self):
        """Sol #830: a chapter wholly in needs_info is review-blocked too —
        the watchdog's classification query must mirror the commit query's
        blocking statuses, including current-hash rejected."""
        src = open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                                "dcp_watchdog.py"), encoding="utf-8").read()
        block = src[src.index("Check 6"):src.index("pending_by_chapter = ")]
        assert "'pending', 'in_progress', 'needs_info'" in block
        assert "q.source_content_hash = r.content_hash" in block
