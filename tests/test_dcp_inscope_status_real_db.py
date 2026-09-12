"""dcp_inscope_status, against the live schema.

It reports which in-scope chapters a council actually serves, reading the
measurement ledger. A rename there turns this report into an empty one,
and an empty report reads as 'nothing wrong'.

Marked `database` and deselected by default. The opt-in is required because
conftest_mocks stubs psycopg2, so without it these would assert against a
MagicMock and pass for the wrong reason:

    PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> python -m pytest -m database \\
        tests/test_dcp_inscope_status_real_db.py -o addopts=
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


def test_the_measurement_ledger_columns_it_reads_still_exist():
    assert_columns_exist("dcp_chapter_measurement", {"council", "chapter_key"})


def test_the_provision_columns_it_reads_still_exist():
    assert_columns_exist("regulatory_provisions", {
        "source_council", "source_chapter_key", "is_current"})


def test_the_ledger_is_not_empty():
    """An empty ledger makes every council read as 'nothing in scope' -- a
    pass-shaped answer to a question that was never asked."""
    n = count_where("dcp_chapter_measurement", "TRUE")
    assert n > 0, ("the chapter measurement ledger is empty -- this report "
                   "would show every council as having nothing in scope")
