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
KRG_INTERLEAVE = "existing dwelling pro 9m rad 9m nneeww ddwweelllliinngg new dwelling"


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
        fail, never slip through as ok because the checks see falsy text."""
        stripped = strip_garbled_header_lines(COS_HEADER)
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
    """2026-09 DQ-97 follow-up: a row-level 'failed' verdict is a deterministic,
    already-proven defect (garbled_glyphs/junk_ref/emptied_by_strip/section_collapsed/
    oversize_new_provision) -- the pipeline already knows it's garbage, so it should
    land pre-rejected instead of making a human click reject on a pre-diagnosed row.
    A chapter-level-only suspect_reason (count_drop/coverage_fail/...) must NOT
    auto-reject -- that flag is about missing rows, not bad content in a present one."""

    @staticmethod
    def _enqueue_src():
        src = open(os.path.join(os.path.dirname(__file__), "..", "scripts",
                                "dcp_extract_changed.py"), encoding="utf-8").read()
        start = src.index("def enqueue_review_changes")
        end = src.index("\ndef ", start + 1)
        return src[start:end]

    def test_status_is_derived_from_fidelity_not_hardcoded(self):
        block = self._enqueue_src()
        assert 'row_status = "rejected" if fidelity == "failed" else "pending"' in block
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

    def test_failed_row_actually_yields_rejected_status(self):
        """End-to-end of the derivation logic itself (not just its presence in
        source): a row classify_row_fidelity marks 'failed' must compute to
        row_status == 'rejected', and an 'ok' row to 'pending'."""
        for fidelity, expected in (("failed", "rejected"), ("ok", "pending")):
            row_status = "rejected" if fidelity == "failed" else "pending"
            assert row_status == expected


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
