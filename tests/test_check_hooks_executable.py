"""Tests for scripts/check_hooks_executable.py."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "check_hooks_executable",
    Path(__file__).resolve().parents[1] / "scripts" / "check_hooks_executable.py",
)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

SHA = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def _line(mode: str, path: str) -> str:
    return f"{mode} {SHA} 0\t{path}"


def test_all_executable_passes():
    out = "\n".join(_line("100755", f".githooks/{h}") for h in ("pre-commit", "pre-push"))
    assert mod.non_executable(out) == []


def test_non_executable_hook_is_reported():
    out = "\n".join([_line("100755", ".githooks/pre-commit"), _line("100644", ".githooks/pre-push")])
    assert mod.non_executable(out) == [".githooks/pre-push"]


def test_paths_outside_hook_dir_ignored():
    assert mod.non_executable(_line("100644", "scripts/x.py")) == []


def test_empty_output_reports_nothing():
    assert mod.non_executable("") == []
