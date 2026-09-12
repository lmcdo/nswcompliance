"""dcp_scope_coverage, against the live schema.

It reports coverage against the chapters each council's own hazards make
relevant, so it joins spatial_overlays as well as the DCP tables. An
overlay rename would quietly drop the hazard half of the scope, and the
reported coverage percentage would RISE.

Marked `database` and deselected by default. The opt-in is required because
conftest_mocks stubs psycopg2, so without it these would assert against a
MagicMock and pass for the wrong reason:

    PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> python -m pytest -m database \\
        tests/test_dcp_scope_coverage_real_db.py -o addopts=
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


def test_the_dcp_columns_it_reads_still_exist():
    assert_columns_exist("dcp_chapter_registry", {
        "council", "chapter_key", "is_active"})
    assert_columns_exist("regulatory_provisions", {
        "source_council", "source_chapter_key", "is_current"})


def test_the_overlay_table_that_drives_hazard_scope_still_exists():
    assert_columns_exist("spatial_overlays", {"layer_type"})


def test_hazard_overlays_are_actually_present():
    """Zero hazard overlays would silently reduce every council's scope to the
    universal chapters, and the coverage percentage would RISE."""
    n = count_where("spatial_overlays", "layer_type IS NOT NULL")
    assert n > 0, ("no spatial overlay rows -- hazard-driven scope would "
                   "collapse to the universal set and coverage would read "
                   "higher than it is")
