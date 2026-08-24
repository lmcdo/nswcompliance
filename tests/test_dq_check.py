"""The DQ ledger's statuses must be enforced, not asserted.

``.claude/DATA_QUALITY_TRACKER.md`` says it exists to "track data quality issues
systematically across Claude sessions". A hand-written status cannot do that —
it is a claim about the past, and this repo has three receipts that such claims
decay silently:

* ``#398`` untracked the QA report and ``.gitignore`` hid it for **ten weeks**.
* ``DQ-54`` was logged naming "three call sites". There were **nine**.
* On 2026-08-12 the ledger still read ``DQ-54: Open`` hours after it was merged.

These tests pin the two properties that make ``scripts/dq_check.py`` worth
having, and both were verified by making them fail first.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "dq_check.py"
_CHECKS = _ROOT / ".claude" / "dq_checks.json"
_LEDGER = _ROOT / ".claude" / "DATA_QUALITY_TRACKER.md"


def _load():
    spec = importlib.util.spec_from_file_location("dq_check_under_test", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def dq():
    return _load()


# ── Coverage: the ledger cannot grow rows nobody has to think about ──────────

def test_every_ledger_row_has_an_entry(dq):
    """A new DQ row without a check entry must fail, even if the check is null.

    The point is not that every row is checkable — most are not yet. It is that
    adding one forces a deliberate decision, recorded as either a check or a
    why_no_check. Same shape as check_test_quarantine.py.
    """
    checks = dq.load_checks()
    missing = [i for i in dq.ledger_ids() if i not in checks]
    assert not missing, (
        f"{len(missing)} ledger row(s) have no entry in dq_checks.json: {missing}"
    )


def test_no_orphan_entries(dq):
    """An entry for a row that no longer exists means the ledger moved on."""
    checks = dq.load_checks()
    ids = set(dq.ledger_ids())
    orphans = [i for i in checks if i not in ids and not i.startswith("_")]
    assert not orphans, f"dq_checks.json has entries not in the ledger: {orphans}"


def test_every_entry_declares_a_check_or_a_reason(dq):
    """``check: null`` is honest only when it says WHY.

    Without the reason, a null is indistinguishable from an oversight, and the
    gap stops being visible — which is how a tracker rots into decoration.
    """
    checks = dq.load_checks()
    silent = [
        i for i, spec in checks.items()
        if not spec.get("check") and not spec.get("why_no_check")
    ]
    assert not silent, f"entries with no check and no why_no_check: {silent}"


# ── The ratchet, in BOTH directions ──────────────────────────────────────────

def test_declared_fixed_requires_a_passing_check(dq):
    """A row claiming fixed whose check fails is a regression or a false claim."""
    verdict, detail = dq.run_one(
        "SYNTH",
        {"declared": "fixed", "check": ["python", "-c", "import sys; sys.exit(1)"]},
    )
    assert verdict == "RED", f"a failing check under 'fixed' was accepted: {detail}"


def test_declared_open_requires_a_failing_check(dq):
    """THE ONE THAT MATTERS.

    A stale "open" row is invisible forever — nobody re-tests a defect they
    believe is still broken. That is exactly how DQ-54 sat open while merged.
    So a check that PASSES under 'open' must go red and force the ledger to
    catch up.
    """
    verdict, detail = dq.run_one(
        "SYNTH",
        {"declared": "open", "check": ["python", "-c", "import sys; sys.exit(0)"]},
    )
    assert verdict == "RED", (
        f"a passing check under 'open' was accepted — the ledger can now sit "
        f"stale in the direction nobody looks: {detail}"
    )


def test_agreement_is_not_flagged(dq):
    """The counterweight: a ratchet that reds everything proves nothing."""
    ok_fixed, _ = dq.run_one(
        "SYNTH", {"declared": "fixed", "check": ["python", "-c", "import sys; sys.exit(0)"]}
    )
    ok_open, _ = dq.run_one(
        "SYNTH", {"declared": "open", "check": ["python", "-c", "import sys; sys.exit(1)"]}
    )
    assert ok_fixed == "OK" and ok_open == "OK", (
        "agreeing rows were flagged; the ratchet is firing on everything"
    )


def test_unenforced_states_are_not_invented(dq):
    """'partial' and friends carry no expectation, deliberately.

    A partial fix can legitimately pass or fail its check. Inventing an
    expectation would manufacture the false precision this whole file exists to
    remove — and a gate that fires on ambiguity gets dismissed by muscle memory.
    """
    for declared in ("partial", "backlog", "accepted", "latent"):
        for exit_code in (0, 1):
            verdict, _ = dq.run_one(
                "SYNTH",
                {"declared": declared,
                 "check": ["python", "-c", f"import sys; sys.exit({exit_code})"]},
            )
            assert verdict == "OK", f"{declared!r} with exit {exit_code} was enforced"


def test_missing_check_is_reported_not_passed(dq):
    """A null check must be visible as a gap, never counted as a pass."""
    verdict, detail = dq.run_one("SYNTH", {"declared": "open", "check": None,
                                           "why_no_check": "needs the live DB"})
    assert verdict == "NO-CHECK"
    assert "live DB" in detail


def test_unrunnable_check_is_an_error_not_a_pass(dq):
    """"Could not run it" must never read as "it is fine"."""
    verdict, _ = dq.run_one(
        "SYNTH", {"declared": "fixed", "check": ["definitely-not-a-real-binary-xyz"]}
    )
    assert verdict == "ERROR"


# ── The two files must not drift apart ───────────────────────────────────────

def test_json_and_markdown_agree(dq):
    """Two sources of truth is how DQ-54 sat 'Open' after it was merged."""
    checks = dq.load_checks()
    disagree = dq.status_disagreements(checks, dq.ledger_ids())
    assert not disagree, "ledger and dq_checks.json contradict each other:\n  " + "\n  ".join(disagree)


def test_the_checks_file_is_valid_json():
    with _CHECKS.open(encoding="utf-8") as f:
        data = json.load(f)
    assert "checks" in data and data["checks"], "no checks recorded"


# ── Probe SQL must define "served" the same way everywhere ───────────────────

def test_probe_sql_uses_one_definition_of_a_served_row():
    """A probe that measures served rows in its outer query must not accept
    FLAGGED rows as evidence in a subquery.

    DQ-66 asks whether a sibling town plan has any controls of its own. Written
    with a bare `e.is_current`, a sibling holding only `needs_review` rows would
    satisfy it — so the probe would stop counting while the sibling still served
    nothing and the mis-citation stood. The count going quiet without the defect
    being fixed is the exact silent-pass shape this ledger exists to remove.

    Asserted structurally rather than against the database, because the bug is
    invisible in today's data: both siblings currently hold zero rows, so the
    count is 30 either way. It would only appear once someone part-extracted a
    sibling — which is precisely when nobody would be re-reading this SQL.
    """
    import re
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import dq_probe_live

    _headline, sql, _params, _means = dq_probe_live.PROBES["DQ-66"]
    current = len(re.findall(r"is_current", sql))
    guards = len(re.findall(r"NOT COALESCE\(\s*\w+\.needs_review,\s*false\s*\)", sql))
    assert current >= 2, "expected the outer query and the sibling subquery to both scope to current rows"
    assert guards == current, (
        f"{current} is_current filter(s) but only {guards} needs_review guard(s) — "
        "one of them treats a flagged row as served"
    )


# ── An UNFINISHED row must be provable ───────────────────────────────────────
#
# `_max_no_check` counts every row without a check, 53 of which are already
# fixed. That total can be stopped from growing but can never reach zero, so it
# is not something anyone can work towards. `_max_unverified_unresolved` counts
# only rows still declared open/partial/backlog — those CAN each be given a
# check or closed, so zero is reachable and the number means something.

def _unverified(checks: dict, unresolved: set) -> list:
    return sorted(k for k, v in checks.items()
                  if v.get("declared") in unresolved and not v.get("check"))


def test_the_unverified_cap_matches_reality(dq):
    """The stored cap must equal today's count — a cap set above the real
    number is slack that lets the next row in for free."""
    checks = dq.load_checks()
    doc = json.loads(_CHECKS.read_text(encoding="utf-8"))
    cap = doc.get("_max_unverified_unresolved")
    assert cap is not None, "the unverified ratchet has no cap recorded"
    assert len(_unverified(checks, dq._UNRESOLVED)) == cap, (
        "cap and count disagree — lower the cap when a row gains a check or closes"
    )


def test_a_fixed_row_without_a_check_does_not_count(dq):
    """Scope is 'still costing something'. Counting the 53 fixed rows is what
    made the older cap unreachable and therefore ignorable."""
    checks = dict(dq.load_checks())
    checks["DQ-SYNTH-FIXED"] = {"declared": "fixed"}
    assert "DQ-SYNTH-FIXED" not in _unverified(checks, dq._UNRESOLVED)


@pytest.mark.parametrize("declared", ["open", "partial", "backlog"])
def test_every_unfinished_state_is_in_scope(dq, declared):
    """open, partial and backlog all mean unfinished. Leaving any of them out
    would be a hole you could park a defect in."""
    checks = dict(dq.load_checks())
    checks["DQ-SYNTH"] = {"declared": declared}
    assert "DQ-SYNTH" in _unverified(checks, dq._UNRESOLVED)


def test_both_ways_out_lower_the_number(dq):
    """Writing a check and closing the row are the only two exits, and the
    ratchet must accept both — otherwise it pushes people towards raising the
    cap, which is the one move that hides the problem."""
    checks = dict(dq.load_checks())
    checks["DQ-SYNTH"] = {"declared": "open"}
    before = len(_unverified(checks, dq._UNRESOLVED))

    with_check = dict(checks)
    with_check["DQ-SYNTH"] = {"declared": "open", "check": ["python", "-c", "pass"]}
    assert len(_unverified(with_check, dq._UNRESOLVED)) == before - 1

    closed = dict(checks)
    closed["DQ-SYNTH"] = {"declared": "fixed"}
    assert len(_unverified(closed, dq._UNRESOLVED)) == before - 1


def test_unresolved_states_are_not_restated_here(dq):
    """The count reuses dq_check._UNRESOLVED. A second list of what 'unfinished'
    means is the same drift this ledger exists to stop, one level up."""
    assert dq._UNRESOLVED == {"open", "partial", "backlog"}


# ── A row declared FIXED must be able to prove it stayed fixed ────────────────
#
# The unresolved ratchet above excludes fixed rows so its number can reach zero.
# This is the cost of that choice: most fixed rows cannot demonstrate anything,
# so a regression is invisible. DQ-54 sat declared FIXED while still broken.
#
# Frozen rather than driven to zero. Zero would need a check written against
# every already-closed defect, and a target nobody can meet gets deleted rather
# than met — so this stops the count GROWING, which is the case still worth
# stopping: a new row marked fixed with nothing behind it.

def _fixed_no_check(checks: dict) -> list:
    return sorted(k for k, v in checks.items()
                  if v.get("declared") == "fixed" and not v.get("check"))


def test_the_fixed_cap_matches_reality(dq):
    checks = dq.load_checks()
    doc = json.loads(_CHECKS.read_text(encoding="utf-8"))
    cap = doc.get("_max_fixed_without_check")
    assert cap is not None, "the fixed-without-check ratchet has no cap recorded"
    assert len(_fixed_no_check(checks)) == cap, (
        "cap and count disagree — lower it in the same change that adds a check"
    )


def test_closing_a_row_without_a_check_raises_the_count(dq):
    """The case this exists to stop: an open row marked fixed, nothing written."""
    checks = dict(dq.load_checks())
    before = len(_fixed_no_check(checks))
    checks["DQ-SYNTH"] = {"declared": "open"}
    assert len(_fixed_no_check(checks)) == before, "an open row must not count"
    checks["DQ-SYNTH"] = {"declared": "fixed"}
    assert len(_fixed_no_check(checks)) == before + 1


def test_closing_a_row_WITH_a_check_does_not(dq):
    """The wanted path stays free: close it, but bring the probe."""
    checks = dict(dq.load_checks())
    before = len(_fixed_no_check(checks))
    checks["DQ-SYNTH"] = {"declared": "fixed", "check": ["python", "-c", "pass"]}
    assert len(_fixed_no_check(checks)) == before


def test_the_three_ratchets_measure_different_sets(dq):
    """Three caps now exist and none may quietly become an alias for another:
    all rows, unresolved-without-check, fixed-without-check."""
    checks = dq.load_checks()
    doc = json.loads(_CHECKS.read_text(encoding="utf-8"))
    all_null = [k for k, v in checks.items() if not v.get("check")]
    unresolved_null = _unverified(checks, dq._UNRESOLVED)
    fixed_null = _fixed_no_check(checks)
    assert doc["_max_no_check"] == len(all_null)
    assert doc["_max_unverified_unresolved"] == len(unresolved_null)
    assert doc["_max_fixed_without_check"] == len(fixed_null)
    # The two sub-counts are disjoint, and together they cannot exceed the total.
    assert not set(unresolved_null) & set(fixed_null)
    assert len(unresolved_null) + len(fixed_null) <= len(all_null)


# ── unwired_checks() must police what git carries, not what is on disk ───────
#
# The guard exists to stop a check shipping with nothing to run it. It read the
# FILESYSTEM (`scripts.glob("*.py")`), and the set that can ever be run by a
# workflow, a hook or another script is the set git CARRIES. In a working tree
# holding local scratch the two diverge, and on 2026-08-24 they diverged badly:
# `scripts/dq_check.py` named 114 orphaned checks and every one of them was
# untracked, while gates.yml on main @05d3d413 was green. A gate that is red on
# every developer's machine for a reason CI cannot see is a gate everyone learns
# to step over, which is the exact failure `unwired_checks` was written to end.
#
# Scoping to tracked files removes nothing from the guard's reach: a check is
# scanned the moment it is `git add`ed, which is before it can be pushed.

import os
import subprocess
import sys
import types


def _git(args, cwd):
    """git, with GIT_* scrubbed.

    Not optional: a git hook exports GIT_DIR, and GIT_DIR OVERRIDES cwd. Run
    under .githooks/pre-push without this, these tests build their fixture in
    the temp directory and then ask THIS repository about it.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env,
        capture_output=True, text=True, timeout=60, check=True,
    )


