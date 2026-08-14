"""The data-watch alarm must name the check that actually failed.

ORIGIN, 2026-08-14. The alarm step maps step outcomes to human names
POSITIONALLY: a comma-joined `${{ steps.X.outcome }}` list in one place, a
JavaScript array of labels in another. Adding a check step means editing both,
in the same order, or the alarm reports a different check than the one that
broke — and it reports it confidently, in an issue, to somebody who will go and
look at the wrong thing.

Adding the served-answer-quality step is what surfaced this: the mapping had to
be extended by hand and nothing would have complained if it had not been. That
is the same shape as the failure message that named DQ-9 as the culprit when
DQ-9 had nothing to do with the change (see dq_check.py's practice-1c comment) —
a check that misdirects is worse than one that only counts.

These tests are cheap and they pin the invariant rather than the wiring, so a
future step can be added in either order as long as both places agree.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml  # noqa: F401  — see below

# A PLAIN import, deliberately, not pytest.importorskip("yaml").
#
# importorskip was the first version, and the dependency-skip ratchet caught it
# on the first CI run: PyYAML sat in requirements.txt but not in
# requirements-test.txt, which is the file CI installs, so these tests would
# have SKIPPED in CI — silently. A guard against a misdirecting alarm would
# itself have been dark, which is the failure this whole file is about.
#
# PyYAML is now declared in requirements-test.txt. A plain import means that if
# it ever falls out again these tests go RED rather than quiet.

_WF = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "data-watch.yml"


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.safe_load(_WF.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def alarm(workflow) -> dict:
    steps = [s for s in workflow["jobs"]["data-checks"]["steps"] if isinstance(s, dict)]
    step = next((s for s in steps if s.get("name") == "Raise or clear the alarm"), None)
    assert step is not None, "the alarm step is gone — nothing would report a failure"
    return step


def _check_step_ids(workflow) -> list:
    """Ids of the steps that actually run a check, in declared order."""
    return [s["id"] for s in workflow["jobs"]["data-checks"]["steps"]
            if isinstance(s, dict) and s.get("id")]


def _mapped_ids(alarm) -> list:
    return re.findall(r"steps\.(\w+)\.outcome", alarm["env"]["FAILED"])


def _display_names(alarm) -> list:
    body = alarm["with"]["script"].split("names =", 1)[1].split("];", 1)[0]
    return re.findall(r"'([^']+)'", body)


def test_every_check_step_is_mapped(workflow, alarm):
    """A step whose outcome is not in the list can fail in total silence."""
    assert _check_step_ids(workflow) == _mapped_ids(alarm), (
        "step ids and the FAILED mapping disagree — add the new step to BOTH, "
        "in the same order"
    )


def test_names_line_up_one_to_one_with_ids(alarm):
    """Positional mapping: a length mismatch renames every check after the gap."""
    assert len(_display_names(alarm)) == len(_mapped_ids(alarm)), (
        "the label array and the outcome list are different lengths, so the "
        "alarm would name the wrong check"
    )


def test_every_check_step_can_still_run_after_an_earlier_failure(workflow):
    """Without `if: always()` the first failure hides every later result — the
    fail-fast mistake that hid ~1,800 tests for three days in gates."""
    missing = [s.get("id") for s in workflow["jobs"]["data-checks"]["steps"]
               if isinstance(s, dict) and s.get("id") and s.get("if") != "always()"]
    assert not missing, f"these check steps would be skipped after a failure: {missing}"


def test_the_alarm_shells_out_to_nothing(alarm):
    """main-red-alarm ran 12 times out of 12 at `gh: command not found` on the
    self-hosted runners, which carry neither gh nor jq. An alarm with an
    environment dependency dies quietly the next time the environment moves."""
    assert "run" not in alarm, "the alarm step must not shell out"
    assert alarm.get("uses", "").startswith("actions/github-script"), (
        "the alarm must talk to the API through github-script"
    )


def test_it_is_scheduled_and_manually_runnable(workflow):
    """The schedule is the whole point — this is the only trigger that sees
    data drift. workflow_dispatch is how a stale-guard failure gets cleared."""
    on = workflow.get("on") or workflow.get(True)
    assert "schedule" in on, "no schedule — nothing would check the data between PRs"
    assert "workflow_dispatch" in on, "no manual trigger — a stale guard could not be cleared"
