"""The QA report's path and its commit binding, tested against real git history.

Two defects, both measured on 2026-08-10 while landing five PRs:

  * ONE SHARED PATH. `.qa_report.json` sat at the repo root, tracked, and every
    branch wrote it. The moment one PR merged, every other open PR touching it
    went CONFLICTING — and a conflicting PR gets NO GitHub Actions run at all,
    which on the PR page is indistinguishable from "still running". 8 of 16
    open PRs were dirty for that reason alone.

  * A BINDING NOTHING COULD SATISFY. qa_gate.py required `commit_hash` to
    appear in `git log --format=%h -5`. A squash merge destroys the commit the
    report names, so main permanently carried a hash present in no history and
    every branch cut from main inherited it and failed before doing anything
    wrong.

These tests use REAL repositories with REAL commits rather than a mocked
subprocess, because the whole check is a claim about ancestry and a mock would
only assert that the code calls the commands it calls. `origin/main` is created
with `update-ref`, which is what a remote-tracking ref actually is.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        f"{name}_under_test", _SCRIPTS / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def qrp():
    return _load("qa_report_path")


@pytest.fixture(scope="module")
def qg():
    return _load("qa_gate")


def _git_env() -> dict[str, str]:
    """The environment with git's per-invocation variables removed.

    A git hook exports GIT_DIR, GIT_INDEX_FILE and friends, and they OVERRIDE
    cwd. Without this, the `git init` below re-initialises THE REAL REPOSITORY
    and every command in this file then operates on it.

    That is not hypothetical. Running this file from .githooks/pre-push on
    2026-08-10 created branches `feature` and `other` in the working repo, added
    two empty commits to the branch under test, and moved its HEAD off it. The
    tests still reported a pass on the run that did it; the damage only surfaced
    on the NEXT run, as "a branch named 'other' already exists".

    tests/test_doc_claims.py and tests/test_sol_review_base.py already do this;
    this file was the one that did not.
    """
    return {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("GIT_")
        or k in ("GIT_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND")
    }


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=_git_env(),
    )
    assert proc.returncode == 0, f"git {' '.join(args)} failed: {proc.stderr}"
    return proc.stdout.strip()


def _commit(root: Path, message: str) -> str:
    """Make an empty commit and return its short hash."""
    _git(root, "commit", "--allow-empty", "-m", message, "--no-verify")
    return _git(root, "rev-parse", "--short", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> SimpleNamespace:
    """A repo with main, a simulated origin/main, and a feature branch.

    Shape::

        main:     M1 ── M2          (origin/main = M2)
                          \\
        feature:            F1      (HEAD)
        other:      O1              (a sibling branch, never merged)

    Returned as a namespace rather than a Path because Path defines __slots__
    and cannot carry the commit hashes the assertions need.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")

    # Prove the repo we just made is the repo git is talking to, BEFORE writing
    # a single commit. Scrubbing GIT_* above should make this impossible to
    # fail, which is exactly why it is asserted: the failure mode it guards is
    # silent, destructive, and lands on the developer's real branch.
    top = Path(_git(root, "rev-parse", "--show-toplevel")).resolve()
    assert top == root.resolve(), (
        f"refusing to continue: git resolved to {top}, not the temporary repo "
        f"{root.resolve()}. Something in the environment is pointing git at "
        f"another repository, and committing here would mutate it."
    )

    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "commit.gpgsign", "false")

    main_1 = _commit(root, "M1")
    main_2 = _commit(root, "M2")
    # A remote-tracking ref IS just a ref under refs/remotes/.
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")

    _git(root, "checkout", "-q", "-b", "other")
    other_1 = _commit(root, "O1")

    _git(root, "checkout", "-q", "main")
    _git(root, "checkout", "-q", "-b", "feature")
    feature_1 = _commit(root, "F1")

    return SimpleNamespace(
        path=root,
        main_1=main_1,
        main_2=main_2,
        other_1=other_1,
        feature_1=feature_1,
    )


# ── The binding: what it must catch ──────────────────────────────────────────


def test_a_branchs_own_commit_passes(qg, repo):
    """The case the old rule broke: a legitimate report on a fresh branch."""
    assert qg.check_commit_hash_binding(repo.feature_1, str(repo.path)) == []


def test_a_report_copied_from_another_branch_is_caught(qg, repo):
    """A hash from a sibling branch is not an ancestor of HEAD."""
    errors = qg.check_commit_hash_binding(repo.other_1, str(repo.path))
    assert errors, "a report copied from another branch was accepted"
    assert "not an ancestor of HEAD" in errors[0]


