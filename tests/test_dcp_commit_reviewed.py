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
    """Records execute() calls; fetchall() returns the queued rows once."""
    def __init__(self, rows):
        self._rows = rows
        self.calls = []
        self.rowcount = 7  # pretend 7 old provisions were superseded

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchall(self):
        return self._rows


class TestCommitReviewedFromQueue:
    def _rows(self):
        # (document_id, ref_number, new_text, new_page)
        return [
            ("doc1", "doc1__A1_1", "# A1.1 TITLE\n\nthe control body", 5),
            ("doc1", "doc1__preamble", "some preamble text", 1),
        ]

    def test_soft_deletes_then_inserts_reviewed_text(self):
        cur = _FakeCursor(self._rows())
        superseded, inserted = commit_reviewed_from_queue(cur, "leichhardt", "part-a")
        assert superseded == 7 and inserted == 2

        # first statement soft-deletes the chapter's current provisions
        assert "is_current = FALSE" in cur.calls[0][0]
        assert cur.calls[0][1] == ("leichhardt", "part-a")

        inserts = [c for c in cur.calls if "INSERT INTO regulatory_provisions" in c[0]]
        assert len(inserts) == 2
        # provision_text is the reviewed new_text VERBATIM (not a re-extraction)
        p0 = inserts[0][1]
        assert p0[3] == "# A1.1 TITLE\n\nthe control body"
        assert p0[2] == "A1.1 TITLE"          # section_header recovered from heading
        assert p0[1] == "doc1__A1_1"          # ref_number preserved
        assert p0[4] == 5                      # pdf_page = new_page
        assert p0[6] == [5]                    # page_range = [new_page]

    def test_preamble_marked_non_actionable(self):
        cur = _FakeCursor(self._rows())
        commit_reviewed_from_queue(cur, "leichhardt", "part-a")
        inserts = [c for c in cur.calls if "INSERT INTO regulatory_provisions" in c[0]]
        # last param is v2_is_actionable: False for the preamble row, None otherwise
        assert inserts[0][1][-1] is None
        assert inserts[1][1][-1] is False
