"""The re-tag PLAN, built against the real database. Read-only; never --apply.

`tests/test_retag_narrowing_is_classified.py` covers `classify()` as a pure
function and the two refusals through --help. Neither touches a row, and the
part that decides what happens to production is `build_plan`: it reads the whole
corpus of the named councils, runs the tagger over each row, and produces the
narrowing list an operator adjudicates. Under `conftest_mocks.py` psycopg2 is
stubbed, so `cur.fetchall()` yields nothing, the plan comes back empty, and the
dry run prints "0 narrowings" -- which is exactly what a correct, finished run
also prints.

Opt-in per this repo's convention: PYTEST_REAL_DB=1 plus @pytest.mark.database,
deselected by pytest.ini in the ordinary run.

    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_retag_applicability_slug_docids_real_db.py -v

NOT COVERED HERE, DELIBERATELY: the --apply path. It writes to
regulatory_provisions, which is the single production database, so exercising it
from a test would mean either writing live rows or building a parallel schema
that would drift. What guards it instead is shape rather than a test: a
timestamped backup table that aborts if the name is taken, a row-count check
against the plan, a per-row optimistic-concurrency guard on the values read
during planning, --expect-narrowings demanding the exact count, and the rollback
UPDATE printed on completion.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytestmark = [
    pytest.mark.database,
    pytest.mark.skipif(
        os.getenv("PYTEST_REAL_DB") != "1",
        reason="needs the real psycopg2 driver; a stubbed one yields an empty "
               "plan, which is indistinguishable from a finished one",
    ),
]

COUNCIL = "canterbury_bankstown"


@pytest.fixture(scope="module")
def plan():
    sys.path.insert(0, str(ROOT / "scripts"))
    import dq_db

    from scripts.retag_applicability_slug_docids import build_plan

    conn = dq_db.connect()
    try:
        yield build_plan(conn.cursor(), [COUNCIL])
    finally:
        conn.close()


def test_the_plan_is_not_empty(plan):
    """An empty plan is what a stubbed driver, a wrong council slug and a
    finished repair all produce. Only one of those is good news."""
    changes, prov_only, _stats, _narrowings = plan
    assert len(changes) + len(prov_only) > 0, (
        "no rows in scope -- check the driver and the source_council slug "
        "before concluding there is nothing to do")


def test_every_narrowing_carries_what_an_operator_needs_to_adjudicate(plan):
    """The list is the whole safety mechanism. A narrowing without its document
    cannot be checked against the chapter that states the scope, and the id is
    what makes the row findable afterwards."""
    _changes, _prov_only, _stats, narrowings = plan
    for pid, doc, field, before, after, kind in narrowings:
        assert isinstance(pid, int) and doc
        assert field in ("zones", "dev_types")
        assert kind in ("narrowed", "narrowed_from_all", "swapped")
        assert before != after


def test_no_narrowing_lands_outside_a_chapter_whose_scope_was_read(plan):
    """Measured 2026-09-23: every Canterbury-Bankstown narrowing belongs to one
    of the four chapters whose Application section was read from the PDF. A
    narrowing anywhere else is a config change nobody adjudicated -- the exact
    thing --expect-narrowings is there to stop being applied by reflex.
    """
    _changes, _prov_only, _stats, narrowings = plan
    adjudicated = ("chapter_9_1_general_requirements",
                   "chapter_10_4_non_residential_land_uses",
                   "chapter_10_1_child_care_centres",
                   "chapter_10_7_sex_services_premises")
    stray = sorted({doc for _pid, doc, *_ in narrowings
                    if not any(a in doc.lower() for a in adjudicated)})
    assert not stray, (
        "narrowings in chapters whose scope statement has not been read:\n  "
        + "\n  ".join(stray)
        + "\nOpen each chapter's PDF and record the scope before applying.")


def test_the_repair_removes_no_config_from_the_column_dq33_counts(plan):
    """The point of the config. If the plan leaves any served row resolving to
    `no_config` on DEV TYPES, DQ-33 still counts it and the floor is not
    reached -- and without this the failure only shows up after the production
    write has already happened.

    The column matters. This assertion originally read the zone source, because
    that was the only one build_plan recorded, and it failed at 7 while the
    number DQ-33 actually counts was already 0. Those 7 are real but are a
    different row: served chapters with no config entry at all, whose text
    yielded dev types and no zones. They are DQ-102, and the test below fixes
    that count in place so it cannot drift unnoticed.
    """
    _changes, _prov_only, stats, _narrowings = plan
    left = sum(v for k, v in stats.items()
               if isinstance(k, tuple) and k == ("devtype", "no_config", "served"))
    assert left == 0, (
        f"{left} served rows still resolve to no_config on development types; "
        f"DQ-33 counts exactly these")


def test_the_zone_side_is_measured_too_and_is_not_silently_worse(plan):
    """build_plan recorded only zone_source until 2026-09-23, so the block it
    prints described zones while the ratchet it serves counts dev types. Both
    are recorded now, and this pins the zone residue rather than leaving it
    invisible: 7 served rows, every one in a chapter with no config entry.
    """
    _changes, _prov_only, stats, _narrowings = plan
    zone_gap = sum(v for k, v in stats.items()
                   if isinstance(k, tuple) and k == ("zone", "no_config", "served"))
    assert zone_gap <= 7, (
        f"{zone_gap} served rows resolve to no_config on zones, up from the 7 "
        f"measured on 2026-09-23 -- a chapter has lost its config entry")
