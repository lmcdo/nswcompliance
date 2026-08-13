"""The gate must refuse a QA report that git will never carry to CI.

ORIGIN, 2026-08-12. Branch ``test/feedback-route-validation`` produced the slug
``.qa/reports/test__feedback-route-validation.json``, which matched
``test_*.json`` in .gitignore. ``git add`` silently did nothing, the commit
reported success, and **qa_gate printed PASSED** — it validated a file on disk
and never asked git whether that file would leave the machine.

That is worse than a missing report. Both enforcing callers share one shape::

    if [ -f "$REPORT" ]; then run the gate; else warn; exit 0; fi

(.githooks/pre-push and .github/workflows/gates.yml). An ignored report exists
locally so the gate runs and passes, and is absent from the CI checkout so CI
warns and exits 0. Green twice over, enforcing nothing. #398 was the same defect
and hid for ten weeks.

WHY THESE TESTS STRIP GIT_* FROM THE ENVIRONMENT
------------------------------------------------
Git hooks export ``GIT_DIR`` and ``GIT_INDEX_FILE``, and those OVERRIDE ``cwd``.
A previous test in this repo ran ``git init`` in a tmpdir, silently operated on
the REAL repository instead, and still passed. Every helper here scrubs ``GIT_*``
and then asserts the toplevel really is the tmpdir before touching anything.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

_QA_GATE = Path(__file__).resolve().parents[1] / "scripts" / "qa_gate.py"


def _load():
    spec = importlib.util.spec_from_file_location("qa_gate_reachability", _QA_GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def qg():
    return _load()


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

    # The assertion that would have caught the earlier incident: if GIT_DIR were
    # still leaking, this toplevel would be the real repository.
    top = _git(r, "rev-parse", "--show-toplevel").stdout.strip()
    assert Path(top).resolve() == r.resolve(), (
        f"git is operating on {top!r}, not the tmpdir — GIT_* leaked into the env"
    )

    (r / ".qa" / "reports").mkdir(parents=True)
    return r


def _report(repo: Path, name: str = "fix__thing.json") -> str:
    p = repo / ".qa" / "reports" / name
    p.write_text("{}", encoding="utf-8")
    return str(p)


# ── IGNORED: never legitimate, so it fails with or without the flag ──────────

def test_gitignored_report_is_refused_without_any_flag(qg, repo):
    """The exact #925 defect: an ignored report can never reach CI."""
    (repo / ".gitignore").write_text("fix_*.json\n", encoding="utf-8")
    path = _report(repo)

    errors = qg.check_report_reachable(path, str(repo), require_tracked=False)

    assert errors, "an ignored report was accepted — this is the #925 defect"
    assert any("GITIGNORED" in e for e in errors)


def test_gitignored_error_names_the_pattern_that_did_it(qg, repo):
    """A rule you cannot find is a rule you cannot fix."""
    (repo / ".gitignore").write_text("# c\nfix_*.json\n", encoding="utf-8")
    path = _report(repo)

    errors = qg.check_report_reachable(path, str(repo), require_tracked=False)

    assert any("fix_*.json" in e for e in errors), (
        f"the offending pattern was not named: {errors}"
    )


def test_negation_rescues_the_report(qg, repo):
    """`!.qa/reports/*.json` is the fix shipped in #925 — prove it works."""
    (repo / ".gitignore").write_text(
        "fix_*.json\n!.qa/reports/*.json\n", encoding="utf-8"
    )
    path = _report(repo)

    errors = qg.check_report_reachable(path, str(repo), require_tracked=False)

    assert not errors, f"the negation did not rescue the report: {errors}"


# ── TRACKED: only enforced where it is meaningful ────────────────────────────

def test_untracked_is_allowed_before_the_first_git_add(qg, repo):
    """The counterweight. Without this, the gate cannot be run while authoring.

    A human or Claude runs the gate by hand BEFORE `git add`, so failing on
    untracked unconditionally would make the gate unusable and get it worked
    around — which is how guards die.
    """
    path = _report(repo)

    errors = qg.check_report_reachable(path, str(repo), require_tracked=False)

    assert not errors, f"untracked was refused without the flag: {errors}"


def test_untracked_is_refused_at_push_time(qg, repo):
    path = _report(repo)

    errors = qg.check_report_reachable(path, str(repo), require_tracked=True)

    assert errors, "an untracked report was accepted at push time"
    assert any("not tracked" in e for e in errors)
    assert any("git add" in e for e in errors), "the error must say how to fix it"


def test_staged_counts_as_tracked(qg, repo):
    """A new file that is staged but not yet committed IS in the index.

    Refusing it would fail the ordinary write-then-stage-then-commit flow.
    """
    path = _report(repo)
    _git(repo, "add", ".qa/reports/fix__thing.json")

    errors = qg.check_report_reachable(path, str(repo), require_tracked=True)

    assert not errors, f"a staged report was refused: {errors}"


def test_committed_report_passes(qg, repo):
    path = _report(repo)
    _git(repo, "add", ".qa/reports/fix__thing.json")
    _git(repo, "commit", "-q", "-m", "add report", "--no-verify")

    errors = qg.check_report_reachable(path, str(repo), require_tracked=True)

    assert not errors, f"a committed report was refused: {errors}"


# ── The gate's OWN git calls must ignore an inherited GIT_DIR ───────────────

