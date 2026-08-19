"""The gate must refuse a report that CLAIMS a file git will never carry.

ORIGIN, 2026-08-19. Two merged PRs lost their only real file and passed every
check:

  * **#982** "A one-page brief for students testing the tool" merged one file —
    its own 46-line QA report. The 109-line brief was written to
    ``docs/outreach/student-brief.md``, matched ``docs/*`` in .gitignore, and
    never entered git. ``git add`` exited 0 and did nothing.
  * **#979** "The stylesheet the README always referenced" merged its report and
    ``docs/pitch/README.md``. ``docs/pitch/style.html`` matched the same rule and
    is now gone from disk as well as from git.

Both reports listed the missing path under ``files``. ``check_diff_coverage``
only ever asked "is a CHANGED file missing from the report?", never the reverse,
and it filters ``.md`` out of its substantive set — so a documentation-only
commit skipped it entirely. Nothing compared the report's claims against what
git actually held.

WHY THE RULE IS "GITIGNORED" AND NOT "UNTRACKED"
-----------------------------------------------
Measured across all 64 reports in the repo: a "claimed files must be tracked"
rule fires on 6 reports and hundreds of paths, nearly all legitimate — files
DELETED by the change, and scratch scripts sitting in the working tree. The
ignored rule fires on exactly 2, and both are the real losses above. An ignored
path is the precise signal because the claim can never become true: no sequence
of ``git add`` makes it so.

WHY THESE TESTS STRIP GIT_* FROM THE ENVIRONMENT
------------------------------------------------
Git hooks export ``GIT_DIR`` and ``GIT_INDEX_FILE`` and those OVERRIDE ``cwd``.
A previous test in this repo ran ``git init`` in a tmpdir, silently operated on
the REAL repository, and still passed. Every helper scrubs ``GIT_*`` and asserts
the toplevel really is the tmpdir before writing anything.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

_QA_GATE = Path(__file__).resolve().parents[1] / "scripts" / "qa_gate.py"


@pytest.fixture(scope="module")
def qg():
    spec = importlib.util.spec_from_file_location("qa_gate_claimed_files", _QA_GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _clean_env() -> dict:
    """Environment with every GIT_* variable removed. See module docstring."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=_clean_env(),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real, isolated git repo — verified isolated before anything is written."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "T")

    top = _git(r, "rev-parse", "--show-toplevel").stdout.strip()
    assert Path(top).resolve() == r.resolve(), (
        f"git is operating on {top!r}, not the tmpdir — GIT_* leaked into the env"
    )
    return r


def _write(repo: Path, rel: str, text: str = "x\n") -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# ── The defect itself ────────────────────────────────────────────────────────

def test_reconstructs_the_982_loss(qg, repo):
    """`docs/*` swallows a new subdirectory file; the report still claims it."""
    _write(repo, ".gitignore", "docs/*\n!docs/*.md\n")
    _write(repo, "docs/outreach/student-brief.md", "# Try to break this\n")

    errors = qg.check_claimed_files_reachable(
        ["docs/outreach/student-brief.md"], str(repo)
    )

    assert errors, (
        "a report claiming a gitignored file was accepted — this is the defect "
        "that lost the student brief in #982"
    )
    assert any("GITIGNORED" in e for e in errors)


def test_reconstructs_the_979_loss_even_though_the_file_is_gone(qg, repo):
    """The stylesheet is absent from disk as well as git.

    Existence on disk must NOT be a precondition. #979's file was lost entirely,
    and a check that only looked at files it could stat would have missed it.
    """
    _write(repo, ".gitignore", "docs/*\n!docs/*.md\n")
    # deliberately do NOT create docs/pitch/style.html

    errors = qg.check_claimed_files_reachable(["docs/pitch/style.html"], str(repo))

    assert errors, "a claimed path that is ignored AND absent was accepted"


def test_names_the_pattern_that_did_it(qg, repo):
    """A rule you cannot find is a rule you cannot fix."""
    _write(repo, ".gitignore", "# a comment\ndocs/*\n")
    _write(repo, "docs/sub/thing.html")

    errors = qg.check_claimed_files_reachable(["docs/sub/thing.html"], str(repo))

    assert errors
    assert "docs/*" in errors[0], f"pattern not named in: {errors[0]!r}"


def test_a_negation_clears_it(qg, repo):
    """The fix must actually be accepted, or the check is unactionable."""
    _write(repo, ".gitignore", "docs/*\n!docs/outreach/\n!docs/outreach/**\n")
    _write(repo, "docs/outreach/student-brief.md")

    errors = qg.check_claimed_files_reachable(
        ["docs/outreach/student-brief.md"], str(repo)
    )

    assert errors == [], f"the documented fix is still refused: {errors}"


# ── Must stay silent: everything the broad rule got wrong ────────────────────

def test_silent_on_a_file_deleted_by_the_change(qg, repo):
    """A deletion is correctly claimed and correctly absent afterwards.

    Measured on the real repo, chore__delete-unreached-zone-surfaces.json claims
    14 such paths. A "must be tracked" rule fails all 14.
    """
    _write(repo, ".gitignore", "docs/*\n")

    errors = qg.check_claimed_files_reachable(
        ["frontend-nextjs/store/index.ts"], str(repo)
    )

    assert errors == [], f"a deleted file was flagged: {errors}"


