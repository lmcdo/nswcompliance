"""dcp_page_map_gate, against the live schema.

The gate that fails closed on an unusable page map: run per PR from the
ledger, nightly against R2. The ledger form is the one CI depends on, so
its columns are the contract that matters here.

Marked `database` and deselected by default. The opt-in is required because
conftest_mocks stubs psycopg2, so without it these would assert against a
MagicMock and pass for the wrong reason:

    PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> python -m pytest -m database \\
        tests/test_dcp_page_map_gate_real_db.py -o addopts=
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


def test_the_ledger_columns_the_fast_form_reads_still_exist():
    assert_columns_exist("dcp_chapter_measurement", {"council", "chapter_key"})


def test_the_registry_columns_it_reads_still_exist():
    assert_columns_exist("dcp_chapter_registry", {
        "council", "chapter_key", "is_active", "r2_current_path"})


def test_there_are_page_maps_to_gate():
    """The gate reports PASS over an empty set exactly as it reports PASS over a
    healthy one. Asserting the set is non-empty is what separates them."""
    n = count_where("dcp_chapter_registry",
                    "is_active AND r2_current_path IS NOT NULL")
    assert n > 0, ("no active chapter has an R2 path -- the gate would pass "
                   "over nothing")
