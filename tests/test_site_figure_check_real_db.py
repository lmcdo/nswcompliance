"""The chapter's own site map against REAL parcels, read-only (DQ-143). Known-right and known-wrong."""
import json
import os
import sys
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

pytestmark = pytest.mark.database
_REAL = os.environ.get("PYTEST_REAL_DB") == "1"
ADDR = {s["precinct_id"]: s for s in json.loads(
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


def _pdf(site):
    return urllib.request.urlopen(urllib.request.Request(site["pdf"], headers={"User-Agent": "Mozilla/5.0"}),
                                  timeout=60).read()


def test_milton_street_parcels_match_the_chapter_map(ro_cursor):
    import site_figure_check as f
    s = ADDR["11.1"]
    m = f.map_check(ro_cursor, _pdf(s), s["figure"], ["//SP108628", "2//DP1321055"])
    assert m["status"] == "pass" and m["iou"] >= 0.9


def test_one_milton_parcel_alone_does_not_match(ro_cursor):
    import site_figure_check as f
    s = ADDR["11.1"]
    outline = f.figure_outline(_pdf(s), s["figure"])
    iou, _ = f.shape_iou(outline, f._mga_union(ro_cursor, ["//SP108628"]))
    assert iou < f.MATCH
