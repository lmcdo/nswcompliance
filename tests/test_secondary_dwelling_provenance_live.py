"""Provenance test: every served granny-flat path rule traces to the law in force.

prior-art-checked: reuse — the real-layer pattern of tests/test_drawdown_verify_real_db.py
(opt-in flags, scripts/dq_db.main_checkout() for the .env, explicit skip reason), and
scripts/provenance_check.py, the single implementation the Fly app also runs weekly.

For each housing_sepp_standards row with an approval_pathway, read from the REAL
database (what is actually served), this checks the whole chain:

    stored number  ->  stored quote  ->  the clause its legislation_url points to
                   ->  legislation.nsw.gov.au, current version

It fails, not skips, when the chain breaks. It skips only when not asked to run.
legislation.nsw.gov.au refuses Python's HTTP client from most networks, so here
the page is fetched with curl (the Fly app's IP is accepted with requests).

Run: PYTEST_REAL_DB=1 PYTEST_REAL_HTTP=1 pytest -m integration tests/test_secondary_dwelling_provenance_live.py -o addopts=
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL = os.environ.get("PYTEST_REAL_DB") == "1" and os.environ.get("PYTEST_REAL_HTTP") == "1"
if _REAL:
    load_dotenv(main_checkout() / ".env")

pytestmark = [pytest.mark.database, pytest.mark.integration]

import provenance_check as pc  # noqa: E402


def _curl_fetch(url: str) -> str:
    p = subprocess.run(["curl", "-s", "-L", "-m", "90", "-A", pc.HEADERS["User-Agent"],
                        "-w", "\n%{http_code}", url], capture_output=True)
    page, _, code = p.stdout.decode("utf-8", "replace").rpartition("\n")
    if code != "200":
        raise RuntimeError(f"HTTP {code}")
    return page


@pytest.mark.database
@pytest.mark.integration
def test_every_served_path_rule_traces_to_its_clause_in_the_law_in_force():
    if not _REAL:
        pytest.skip("Live provenance test. Run with PYTEST_REAL_DB=1 PYTEST_REAL_HTTP=1 "
                    "pytest -m integration " + __file__ + " -o addopts=")
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"],
                            options="-c statement_timeout=30000 -c default_transaction_read_only=on")
    try:
        rows = [r for r in pc.served_rows(conn)
                if r.get("development_type") == "secondary_dwelling" and r.get("approval_pathway")]
    finally:
        conn.close()
    assert rows, "no approval-path rules are served: migration 084 not applied"
    traced, problems = pc.run(rows, fetch=_curl_fetch)
    print(f"\nprovenance: {traced}/{len(rows)} rules traced to their clause")
    assert not problems, "\n".join(problems)
