"""Unit tests for the commit-reviewed-text path (scripts/dcp_commit_approved.py).

Importing the module pulls dcp_extract_changed (R2_*/DATABASE_URL at import); the
conftest mocks stub the native deps and we set the env defaults it reads.
"""
import os
import sys
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://x")
os.environ.setdefault("R2_BUCKET_NAME", "x")
os.environ.setdefault("R2_ACCESS_KEY_ID", "x")
os.environ.setdefault("R2_SECRET_ACCESS_KEY", "x")
os.environ.setdefault("R2_ACCOUNT_ID", "x")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pytest  # noqa: E402

from dcp_commit_approved import (  # noqa: E402
    _section_header_from_text,
    commit_reviewed_from_queue,
    latest_approved_batch,
)


class TestSectionHeaderFromText:
    def test_recovers_heading_line(self):
        assert _section_header_from_text("# A1.1 NAME OF PLAN\n\nbody") == "A1.1 NAME OF PLAN"

    def test_none_for_headerless_or_preamble(self):
        assert _section_header_from_text("plain preamble text with no header") is None
        assert _section_header_from_text("") is None
        assert _section_header_from_text("#   \n\nbody") is None


BATCH_TS = datetime(2026, 9, 18, 3, 3, 29, 700277, tzinfo=timezone.utc)


class _FakeCursor:
    """Records execute() calls. fetchone() returns the is_full_replace flag; fetchall()
    returns the queued rows. rowcount is 7 for a blanket delete, 1 for a per-ref delete.

    `batches` answers the run-resolution query — (created_at, row_count) newest first.
    The default is one run holding every queued row, which is what a chapter read once
    looks like; a chapter re-read carries several, and only the newest may be committed.
    """
    def __init__(self, rows, full_replace=None, unqueued=(), batches=None):
        self._rows = rows
        self._full_replace = full_replace
        self._unqueued = list(unqueued)
        self._batches = list(batches) if batches is not None else [(BATCH_TS, len(rows))]
        self.calls = []
        self._last = ""

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        self._last = sql

    @property
    def rowcount(self):
        # blanket chapter-wide delete supersedes 7; a per-ref delete supersedes 1
        return 1 if "ref_number = %s" in self._last else 7

    def fetchone(self):
        return (self._full_replace,)

    def fetchall(self):
        # The run-resolution query groups the approved rows on created_at; the
        # full-replace completeness check asks for live refs the approved queue does not
        # name; every other fetchall is the queued rows of the run being committed.
        if "GROUP BY created_at" in self._last:
            return self._batches
        if "live_n > queued_n" in self._last:
            # (ref_number, live_n, queued_n) for refs the run does not fully replace.
            # A bare string in `unqueued` is the old shape: one live row, none queued.
            return [u if isinstance(u, tuple) else (u, 1, 0) for u in self._unqueued]
        return self._rows


