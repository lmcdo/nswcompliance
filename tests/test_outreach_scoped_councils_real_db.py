"""OC-17's council list against the REAL database: the SQL runs, the split adds up to DQ-114's own total,
and every council the site publishes is one the database serves rule text for.

The unit tests in test_outreach_scoped_councils.py feed a fake cursor, so they cannot catch a column that
was renamed or a query that no longer parses. This does, and only when asked for (the repo's opt-in):

    PYTEST_REAL_DB=1 pytest -m database tests/test_outreach_scoped_councils_real_db.py -o addopts=
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

import outreach_scoped_councils as osc  # noqa: E402


@pytest.fixture
def conn():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_outreach_scoped_councils_real_db.py -o addopts=")
    from dq_db import connect
    c = connect()
    yield c
    c.close()


def test_compute_runs_and_adds_up_to_dq114(conn):
    published = osc.load_published()
    reasons, names, problems = osc.compute(conn, published["exceptions"])
    assert reasons, "no council serves rule text -- the universe query matched nothing"
    assert not [p for p in problems if "drifted apart" in p], problems
    assert not [p for p in problems if "DQ-115 hit in a config" in p], problems


def test_every_published_council_serves_rule_text_under_its_registry_name(conn):
    published = osc.load_published()
    _reasons, names, _problems = osc.compute(conn, published["exceptions"])
    for c in published["councils"]:
        assert c["slug"] in names, f"{c['slug']} is published but serves no rule text"
        assert names[c["slug"]] == c["name"], (c, names[c["slug"]])


def test_a_former_council_is_named_as_its_merged_council_and_area(conn):
    """DQ-129: Leichhardt is a plan inside Inner West, not a council, and only that plan passes."""
    _reasons, names, _problems = osc.compute(conn, osc.load_published()["exceptions"])
    assert names.get("leichhardt") == "Inner West (former Leichhardt area only)", names.get("leichhardt")
    assert names.get("hornsby") == "Hornsby"
