# prior-art-checked: scripts/ has check_* gates and rules_per_address.py, none builds a file-level import graph from deploy entry points.
"""Classify every source file as served / scheduled / ci / unreached, by import graph.

Code-quality review gate G1 (see docs/qa/review-protocol.md). The live set is a machine
output so that no reviewer can call bad code "tooling" by hand.

Entry points are read from the deploy config itself, never typed here:
  served    - Dockerfile CMD uvicorn app, every file under frontend-nextjs/app/, and any
              .py file a reached TS/py file names in a string literal (spawned scripts).
  scheduled - railway*.toml startCommand, run_monitors.MONITORS commands, workflows with
              `schedule:`.
  ci        - workflows without `schedule:` (gates).
A file reached from several classes gets the first in that order.

Limits (stated in the output header, not hidden): dynamic imports by computed name are
not followed; a TS import of a non-relative package is ignored (node_modules).

Usage: python scripts/qa_live_files.py [--out docs/qa/quality-baseline-<date>/live_files.tsv]
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FE = ROOT / "frontend-nextjs"
PY_SEARCH = [ROOT, ROOT / "scripts", ROOT / "services", ROOT / "src", ROOT / "enrichment"]
TS_EXT = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]
CLASSES = ["served", "scheduled", "ci"]

PY_CMD_RE = re.compile(r"python3?\s+(?:-m\s+([\w.]+)|([\w./-]+\.py))")
PY_LITERAL_RE = re.compile(r"""['"]([\w./-]*?[\w-]+\.py)['"]""")
TS_IMPORT_RE = re.compile(
    r"""(?:import|export)\s[^'"]*?from\s*['"]([^'"]+)['"]|import\(\s*['"]([^'"]+)['"]\s*\)|require\(\s*['"]([^'"]+)['"]\s*\)|^\s*import\s+['"]([^'"]+)['"]""",
    re.M,
)


def tracked_files() -> list[Path]:
    """All git-tracked source files (py + ts family), so untracked junk is never scored."""
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    keep = {".py", *TS_EXT}
    return [ROOT / p for p in out.stdout.splitlines() if Path(p).suffix in keep and "node_modules" not in p]


def py_from_cmd(text: str) -> list[Path]:
    """Python files named by `python x.py` / `python -m a.b` / `uvicorn a.b:app` in a command."""
    found = []
    for mod, path in PY_CMD_RE.findall(text):
        if path:
            found.append(ROOT / path)
        elif mod and mod not in {"pytest", "pip", "uvicorn"}:
            found.append(ROOT / (mod.replace(".", "/") + ".py"))
    for app in re.findall(r"uvicorn\s+([\w.]+):", text):
        found.append(ROOT / (app.replace(".", "/") + ".py"))
    return found


def entry_points() -> dict[str, list[Path]]:
    """Entry files per class, read from Dockerfiles, railway tomls, run_monitors, workflows."""
    eps: dict[str, list[Path]] = {c: [] for c in CLASSES}
    for df in ROOT.glob("Dockerfile*"):
        if df.suffix == ".dockerignore":
            continue
        for line in df.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("CMD"):
                cls = "served" if "uvicorn" in line else "scheduled"
                eps[cls] += py_from_cmd(line.replace('", "', " "))
    for toml in ROOT.glob("railway*.toml"):
        for m in re.findall(r'startCommand\s*=\s*"([^"]*)"', toml.read_text(encoding="utf-8")):
            eps["scheduled"] += py_from_cmd(m)
    rm = ROOT / "scripts" / "run_monitors.py"
    if rm.exists():
        tree = ast.parse(rm.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "MONITORS" for t in node.targets):
                for s in ast.walk(node.value):
                    if isinstance(s, ast.Constant) and isinstance(s.value, str) and s.value.endswith(".py"):
                        eps["scheduled"].append(ROOT / s.value)
    for wf in (ROOT / ".github" / "workflows").glob("*.y*ml"):
        text = wf.read_text(encoding="utf-8")
        cls = "scheduled" if re.search(r"^\s*schedule:", text, re.M) else "ci"
        eps[cls] += py_from_cmd(text)
    app = FE / "app"
    eps["served"] += [p for p in app.rglob("*") if p.suffix in TS_EXT and "node_modules" not in p.parts]
    for c in eps:
        eps[c] = sorted({p.resolve() for p in eps[c] if p.exists()})
    return eps


