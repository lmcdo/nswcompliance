"""Address-only site proofs against the REAL cadastre and NSW address register, read-only (DQ-143)."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

pytestmark = pytest.mark.database
_REAL = os.environ.get("PYTEST_REAL_DB") == "1"
SITES = {s["precinct_id"]: s for s in json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "site_chapters" / "address_sites.json").read_text(encoding="utf-8"))["sites"]}


@pytest.fixture
def ro_cursor():
    if not _REAL:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database -o addopts= <file>")
    import dq_db
    conn = dq_db.connect()
    try:
        yield conn.cursor()
    finally:
        conn.close()


def test_brighton_avenue_passes_and_no_neighbour_is_inside(ro_cursor):
    import site_addresses as sa
    r = sa.prove_address(ro_cursor, SITES["11.11"])
    assert r["ok"] and r["neighbours_checked"] > 0 and r["neighbours_inside"] == []


def test_a_number_missing_from_the_register_holds_the_site(ro_cursor):
    import site_addresses as sa
    r = sa.prove_address(ro_cursor, SITES["14H"])  # 101 Eton Road is not in the register
    assert not r["ok"] and r["missing_named"] == ["101"]