class TestCommitReviewedFromQueue:
    def _rows(self):
        # (document_id, ref_number, new_text, new_page, change_type)
        return [
            ("doc1", "doc1__A1_1", "# A1.1 TITLE\n\nthe control body", 5, "changed"),
            ("doc1", "doc1__preamble", "some preamble text", 1, "added"),
        ]

    def test_full_replace_blanket_deletes_then_inserts(self):
        cur = _FakeCursor(self._rows(), full_replace=True)
        superseded, inserted = commit_reviewed_from_queue(cur, "leichhardt", "part-a")
        assert superseded == 7 and inserted == 2

        # a blanket chapter-scoped soft-delete happens (no ref_number in its WHERE)
        blanket = [c for c in cur.calls if "is_current = FALSE" in c[0] and "ref_number" not in c[0]]
        assert blanket and blanket[0][1] == ("leichhardt", "part-a")

        inserts = [c for c in cur.calls if "INSERT INTO regulatory_provisions" in c[0]]
        assert len(inserts) == 2
        p0 = inserts[0][1]
        assert p0[3] == "# A1.1 TITLE\n\nthe control body"   # verbatim reviewed text
        assert p0[2] == "A1.1 TITLE"                          # header recovered
        assert p0[1] == "doc1__A1_1" and p0[4] == 5 and p0[6] == [5]

    def test_legacy_null_flag_defaults_to_full_replace(self):
        cur = _FakeCursor(self._rows(), full_replace=None)
        superseded, _ = commit_reviewed_from_queue(cur, "leichhardt", "part-a")
        assert superseded == 7  # blanket delete ran (legacy rows treated as full replace)
        assert any("is_current = FALSE" in c[0] and "ref_number" not in c[0] for c in cur.calls)

    def test_targeted_supersedes_only_named_refs_not_the_whole_chapter(self):
        # an amendment: only 1 rule changed + 1 removed; unchanged rules must survive
        rows = [
            ("doc1", "doc1__E1_1_3", "# E1.1.3 Updated\n\nnew body", 6, "changed"),
            ("doc1", "doc1__E1_1_9", None, None, "removed"),
        ]
        cur = _FakeCursor(rows, full_replace=False)
        superseded, inserted = commit_reviewed_from_queue(cur, "leichhardt", "part-e-water")
        # NO blanket chapter-wide delete — that would drop the unchanged rules
        assert not any("is_current = FALSE" in c[0] and "ref_number" not in c[0] for c in cur.calls)
        # instead, exactly one per-ref supersede per queue row (ref_number in WHERE)
        per_ref = [c for c in cur.calls if "is_current = FALSE" in c[0] and "ref_number = %s" in c[0]]
        assert len(per_ref) == 2
        assert per_ref[0][1] == ("leichhardt", "part-e-water", "doc1__E1_1_3")
        # the 'removed' row is superseded but NOT re-inserted; the 'changed' row is inserted
        inserts = [c for c in cur.calls if "INSERT INTO regulatory_provisions" in c[0]]
        assert inserted == 1 and len(inserts) == 1
        assert inserts[0][1][1] == "doc1__E1_1_3"

    # -- A full replace must not drop a live rule the approved queue does not name ------
    # Queues built before 2026-09-13 never held unchanged or renumbered rules. Measured
    # then: 5 open full-replace chapters would have lost 92 live rules on commit.

    def test_full_replace_refuses_when_a_live_rule_is_not_in_the_approved_queue(self):
        cur = _FakeCursor(self._rows(), full_replace=True, unqueued=["doc1__A1_2"])
        try:
            commit_reviewed_from_queue(cur, "waverley", "waverley-dcp-2022")
        except RuntimeError as exc:
            assert "doc1__A1_2" in str(exc) and "--allow-section-loss" in str(exc)
        else:
            raise AssertionError("a full replace went ahead while a live rule was unqueued")
        # refused before anything was switched off or inserted
        assert not any("is_current = FALSE" in c[0] for c in cur.calls)
        assert not any("INSERT INTO regulatory_provisions" in c[0] for c in cur.calls)

    def test_a_person_can_let_a_checked_loss_through(self):
        cur = _FakeCursor(self._rows(), full_replace=True, unqueued=["doc1__A1_2"])
        superseded, inserted = commit_reviewed_from_queue(
            cur, "waverley", "waverley-dcp-2022", allow_unqueued=True)
        assert superseded == 7 and inserted == 2

    def test_a_complete_full_replace_commits(self):
        """Confusable negative: the check must not refuse a queue that names every rule."""
        cur = _FakeCursor(self._rows(), full_replace=True, unqueued=[])
        superseded, inserted = commit_reviewed_from_queue(cur, "waverley", "waverley-dcp-2022")
        assert superseded == 7 and inserted == 2

    def test_a_targeted_commit_does_not_run_the_completeness_check(self):
        """A targeted commit supersedes only the refs it names, so unqueued live rules
        stay live there and must not block it."""
        rows = [("doc1", "doc1__E1_1_3", "# E1.1.3 Updated\n\nnew body", 6, "changed")]
        cur = _FakeCursor(rows, full_replace=False, unqueued=["doc1__E1_1_9"])
        _, inserted = commit_reviewed_from_queue(cur, "leichhardt", "part-e-water")
        assert inserted == 1
        assert not any("NOT EXISTS" in c[0] for c in cur.calls)

    def test_a_targeted_commit_serves_a_renumbered_rule_under_its_new_number_only(self):
        """enqueue_review_changes queues a targeted renumbering as the old number removed
        and the new number added; committed, the old number goes and the new one is live."""
        rows = [
            ("doc1", "doc1__B7_7_1", None, None, "removed"),
            ("doc1", "doc1__B7_7_2", "# B7.7.2 Vehicle access\n\nVehicle access rule.", 61, "added"),
        ]
        cur = _FakeCursor(rows, full_replace=False)
        _, inserted = commit_reviewed_from_queue(cur, "ku_ring_gai", "section-a-part-8-mixed-use")
        switched_off = [c[1][2] for c in cur.calls
                        if "is_current = FALSE" in c[0] and "ref_number = %s" in c[0]]
        assert "doc1__B7_7_1" in switched_off
        inserts = [c[1] for c in cur.calls if "INSERT INTO regulatory_provisions" in c[0]]
        assert inserted == 1 and inserts[0][1] == "doc1__B7_7_2" and inserts[0][4] == 61

    def test_preamble_marked_non_actionable(self):
        cur = _FakeCursor(self._rows(), full_replace=True)
        commit_reviewed_from_queue(cur, "leichhardt", "part-a")
        inserts = [c for c in cur.calls if "INSERT INTO regulatory_provisions" in c[0]]
        assert inserts[0][1][-1] is None   # A1.1 -> classifier decides
        assert inserts[1][1][-1] is False  # preamble -> non-actionable


