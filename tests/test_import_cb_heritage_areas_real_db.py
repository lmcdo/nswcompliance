"""C-B chapter 4.3's seven HCAs against the REAL state layer and PDF (read-only)."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

pytestmark = pytest.mark.database


def test_seven_listed_seven_mapped():
    if os.environ.get("PYTEST_REAL_DB") != "1":
        pytest.skip("Real-source test. Run with: PYTEST_REAL_DB=1 pytest -m database -o addopts= <file>")
    import import_cb_heritage_areas as m
    checks, matched = m.prove(m.fetch_areas())
    assert all(checks.values()) and len(matched) == 7
