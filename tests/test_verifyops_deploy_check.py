"""deployed_not_main and DCP_MONITOR_FORCE, on the real Dockerfile and real commits.

The commits are fixed history, so the answers cannot drift:
  732ef41b (#1444) -> 2caecd2e (#1453): #1453 changed scripts/verifyops_classify.py, which the image
      COPYs. Run 1 (2026-10-22) ran on 732ef41b after 2caecd2e had merged -> red.
  2caecd2e -> 54abc444 (#1451): no image file changed; Railway SKIPPED that deploy -> green.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_monitors  # noqa: E402
import verifyops_coverage as v  # noqa: E402

SHA_1444 = "732ef41b20da25fcc7b69023ec0c0b4e8878bf7e"
SHA_1453 = "2caecd2ea8a70f9529207236271093064db6cf18"
SHA_1451 = "54abc4440bc7ba45ce29a1ca4325b6a2192172f2"


def _have(sha: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", sha], cwd=ROOT, capture_output=True).returncode == 0


@pytest.fixture(scope="module")
def paths():
    return v.image_paths(v.DOCKERFILE.read_text(encoding="utf-8"))


def test_image_paths_are_the_copy_sources(paths):
    assert "scripts/r2_monitor.py" in paths and "scripts/verifyops_classify.py" in paths
    assert "./scripts/r2_monitor.py" not in paths  # the destination is not a source


@pytest.mark.skipif(not (_have(SHA_1444) and _have(SHA_1451)), reason="shallow clone")
def test_an_image_file_changed_after_the_deployed_sha_is_red(paths):
    assert v.deployed_not_main(SHA_1444, paths, main=SHA_1453) is True


@pytest.mark.skipif(not (_have(SHA_1453) and _have(SHA_1451)), reason="shallow clone")
def test_a_merge_touching_no_image_file_is_green(paths):
    assert v.deployed_not_main(SHA_1453, paths, main=SHA_1451) is False


def test_no_sha_unknown_sha_or_no_paths_is_red(paths):
    assert v.deployed_not_main(None, paths) is True
    assert v.deployed_not_main("", paths) is True
    assert v.deployed_not_main("0" * 40, paths, main=SHA_1451) is True
    assert v.deployed_not_main(SHA_1453, [], main=SHA_1453) is True  # same sha: only the guard says red


class _Cur:
    def __init__(self, row):
        self.row = row

    def execute(self, sql):
        self.sql = sql

    def fetchone(self):
        return self.row

    def close(self):
        pass


class _Conn:
    def __init__(self, row):
        self.row = row

    def cursor(self):
        return _Cur(self.row)


def test_deploy_keys_reads_the_latest_run(monkeypatch):
    monkeypatch.setattr(v, "deployed_not_main", lambda sha, paths: sha != "good")
    assert v.deploy_keys(_Conn(("bad",))) == ["*|*|deployed_not_main"]
    assert v.deploy_keys(_Conn(("good",))) == []
    assert v.deploy_keys(_Conn(None)) == []


@pytest.mark.parametrize("name,env,expect_force", [
    ("dcp-monitor", {"DCP_MONITOR_FORCE": "1"}, True),
    ("dcp-monitor", {"DCP_MONITOR_FORCE": " 1 "}, True),
    ("dcp-monitor", {"DCP_MONITOR_FORCE": "0"}, False),
    ("dcp-monitor", {"DCP_MONITOR_FORCE": "true"}, False),
    ("dcp-monitor", {}, False),
    ("dcp-extract", {"DCP_MONITOR_FORCE": "1"}, False),
])
def test_force_switch(name, env, expect_force):
    base = ["python", "scripts/r2_monitor.py"]
    out = run_monitors.monitor_cmd(name, base, env)
    assert (out[-1] == "--force") is expect_force
    assert base == ["python", "scripts/r2_monitor.py"]  # caller's list untouched


def test_copy_from_another_stage_is_not_a_repo_path():
    df = "COPY --from=build /app/x ./x\nCOPY scripts/a.py ./scripts/a.py\n"
    assert v.image_paths(df) == ["scripts/a.py"]
