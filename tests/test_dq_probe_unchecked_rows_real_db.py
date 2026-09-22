"""The three DB-backed checks, against the REAL database.

`conftest_mocks.py` stubs psycopg2 by default, so under the ordinary run
`cur.fetchall()` returns a MagicMock: probe_42 and probe_43 would iterate
nothing and report 0, and probe_58's `cur.fetchone()[0] == 0` branch would
compare a mock to an int. A probe that never touched a row reports exactly the
same "clean" as one that did, which is the silent-pass shape the whole ledger
exists to remove.

Opt-in the way this repo already does it (tests/test_lga_coverage.py,
tests/test_drawdown_verify_real_db.py): PYTEST_REAL_DB=1 plus
@pytest.mark.database, which pytest.ini deselects by default.

    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_dq_probe_unchecked_rows_real_db.py -v

WHAT THIS PINS THAT A MOCK CANNOT
  * every column these three name still exists under that spelling. The handoff
    for this very session named `regulatory_provisions.source_url`, which has
    never existed; CLAUDE.md records two more (`former_council`, `source_ref`)
    that scripts still assume. A probe whose SQL no longer parses exits 2 and
    is read as "unreachable", not as "wrong".
  * DQ-58's branch actually taken. It has two, and which one runs depends on a
    column existing in production -- something no fixture can decide.
  * the exit-code contract: the ledger reads the code, not the text.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import dq_probe_unchecked_rows as probe  # noqa: E402

pytestmark = [
    pytest.mark.database,
    pytest.mark.skipif(
        os.getenv("PYTEST_REAL_DB") != "1",
        reason="needs the real psycopg2 driver; conftest_mocks.py stubs it by "
               "default and a stubbed run reports 0 for every DB-backed probe",
    ),
]


@pytest.fixture(scope="module")
def cur():
    sys.path.insert(0, str(ROOT / "scripts"))
    import dq_db

    conn = dq_db.connect()
    try:
        yield conn.cursor()
    finally:
        conn.close()


def test_dq42_sql_parses_against_the_live_schema(cur):
    """Every column named -- portal_date, portal_plan_name,
    currency_confirmed_plan -- still exists on dcp_plan_as_at. A rename makes
    this raise rather than quietly report clean."""
    count, detail = probe.probe_42(cur)
    assert isinstance(count, int)
    assert count == len(detail)


def test_dq43_sees_a_real_slice_of_the_corpus(cur):
    """The three-table join must actually match. If `chapter_key` or
    `source_chapter_key` changes shape the join silently returns nothing, and
    an empty result reads identically to 'every council serves one plan'."""
    cur.execute(
        """SELECT count(*)::int
             FROM regulatory_provisions rp
             JOIN dcp_chapter_registry r
               ON r.council = rp.source_council
              AND replace(r.chapter_key, '-', '_')
                  = replace(coalesce(rp.source_chapter_key, ''), '-', '_')
            WHERE rp.is_current AND rp.v2_is_actionable"""
    )
    joined = cur.fetchone()[0]
    assert joined > 0, (
        "the registry join matched nothing -- the probe would report every "
        "council as single-plan without having looked at one")

    count, detail = probe.probe_43(cur)
    assert count == len(detail)
    for council, note in detail:
        assert isinstance(council, str) and council
        assert "names" in note


def test_dq43_states_its_blind_spot_rather_than_hiding_it(cur):
    """The join needs source_chapter_key, and a large minority of served rows
    have none. The probe's docstring carries that number; this asserts the
    number is still roughly true, so the docstring cannot quietly rot into a
    claim of full coverage."""
    cur.execute(
        """SELECT count(*) FILTER (WHERE source_chapter_key IS NULL)::int,
                  count(*)::int
             FROM regulatory_provisions
            WHERE is_current AND v2_is_actionable"""
    )
    missing, total = cur.fetchone()
    assert missing > 0, (
        "no served row lacks a chapter key any more -- the blind spot recorded "
        "in probe_43's docstring is gone, so REMOVE that paragraph rather than "
        "leaving a stale caveat")
    assert missing < total, "every served row lacks a chapter key; the join is dead"


def test_dq58_takes_the_branch_production_actually_dictates(cur):
    """Two branches, and only production decides which. While
    url_page_last_status is absent the count is 'URLs whose status is recorded
    nowhere'; once it exists the same probe counts non-200s. Both are the same
    question and the switch must be the column, not a flag someone sets."""
    cur.execute(
        """SELECT count(*) FROM information_schema.columns
            WHERE table_name = 'dcp_chapter_registry'
              AND column_name = 'url_page_last_status'"""
    )
    column_exists = cur.fetchone()[0] > 0
    count, detail = probe.probe_58(cur)
    if column_exists:
        assert count == len(detail)
    else:
        assert len(detail) == 1
        key = next(iter(detail))
        assert "no url_page_last_status column" in key[0]
        assert count > 0, "the column is absent, so every page URL is unrecorded"


class TestDQ105AsksTheTaggersQuestion:
    """Both corrections, pinned against the live corpus.

    The check is "does this council have an applicability config", and it got
    that wrong twice in one afternoon by asking something ADJACENT to the
    question the tagger asks:

      1. It compared each `source_council` string to COUNCIL_CONFIGS. The tagger
         keys on DOCUMENT_ID, so `inner_west` was reported as unconfigured on
         the strength of 11 rows -- 10 from "Marrickville_DCP_2011__..." and 1
         from "Ashfield_DCP_2007__..." -- which the tagger resolves perfectly
         well. Inner West is the most deeply configured council in the product.
      2. It then resolved each document_id with an EMPTY provision text.
         Waverley and Woollahra key on a section code read out of the text, so
         both resolved to nothing and waverley was reported as unconfigured
         while serving 392 rows with zero fallthrough.
    """

    @pytest.mark.parametrize("council", ["inner_west", "waverley", "woollahra",
                                         "marrickville", "ashfield", "leichhardt"])
    def test_a_configured_council_is_never_reported(self, cur, council):
        _count, detail = probe.probe_105(cur)
        named = {c for c, _ in detail}
        assert council not in named, (
            f"{council} has a working config -- if it is reported here the probe "
            f"is asking something other than what the tagger asks")

    def test_it_still_reports_the_councils_that_genuinely_have_none(self, cur):
        """The confusable negative for the corrections: a fix that made the
        probe resolve EVERYTHING would silence it completely, which reads the
        same as 'all configured'."""
        count, detail = probe.probe_105(cur)
        assert count > 0, (
            "no council reports as unconfigured -- either every config has been "
            "written (check by hand before believing it) or the resolver now "
            "matches anything")
        named = {c for c, _ in detail}
        assert "parramatta" in named, (
            "parramatta serves 616 rules with no config and must still be named")

    def test_the_count_is_councils_not_rows(self, cur):
        """Counting rows would let a council with no config read 0 because its
        prose happened to match the text regex."""
        count, detail = probe.probe_105(cur)
        assert count == len(detail)


@pytest.mark.parametrize("dq_id", ["DQ-42", "DQ-43", "DQ-58"])
def test_the_exit_code_matches_the_count(dq_id):
    """The ledger reads the exit code, not the printed text. A probe that
    reported a non-zero count and still exited 0 would be recorded as passing."""
    done = subprocess.run(
        [sys.executable, "scripts/dq_probe_unchecked_rows.py", "--id", dq_id],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
    )
    assert done.returncode in (0, 1), done.stderr[-2000:]
    count = int(done.stdout.split("count :")[1].split()[0].replace(",", ""))
    assert done.returncode == (0 if count == 0 else 1), (
        "%s printed %d but exited %d" % (dq_id, count, done.returncode))
