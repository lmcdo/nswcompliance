"""Guards for the council flood-study raster deployment (R2 startup-download wiring).

The same class of guard as tests/test_narclim_raster_deploy.py, which has existed
for the NARCliM rasters for months. It was never written for the flood studies,
and the gap it would have caught was live on origin/main until 2026-08-24:

  Dockerfile.python set HAWKESBURY_RASTER_DIR and REDBANK_RASTER_DIR but NOT
  TWEED_RASTER_DIR or WOLLONGONG_RASTER_DIR. With the variable unset the two
  sides fall back to DIFFERENT defaults —
    writer  scripts/download_tweed_wollongong_rasters.py -> /tmp/<study>_rasters
    reader  services/flood_truth.py                     -> data/flood_studies/<study>
  — and data/flood_studies is gitignored and never COPY'd into the image. So the
  container downloaded 1.6 GB on every cold start into two directories nothing
  read, and every Tweed/Wollongong 1% AEP answer came back "not assessed".

  It degraded honestly (PR #892 guarantees "not assessed", never "no") and
  _warn_on_absent_flood_studies() logged it at import — a log line nobody reads.
  That is precisely why this needs to be a test rather than a warning.

No network, no R2, no rasters on disk: these assert config contracts only.
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.flood_truth import FLOOD_STUDIES  # noqa: E402

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DOCKERFILE = os.path.join(REPO_ROOT, "Dockerfile.python")
FLOOD_TRUTH = os.path.join(REPO_ROOT, "services", "flood_truth.py")


def _dockerfile_text() -> str:
    with open(DOCKERFILE, encoding="utf-8") as fh:
        return fh.read()


def _dockerfile_env() -> dict[str, str]:
    """ENV KEY=VALUE pairs declared in Dockerfile.python."""
    return {
        m.group(1): m.group(2).strip()
        for m in re.finditer(r"^ENV\s+([A-Z0-9_]+)=(.+)$", _dockerfile_text(), re.M)
    }


def _reader_env_var(study_key: str) -> str:
    """The env var services/flood_truth.py reads for this study's directory."""
    with open(FLOOD_TRUTH, encoding="utf-8") as fh:
        text = fh.read()
    start = text.find("FLOOD_STUDIES: dict[str, dict] = {")
    assert start != -1, "FLOOD_STUDIES not found in services/flood_truth.py"
    block = text[start:text.find("\n}\n", start)]
    m = re.search(
        rf"['\"]{re.escape(study_key)}['\"]\s*:\s*\{{.*?os\.environ\.get\(\s*['\"](\w+)['\"]",
        block,
        re.S,
    )
    assert m, f"no os.environ.get(...) dir for study {study_key!r}"
    return m.group(1)


@pytest.mark.parametrize("study_key", sorted(FLOOD_STUDIES))
def test_every_declared_study_has_its_dir_pinned_in_the_image(study_key):
    """A study in FLOOD_STUDIES is a promise the service can answer for that area.

    If its directory env var is not pinned in the image, writer and reader fall
    back to different defaults and the promise cannot be kept.
    """
    env_var = _reader_env_var(study_key)
    declared = _dockerfile_env()
    assert env_var in declared, (
        f"FLOOD_STUDIES declares {study_key!r} but Dockerfile.python never sets "
        f"{env_var}. Unset, the download script writes to /tmp/{study_key}_rasters "
        f"while flood_truth.py reads data/flood_studies/{study_key}, which is not "
        f"in the image — so the study downloads on every boot and is never used. "
        f"Add: ENV {env_var}=/tmp/{study_key}_rasters"
    )


@pytest.mark.parametrize("study_key", sorted(FLOOD_STUDIES))
def test_pinned_dir_is_a_writable_runtime_path(study_key):
    """The pinned path must be somewhere the startup download can actually write.

    data/flood_studies is gitignored and Dockerfile.python does not COPY data/,
    so pinning a study there would reproduce the original defect with the
    variable merely looking set.
    """
    env_var = _reader_env_var(study_key)
    value = _dockerfile_env().get(env_var)
    if value is None:
        pytest.skip(f"{env_var} not set — reported by the pinning test, not here")
    assert value.startswith("/tmp/"), (
        f"{study_key}: pinned to {value!r}. The startup download needs a writable "
        f"runtime path; data/ is not copied into the image."
    )


def test_download_scripts_cover_every_declared_study():
    """Every declared study must be fetched by something the CMD actually runs.

    A study can be declared, its env var pinned, and still never arrive if no
    download script for it is invoked at startup.
    """
    dockerfile = _dockerfile_text()
    cmd = dockerfile[dockerfile.rfind("CMD "):]
    missing = [
        key for key in sorted(FLOOD_STUDIES)
        if key not in cmd.lower()
    ]
    assert not missing, (
        f"declared in FLOOD_STUDIES but no startup download names them: {missing}. "
        f"Either add a download script to the CMD or remove them from FLOOD_STUDIES "
        f"— services/flood_truth.py's own warning says exactly this."
    )