def resolve_py(mod: str, level: int, here: Path) -> list[Path]:
    """Files for an import. Searches the file's own dir plus the sys.path dirs the code inserts."""
    if level:
        base = here.parent
        for _ in range(level - 1):
            base = base.parent
        roots = [base]
    else:
        roots = [here.parent, *PY_SEARCH]
    parts = mod.split(".") if mod else []
    for r in roots:
        out = []
        for i in range(1, len(parts) + 1):  # each package on the way down, then the module
            stem = r.joinpath(*parts[:i])
            if (stem / "__init__.py").is_file():
                out.append(stem / "__init__.py")
            elif stem.with_suffix(".py").is_file():
                out.append(stem.with_suffix(".py"))
                break
            else:
                break
        if out:
            return out
    return []


def py_edges(path: Path) -> list[Path]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out: list[Path] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out += resolve_py(a.name, 0, path)
        elif isinstance(node, ast.ImportFrom):
            out += resolve_py(node.module or "", node.level, path)
            for a in node.names:  # `from pkg import submodule`
                sub = f"{node.module}.{a.name}" if node.module else a.name
                out += resolve_py(sub, node.level, path)
    return out + literal_py(text, path)


def literal_py(text: str, here: Path) -> list[Path]:
    """`.py` names inside string literals = spawned scripts (subprocess, Next spawn)."""
    out = []
    for name in PY_LITERAL_RE.findall(text):
        for base in [here.parent, ROOT, *PY_SEARCH]:
            p = base / name
            if p.is_file():
                out.append(p)
                break
    return out


def resolve_ts(spec: str, here: Path) -> Path | None:
    if spec.startswith("@/"):
        stem = FE / spec[2:]
    elif spec.startswith("."):
        stem = here.parent / spec
    else:
        return None
    cands = [stem] + [stem.with_name(stem.name + e) for e in TS_EXT] + [stem / ("index" + e) for e in TS_EXT]
    return next((c for c in cands if c.is_file()), None)


def ts_edges(path: Path) -> list[Path]:
    text = path.read_text(encoding="utf-8", errors="replace")
    out = []
    for groups in TS_IMPORT_RE.findall(text):
        spec = next(g for g in groups if g)
        r = resolve_ts(spec, path)
        if r:
            out.append(r)
    return out + literal_py(text, path)


def reach(starts: list[Path]) -> set[Path]:
    seen: set[Path] = set()
    stack = list(starts)
    while stack:
        p = stack.pop().resolve()
        if p in seen or not p.is_file() or "node_modules" in p.parts:
            continue
        seen.add(p)
        stack += py_edges(p) if p.suffix == ".py" else ts_edges(p)
    return seen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    eps = entry_points()
    cls_of: dict[Path, str] = {}
    for c in CLASSES:
        for p in reach(eps[c]):
            cls_of.setdefault(p, c)
    rows = sorted((cls_of.get(f.resolve(), "unreached"), f.resolve().relative_to(ROOT).as_posix())
                  for f in tracked_files())
    counts = {c: sum(1 for r in rows if r[0] == c) for c in [*CLASSES, "unreached"]}
    header = [
        f"# sha {sha}",
        "# entry points: " + ", ".join(f"{c}={len(eps[c])}" for c in CLASSES),
        "# limits: computed-name dynamic imports not followed; npm packages ignored",
        "# counts: " + ", ".join(f"{k}={v}" for k, v in counts.items()),
    ]
    text = "\n".join(header + [f"{c}\t{p}" for c, p in rows]) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print("\n".join(header))
    return 0


if __name__ == "__main__":
    sys.exit(main())
