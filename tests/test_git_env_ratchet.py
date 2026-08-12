"""No script may run git with an explicit cwd and an unscrubbed environment.

DQ-54. Git exports ``GIT_DIR`` and ``GIT_INDEX_FILE`` to its hooks, and they
**override cwd**. So a script that carefully passes ``cwd=<repo>`` and is then
invoked from a hook reads a DIFFERENT repository — exit 0, no warning, confident
wrong answer.

This is not theoretical in this repo. It has already caused two incidents:

* 2026-08-07 — ``tests/test_doc_claims.py``'s fixture ``git commit`` landed on
  the real worktree's branch and replaced its index. Recovered by SHA.
* 2026-08-12 — the reachability check added in #927 passed standalone and
  failed inside ``pre-push``, because pytest there inherited the hook's
  ``GIT_DIR``.

DQ-54 was logged on 2026-08-08 as prose: *"fix is one shared git_env() helper at
three call sites."* Four days later the same class produced incident two, and
the highest-consequence site — the one deciding which ``.env`` supplies
``DATABASE_URL`` — was still unscrubbed. A rule in a tracker is not enforcement.
This file is the enforcement.

WHAT THIS DOES **NOT** CATCH
----------------------------
It is a source scan, not a semantic one. A call assembled dynamically, or one
that reaches git through a wrapper this scan cannot follow, is invisible to it.
It pins the shape that actually recurred; it does not prove the class is empty.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

#: Passing no ``cwd`` means "the repo git was invoked from", and inheriting the
#: hook's GIT_DIR is then the CORRECT behaviour — these genuinely want it.
#: Listing a file here is a claim that it has no cwd= on any git call, and the
#: test below verifies that claim rather than trusting it.
_INHERITS_BY_DESIGN = {
    "lint_bracket_access.py",
    "lint_hardcoded_zone_codes.py",
    "liability_language_check.py",
    "pr_overlap_guard.py",
}

#: Modules that define the scrub itself, or a deliberate second copy of it.
_DEFINES_THE_HELPER = {"qa_report_path.py", "doc_claims.py"}


def _git_calls_with_cwd(tree: ast.AST) -> list[ast.Call]:
    """Every subprocess call that runs `git` AND pins a cwd."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "attr", None) or getattr(func, "id", None)
        if name not in ("run", "check_output", "Popen", "call", "check_call"):
            continue
        # First positional arg is the argv list; look for a literal "git".
        if not node.args:
            continue
        argv = node.args[0]
        if not isinstance(argv, (ast.List, ast.Tuple)):
            continue
        first = argv.elts[0] if argv.elts else None
        if not (isinstance(first, ast.Constant) and first.value == "git"):
            continue
        kwargs = {kw.arg for kw in node.keywords}
        if "cwd" in kwargs:
            found.append(node)
    return found


def _has_env(call: ast.Call) -> bool:
    return any(kw.arg == "env" for kw in call.keywords)


def _py_files() -> list[Path]:
    return sorted(p for p in _SCRIPTS.glob("*.py") if p.name not in _DEFINES_THE_HELPER)


@pytest.mark.parametrize("path", _py_files(), ids=lambda p: p.name)
def test_git_calls_that_pin_cwd_also_pin_env(path: Path):
    """cwd= without env= is the DQ-54 shape: it looks scoped and is not."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders = [c for c in _git_calls_with_cwd(tree) if not _has_env(c)]

    assert not offenders, (
        f"{path.name} runs git with cwd= but no env= at line(s) "
        f"{[c.lineno for c in offenders]}.\n"
        "A git hook exports GIT_DIR/GIT_INDEX_FILE and they OVERRIDE cwd, so "
        "this call can silently read a different repository.\n"
        "Fix: pass env=git_env() — `from qa_report_path import git_env`."
    )


@pytest.mark.parametrize(
    "name", sorted(_INHERITS_BY_DESIGN), ids=lambda n: n
)
def test_the_exemption_list_is_still_true(name: str):
    """An exemption is a claim, and claims rot.

    These four are exempt because they pass no ``cwd`` and genuinely want the
    hook's repository. If one later grows a ``cwd=``, the exemption silently
    becomes a licence for the exact defect — so verify it rather than trust it.
    """
    path = _SCRIPTS / name
    if not path.exists():
        pytest.skip(f"{name} no longer exists")

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    with_cwd = _git_calls_with_cwd(tree)

    assert not with_cwd, (
        f"{name} is on the inherits-by-design exemption list, but now runs git "
        f"with cwd= at line(s) {[c.lineno for c in with_cwd]}. Either drop the "
        "cwd or remove it from _INHERITS_BY_DESIGN and pass env=git_env()."
    )


def test_the_shared_helper_keeps_auth_variables():
    """git_env must scrub repo selection, NOT authentication.

    GIT_ASKPASS, GIT_SSH and GIT_SSH_COMMAND configure how git authenticates,
    not which repository it reads. Dropping them would break credential helpers
    and signed operations for no safety gain — and #927's local scrub did
    exactly that before this consolidation.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "qa_report_path_under_test", _SCRIPTS / "qa_report_path.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    import os

    for keep in ("GIT_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND"):
        os.environ[keep] = "sentinel"
    for drop in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY"):
        os.environ[drop] = "sentinel"
    try:
        env = mod.git_env()
        for keep in ("GIT_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND"):
            assert env.get(keep) == "sentinel", f"{keep} must be preserved"
        for drop in (
            "GIT_DIR",
            "GIT_INDEX_FILE",
            "GIT_WORK_TREE",
            "GIT_OBJECT_DIRECTORY",
        ):
            assert drop not in env, f"{drop} must be scrubbed"
    finally:
        for var in (
            "GIT_ASKPASS",
            "GIT_SSH",
            "GIT_SSH_COMMAND",
            "GIT_DIR",
            "GIT_INDEX_FILE",
            "GIT_WORK_TREE",
            "GIT_OBJECT_DIRECTORY",
        ):
            os.environ.pop(var, None)
