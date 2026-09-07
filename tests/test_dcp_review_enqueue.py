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
