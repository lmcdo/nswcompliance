"""Guard: every `from scripts.X import` in a monitor worker must be COPYd into
Dockerfile.monitors, or the container ModuleNotFounds at runtime.

This bug class bit the DCP review path live: extract_chapter imports
`scripts.verify_dcp_formatting` and `scripts.dcp_quality_report`, neither of which
was copied into the image, so the quarterly run crashed mid-extraction.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Worker scripts that run inside the Dockerfile.monitors image (via run_monitors).
WORKERS = [
    "scripts/dcp_extract_changed.py",
    "scripts/dcp_commit_approved.py",
    "scripts/r2_monitor.py",
    "scripts/dcp_watchdog.py",
    "scripts/run_monitors.py",
]


def _sibling_imports(src: str) -> set[str]:
    # `from scripts.X import ...` and `import scripts.X`
    mods = set(re.findall(r"from\s+scripts\.(\w+)\s+import", src))
    mods |= set(re.findall(r"import\s+scripts\.(\w+)\b", src))
    return mods


def test_every_sibling_import_is_copied_into_the_image():
    docker = (REPO / "Dockerfile.monitors").read_text(encoding="utf-8")
    missing = []
    for worker in WORKERS:
        path = REPO / worker
        if not path.exists():
            continue
        for mod in sorted(_sibling_imports(path.read_text(encoding="utf-8"))):
            if f"COPY scripts/{mod}.py" not in docker:
                missing.append(f"{worker} imports scripts.{mod} but Dockerfile.monitors does not COPY scripts/{mod}.py")
    assert not missing, "Missing COPY in Dockerfile.monitors:\n  " + "\n  ".join(missing)


def test_the_two_known_review_loop_deps_are_present():
    docker = (REPO / "Dockerfile.monitors").read_text(encoding="utf-8")
    assert "COPY scripts/verify_dcp_formatting.py" in docker
    assert "COPY scripts/dcp_quality_report.py" in docker


# ── Same bug class, second image: deploy/flyio-legislation-monitor ────────────
# That image is FLAT (`COPY x.py .`), so the imports are bare module names and
# the Dockerfile.monitors regex above cannot see them. It bit live: #504 added
# `refresh_runbook` as an import of legislation_monitor and never added the COPY,
# so the container ModuleNotFound'ed at import on every cycle from then on.
# run_loop.sh swallows a failed run (`|| echo "will retry next cycle"`), so the
# machine stayed `started` and silent — 67 days of it, confirmed by running the
# monitor on the live machine 2026-08-14.
FLY_DIR = REPO / "deploy" / "flyio-legislation-monitor"


def _flat_local_imports(src: str) -> set[str]:
    """Bare-module imports that resolve to a repo file — i.e. must be COPYd.

    Catches both halves of the try/except shim in legislation_monitor.py:
    `from scripts.refresh_runbook import X` and `from refresh_runbook import X`.
    """
    mods = set(re.findall(r"(?m)^\s*from\s+(?:scripts\.)?(\w+)\s+import", src))
    mods |= set(re.findall(r"(?m)^\s*import\s+(?:scripts\.)?(\w+)\b", src))
    # local == a .py of that name exists in the fly dir or in scripts/
    return {m for m in mods
            if (FLY_DIR / f"{m}.py").exists() or (REPO / "scripts" / f"{m}.py").exists()}


def test_every_local_import_is_copied_into_the_fly_image():
    docker = (FLY_DIR / "Dockerfile").read_text(encoding="utf-8")
    copied = set(re.findall(r"(?m)^COPY\s+(\S+)\.py\s", docker))
    missing = []
    for name in sorted(copied):
        src_path = FLY_DIR / f"{name}.py"
        if not src_path.exists():
            missing.append(f"Dockerfile COPYs {name}.py but deploy/flyio-legislation-monitor/{name}.py does not exist")
            continue
        for mod in sorted(_flat_local_imports(src_path.read_text(encoding="utf-8"))):
            if mod in copied:
                continue
            missing.append(
                f"{name}.py imports '{mod}' but the Dockerfile does not COPY {mod}.py "
                f"— the container will ModuleNotFound at import"
            )
    assert not missing, "Fly legislation-monitor image is incomplete:\n  " + "\n  ".join(missing)


def test_the_known_fly_dep_is_present():
    """The specific regression: refresh_runbook must ship in the image."""
    docker = (FLY_DIR / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY refresh_runbook.py" in docker
    assert (FLY_DIR / "refresh_runbook.py").exists()
