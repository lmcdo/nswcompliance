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


def test_scripts_invoked_as_subprocesses_are_copied_too():
    """The import scan above cannot see a sibling that is RUN rather than imported.

    check_council_completeness shells out to the two existing checkers instead of
    copying their logic, so they are runtime dependencies of the commit job with
    no `import` line to find them by. A missing one does not crash: _run_sibling
    returns 127 and the run degrades to a warning, which is the silence the whole
    check exists to remove. The list is derived from the source, so adding a third
    sibling without its COPY fails here rather than in production.
    """
    src = (REPO / "scripts" / "check_council_completeness.py").read_text(encoding="utf-8")
    called = set(re.findall(r"_run_sibling\(\s*[\"'](\w+\.py)[\"']", src))
    assert called, "no _run_sibling calls found -- has the call form changed?"
    docker = (REPO / "Dockerfile.monitors").read_text(encoding="utf-8")
    missing = [s for s in sorted(called) if f"COPY scripts/{s}" not in docker]
    assert not missing, (
        "check_council_completeness runs these but Dockerfile.monitors does not COPY them: "
        + ", ".join(missing)
    )


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


# ── Same bug class, third form: bare and function-level imports ───────────────
# 2026-09-25 03:01 UTC the dcp-extract cron failed all 22 chapters with
# "No module named 'httpx'": ai_extractor imports httpx/openai INSIDE a function
# and its siblings as bare names (`import page_coverage`), and the test above only
# reads `from scripts.X import`. Every import is now followed, transitively, from
# each worker; a local one must be COPYd, an outside one must be installed.

import sys  # noqa: E402

# Import name -> the distribution that provides it, where they differ.
_DIST = {"fitz": "pymupdf", "dotenv": "python-dotenv", "psycopg2": "psycopg2-binary",
         "bs4": "beautifulsoup4", "yaml": "pyyaml", "PIL": "pillow"}
# Local modules imported only on a path the container never takes, each wrapped:
# check_council_completeness reads qa_report_path only without DATABASE_URL;
# dcp_toc_parse imports tests.fixtures only under its __main__ self-check.
_DEV_ONLY = {"qa_report_path", "tests"}
# Top-level packages the image COPYs whole from the repo root.
_ROOT_PACKAGES = {"enrichment", "services", "scripts", "__future__"}
# Provided by another installed package (pydantic arrives with anthropic/fastapi).
_TRANSITIVE = {"pydantic", "starlette", "typing_extensions", "anyio", "botocore",
               "urllib3", "certifi", "charset_normalizer", "idna"}
_ANY_IMPORT = re.compile(r"(?m)^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+(?:\s*,\s*[\w.]+)*))")


def _imports(src: str) -> set[str]:
    out = set()
    for frm, imp in _ANY_IMPORT.findall(src):
        for name in ([frm] if frm else [n.strip() for n in imp.split(",")]):
            if name.startswith("scripts."):
                name = name.split(".", 1)[1]
            out.add(name.split(".")[0])
    return out


def _closure():
    """(local script modules, outside top-level modules) reachable from WORKERS."""
    local, outside, todo = set(), set(), [Path(w).stem for w in WORKERS]
    while todo:
        mod = todo.pop()
        path = REPO / "scripts" / f"{mod}.py"
        if mod in local or not path.exists():
            continue
        local.add(mod)
        for name in _imports(path.read_text(encoding="utf-8")):
            if name in _DEV_ONLY or name in _ROOT_PACKAGES:
                continue
            if (REPO / "scripts" / f"{name}.py").exists():
                todo.append(name)
            elif (REPO / "scripts" / name).is_dir():
                local.add(name + "/")
            elif name not in sys.stdlib_module_names:
                outside.add(name)
    return local, outside


def test_every_local_module_a_worker_reaches_is_copied():
    docker = (REPO / "Dockerfile.monitors").read_text(encoding="utf-8")
    local, _ = _closure()
    missing = sorted(m for m in local if (f"COPY scripts/{m} " if m.endswith("/") else f"COPY scripts/{m}.py") not in docker)
    assert not missing, "Dockerfile.monitors does not COPY: " + ", ".join(missing)


def test_every_services_module_a_worker_reaches_is_copied():
    """verify_extraction_fidelity (behind the fidelity gate) imports
    services.extracted_data_integrity; the scan above skips services/."""
    docker = (REPO / "Dockerfile.monitors").read_text(encoding="utf-8")
    local, _ = _closure()
    missing = set()
    for mod in local:
        path = REPO / "scripts" / f"{mod}.py"
        if path.exists():
            for svc in re.findall(r"(?m)^\s*from\s+services\.(\w+)\s+import", path.read_text(encoding="utf-8")):
                if f"COPY services/{svc}.py" not in docker:
                    missing.add(svc)
    assert not missing, "Dockerfile.monitors does not COPY services/: " + ", ".join(sorted(missing))


def test_every_outside_package_a_worker_reaches_is_installed():
    reqs = (REPO / "scripts" / "requirements-monitor.txt").read_text(encoding="utf-8").lower()
    installed = set(re.findall(r"(?m)^([a-z0-9_.\-]+)", reqs))
    _, outside = _closure()
    missing = sorted(m for m in outside - _TRANSITIVE
                     if _DIST.get(m, m).lower().replace("_", "-") not in
                     {i.replace("_", "-") for i in installed})
    assert not missing, "scripts/requirements-monitor.txt does not install: " + ", ".join(missing)