def test_a_hash_inherited_from_main_is_caught(qg, repo):
    """The stale-report case: the hash names a commit already on origin/main."""
    errors = qg.check_commit_hash_binding(repo.main_1, str(repo.path))
    assert errors, "a hash already on origin/main was accepted"
    assert "already on origin/main" in errors[0]


def test_a_hash_naming_no_commit_is_caught(qg, repo):
    errors = qg.check_commit_hash_binding("deadbee", str(repo.path))
    assert errors, "a hash naming no commit was accepted"
    assert "names no commit" in errors[0]


# ── The trap the old rule created ────────────────────────────────────────────


def test_the_old_five_commit_window_would_have_failed_this(qg, repo):
    """The regression this change exists to remove, pinned as a fact.

    A branch one commit deep, cut from a main whose last five commits do not
    include the branch's own commit, is exactly the state every PR was in after
    a squash merge. The report is legitimate; the old rule rejected it.
    """
    recent = _git(repo.path, "log", "--format=%h", "-5").split("\n")
    # A squash merge leaves main naming a commit that is in no history at all.
    inherited = "0" * 7
    assert inherited not in recent, "fixture does not reproduce the trap"
    assert qg.check_commit_hash_binding(repo.feature_1, str(repo.path)) == [], (
        "the branch's own commit must pass"
    )
    assert qg.check_commit_hash_binding(inherited, str(repo.path)), (
        "an inherited phantom hash must still be caught"
    )


def test_binding_is_independent_of_abbreviation_length(qg, repo):
    """Full SHA and short hash must agree.

    The old rule string-compared against `git log %h`, so it broke whenever git
    chose a different abbreviation length on either side. Ancestry resolves the
    SHA first, so length cannot matter.
    """
    full = _git(repo.path, "rev-parse", "HEAD")
    assert len(full) == 40
    assert qg.check_commit_hash_binding(full, str(repo.path)) == []
    assert qg.check_commit_hash_binding(full[:7], str(repo.path)) == []
    assert qg.check_commit_hash_binding(full[:12], str(repo.path)) == []


# ── When the question is unanswerable, it must not be answered "fail" ────────


def test_on_main_the_check_is_skipped_not_failed(qg, repo):
    """On main there are no branch-only commits, so there is nothing to bind.

    Failing here is what made every push to main red under the old rule, and a
    gate that can only ever be red teaches people that red means nothing.
    """
    _git(repo.path, "checkout", "-q", "main")
    assert qg.check_commit_hash_binding(repo.main_2, str(repo.path)) == []
    assert qg.check_commit_hash_binding(repo.main_1, str(repo.path)) == []


def test_missing_origin_main_does_not_block(qg, repo):
    """No remote-tracking ref means the question cannot be asked, not that it failed."""
    _git(repo.path, "update-ref", "-d", "refs/remotes/origin/main")
    assert qg.check_commit_hash_binding(repo.feature_1, str(repo.path)) == []


def test_unusable_git_does_not_block(qg, repo, monkeypatch):
    """Git absent is an infrastructure fact, not evidence about the report."""
    monkeypatch.setattr(qg, "_git_query", lambda *a, **k: (None, ""))
    assert qg.check_commit_hash_binding("deadbee", str(repo.path)) == []


def test_is_ancestor_never_reads_an_error_as_no(qg, repo, monkeypatch):
    """merge-base uses 0=yes, 1=no; anything else is an error, not a 'no'.

    Reading 128 as "not an ancestor" would turn a corrupt object or a bad ref
    into a confident, wrong rejection.
    """
    monkeypatch.setattr(qg, "_git_query", lambda *a, **k: (128, ""))
    assert qg._is_ancestor("abc", "HEAD", str(repo.path)) is None


# ── The path: no two branches may write the same file ────────────────────────


def test_slugs_are_flat_and_branch_unique(qrp):
    assert qrp.slugify_branch("fix/lot-area-mercator") == "fix__lot-area-mercator"
    assert qrp.slugify_branch("main") == "main"
    assert "/" not in qrp.slugify_branch("a/b/c")
    assert qrp.slugify_branch("feat/x") != qrp.slugify_branch("fix/x")


def test_slug_rejects_a_name_it_cannot_represent(qrp):
    for bad in ("", "   ", "...", "."):
        with pytest.raises(ValueError):
            qrp.slugify_branch(bad)