@pytest.fixture
def repo(tmp_path):
    """A miniature repo: one wired check, one orphan, both tracked; plus scratch.

    ``check_scratch.py`` is untracked and orphaned — a clean checkout will not
    have it. ``_launder.py`` is untracked and NAMES the tracked orphan, which is
    how an unwired check can be made to look wired by a file that never ships.
    """
    (tmp_path / "scripts").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".githooks").mkdir()
    (tmp_path / ".claude").mkdir()

    (tmp_path / ".claude" / "dq_checks.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".githooks" / "pre-commit").write_text("#!/bin/sh\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows" / "gates.yml").write_text(
        "jobs:\n  x:\n    steps:\n      - run: python scripts/check_wired.py\n",
        encoding="utf-8",
    )
    for name in ("check_wired.py", "check_orphan.py", "check_scratch.py"):
        (tmp_path / "scripts" / name).write_text("print('x')\n", encoding="utf-8")

    _git(["init", "-q"], tmp_path)
    _git(["add", "scripts/check_wired.py", "scripts/check_orphan.py",
          ".github/workflows/gates.yml", ".githooks/pre-commit",
          ".claude/dq_checks.json"], tmp_path)
    _git(["-c", "user.email=t@t", "-c", "user.name=t",
          "commit", "-q", "--no-verify", "-m", "fixture"], tmp_path)

    # Untracked, and it names the tracked orphan.
    (tmp_path / "scripts" / "_launder.py").write_text(
        "# see scripts/check_orphan.py for the query\n", encoding="utf-8")
    return tmp_path