def test_gate_ignores_inherited_git_dir(qg, repo, monkeypatch):
    """The gate must consult the repo it is pointed at, not GIT_DIR.

    This is not hypothetical and it is not only a test concern. The gate's
    main caller IS a git hook, and hooks export ``GIT_DIR`` and
    ``GIT_INDEX_FILE``, which OVERRIDE ``cwd``. Without scrubbing them,
    ``git ls-files`` inside the gate answers about whatever repository git was
    invoked from — so at push time the gate would report on the wrong index.

    Caught the hard way: the reachability tests passed standalone and three of
    them failed inside pre-push, because pytest there inherited the hook's
    GIT_DIR. Running the suite with GIT_DIR set reproduces it; this test pins
    it so a standalone run catches it too.
    """
    path = _report(repo)
    _git(repo, "add", ".qa/reports/fix__thing.json")

    # Point GIT_DIR somewhere real but WRONG — a different repository.
    other = repo.parent / "other"
    other.mkdir()
    _git(other, "init", "-q")
    monkeypatch.setenv("GIT_DIR", str((other / ".git").resolve()))
    monkeypatch.setenv("GIT_INDEX_FILE", str((other / ".git" / "index").resolve()))

    errors = qg.check_report_reachable(path, str(repo), require_tracked=True)

    assert not errors, (
        "the gate consulted GIT_DIR instead of the repo it was given: "
        f"{errors}"
    )


# ── Fail closed when git cannot answer ───────────────────────────────────────

def test_unknowable_fails_closed_only_where_it_matters(qg, tmp_path):
    """Outside a repo, git cannot say. Refuse under the flag, stay quiet without.

    "Cannot determine" must never be reported as "fine" at push time — that is
    the same silent-pass shape this whole file exists to close.
    """
    not_a_repo = tmp_path / "bare"
    (not_a_repo / ".qa" / "reports").mkdir(parents=True)
    path = not_a_repo / ".qa" / "reports" / "fix__thing.json"
    path.write_text("{}", encoding="utf-8")

    strict = qg.check_report_reachable(str(path), str(not_a_repo), require_tracked=True)
    assert strict, "unverifiable was treated as verified at push time"
    assert any("Cannot determine" in e for e in strict)

    lenient = qg.check_report_reachable(
        str(path), str(not_a_repo), require_tracked=False
    )
    assert not lenient, f"non-strict mode should not fail outside a repo: {lenient}"


# ---------------------------------------------------------------------------
# The same defect, one level down: the FILES a report cites
# ---------------------------------------------------------------------------
#
# ORIGIN, 2026-08-13. The tests above stop a report git will never carry. They
# say nothing about the files that report NAMES. `find_file` asked the
# filesystem, so a repair script under the default-ignored `scripts/*` resolved
# locally, the gate printed PASSED, and CI — which checks out only tracked
# files — failed on "no such file is tracked or on disk".
#
# The doc-claim checker in the same script already asked git the right question,
# but only in observation mode. So the BLOCKING check was strictly weaker than
# the observing one, which is the shape of every incident in this file.


def test_gitignored_cited_file_does_not_resolve(qg, repo):
    """A file on disk that git will never carry must not satisfy a citation."""
    (repo / "scripts").mkdir()
    (repo / "scripts" / "repair_thing.py").write_text("def main():\n    return 0\n")
    (repo / ".gitignore").write_text("scripts/*\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    assert (repo / "scripts" / "repair_thing.py").exists(), "precondition: on disk"
    assert qg.find_file("scripts/repair_thing.py", str(repo)) is None


def test_negation_makes_the_cited_file_resolve(qg, repo):
    """...and adding the `!` exception is what fixes it — same as the report."""
    (repo / "scripts").mkdir()
    (repo / "scripts" / "repair_thing.py").write_text("def main():\n    return 0\n")
    (repo / ".gitignore").write_text("scripts/*\n!scripts/repair_thing.py\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    assert qg.find_file("scripts/repair_thing.py", str(repo)) is not None


def test_staged_but_uncommitted_cited_file_resolves(qg, repo):
    """Staged is enough: it is in the index and will reach CI on push."""
    (repo / "a.py").write_text("x = 1\n")
    _git(repo, "add", "a.py")
    assert qg.find_file("a.py", str(repo)) is not None


def test_basename_collision_is_ambiguous_not_a_guess(qg, repo):
    """Two tracked files share a basename — resolving either would let the AST
    check verify against a file the report never named."""
    (repo / "one").mkdir()
    (repo / "two").mkdir()
    (repo / "one" / "thing.py").write_text("def a():\n    return 1\n")
    (repo / "two" / "thing.py").write_text("def b():\n    return 2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    assert qg.find_file("thing.py", str(repo)) is None, "ambiguous must not resolve"
    # The unambiguous full path still works.
    assert qg.find_file("one/thing.py", str(repo)) is not None


def test_unique_suffix_still_resolves(qg, repo):
    """Reports legitimately write a partial path; that must keep working."""
    (repo / "pkg").mkdir()
    (repo / "pkg" / "only.py").write_text("def a():\n    return 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    got = qg.find_file("only.py", str(repo))
    assert got is not None and got.endswith("only.py")


def test_dotfile_paths_resolve(qg, repo):
    """Regression: an early version of this fix used `lstrip("./")`, which
    strips CHARACTERS rather than a prefix — so `.github/workflows/x.yml` lost
    its leading dot and matched nothing. Caught by re-checking every committed
    report before shipping; one real citation would have started failing.
    """
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "gates.yml").write_text("name: gates\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    assert qg.find_file(".github/workflows/gates.yml", str(repo)) is not None


def test_explicit_relative_prefix_resolves(qg, repo):
    """`./a.py` and `a.py` name the same tracked file."""
    (repo / "a.py").write_text("x = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    assert qg.find_file("./a.py", str(repo)) is not None
