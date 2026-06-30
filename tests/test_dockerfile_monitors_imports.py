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
