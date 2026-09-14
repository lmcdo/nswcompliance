"""Unit tests for the commit-reviewed-text path (scripts/dcp_commit_approved.py).

Importing the module pulls dcp_extract_changed (R2_*/DATABASE_URL at import); the
conftest mocks stub the native deps and we set the env defaults it reads.
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "postgresql://x")
os.environ.setdefault("R2_BUCKET_NAME", "x")
os.environ.setdefault("R2_ACCESS_KEY_ID", "x")
os.environ.setdefault("R2_SECRET_ACCESS_KEY", "x")
os.environ.setdefault("R2_ACCOUNT_ID", "x")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from dcp_commit_approved import _section_header_from_text, commit_reviewed_from_queue  # noqa: E402


class TestSectionHeaderFromText:
    def test_recovers_heading_line(self):
        assert _section_header_from_text("# A1.1 NAME OF PLAN\n\nbody") == "A1.1 NAME OF PLAN"

    def test_none_for_headerless_or_preamble(self):
        assert _section_header_from_text("plain preamble text with no header") is None
        assert _section_header_from_text("") is None
        assert _section_header_from_text("#   \n\nbody") is None


class _FakeCursor:
    """Records execute() calls. fetchone() returns the is_full_replace flag; fetchall()
    returns the queued rows. rowcount is 7 for a blanket delete, 1 for a per-ref delete."""
    def __init__(self, rows, full_replace=None, unqueued=()):
        self._rows = rows
        self._full_replace = full_replace
        self._unqueued = list(unqueued)
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
        # The full-replace completeness check asks for live refs the approved queue
        # does not name; every other fetchall is the queued rows.
        if "NOT EXISTS" in self._last:
            return [(ref,) for ref in self._unqueued]
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