def test_git_actually_answers(dq, repo):
    """The scoping must come from git, not from a silent fallback.

    Without this the two tests below pass for the wrong reason the moment the
    ``git ls-files`` call breaks: the fallback scans everything, so the orphan
    is still found and the scratch file is simply mis-reported again.
    """
    assert dq._tracked_paths(repo) is not None, (
        "git ls-files did not answer, so unwired_checks fell back to globbing "
        "the filesystem and these tests prove nothing"
    )


def test_a_tracked_orphan_is_still_reported(dq, repo):
    """The guard must not lose a single file it already caught."""
    assert "check_orphan.py" in dq.unwired_checks(repo)


def test_an_untracked_scratch_check_is_not_reported(dq, repo):
    """114 of these made the gate red on every machine and green in CI."""
    assert "check_scratch.py" not in dq.unwired_checks(repo)


def test_an_untracked_file_cannot_launder_a_tracked_orphan(dq, repo):
    """A mention from a file that never ships is not wiring.

    The haystack globbed scripts/*.py too, so scratch could vouch for an orphan
    — the guard reading looser than it looks, in the direction nobody checks.
    """
    assert "check_orphan.py" in dq.unwired_checks(repo), (
        "scripts/_launder.py is untracked; it cannot wire anything"
    )


def test_a_foreign_qa_report_path_is_refused(dq, repo, tmp_path, monkeypatch):
    """The scrub has to come from THIS repo's qa_report_path, not any other.

    dq_check.py APPENDS scripts/ to sys.path, and append means every earlier
    entry wins. A same-named module elsewhere would then decide how GIT_* is
    scrubbed here, and one that let GIT_DIR through would point `git ls-files`
    at a different repository: no check would look tracked, and the gate would
    report nothing at all. Silent green.

    Forced red by deleting the provenance comparison in _tracked_paths — this
    then returns a populated set built from the foreign env instead of None.
    """
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "qa_report_path.py").write_text(
        "import os" + os.linesep
        + "def git_env():" + os.linesep
        + "    return dict(os.environ)  # scrubs nothing" + os.linesep,
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location(
        "qa_report_path", foreign / "qa_report_path.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setitem(sys.modules, "qa_report_path", mod)

    assert dq._tracked_paths(repo) is None, (
        "a qa_report_path from outside this repository was trusted to scrub GIT_*"
    )


def test_an_uninspectable_git_env_is_refused_not_raised(dq, repo, monkeypatch):
    """A git_env with no source file must fall back, not abort the gate.

    inspect.getfile() raises TypeError for a builtin or a callable OBJECT — the
    shape a foreign module is most likely to expose. Without the except clause
    the whole ledger run dies on a traceback instead of reporting its rows.
    Forced red by removing that clause: this test then errors with TypeError.
    """
    class Callable:  # no __code__, so getfile() cannot answer
        def __call__(self):
            return {}

    module = types.ModuleType("qa_report_path")
    module.git_env = Callable()
    monkeypatch.setitem(sys.modules, "qa_report_path", module)

    assert dq._tracked_paths(repo) is None
