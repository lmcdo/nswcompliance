"""dcp_chapter_measure, against the live schema.

It measures whether a DCP chapter is completely served, and writes that
verdict to the ledger the frozen baseline ratchets against. If a column it
reads disappears, the measurement stops being taken and the ratchet has
nothing to compare -- which reads as 'no regression'.

Marked `database` and deselected by default. The opt-in is required because
conftest_mocks stubs psycopg2, so without it these would assert against a
MagicMock and pass for the wrong reason:

    PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> python -m pytest -m database \\
        tests/test_dcp_chapter_measure_real_db.py -o addopts=
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


def test_the_registry_columns_it_reads_still_exist():
    assert_columns_exist("dcp_chapter_registry", {
        "council", "chapter_key", "is_active", "is_spatial", "is_inert",
        "r2_current_path"})


def test_the_provision_columns_it_reads_still_exist():
    assert_columns_exist("regulatory_provisions", {
        "source_council", "source_chapter_key", "pdf_page", "section_header",
        "provision_text", "is_current", "ref_number"})


def test_the_measurement_ledger_it_writes_to_still_exists():
    assert columns_of("dcp_chapter_measurement"), (
        "dcp_chapter_measurement is gone -- migration 069 defined it and the "
        "ratchet has nowhere to read from")
    assert_columns_exist("dcp_chapter_measurement", {"council", "chapter_key"})


def test_its_scope_predicate_still_selects_chapters():
    """A predicate that selects nothing produces a clean run and no measurement.
    Silence and success look identical, so the count is asserted."""
    n = count_where("dcp_chapter_registry",
                    "is_active AND NOT is_spatial AND NOT is_inert")
    assert n > 0, ("no active, non-spatial, non-inert chapter exists -- the "
                   "measurement would report nothing and exit 0")