def test_two_branches_never_resolve_to_the_same_path(qrp, repo, monkeypatch):
    """The entire point of the change, asserted directly."""
    monkeypatch.setenv("QA_REPORT_BRANCH", "fix/alpha")
    first = qrp.target_path(repo.path)
    monkeypatch.setenv("QA_REPORT_BRANCH", "fix/beta")
    second = qrp.target_path(repo.path)
    assert first != second


def test_ci_detached_head_still_finds_the_branch(qrp, repo, monkeypatch):
    """A pull_request event checks out a detached merge commit.

    git cannot name the branch there; GITHUB_HEAD_REF is the only thing that
    can. Missing this would make CI fall through to another file and pass
    without saying it checked the wrong one.
    """
    monkeypatch.delenv("QA_REPORT_BRANCH", raising=False)
    # GitHub Actions SETS GITHUB_HEAD_REF, so without this the "git cannot name
    # the branch" half of the test is answered by the ambient CI environment and
    # passes for the wrong reason locally while failing on the runner. Caught by
    # CI on the first run of this file, 2026-08-10.
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    _git(repo.path, "checkout", "-q", "--detach", "HEAD")
    assert qrp.current_branch(repo.path) is None
    monkeypatch.setenv("GITHUB_HEAD_REF", "feat/from-ci")
    assert qrp.current_branch(repo.path) == "feat/from-ci"
    assert qrp.target_path(repo.path).name == "feat__from-ci.json"


def test_resolution_order_is_explicit_first(qrp, repo, monkeypatch):
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    monkeypatch.setenv("QA_REPORT_BRANCH", "feature")

    branch_report = qrp.target_path(repo.path)
    branch_report.parent.mkdir(parents=True, exist_ok=True)
    branch_report.write_text("{}", encoding="utf-8")
    legacy = repo.path / qrp.LEGACY_PATH
    legacy.write_text("{}", encoding="utf-8")
    override = repo.path / "elsewhere.json"
    override.write_text("{}", encoding="utf-8")

    assert qrp.resolve(repo.path, str(override)) == override
    monkeypatch.setenv("QA_REPORT_PATH", "elsewhere.json")
    assert qrp.resolve(repo.path) == override
    monkeypatch.delenv("QA_REPORT_PATH")
    assert qrp.resolve(repo.path) == branch_report
    branch_report.unlink()
    assert qrp.resolve(repo.path) == legacy


def test_a_branch_cut_before_the_move_still_gets_checked(qrp, repo, monkeypatch):
    """The legacy fallback exists so an unmigrated branch is not silently unenforced.

    CI treats an absent report as a warning and exit 0. If resolution simply
    stopped at the new path, every one of the ~240 branches carrying the old
    root file would have gone green while checking nothing.
    """
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    monkeypatch.setenv("QA_REPORT_BRANCH", "feature")
    legacy = repo.path / qrp.LEGACY_PATH
    legacy.write_text('{"tier": "minor"}', encoding="utf-8")
    assert qrp.resolve(repo.path) == legacy


def test_no_report_anywhere_resolves_to_none(qrp, repo, monkeypatch):
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    monkeypatch.setenv("QA_REPORT_BRANCH", "feature")
    assert qrp.resolve(repo.path) is None


def test_migrate_moves_the_legacy_file_and_is_idempotent(qrp, repo, monkeypatch):
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    monkeypatch.setenv("QA_REPORT_BRANCH", "feature")
    legacy = repo.path / qrp.LEGACY_PATH
    legacy.write_text('{"tier": "standard"}', encoding="utf-8")

    dest, message = qrp.migrate(repo.path)
    assert dest is not None and dest.is_file()
    assert not legacy.exists(), "the legacy file must be gone, not copied"
    assert json.loads(dest.read_text(encoding="utf-8"))["tier"] == "standard"
    assert "moved" in message

    again, message = qrp.migrate(repo.path)
    assert again == dest and "already migrated" in message


def test_discovery_refuses_to_guess_between_two_candidates(qrp, repo, monkeypatch):
    """Ambiguity must resolve to None, not to an arbitrary file."""
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
    monkeypatch.delenv("QA_REPORT_BRANCH", raising=False)
    reports = repo.path / qrp.REPORT_DIR
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "one.json").write_text("{}", encoding="utf-8")
    (reports / "two.json").write_text("{}", encoding="utf-8")
    _git(repo.path, "add", "-A", ".qa")
    _commit(repo.path, "two reports")
    _git(repo.path, "checkout", "-q", "--detach", "HEAD")
    assert qrp._discovered(repo.path) is None
