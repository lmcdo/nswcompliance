"""The ratchet enforcement must itself be provable, or it is one more promise.

WHY THIS FILE EXISTS
--------------------
Before practice 1c, every cap in ``.claude/dq_checks.json`` lived in the file it
policed. Raising the bar was a one-line edit that PASSED, and practice 1b's own
failure text said out loud to "raise the cap deliberately". So "we only go
forwards" was a convention, not a rule, and the ledger it guards had already
been wrong in both directions on 2026-08-13.

Practices 1c and 1d close that. But a guard with no test is exactly the thing
this whole campaign exists to stop -- a check that looks like coverage and can
never fire. So each one is tested in BOTH directions: it catches the regression
it was written for, AND it stays quiet on the cases that must not trip it.

No git here on purpose. ``raised_caps`` and ``newly_fixed_without_check`` are
pure functions over two dicts, so these tests cannot touch a repository. The
recorded hazard is that hooks export ``GIT_DIR`` which OVERRIDES ``cwd``, and a
test that shelled out to git once mutated the real repo and still passed.
``_committed_doc`` is the only part that runs git, and its contract -- return
None rather than guess -- is asserted separately.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import dq_check  # noqa: E402


# --------------------------------------------------------------------------
# practice 1c: a cap may fall, never rise
# --------------------------------------------------------------------------

def test_raised_cap_is_caught():
    """The regression the practice exists for: the bar moved up."""
    found = dq_check.raised_caps({"_max_no_check": 57}, {"_max_no_check": 56})
    assert found == [("_max_no_check", 56, 57)]


def test_lowered_cap_is_not_flagged():
    """Progress must not read as a failure, or the guard gets deleted."""
    assert dq_check.raised_caps({"_max_no_check": 48}, {"_max_no_check": 56}) == []


def test_unchanged_cap_is_not_flagged():
    assert dq_check.raised_caps({"_max_no_check": 56}, {"_max_no_check": 56}) == []


def test_every_ratchet_key_is_covered():
    """A cap added to the file but not to _RATCHET_KEYS would be unguarded.

    This is the failure mode that produced the campaign: the check existed and
    simply did not look at the thing that regressed.
    """
    current = {k: 10 for k in dq_check._RATCHET_KEYS}
    committed = {k: 1 for k in dq_check._RATCHET_KEYS}
    found = dq_check.raised_caps(current, committed)
    assert {k for k, _, _ in found} == set(dq_check._RATCHET_KEYS)


def test_cap_absent_on_main_is_skipped_not_treated_as_zero():
    """A NEW cap must not read as a rise from zero.

    Treating absent as 0 would fail every branch that introduces a cap, which
    punishes exactly the behaviour the ledger wants to encourage.
    """
    assert dq_check.raised_caps({"_max_no_check": 5}, {}) == []


@pytest.mark.parametrize("bad", [True, False, "56", None, 5.5])
def test_non_integer_caps_are_ignored_both_sides(bad):
    """bool is a subclass of int; `true` must not ratchet the cap at 1."""
    assert dq_check.raised_caps({"_max_no_check": bad}, {"_max_no_check": 56}) == []
    assert dq_check.raised_caps({"_max_no_check": 57}, {"_max_no_check": bad}) == []


# --------------------------------------------------------------------------
# practice 1d: a row newly marked fixed must arrive with its proof
# --------------------------------------------------------------------------

def _row(declared, check=None):
    return {"declared": declared, "check": check}


def test_open_flipped_to_fixed_without_check_is_caught_and_named():
    """The regression: a live defect declared solved on a memory.

    Naming the row matters. practice 1b could only count, and its own text
    admits it "cannot tell WHICH row is new" -- it once fingered DQ-9, which had
    nothing to do with the change.
    """
    cur = {"DQ-66": _row("fixed")}
    prev = {"DQ-66": _row("open", ["python", "probe.py"])}
    assert dq_check.newly_fixed_without_check(cur, prev, cur) == [("DQ-66", "open")]


def test_brand_new_row_declared_fixed_without_check_is_caught():
    cur = {"DQ-99": _row("fixed")}
    assert dq_check.newly_fixed_without_check(cur, {}, cur) == [
        ("DQ-99", "absent on main")]


def test_preexisting_fixed_without_check_is_not_flagged():
    """The backlog must not trip a FORWARD standard.

    38 rows are already fixed with no check. If this fired on them the gate
    would be red on every branch and would be removed within the week -- which
    is the documented reason practice 1b froze instead of demanding zero.
    """
    cur = {"DQ-9": _row("fixed")}
    prev = {"DQ-9": _row("fixed")}
    assert dq_check.newly_fixed_without_check(cur, prev, cur) == []


def test_newly_fixed_WITH_a_check_is_not_flagged():
    """Doing it correctly must pass, or the standard is unmeetable."""
    cur = {"DQ-41": _row("fixed", ["python", "scripts/dq_probe_live.py", "--id", "DQ-41"])}
    prev = {"DQ-41": _row("open")}
    assert dq_check.newly_fixed_without_check(cur, prev, cur) == []


def test_still_open_without_a_check_is_not_this_practices_business():
    """DQ-58 is open with no check for a reason that was verified correct.

    1d is about false claims of completion, not about coverage. Conflating them
    would make the message wrong and the guard distrusted.
    """
    cur = {"DQ-58": _row("open")}
    assert dq_check.newly_fixed_without_check(cur, {"DQ-58": _row("open")}, cur) == []


def test_ids_argument_scopes_the_sweep():
    """Only rows in `ids` are judged, so a row can be retired without tripping."""
    cur = {"DQ-1": _row("fixed"), "DQ-2": _row("fixed")}
    assert dq_check.newly_fixed_without_check(cur, {}, ["DQ-2"]) == [
        ("DQ-2", "absent on main")]


# --------------------------------------------------------------------------
# the git-reading half: must SKIP, never guess
# --------------------------------------------------------------------------

def test_committed_doc_returns_none_when_git_cannot_answer(monkeypatch):
    """"git could not answer" and "git answered no" are different.

    Conflating them is how a gate fails open, so an unreadable origin/main must
    yield None -- which main() reports as a SKIP, explicitly not a pass.
    """
    import subprocess as sp

    def boom(*a, **k):
        raise sp.SubprocessError("no such ref")

    monkeypatch.setattr(dq_check.subprocess, "run", boom)
    assert dq_check._committed_doc() is None


def test_committed_doc_strips_git_env_vars(monkeypatch):
    """GIT_DIR overrides cwd, so it must not survive into the subprocess.

    Without this, the gate reads the HOOK's repository and answers confidently
    about the wrong one. DQ-54 ratchets the same rule across scripts/.
    """
    seen = {}

    class Result:
        returncode = 1
        stdout = ""

    def fake_run(cmd, **kw):
        seen.update(kw.get("env") or {})
        return Result()

    monkeypatch.setenv("GIT_DIR", "/somewhere/else/.git")
    monkeypatch.setattr(dq_check.subprocess, "run", fake_run)
    dq_check._committed_doc()
    assert "GIT_DIR" not in seen
