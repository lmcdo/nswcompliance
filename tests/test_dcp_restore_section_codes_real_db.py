"""dcp_restore_section_codes, against the live schema.

The only script here that WRITES to production, and only under --apply. It
restored 2,259 section codes on 2026-09-12. Its UPDATE is scoped by id AND
is_current; if is_current were gone that predicate must RAISE rather than
silently widen to superseded rows.

Marked `database` and deselected by default. The opt-in is required because
conftest_mocks stubs psycopg2, so without it these would assert against a
MagicMock and pass for the wrong reason:

    PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> python -m pytest -m database \\
        tests/test_dcp_restore_section_codes_real_db.py -o addopts=
"""
from __future__ import annotations

import os
import pathlib
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from real_db_contract import (  # noqa: E402
    assert_columns_exist, columns_of, connect, count_where)

pytestmark = pytest.mark.database


def test_the_columns_it_reads_and_writes_still_exist():
    assert_columns_exist("regulatory_provisions", {
        "id", "source_council", "section_header", "ref_number", "document_id",
        "provision_text", "is_current", "source_chapter_key"})


def test_the_currency_filter_its_update_depends_on_still_exists():
    """Both the SELECT that gathers ids and the UPDATE that writes them are
    scoped by is_current. Losing that column must break the script loudly."""
    assert "is_current" in columns_of("regulatory_provisions")


def test_its_scope_predicate_still_selects_rows():
    n = count_where("regulatory_provisions",
                    "is_current AND source_council IS NOT NULL")
    assert n > 0, "no live council-scoped provision exists to repair"
