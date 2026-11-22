"""Real-database check of the re-quote plan (read only). Opt in:
PYTEST_REAL_DB=1 DATABASE_URL=... pytest tests/test_requote_controls_from_provisions_real_db.py -o addopts= -m database

conftest_mocks stubs psycopg2 by default, so the flag is required; without it the test skips (never passes). Nothing is written."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import requote_controls_from_provisions as r  # noqa: E402


@pytest.mark.database
def test_every_planned_quote_for_a_real_council_is_a_substring_of_its_current_rule_and_holds_the_number():
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("real database test: run with PYTEST_REAL_DB=1 DATABASE_URL=... -o addopts= -m database; skipped, not a pass")
    conn = r._connect(readonly=True)
    try:
        ctls, provs, others = r._load(conn.cursor(), "waverley")
    finally:
        conn.close()
    assert provs, "no current Waverley rules"
    planned, rejected = r.plan(ctls, provs, {}, others)
    by_id = {p["id"]: p for p in provs}
    for cid, p in planned.items():
        assert r.ws(p["quote"]) in r.ws(by_id[p["provision_id"]]["text"])
        assert r.numbers_of(p["ctl"]) <= set(r._NUM.findall(p["quote"]))
        assert not r.OBJECTIVE.match(p["quote"])
    assert len(planned) + len(rejected) == len(ctls)
