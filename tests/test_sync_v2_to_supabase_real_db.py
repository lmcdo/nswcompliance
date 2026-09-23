"""The sync's zone gate, against the REAL land-use tables it will be judged by.

`scripts/sync_v2_to_supabase.py` UPDATEs 16 `v2_*` columns across ~48.8k rows,
row by row, committing every 100. Until 2026-09-24 the only thing in front of
that was `input("Continue? (yes/no): ")`.

⚠ AND IT DOES NOT CONNECT WHERE ITS CODE SAYS. `get_local_connection()` is
written with `localhost` / `nsw_planning` defaults, but `load_dotenv()` puts the
repo `.env` on top and `.env` points `PG*` at the Supabase pooler — so BOTH ends
resolve to production. On a machine where `PG*` is unset the same command reads
a stale local mirror instead (46,585 rows, no `source_council` column, 200 rows
carrying zone codes the 2022 employment-zone reform retired). Same file, same
command, two payloads, decided by a dotfile. That is why the gate under test
loads its ground truth from the TARGET rather than from the source.

Under `conftest_mocks.py` psycopg2 is stubbed, so `load_ground_truth` would come
back empty and `rows_with_retired_zones` would return `[]` for every input —
indistinguishable from "the payload is clean". That is the exact false pass this
file exists to prevent, hence the opt-in:

    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \\
        tests/test_sync_v2_to_supabase_real_db.py -v
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = [
    pytest.mark.database,
    pytest.mark.skipif(
        os.getenv("PYTEST_REAL_DB") != "1",
        reason="needs the real psycopg2 driver; a stubbed one yields empty "
               "ground truth, and an empty land-use table passes every row",
    ),
]


@pytest.fixture(scope="module")
def conn():
    import dq_db

    c = dq_db.connect()
    try:
        yield c
    finally:
        c.close()


def _row(council, zones, pid=1):
    """The shape `export_v2_data` yields: a RealDictCursor row."""
    return {"id": pid, "source_council": council, "v2_applicable_zones": zones}


class TestTheZoneGateAgainstRealLandUseTables:
    def test_a_retired_code_is_caught_for_a_council_that_resolves(self, conn):
        """The 2022 employment-zone reform retired the B series. No NSW LGA has
        a B2 in its land-use table any more, so this must be reported whichever
        council resolves first."""
        from sync_v2_to_supabase import rows_with_retired_zones

        bad = rows_with_retired_zones(
            conn, [_row("northern_beaches", ["B2"])])  # noqa: zone-codes (a retired code, fixed on purpose)
        assert bad, "a retired business zone passed the gate"
        assert bad[0][2] == ["B2"]  # noqa: zone-codes (same retired code, echoed back)

    def test_a_current_code_from_that_councils_own_table_passes(self, conn):
        """The confusable negative, and it is NOT hardcoded: the zone is read
        out of the live land-use table for the same council used above, so this
        cannot drift away from reality the way a literal would."""
        from validate_zone_code_validity import (load_ground_truth,
                                                 load_slug_resolution)
        from sync_v2_to_supabase import rows_with_retired_zones

        cur = conn.cursor()
        truth = load_ground_truth(cur)
        slugs = load_slug_resolution(cur, truth)
        key = slugs.get("northern_beaches")
        if not key or not truth.get(key):
            pytest.skip("no ground truth for northern_beaches to draw a zone from")

        real_zone = sorted(truth[key])[0]
        assert rows_with_retired_zones(conn, [_row("northern_beaches", [real_zone])]) == []

    def test_ALL_is_never_treated_as_a_zone_code(self, conn):
        """`'ALL'` is the universal marker the serving query tests with
        `'ALL' = ANY(col)`. Most rows hold it, so testing it against a land-use
        table would abort every sync."""
        from sync_v2_to_supabase import rows_with_retired_zones

        assert rows_with_retired_zones(conn, [_row("northern_beaches", ["ALL"])]) == []

    def test_an_unresolvable_council_is_skipped_not_silently_passed(self, conn):
        """Three-state, matching `validate_zone_code_validity.py`. Statewide
        instruments carry a NULL council and have no LGA land-use table; failing
        them all would get the gate switched off within a day."""
        from sync_v2_to_supabase import rows_with_retired_zones

        assert rows_with_retired_zones(conn, [_row(None, ["B2"])]) == []  # noqa: zone-codes (retired code on a row with no council)

    def test_ground_truth_is_actually_loaded_not_silently_empty(self, conn):
        """The failure this whole file guards against. If `lep_zone_coverage`
        came back empty, every assertion above except the first would still
        pass, and the gate would be a no-op in production."""
        from validate_zone_code_validity import load_ground_truth

        truth = load_ground_truth(conn.cursor())
        assert truth, "no land-use tables loaded — the gate would pass everything"
        assert sum(len(v) for v in truth.values()) > 50, (
            "suspiciously few zones loaded; the gate would be near-vacuous")


class TestItCannotWriteWithoutBeingAsked:
    def test_apply_is_required_and_dry_run_is_the_default(self):
        """A production write behind a flag, not behind a typed word. Checked on
        the source because actually running it exports ~48.8k rows from
        production on both ends."""
        src = (ROOT / "scripts" / "sync_v2_to_supabase.py").read_text(
            encoding="utf-8")
        assert '"--apply"' in src
        assert "if not args.apply:" in src
        assert "DRY RUN" in src

    def test_the_gate_runs_before_the_confirmation_prompt_and_before_any_update(self):
        """Order matters. A prompt asks whether the operator MEANT to run it; it
        cannot tell them the payload is wrong. The gate has to come first, and
        it has to exit rather than warn."""
        # Every anchor is the ASSIGNMENT, not the bare call. This assertion
        # failed twice against perfectly correct code before that: once because
        # a bare `index()` on the call text found `def sync_to_supabase(...)`
        # above main(), and once because the module docstring QUOTES the
        # confirmation prompt, putting "prompt" at line 27 — ahead of
        # everything. A source-text check that reads prose is measuring the
        # wrong file.
        src = (ROOT / "scripts" / "sync_v2_to_supabase.py").read_text(
            encoding="utf-8")
        gate = src.index("bad = rows_with_retired_zones(supa_conn, data)")
        prompt = src.index('confirm = input("Continue? (yes/no): ")')
        write = src.index("= sync_to_supabase(supa_conn, data)")
        assert gate < prompt < write, "the gate must precede the prompt and the write"
        assert "sys.exit(2)" in src[gate:prompt], "the gate warns instead of refusing"

    def test_help_does_not_touch_the_database(self):
        """`--help` must not open a production connection just to print usage."""
        done = subprocess.run(
            [sys.executable, "scripts/sync_v2_to_supabase.py", "--help"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        assert done.returncode == 0, done.stderr[-1500:]
        assert "--apply" in done.stdout