def test_silent_on_an_untracked_scratch_file(qg, repo):
    """Working-tree scratch is not the defect.

    fix__dates-currency-provenance.json claims several hundred scripts/ paths
    that are untracked but perfectly addable.
    """
    _write(repo, "scripts/check_setbacks.py")

    errors = qg.check_claimed_files_reachable(["scripts/check_setbacks.py"], str(repo))

    assert errors == [], f"an addable untracked file was flagged: {errors}"


def test_silent_on_dot_prefixed_local_markers(qg, repo):
    """Reports legitimately mention ignored local markers.

    .claude/.pre-impl-done.json and .qa_report.json are both ignored and both
    named by real reports. Dot-prefixed reuses the module's own convention for
    non-substantive paths.
    """
    _write(repo, ".gitignore", ".claude/\n.qa_report.json\n")
    _write(repo, ".claude/.pre-impl-done.json", "{}\n")
    _write(repo, ".qa_report.json", "{}\n")

    errors = qg.check_claimed_files_reachable(
        [".claude/.pre-impl-done.json", ".qa_report.json"], str(repo)
    )

    assert errors == [], f"a local marker was flagged: {errors}"


def test_silent_on_a_tracked_file_that_also_matches_a_pattern(qg, repo):
    """Tracked beats ignored, and the check must inherit that.

    docs/pitch/README.md sits under `docs/*` yet is tracked, so git does not
    call it ignored. #979 could modify it while silently dropping its new
    sibling — which is exactly why the bug was so easy to miss.
    """
    _write(repo, "docs/pitch/README.md", "# pitch\n")
    _git(repo, "add", "-f", "docs/pitch/README.md")
    _git(repo, "-c", "commit.gpgsign=false", "commit", "-q", "-m", "add readme")
    _write(repo, ".gitignore", "docs/*\n")

    errors = qg.check_claimed_files_reachable(["docs/pitch/README.md"], str(repo))

    assert errors == [], f"a tracked file was flagged as unreachable: {errors}"


# ── Shape and robustness ─────────────────────────────────────────────────────

@pytest.mark.parametrize("claimed", [[], ["   "], ["N/A"], ["n/a — no code"]])
def test_silent_on_empty_and_na_entries(qg, repo, claimed):
    _write(repo, ".gitignore", "docs/*\n")
    assert qg.check_claimed_files_reachable(claimed, str(repo)) == []


def test_does_not_crash_on_non_string_entries(qg, repo):
    """A malformed report must not take the gate down with a TypeError."""
    _write(repo, ".gitignore", "docs/*\n")
    assert qg.check_claimed_files_reachable([None, 7, {"f": "x"}], str(repo)) == []


def test_windows_separators_are_normalised(qg, repo):
    """Reports written on Windows can carry backslashes."""
    _write(repo, ".gitignore", "docs/*\n")
    _write(repo, "docs/sub/thing.html")

    errors = qg.check_claimed_files_reachable(["docs\\sub\\thing.html"], str(repo))

    assert errors, "a backslash path bypassed the check"


def test_flags_every_offender_not_only_the_first(qg, repo):
    """Fixing one directory at a time is how this trap kept recurring.

    .gitignore already carries hand-added negations for docs/qa/ and
    docs/servicing/, each patched after a separate incident. A check that
    reported one path per run would repeat that history.
    """
    _write(repo, ".gitignore", "docs/*\n")

    errors = qg.check_claimed_files_reachable(
        ["docs/a/one.md", "docs/b/two.html", "docs/c/three.css"], str(repo)
    )

    assert len(errors) == 3, f"expected all three reported, got {len(errors)}"


# ── Wiring: the check must run on the commits that actually lost files ───────

def test_runs_when_there_is_no_diff_file_list(qg, repo):
    """Both losses were documentation-only commits.

    check_diff_coverage lives behind `if diff_files:` and filters .md out of its
    substantive set, so those commits reached it and did nothing. This check is
    called unconditionally; if it is ever moved inside that guard, this fails.
    """
    _write(repo, ".gitignore", "docs/*\n")
    _write(repo, "docs/outreach/student-brief.md")

    passed, errors, _ = qg.validate_report(
        {
            "tier": "minor",
            "justification": "a documentation change with no code",
            "files": ["docs/outreach/student-brief.md"],
            "break_it": [
                {
                    "scenario": "the handout is emailed while missing from the repo",
                    "what_happens": "reviewers cannot read what was sent",
                    "mitigated": False,
                }
            ],
            "post_merge": {
                "db_reset": "none at all",
                "secrets": "none at all",
                "other_repo": "none at all",
                "manual_verify": "open the file on main",
            },
        },
        diff_files=None,
        project_dir=str(repo),
    )

    assert not passed
    assert any("GITIGNORED" in e for e in errors), (
        "the claimed-files check did not run without a diff list — it has "
        f"probably been moved inside `if diff_files:`. errors={errors}"
    )
