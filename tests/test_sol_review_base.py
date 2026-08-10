"""The Sol cross-review must read the NEW commits, not the whole branch.

WHY THIS EXISTS
---------------
On 2026-08-10 the gate blocked one branch four times in a row. Every finding
checked out as real, so the reviewer was not the problem. The harness was: it
passed the merge-base with main as the review base, so each push re-read the
entire branch — 18 files, 2,500 lines, 175 KB. A model reading that much does
not return the same subset twice, so each run surfaced a different sample of
findings from an unchanged pool, including files last touched days earlier that
earlier runs had said nothing about. Fixing everything in run N did nothing to
shrink what run N+1 could find, and each fix made the diff bigger.

A non-deterministic sampler is a reasonable reviewer and a bad gate: without a
shrinking input it has no fixed point.

These tests drive real git repositories rather than mocking, because the bug
was in what git actually returns for a given history — a mock would have
happily reproduced my wrong assumption. The first draft of the fix used the
last pushed commit unconditionally; that was WRONG and this suite is what the
wrongness looks like (test_main_merged_in_after_the_last_push).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "sol_review_base.sh"


def _bash() -> str | None:
    """Git Bash specifically, not whatever `bash` PATH happens to resolve to.

    On Windows a bare "bash" can resolve to the WSL shim in System32, which
    cannot open a C:/... path and exits 127 with "No such file or directory" —
    a failure indistinguishable from a missing script. It cost twenty minutes
    here. Prefer the Git for Windows shell, which is what the hook runs under.
    """
    for candidate in (r"C:/Program Files/Git/bin/bash.exe",
                      r"C:/Program Files/Git/usr/bin/bash.exe"):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if found and "System32" not in found:
        return found
    return None


BASH = _bash()

pytestmark = pytest.mark.skipif(
    not SCRIPT.exists() or BASH is None,
    reason="sol_review_base.sh or a non-WSL bash is unavailable here",
)


def _clean_env() -> dict:
    """Environment with git's own variables stripped.

    These tests build throwaway repositories in tmp_path. When pytest is
    invoked FROM a git hook — which is exactly when this suite matters most,
    because the pre-push hook runs it — git exports GIT_DIR, GIT_INDEX_FILE and
    GIT_WORK_TREE pointing at the REAL repository. Every `git` call below would
    then operate on this repo instead of the temp one: the fixture blew up on
    the first push, and a subtler version could have quietly asserted against
    the wrong history and passed. Inherited state is not test isolation.
    """
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def sh(cwd: Path, *args: str) -> str:
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=_clean_env())
    if p.returncode != 0:
        raise AssertionError(f"{' '.join(args)} failed in {cwd}:\n{p.stderr}")
    return p.stdout.strip()


def assert_isolated(repo: Path) -> None:
    """Refuse to mutate anything that is not a throwaway repository.

    This is not paranoia, it is a post-mortem. Before _clean_env existed, this
    suite ran under the pre-push hook with git's GIT_DIR exported, so every
    command below addressed the REAL repository from a temp working directory:
    `git add -A` staged the whole repo as deleted, `git commit` landed a junk
    commit named "add base.txt" on the branch, and `git init` + `git config`
    rewrote the shared .git/config — setting core.bare=true, which broke
    `git status` in every worktree at once.

    _clean_env fixes the cause. This checks the consequence, so that if the
    guard is ever removed or bypassed the suite fails on its first mutation
    instead of quietly wrecking the checkout it is running inside.
    """
    git_dir = subprocess.run(["git", "rev-parse", "--absolute-git-dir"], cwd=repo,
                             capture_output=True, text=True, env=_clean_env()).stdout.strip()
    resolved = Path(git_dir).resolve()
    assert repo.resolve() in resolved.parents or resolved.is_relative_to(repo.resolve()), (
        f"REFUSING TO MUTATE: {repo} resolves to git dir {resolved}, which is "
        f"outside the temp repository. The git environment has leaked — see "
        f"_clean_env. Stopping before anything is written."
    )


def commit(repo: Path, name: str, body: str = "x") -> str:
    assert_isolated(repo)
    (repo / name).write_text(body, encoding="utf-8")
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "-c", "user.email=t@t", "-c", "user.name=t",
       "commit", "-q", "-m", f"add {name}")
    return sh(repo, "git", "rev-parse", "HEAD")


def base_for(repo: Path) -> str:
    """What the hook would choose, invoked exactly as the hook invokes it."""
    dup = sh(repo, "git", "merge-base", "origin/main", "HEAD")
    p = subprocess.run([BASH, SCRIPT.as_posix(), dup], cwd=repo, capture_output=True,
                       text=True, env=_clean_env())
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A branch off main, pushed once, in a real clone with a real upstream."""
    origin = tmp_path / "origin"
    origin.mkdir()
    sh(origin, "git", "init", "-q", "-b", "main")
    commit(origin, "base.txt")
    sh(origin, "git", "config", "receive.denyCurrentBranch", "ignore")

    work = tmp_path / "work"
    sh(tmp_path, "git", "clone", "-q", str(origin), str(work))
    sh(work, "git", "checkout", "-q", "-b", "feat")
    commit(work, "feat1.txt")
    sh(work, "git", "push", "-q", "-u", "origin", "feat")
    return work


