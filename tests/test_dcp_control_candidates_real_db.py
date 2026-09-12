"""dcp_control_candidates, against the live schema.

It selects the passages a model is allowed to cite. If v2_topic or
provision_text moved, the harness would select nothing and report zero
candidates -- indistinguishable from a council that genuinely states no
such control.

Marked `database` and deselected by default. The opt-in is required because
conftest_mocks stubs psycopg2, so without it these would assert against a
MagicMock and pass for the wrong reason:

    PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> python -m pytest -m database \\
        tests/test_dcp_control_candidates_real_db.py -o addopts=
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


def test_the_provision_columns_it_reads_still_exist():
    assert_columns_exist("regulatory_provisions", {
        "source_council", "source_chapter_key", "pdf_page", "section_header",
        "provision_text", "v2_topic", "is_current"})


def test_the_registry_columns_the_pdf_path_needs_still_exist():
    assert_columns_exist("dcp_chapter_registry", {
        "council", "chapter_key", "r2_current_path", "is_active", "is_spatial",
        "is_inert"})


def test_the_excluded_topics_are_real_values_not_typos():
    """An excluded topic that does not exist excludes nothing, and the run looks
    identical to one where the exclusion worked."""
    from scripts.dcp_control_candidates import NUMERIC_POOR_TOPICS
    conn, cur = connect()
    try:
        cur.execute("SELECT DISTINCT v2_topic FROM regulatory_provisions "
                    "WHERE is_current AND v2_topic IS NOT NULL")
        live = {r[0] for r in cur.fetchall()}
    finally:
        conn.close()
    named = {t for t in NUMERIC_POOR_TOPICS if t not in ("untagged", "None")}
    unknown = sorted(named - live)
    assert not unknown, (
        "these topics are excluded but do not exist in the corpus, so the "
        "exclusion is doing nothing: " + str(unknown))


def test_its_scope_predicate_still_selects_provisions():
    n = count_where("regulatory_provisions",
                    "is_current AND provision_text IS NOT NULL "
                    "AND source_chapter_key IS NOT NULL")
    assert n > 0, "no live provision carries both text and a chapter key"
