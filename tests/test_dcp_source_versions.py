"""Guards for the dated ledger of council source files (migration 126 + scripts/backfill_dcp_source_versions.py).

The ledger is evidence, so the tests pin the properties that make it trustworthy: unexpected paths are reported not guessed,
rows are idempotent, the ledger cannot be edited, the registry trigger can never block a write, and no existing table is changed.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import backfill_dcp_source_versions as bf  # noqa: E402

MIGRATION = REPO / "migrations" / "126_dcp_source_versions.sql"
LM = datetime(2026, 2, 28, 3, 4, 5, tzinfo=timezone.utc)


@pytest.mark.parametrize("key,expected", [
    ("source-pdfs/dcps/ashfield/v1.0-baseline/chapter-a-miscellaneous.pdf",
     {"council": "ashfield", "version_label": "v1.0-baseline", "chapter_key": "chapter-a-miscellaneous"}),
    ("source-pdfs/dcps/city_of_sydney/v1.1-2026-05-18/part-3.pdf",
     {"council": "city_of_sydney", "version_label": "v1.1-2026-05-18", "chapter_key": "part-3"}),
    ("source-pdfs/dcps/ASHFIELD/v1.0/Chapter-A.PDF", {"council": "ASHFIELD", "version_label": "v1.0", "chapter_key": "Chapter-A"}),
])
def test_parse_key_reads_the_five_part_shape(key, expected):
    assert bf.parse_key(key) == expected


@pytest.mark.parametrize("key", [
    "source-pdfs/dcps/ashfield/v1.0-baseline/chapter-a.txt",              # not a PDF
    "source-pdfs/dcps/ashfield/chapter-a.pdf",                            # version folder missing
    "source-pdfs/dcps/ashfield/v1.0/sub/chapter-a.pdf",                   # extra depth: never guess a chapter
    "other-prefix/dcps/ashfield/v1.0/chapter-a.pdf",                      # wrong prefix
    "source-pdfs/dcps//v1.0/chapter-a.pdf",                               # empty council
    "source-pdfs/dcps/ashfield/v1.0/.pdf",                                # empty chapter
    "",
])
def test_parse_key_refuses_anything_it_cannot_read_exactly(key):
    assert bf.parse_key(key) is None


def test_rows_carry_the_object_date_and_strip_the_etag_quotes():
    objs = [{"Key": "source-pdfs/dcps/ashfield/v1.0-baseline/a.pdf", "Size": 123, "ETag": '"abc123"', "LastModified": LM}]
    rows, skipped = bf.rows_from_objects(objs)
    assert skipped == []
    assert rows == [("ashfield", "a", "v1.0-baseline", "source-pdfs/dcps/ashfield/v1.0-baseline/a.pdf", "stored", 123, "abc123", None, LM,
                     "r2_listing_backfill")]


def test_unreadable_objects_are_reported_not_dropped():
    objs = [{"Key": "source-pdfs/dcps/ashfield/v1.0/sub/x.pdf", "Size": 1, "LastModified": LM},
            {"Key": "source-pdfs/dcps/ashfield/v1.0/ok.pdf", "Size": 1, "LastModified": None},        # no date: cannot be dated, so not a row
            {"Key": "source-pdfs/dcps/ashfield/v1.0/ok2.pdf", "Size": 1, "LastModified": LM}]
    rows, skipped = bf.rows_from_objects(objs)
    assert len(rows) == 1 and rows[0][3].endswith("ok2.pdf")
    assert len(skipped) == 2


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_migration_is_one_transaction_the_dry_run_tool_accepts():
    sql = _sql()
    assert len(re.findall(r"^[ \t]*(BEGIN|COMMIT);[ \t]*\r?$", sql, re.M)) == 2
    assert len(re.findall(r"\b(BEGIN|COMMIT);", sql)) == 2


def test_migration_number_is_unique():
    assert [p.name for p in (REPO / "migrations").glob("126_*.sql")] == ["126_dcp_source_versions.sql"]


def test_the_ledger_is_append_only_and_idempotent():
    sql = _sql()
    assert "UNIQUE (r2_key, event)" in sql
    assert re.search(r"BEFORE UPDATE OR DELETE ON dcp_source_versions", sql)
    assert re.search(r"BEFORE TRUNCATE ON dcp_source_versions", sql)
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_the_registry_trigger_can_never_block_a_write():
    sql = _sql()
    body = sql.split("CREATE OR REPLACE FUNCTION dcp_registry_log_source_version", 1)[1].split("$$;", 1)[0]
    assert "EXCEPTION WHEN OTHERS THEN" in body and "RAISE WARNING" in body and "RAISE EXCEPTION" not in body
    assert "ON CONFLICT (r2_key, event) DO NOTHING" in body


def test_no_existing_table_is_altered_or_emptied():
    sql = _sql()
    for bad in (r"ALTER\s+TABLE\s+dcp_chapter_registry", r"DROP\s+TABLE", r"\bDELETE\s+FROM\b", r"\bUPDATE\s+\w+\s+SET\b", r"\bTRUNCATE\s+TABLE\b"):
        assert not re.search(bad, sql, re.I), bad
