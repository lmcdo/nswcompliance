"""DQ-102 and DQ-103 against the REAL database, not conftest_mocks.py's stub.

Every other test of this work stops at a config dict or a pure function. The
probe's whole job is a live measurement, and `conftest_mocks.py` stubs psycopg2
by default -- so under the ordinary run `cur.fetchall()` returns a MagicMock,
`for council, doc, text, src in rows` iterates nothing, and BOTH probes would
report 0 and exit 0. A green probe that never touched a row reads exactly like a
clean one, which is the silent-pass shape the ledger exists to remove.

Opt-in, the way this repo already does it (tests/test_lga_coverage.py,
tests/test_drawdown_verify_real_db.py): PYTEST_REAL_DB=1 plus
@pytest.mark.database, which pytest.ini deselects by default, so the normal
`pytest` run is unaffected.

    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_dq_probe_applicability_config_real_db.py -v

WHAT THIS PINS THAT A MOCK CANNOT
  * the SQL actually parses against the live schema -- every column named here
    (source_council, document_id, provision_text, v2_dev_type_source,
    is_current, v2_is_actionable) still exists under that spelling. CLAUDE.md
    records two columns, former_council and source_ref, that several scripts
    still assume and which have never existed on this table.
  * the query carries its currency filter, so the count describes rows somebody
    is actually served rather than the whole 55k-row history.
  * the two probes disagree. They partition on different states of the same
    entry (no match at all vs matched-and-silent), so a refactor that collapsed
    them would leave both numbers identical and neither test elsewhere notices.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytestmark = [
    pytest.mark.database,
    pytest.mark.skipif(
        os.getenv("PYTEST_REAL_DB") != "1",
        reason="needs the real psycopg2 driver; conftest_mocks.py stubs it by "
               "default and a stubbed run reports 0 for both probes",
    ),
]


@pytest.fixture(scope="module")
def rows():
    sys.path.insert(0, str(ROOT / "scripts"))
    import dq_db

    from scripts.dq_probe_applicability_config import _rows

    conn = dq_db.connect()
    try:
        yield _rows(conn.cursor())
    finally:
        conn.close()


def test_the_query_runs_against_the_live_schema_and_returns_rows(rows):
    """An empty result is the failure this file exists to catch: it is what a
    stubbed driver, a renamed column or a dropped currency filter all produce,
    and all three are indistinguishable from 'clean' in the exit code."""
    assert len(rows) > 0, (
        "the served set came back empty -- either the driver is stubbed, a "
        "column was renamed, or the filter no longer matches anything")
    council, doc, _text, _src = rows[0]
    assert isinstance(council, str) and isinstance(doc, str)


def test_the_result_is_the_served_set_not_the_whole_table(rows):
    """v2_is_actionable and is_current are both in the WHERE clause. Without
    them the probe counts superseded and non-actionable rows -- a defect
    reported against provisions nobody is shown."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import dq_db

    conn = dq_db.connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM regulatory_provisions")
        whole_table = cur.fetchone()[0]
    finally:
        conn.close()
    assert 0 < len(rows) < whole_table, (
        f"{len(rows):,} rows of {whole_table:,} -- the filter is not narrowing, "
        f"so the count is not about the served set")


def test_the_two_probes_measure_different_populations(rows):
    """DQ-102 is 'no entry matched'; DQ-103 is 'an entry matched and declined to
    decide'. They are disjoint by construction, so identical counts mean one of
    them has stopped asking its own question."""
    from enrichment.extractors.applicability_tagger import ApplicabilityTagger
    from scripts.dq_probe_applicability_config import probe_102, probe_103

    tagger = ApplicabilityTagger()
    n102, by102 = probe_102(rows, tagger)
    n103, by103 = probe_103(rows, tagger)
    assert n102 != n103, (
        f"both probes report {n102} -- they partition on different states and "
        f"cannot legitimately agree")
    assert not (set(by102) & set(by103)), (
        "a document cannot both fail to match an entry and match one that left "
        "a key silent")


@pytest.mark.parametrize("dq_id", ["DQ-102", "DQ-103"])
def test_the_exit_code_matches_the_count(dq_id):
    """The ledger reads the exit code, not the text. A probe that printed a
    non-zero count and still exited 0 would be recorded as passing."""
    done = subprocess.run(
        [sys.executable, "scripts/dq_probe_applicability_config.py", "--id", dq_id],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
    )
    assert done.returncode in (0, 1), done.stderr[-2000:]
    count = int(done.stdout.split("count   :")[1].split()[0].replace(",", ""))
    assert done.returncode == (0 if count == 0 else 1), (
        f"count {count} but exit {done.returncode}")
