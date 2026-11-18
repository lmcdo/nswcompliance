"""Real-layer check of the saved state map copies. Opt in: PYTEST_REAL_HTTP=1 pytest -o addopts= -m integration tests/test_download_map_layers_real.py

(tests/conftest_mocks.py replaces requests with a stand-in unless PYTEST_REAL_HTTP=1, so without it this skips rather than passes.)
Compares the live layer with our saved copy: a difference means the state changed the map and the copy needs a refresh.
"""
import gzip
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "lmr_area"))
import download_map_layers as dl  # noqa: E402

MAPS = REPO / "data" / "law" / "maps"
SMALL = ["accelerated_tod", "lmr_exclusion", "hn_catchment", "georges_catchment", "coastal_vuln", "airport_noise"]


@pytest.mark.integration
@pytest.mark.parametrize("name", SMALL)
def test_our_saved_copy_matches_the_live_layer(name):
    if os.environ.get("PYTEST_REAL_HTTP") != "1":
        pytest.skip("needs PYTEST_REAL_HTTP=1 (otherwise requests is a stand-in); not a pass")
    live = dl.fetch_layer(dl.LAYERS[name][0])
    if live is None:
        pytest.skip("the live service did not answer; not a pass")
    info = json.loads((MAPS / "manifest.json").read_text(encoding="utf-8"))["layers"][name]
    ours = [f for part in info["files"] for f in json.loads(gzip.decompress((MAPS / part["file"]).read_bytes()))["features"]]
    assert len(live["features"]) == len(ours), "the live layer changed size: refresh the copy"
    key = lambda f: json.dumps(f["geometry"], sort_keys=True)  # noqa: E731
    assert sorted(map(key, live["features"])) == sorted(map(key, ours)), "the live geometry changed: refresh the copy"
