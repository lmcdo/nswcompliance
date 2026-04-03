"""
Root conftest.py — provides fixtures for integration test scripts that were
written as scripts (parameterised functions) but discovered by pytest.
"""

import json
import os
import pytest
from pathlib import Path
from typing import Dict

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "test_addresses.json"

# ---------------------------------------------------------------------------
# test_address_validation.py — test_addr + report
# ---------------------------------------------------------------------------

def _load_test_addresses():
    with open(FIXTURES_PATH) as f:
        return json.load(f)["addresses"]


class _ValidationReport:
    """Minimal stand-in so tests can call report.add() without importing the
    test module (which would cause collection-time side effects)."""
    def __init__(self):
        self.total_tests = 0
        self.passed = 0
        self.failed = 0
        self.results = []

    def add(self, result):
        self.total_tests += 1
        if getattr(result, "passed", False):
            self.passed += 1
        else:
            self.failed += 1
        self.results.append(result)


@pytest.fixture
def report():
    return _ValidationReport()


def pytest_generate_tests(metafunc):
    """Parametrize fixtures that differ per test file."""

    # test_address_validation.py
    if "test_addr" in metafunc.fixturenames:
        addresses = _load_test_addresses()
        metafunc.parametrize(
            "test_addr",
            addresses,
            ids=[a["address"][:50] for a in addresses],
        )

    # test_dev_type_filtering.py
    if "council_name" in metafunc.fixturenames:
        metafunc.parametrize("council_name", ["Marrickville", "Ashfield", "Leichhardt"])

    # test_leichhardt_thorough.py — address only (no description)
    if (
        "address" in metafunc.fixturenames
        and "description" not in metafunc.fixturenames
    ):
        addresses = [
            "180 Addison Road Marrickville 2204",
            "45 Denison Road Dulwich Hill 2203",
            "15 Alt Street Ashfield 2131",
            "1 The Parade Haberfield 2045",
            "10 Norton Street Leichhardt 2040",
            "25 Marion Street Leichhardt 2040",
            "150 Balmain Road Leichhardt 2040",
            "5 Lombard Street Glebe 2037",
        ]
        metafunc.parametrize("address", addresses)

    # test_real_user_flow_with_pp.py — paired address + description
    if (
        "address" in metafunc.fixturenames
        and "description" in metafunc.fixturenames
    ):
        cases = [
            ("10 Norton Street, Leichhardt NSW 2040", "Commercial/retail in Norton St precinct"),
            ("45 Terry Street, Rozelle NSW 2039", "Residential in Rozelle"),
            ("25 Flood Street, Leichhardt NSW 2040", "Residential near Norton Street"),
            ("100 Stanmore Road, Stanmore NSW 2048", "Main road property in Stanmore"),
            ("52 Norton Street, Leichhardt NSW 2040", "Norton Street retail/commercial"),
            ("50 Liverpool Road, Ashfield NSW 2131", "Commercial area in Ashfield"),
            ("1 Metropolitan Road, Enmore NSW 2042", "Residential in Enmore"),
        ]
        metafunc.parametrize("address,description", cases)


# ---------------------------------------------------------------------------
# test_version_tracking.py — db cursor
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def cur():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set — skipping DB tests")

    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        pytest.skip("psycopg2 not installed")

    conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    cursor = conn.cursor()
    yield cursor
    cursor.close()
    conn.close()
