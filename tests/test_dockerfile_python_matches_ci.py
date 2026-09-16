"""An image that installs CI's test requirements must run CI's Python.

requirements-test.txt is validated by CI on the Python version in
.github/workflows/gates.yml. Dockerfile.maintenance installs the same file but
stayed on python:3.11-slim. When the 2026-09-14 dependency updates raised numpy
to >=2.5.3 (Requires-Python >=3.12), CI stayed green while every Railway deploy
of maintenance-security and maintenance-mutation failed at `pip install`. A
failed cron deploy is quiet: the jobs kept running the last image built before
the bump, so nothing alerted for three days.

prior-art-checked: tests/test_dockerfile_monitors_imports.py guards COPY lines
in Dockerfile.monitors; tests/test_railway_cron_drift.py guards cron schedules;
tests/test_flood_raster_deploy.py guards ENV in Dockerfile.python. None compares
a Dockerfile's Python version with CI's (grep 'python:3' and 'python-version'
across tests/ and scripts/, 2026-09-17).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED_REQUIREMENTS = "requirements-test.txt"


def ci_python_versions(workflow_text: str) -> set[str]:
    """Every `python-version:` value set by setup-python steps in a workflow."""
    return set(re.findall(r"python-version:\s*['\"]?(\d+\.\d+)", workflow_text))


def image_python_version(dockerfile_text: str) -> str | None:
    """X.Y from the first `FROM python:X.Y...` line, or None when the base is not a python image."""
    m = re.search(r"^FROM\s+python:(\d+\.\d+)", dockerfile_text, re.M)
    return m.group(1) if m else None


def installs_shared_requirements(dockerfile_text: str) -> bool:
    """True when a pip install in the image reads requirements-test.txt."""
    return re.search(r"-r\s+\S*" + re.escape(SHARED_REQUIREMENTS), dockerfile_text) is not None


def mismatches(ci_version: str, dockerfiles: dict[str, str]) -> list[str]:
    out = []
    for name, text in sorted(dockerfiles.items()):
        if not installs_shared_requirements(text):
            continue
        version = image_python_version(text)
        if version != ci_version:
            out.append(f"{name} installs {SHARED_REQUIREMENTS} on python {version}, but CI validates it on {ci_version}")
    return out


def _repo_dockerfiles() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in ROOT.glob("Dockerfile*") if p.is_file()}


def test_ci_uses_one_python_version():
    versions = ci_python_versions((ROOT / ".github" / "workflows" / "gates.yml").read_text(encoding="utf-8"))
    assert len(versions) == 1, f"gates.yml sets more than one python-version: {sorted(versions)}"


def test_images_installing_ci_requirements_use_ci_python():
    (ci_version,) = ci_python_versions((ROOT / ".github" / "workflows" / "gates.yml").read_text(encoding="utf-8"))
    dockerfiles = _repo_dockerfiles()
    in_scope = [n for n, t in dockerfiles.items() if installs_shared_requirements(t)]
    # Without this the test passes vacuously if the install line is ever reworded.
    assert "Dockerfile.maintenance" in in_scope, f"expected Dockerfile.maintenance to install {SHARED_REQUIREMENTS}"
    assert mismatches(ci_version, dockerfiles) == []


def test_the_2026_09_14_state_is_reported():
    """The confusable negative: the exact image that broke, next to CI's 3.12."""
    broken = "FROM python:3.11-slim\nRUN pip install --no-cache-dir \\\n    -r scripts/requirements-maintenance.txt \\\n    -r requirements-test.txt\n"
    out = mismatches("3.12", {"Dockerfile.maintenance": broken})
    assert len(out) == 1
    assert "3.11" in out[0] and "3.12" in out[0]


def test_an_image_not_installing_ci_requirements_is_out_of_scope():
    """Dockerfile.python installs services/requirements.txt; its version is not CI's contract."""
    other = "FROM python:3.11-slim\nRUN pip install --no-cache-dir -r requirements.txt\n"
    assert mismatches("3.12", {"Dockerfile.python": other}) == []


def test_a_non_python_base_installing_ci_requirements_is_reported():
    """A base image swap (e.g. to ubuntu) must not silently drop the check."""
    swapped = "FROM ubuntu:24.04\nRUN pip install -r requirements-test.txt\n"
    out = mismatches("3.12", {"Dockerfile.maintenance": swapped})
    assert len(out) == 1 and "python None" in out[0]