class TestOnlyTheLatestExtractionRunIsCommitted:
    """Approved rows accumulate across repeated reads of an UNCHANGED document. Committing
    all of them inserted each provision two or three times and the chapter rolled back on
    uq_provisions_current_identity — ten chapters in the 2026-09-18 run."""

    def _rows(self):
        return [("doc1", "doc1__A1_1", "# A1.1 TITLE\n\nbody", 5, "changed")]

    def _batch_params(self, cur):
        """Every query that reads the approved queue, with the params it was given."""
        return [(sql, params) for sql, params in cur.calls
                if "dcp_review_queue" in sql and "GROUP BY created_at" not in sql]

    def test_the_run_is_resolved_before_anything_is_read_or_written(self):
        cur = _FakeCursor(self._rows(), full_replace=True)
        commit_reviewed_from_queue(cur, "hornsby", "part-1-general")
        first = cur.calls[0][0]
        assert "GROUP BY created_at" in first, \
            f"the run is not resolved first; the first query was: {first}"

    def test_every_read_of_the_queue_is_pinned_to_that_one_run(self):
        """The mode, the section-loss guard and the insert must judge the same rows. A
        guard reading the whole approved history would clear a live rule named only in an
        older run, and the insert — scoped to the newest — would not restore it."""
        cur = _FakeCursor(self._rows(), full_replace=True)
        commit_reviewed_from_queue(cur, "hornsby", "part-1-general")
        reads = self._batch_params(cur)
        assert reads, "no query read the approved queue"
        for sql, params in reads:
            assert BATCH_TS in params, (
                f"a queue read is not pinned to the run timestamp: {' '.join(sql.split())}")

    def test_an_older_run_is_never_the_one_committed(self):
        """batches arrive newest first; the function must take the head, not the tail."""
        older = datetime(2026, 7, 28, 21, 41, 24, tzinfo=timezone.utc)
        cur = _FakeCursor(self._rows(), full_replace=True,
                          batches=[(BATCH_TS, 27), (older, 24)])
        commit_reviewed_from_queue(cur, "hornsby", "part-1-general")
        for _sql, params in self._batch_params(cur):
            assert older not in params, "July's run was committed over September's"

    def test_a_queue_whose_timestamps_are_not_runs_is_refused(self):
        """If created_at ever stops being transaction time, every run is one row and the
        newest is a single provision. Committing that would publish a fragment and report
        success, so the resolution refuses instead."""
        per_row = [(datetime(2026, 9, 18, 3, 3, 29, n, tzinfo=timezone.utc), 1)
                   for n in range(5)]
        cur = _FakeCursor(self._rows(), full_replace=True, batches=per_row)
        with pytest.raises(RuntimeError, match="one transaction and one timestamp"):
            commit_reviewed_from_queue(cur, "hornsby", "part-1-general")
        assert not any("INSERT INTO regulatory_provisions" in c[0] for c in cur.calls)
        assert not any("is_current = FALSE" in c[0] for c in cur.calls)

    def test_a_chapter_read_several_times_with_real_runs_is_NOT_refused(self):
        """Confusable negative: three genuine runs of 24, 26 and 27 rows — the hornsby
        shape that started this — must commit, not trip the fragmentation refusal."""
        cur = _FakeCursor(self._rows(), full_replace=True, batches=[
            (BATCH_TS, 27),
            (datetime(2026, 9, 2, 1, 0, tzinfo=timezone.utc), 26),
            (datetime(2026, 7, 28, 21, 41, tzinfo=timezone.utc), 24),
        ])
        _, inserted = commit_reviewed_from_queue(cur, "hornsby", "part-1-general")
        assert inserted == 1

    def test_no_approved_rows_resolves_to_nothing_rather_than_raising(self):
        cur = _FakeCursor([], full_replace=True, batches=[])
        assert latest_approved_batch(cur, "hornsby", "part-1-general") == (None, 0)

    def test_an_empty_queue_touches_nothing_even_with_the_loss_override(self):
        """Every query below the resolution is scoped to the run timestamp, so a NULL one
        matches nothing: bool_or over no rows is NULL, which reads as a full replace, and
        --allow-section-loss would then blanket-supersede a live chapter and insert nothing
        in its place. The function must return before any of that."""
        cur = _FakeCursor([], full_replace=None, batches=[])
        superseded, inserted = commit_reviewed_from_queue(
            cur, "hornsby", "part-1-general", allow_unqueued=True)
        assert (superseded, inserted) == (0, 0)
        assert not any("is_current = FALSE" in c[0] for c in cur.calls)
        assert not any("INSERT INTO regulatory_provisions" in c[0] for c in cur.calls)

    def test_one_large_old_batch_cannot_hide_a_one_row_newest_run(self):
        """The fragmentation test is the shape of the distribution, not its mean. A 100-row
        July batch beside a single stray row stamped today averages 50 — comfortably past
        any per-run threshold — and the stray row would be published as the whole run."""
        cur = _FakeCursor(self._rows(), full_replace=True, batches=[
            (BATCH_TS, 1),
            (datetime(2026, 9, 17, 3, 0, tzinfo=timezone.utc), 1),
            (datetime(2026, 7, 28, 21, 41, tzinfo=timezone.utc), 100),
        ])
        with pytest.raises(RuntimeError, match="single row"):
            commit_reviewed_from_queue(cur, "hornsby", "part-1-general")

    def test_a_targeted_amendment_of_one_rule_is_NOT_refused(self):
        """Confusable negative: one changed rule enqueued after a full read is a single
        batch of one among a majority that are not, and must commit."""
        cur = _FakeCursor(self._rows(), full_replace=True, batches=[
            (BATCH_TS, 1),
            (datetime(2026, 7, 28, 21, 41, tzinfo=timezone.utc), 100),
        ])
        _, inserted = commit_reviewed_from_queue(cur, "hornsby", "part-1-general")
        assert inserted == 1