def test_ordinary_case_reviews_only_commits_since_the_last_push(repo: Path):
    """Push, add commits, push again -> the base is the last push.

    This is the case the whole fix exists for. If it regresses, the review
    silently goes back to re-reading the entire branch every time.
    """
    pushed = sh(repo, "git", "rev-parse", "HEAD")
    commit(repo, "feat2.txt")
    commit(repo, "feat3.txt")

    assert base_for(repo) == pushed, (
        "base must be the last pushed commit, so only the new commits are read"
    )
    changed = sh(repo, "git", "diff", "--name-only", f"{base_for(repo)}...HEAD").split()
    assert sorted(changed) == ["feat2.txt", "feat3.txt"], (
        f"only the new work should be reviewed, got {changed}"
    )


def test_main_merged_in_after_the_last_push_falls_back_to_the_merge_base(repo: Path):
    """The case that made my first attempt at this fix wrong.

    Merging main into the branch after a push makes the last-pushed commit an
    ancestor of a pile of ALREADY-REVIEWED main commits. Using it as the base
    would hand the reviewer all of main's work again — measured at 66 files
    against the merge-base's 18 on the real branch. So the merge-base wins here.
    """
    origin = repo.parent / "origin"
    commit(origin, "main_new1.txt")
    commit(origin, "main_new2.txt")
    sh(repo, "git", "fetch", "-q", "origin")
    sh(repo, "git", "-c", "user.email=t@t", "-c", "user.name=t",
       "merge", "-q", "--no-ff", "-m", "merge main", "origin/main")
    commit(repo, "feat2.txt")

    chosen = base_for(repo)
    merge_base = sh(repo, "git", "merge-base", "origin/main", "HEAD")
    assert chosen == merge_base, (
        "after merging main, the last push is NOT the later boundary — using it "
        "would re-review every commit main brought in"
    )
    changed = sh(repo, "git", "diff", "--name-only", f"{chosen}...HEAD").split()
    assert "main_new1.txt" not in changed and "main_new2.txt" not in changed, (
        f"main's already-reviewed files must not be re-reviewed, got {changed}"
    )


def test_never_pushed_branch_reviews_the_whole_branch(repo: Path):
    """With no upstream there is no 'already reviewed' point, so everything is new."""
    # A branch created with `checkout -b` has no upstream of its own, which is
    # exactly the never-pushed state under test.
    sh(repo, "git", "checkout", "-q", "-b", "fresh")
    commit(repo, "fresh1.txt")
    assert subprocess.run(["git", "rev-parse", "--verify", "--quiet", "@{u}"],
                          cwd=repo, capture_output=True,
                          env=_clean_env()).returncode != 0, \
        "fixture is wrong: this branch should have no upstream"

    assert base_for(repo) == sh(repo, "git", "merge-base", "origin/main", "HEAD")


def test_a_rebased_branch_ignores_its_stale_upstream(repo: Path):
    """After a rebase the pushed commit is no longer on this history.

    Its sha still resolves, so a naive check would use it and produce a diff
    against a commit that shares no ancestry — nonsense. It must be ignored.
    """
    commit(repo, "feat2.txt")
    origin = repo.parent / "origin"
    commit(origin, "main_new.txt")
    sh(repo, "git", "fetch", "-q", "origin")
    sh(repo, "git", "-c", "user.email=t@t", "-c", "user.name=t",
       "rebase", "-q", "origin/main")

    upstream = sh(repo, "git", "rev-parse", "@{u}")
    assert base_for(repo) != upstream, (
        "a stale upstream that is not an ancestor of HEAD must not be the base"
    )
    assert base_for(repo) == sh(repo, "git", "merge-base", "origin/main", "HEAD")


def test_the_script_never_fails_open_to_empty(repo: Path):
    """A base of "" would make the hook diff against nothing. Print the fallback."""
    p = subprocess.run([BASH, SCRIPT.as_posix()], cwd=repo, capture_output=True,
                       text=True, env=_clean_env())
    assert p.returncode == 0
    assert p.stdout.strip(), "must print a usable ref even with no argument"
