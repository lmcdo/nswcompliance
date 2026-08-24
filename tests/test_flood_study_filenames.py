"""The filenames FLOOD_STUDIES reads must be the filenames the downloader writes.

Two in-repo constants describe the same files and nothing compared them:

* ``scripts/download_tweed_wollongong_rasters.py`` builds the R2 keys it fetches
  and writes to disk under those exact names.
* ``services/flood_truth.py::FLOOD_STUDIES`` builds the paths it later opens.

They drifted. R2 holds ``design/Wollongong_PMF_d_Max.asc`` and the config asked
for ``design/Wollongong_pmf_{type}_Max.asc`` — a CASE mismatch, verified against
the live bucket on 2026-08-24. On Windows, where this repo is developed, NTFS is
case-insensitive and the file opens. On the Linux container it does not exist,
so Wollongong's Probable Maximum Flood grid could never be read in production.

Nothing caught it, and two things that look like they should have did not:

* ``flood_study_raster_availability()`` checks the **1% AEP** file specifically
  and nothing else, so a study whose PMF is unreadable still reports PRESENT.
* the import-time ``_warn_on_absent_flood_studies()`` warning is built from that
  same 1%-only signal.

The failure is fail-SAFE at sample time — a missing grid appends to
``absent_studies`` and the verdict becomes "not assessed", never a false "no" —
so this is a capability declared and silently undeliverable rather than a wrong
answer. That is the #880 class this module's own docstring names.

This test is pure string comparison over two module-level constants: no network,
no database, no rasters on disk. It fails on the mismatch itself, which is the
only place the two definitions can be compared without a Linux container.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(relpath: str, name: str):
    spec = importlib.util.spec_from_file_location(name, _ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def downloader():
    return _load("scripts/download_tweed_wollongong_rasters.py", "_dl_tw")


@pytest.fixture(scope="module")
def studies():
    import sys
    sys.path.insert(0, str(_ROOT / "services"))
    return _load("services/flood_truth.py", "_flood_truth_names").FLOOD_STUDIES


def _expected_paths(cfg: dict) -> set[str]:
    """Every relative path this study's config will ever try to open.

    Both ``{type}`` expansions, not just the one ``has_depth`` selects: the
    downloader fetches d and h for these studies, so a drift in either is a
    drift, and pinning only the read side would let the unread half rot until
    something starts reading it.
    """
    out: set[str] = set()
    for group in ("design", "historical"):
        for template in (cfg.get(group) or {}).values():
            if "{type}" in template:
                out.update(template.format(type=t) for t in ("d", "h"))
            else:
                out.add(template)
    return out


@pytest.mark.parametrize("study_key", ["tweed", "wollongong"])
def test_config_filenames_match_what_the_downloader_writes(downloader, studies, study_key):
    """Case-sensitive, exact. A Linux container gets no second chance."""
    fetched = {
        key: set(files)
        for key, _prefix, _dir, files in downloader.STUDIES
    }
    assert study_key in fetched, (
        f"{study_key} is in FLOOD_STUDIES but download_tweed_wollongong_rasters.py "
        f"does not fetch it, so its rasters reach no container"
    )

    expected = _expected_paths(studies[study_key])
    missing = sorted(expected - fetched[study_key])
    assert not missing, (
        f"{study_key}: FLOOD_STUDIES will open {len(missing)} path(s) the downloader "
        f"never writes: {missing}. Case matters — the container is Linux and this "
        f"repo is developed on a case-insensitive filesystem."
    )


@pytest.mark.parametrize("study_key", ["tweed", "wollongong"])
def test_downloader_fetches_nothing_the_config_ignores(downloader, studies, study_key):
    """The other direction: bytes pulled on every cold start that nothing opens.

    Not a correctness bug, but it is the same waste #996 fixed — 1.6 GB per cold
    start into a directory nothing read — and it is invisible without this.
    """
    fetched = {
        key: set(files)
        for key, _prefix, _dir, files in downloader.STUDIES
    }
    expected = _expected_paths(studies[study_key])
    unread = sorted(fetched[study_key] - expected)
    assert not unread, (
        f"{study_key}: the downloader fetches {len(unread)} file(s) FLOOD_STUDIES "
        f"never opens: {unread}. Either read them or stop paying to move them."
    )
