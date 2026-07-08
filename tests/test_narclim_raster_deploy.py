"""Guards for the NARCliM raster deployment (R2 startup-download wiring).

No network/R2 — these assert the config contracts that keep the deployed
runtime and the code in sync:
  - the download script's file list matches climate_risk_raster.NARCLIM_FILES
    (drift here = a scenario the code queries but the deploy never downloads);
  - both the download destination and the raster reader honour NARCLIM_DIR,
    so the files land where the reader looks.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from services.climate_risk_raster import NARCLIM_FILES
import download_narclim_rasters as dl


def _manifest_filenames() -> set[str]:
    return {fname for scenarios in NARCLIM_FILES.values() for fname in scenarios.values()}


def test_download_list_matches_raster_manifest():
    """Every .nc the reader can request must be in the download list, and vice
    versa — no scenario the code queries but the deploy never fetches."""
    assert set(dl.NARCLIM_NC_FILES) == _manifest_filenames()


def test_download_list_has_no_duplicates():
    assert len(dl.NARCLIM_NC_FILES) == len(set(dl.NARCLIM_NC_FILES))


def test_dest_dir_honours_narclim_dir_env(monkeypatch):
    monkeypatch.setenv("NARCLIM_DIR", "/tmp/narclim-test-xyz")
    reloaded = importlib.reload(dl)
    try:
        assert str(reloaded.DEST_DIR) == os.path.normpath("/tmp/narclim-test-xyz") \
            or str(reloaded.DEST_DIR) == "/tmp/narclim-test-xyz"
    finally:
        monkeypatch.delenv("NARCLIM_DIR", raising=False)
        importlib.reload(dl)


def test_raster_reader_data_dir_honours_narclim_dir_env(monkeypatch):
    """climate_risk_raster.DATA_DIR must follow NARCLIM_DIR so it reads exactly
    where the download script wrote."""
    monkeypatch.setenv("NARCLIM_DIR", "/tmp/narclim-read-xyz")
    import services.climate_risk_raster as crr
    reloaded = importlib.reload(crr)
    try:
        assert str(reloaded.DATA_DIR).replace("\\", "/").endswith("narclim-read-xyz")
    finally:
        monkeypatch.delenv("NARCLIM_DIR", raising=False)
        importlib.reload(crr)


def test_download_uses_narclim_r2_prefix():
    assert dl.R2_PREFIX == "narclim"


def test_download_default_dest_is_writable_tmp():
    """Without NARCLIM_DIR the default must be a writable path (Railway /tmp),
    never a repo path that may be read-only in the container."""
    # Re-import with env unset to read the module-level default.
    os.environ.pop("NARCLIM_DIR", None)
    reloaded = importlib.reload(dl)
    assert str(reloaded.DEST_DIR).replace("\\", "/").startswith("/tmp")
