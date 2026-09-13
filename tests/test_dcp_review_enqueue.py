"""Offline gate for enqueue_review_changes (dcp_extract_changed.py).

dcp_extract_changed imports boto3/pdfplumber at module top, which aren't in the
mocked pre-push env — so we exec-extract just the function (it only needs a DB
connection object) and drive it with a MagicMock. Verifies the queue insertion,
the per-change-type mapping, the idempotent refresh, and the numeric flag.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent


def _extract_def(src: str, name: str) -> str:
    start = src.index(f"def {name}(")
    nxt = re.search(r"\n(?:def |class |# ── )", src[start + 10:])
    end = start + 10 + nxt.start() if nxt else len(src)
    return src[start:end]


def _load_enqueue():
    src = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
    # enqueue_review_changes calls module-level suspect_reason() (stubbed) and
    # the fidelity helpers (real implementations — they're pure and part of the
    # behaviour under test since the 2026-07 fidelity gate).
    ns: dict = {"suspect_reason": lambda ch: ch.get("suspect_reason"), "re": re}
    garble = re.search(r"_GARBLE_RUN = .+", src).group(0)
    junk = re.search(r"_JUNK_REF = .+", src).group(0)
    exec(garble, ns)
    exec(junk, ns)
    # 2026-09-07 (DQ-97 cause 5): strip_garbled_header_lines now delegates to
    # _strip_garbled_phrase_spans, which needs these three module-level
    # regexes too -- same exec-extract pattern as _GARBLE_RUN/_JUNK_REF above.
    for const in ("_GARBLE_RUN_TOLERANT", "_WHOLE_TOKEN_GARBLE", "_SPACED_GARBLE_RUN"):
        exec(re.search(rf"{const} = .+", src).group(0), ns)
    exec(_extract_def(src, "_garble_evidence"), ns)
    exec(_extract_def(src, "_strip_garbled_phrase_spans"), ns)
    exec(_extract_def(src, "strip_garbled_header_lines"), ns)
    exec(_extract_def(src, "classify_row_fidelity"), ns)
    exec(_extract_def(src, "enqueue_review_changes"), ns)
    return ns["enqueue_review_changes"]


def _review_chapter(**diff):
    return [{
        "council": "test_c", "chapter_key": "test_ch",
        "document_id": "doc", "content_hash": "hash123",
        "diff": {"changed": [], "added": [], "removed": [], **diff},
    }]


class TestEnqueueReviewChanges:
    def test_inserts_one_row_per_change_and_refreshes(self):
        enqueue = _load_enqueue()
        conn = MagicMock()
        cur = conn.cursor.return_value
        review = _review_chapter(
            changed=[{"ref_number": "1.1", "old_text": "6m", "new_text": "7m",
                      "has_numeric_change": True, "old_page": 3, "new_page": 3}],
            added=[{"ref_number": "1.2", "new_text": "new", "new_page": 4}],
            removed=[{"ref_number": "1.3", "old_text": "gone"}],
        )
        n = enqueue(conn, review)
        assert n == 3
        sqls = [c.args[0] for c in cur.execute.call_args_list]
        # idempotent refresh: stale pending rows cleared before insert
        assert any("DELETE FROM dcp_review_queue" in s and "status = 'pending'" in s for s in sqls)
        # one insert per change
        assert sum("INSERT INTO dcp_review_queue" in s for s in sqls) == 3
        conn.commit.assert_called()

    def test_numeric_flag_propagates(self):
        enqueue = _load_enqueue()
        conn = MagicMock()
        cur = conn.cursor.return_value
        enqueue(conn, _review_chapter(
            changed=[{"ref_number": "1.1", "old_text": "a", "new_text": "b",
                      "has_numeric_change": True, "old_page": 1, "new_page": 1}]))
        # the changed-row INSERT carries has_numeric_change=True in its params
        insert_calls = [c for c in cur.execute.call_args_list
                        if "INSERT INTO dcp_review_queue" in c.args[0]]
        assert insert_calls
        assert True in insert_calls[0].args[1]

    def test_empty_diff_enqueues_nothing(self):
        enqueue = _load_enqueue()
        conn = MagicMock()
        assert enqueue(conn, _review_chapter()) == 0

    # -- A chapter replaced whole must queue every rule it keeps ---------------------
    # dcp_commit_approved soft-deletes EVERY live row of a full-replace chapter, then
    # inserts only the approved queue rows. A rule the queue never held is gone from
    # the app. Measured 2026-09-13: waverley's re-extraction was a restructure with 46
    # rules whose text had not changed, none of which were queued.

    @staticmethod
    def _inserts(cur):
        return [c.args[1] for c in cur.execute.call_args_list
                if "INSERT INTO dcp_review_queue" in c.args[0]]

    def test_a_full_replace_queues_its_unchanged_rules_at_their_new_page(self):
        enqueue = _load_enqueue()
        conn = MagicMock()
        cur = conn.cursor.return_value
        enqueue(conn, _review_chapter(
            status="restructure", total_old=2,
            changed=[{"ref_number": "doc_C1_1_1", "old_text": "6m", "new_text": "7m",
                      "has_numeric_change": True, "old_page": 167, "new_page": 168}],
            unchanged=[{"ref_number": "doc_C1_1_2", "old_text": "Keep this rule.",
                        "new_text": "Keep this rule.", "old_page": 167, "new_page": 169}]))
        rows = {p[3]: p for p in self._inserts(cur)}
        assert "doc_C1_1_2" in rows, "an unchanged rule of a full-replace chapter was not queued"
        kept = rows["doc_C1_1_2"]
        assert kept[4] == "changed"   # the queue's CHECK has no 'unchanged' type
        assert kept[6] == "Keep this rule." and kept[8] == 169
        assert kept[12] is True
        # Identical old and new text must not look like a defect: an auto-rejected row
        # under the current hash would block the whole chapter at commit.
        assert kept[13] == "pending", f"carried-over row landed {kept[13]!r}"
        assert "unchanged" in (kept[15] or ""), "the reviewer is not told why the row is here"

    def test_a_targeted_amendment_leaves_unchanged_rules_out_of_the_queue(self):
        """Confusable negative: a targeted commit supersedes only the refs the queue
        names, so unchanged rules stay live without being queued."""
        enqueue = _load_enqueue()
        conn = MagicMock()
        cur = conn.cursor.return_value
        enqueue(conn, _review_chapter(
            status="ok", total_old=40,
            changed=[{"ref_number": "doc_1", "old_text": "a", "new_text": "b",
                      "has_numeric_change": False, "old_page": 1, "new_page": 1}],
            unchanged=[{"ref_number": "doc_2", "old_text": "same", "new_text": "same",
                        "old_page": 2, "new_page": 2}]))
        assert [p[3] for p in self._inserts(cur)] == ["doc_1"]

    def test_a_full_replace_queues_a_renumbered_rule_under_its_new_number(self):
        enqueue = _load_enqueue()
        conn = MagicMock()
        cur = conn.cursor.return_value
        enqueue(conn, _review_chapter(
            status="restructure", total_old=3,
            removed=[{"ref_number": "doc_gone", "old_text": "x"}],
            renumbered=[{"old_ref_number": "doc_B7_7_1", "new_ref_number": "doc_B7_7_2",
                         "text": "Vehicle access rule.", "new_page": 61}]))
        rows = {p[3]: p for p in self._inserts(cur)}
        assert "doc_B7_7_2" in rows, "a renumbered rule of a full-replace chapter was not queued"
        moved = rows["doc_B7_7_2"]
        assert moved[4] == "added" and moved[6] == "Vehicle access rule." and moved[8] == 61
        assert "doc_B7_7_1" in (moved[15] or "")

    def test_added_and_removed_are_never_numeric(self):
        enqueue = _load_enqueue()
        conn = MagicMock()
        cur = conn.cursor.return_value
        enqueue(conn, _review_chapter(
            added=[{"ref_number": "2", "new_text": "x", "new_page": 1}],
            removed=[{"ref_number": "3", "old_text": "y"}]))
        for c in cur.execute.call_args_list:
            if "INSERT INTO dcp_review_queue" in c.args[0]:
                # has_numeric_change is the 10th positional param (index 9)
                assert c.args[1][9] is False