class TestTheLossGuardCountsProvisionsNotRefNumbers:
    """A ref does not identify a provision. Five refs carry two current provisions each
    (woollahra C1_4_10, D5_4, D5_6, D1_10, D6_6_7), so a guard that merely asks whether
    the ref appears in the run calls it covered when the run replaces only one of them —
    and the blanket supersede then drops the other with nothing reporting it."""

    def _rows(self):
        return [("doc1", "doc1__C1_4_10", "# C1.4.10 Acoustic and visual privacy\n\nbody",
                 22, "changed")]

    def test_two_live_provisions_under_one_ref_with_one_queued_is_refused(self):
        cur = _FakeCursor(self._rows(), full_replace=True,
                          unqueued=[("doc1__C1_4_10", 2, 1)])
        with pytest.raises(RuntimeError) as exc:
            commit_reviewed_from_queue(cur, "woollahra", "chapter-c1-paddington-hca")
        assert "2 live, 1 queued" in str(exc.value)
        assert not any("is_current = FALSE" in c[0] for c in cur.calls)

    def test_the_refusal_counts_rules_lost_not_refs_affected(self):
        """Three refs each losing one of two provisions is three rules gone, and saying
        'three refs' would understate it the moment one ref carried three."""
        cur = _FakeCursor(self._rows(), full_replace=True, unqueued=[
            ("doc1__C1_4_10", 2, 1), ("doc1__D5_4", 3, 1), ("doc1__D5_6", 2, 1)])
        with pytest.raises(RuntimeError) as exc:
            commit_reviewed_from_queue(cur, "woollahra", "chapter-c1-paddington-hca")
        assert str(exc.value).startswith("4 live rule(s)"), str(exc.value)
        assert "across 3 ref(s)" in str(exc.value)

    def test_a_run_that_replaces_both_is_NOT_refused(self):
        """Confusable negative: the guard must not fire when the run carries as many rows
        for the ref as the live set holds."""
        cur = _FakeCursor(self._rows(), full_replace=True, unqueued=[])
        _, inserted = commit_reviewed_from_queue(cur, "woollahra", "chapter-c1-paddington-hca")
        assert inserted == 1

    def test_the_count_is_asked_of_the_committed_run_only(self):
        """Counting queued rows across every run would find July's copy of a ref and call
        September's run complete when it is not."""
        cur = _FakeCursor(self._rows(), full_replace=True)
        commit_reviewed_from_queue(cur, "woollahra", "chapter-c1-paddington-hca")
        guard = [c for c in cur.calls if "live_n > queued_n" in c[0]]
        assert guard, "the counting loss guard did not run"
        assert BATCH_TS in guard[0][1], guard[0][1]
        assert "IS NOT DISTINCT FROM" in guard[0][0], \
            "a NULL ref_number on both sides must match; ref_number is nullable"
