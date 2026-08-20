# prior-art-checked: reuse not viable because no test asserts anything about a
# CI STEP's failure behaviour. Swept tests/ for "::warning::" (0 files), for
# gates.yml (test_doc_claims writes its own fixture copy; test_shadow_calibration
# and test_qa_gate_reachability only cite it in comments) and for .githooks
# (all four references are prose about GIT_DIR, or a directory in a search list).
# test_qa_gate_reachability.py covers the sibling failure — a gate passing on a
# file git will not carry — but entirely through qa_gate.py's own internals, so
# it is the wrong home for assertions about workflow YAML.
"""A check that could not run must not report a pass.

ORIGIN, 2026-08-16. Three steps in .github/workflows/gates.yml degraded to
``::warning::`` + exit 0 when their input was missing or their tool failed::

    mutation-count baselines   "mutation-baselines.json absent - ratchet NOT enforced"
    brief field-coverage       "ratchet script absent - NOT enforced"
    jscpd duplication          "jscpd could not run cleanly - ratchet NOT enforced"

Each one keeps its green tick while enforcing nothing, and the only signal that
it stopped is a warning nobody is assigned to read. That is the #398 shape,
which hid for ten weeks, and the #927 shape, where a gate PASSED on a report git
would never carry. The distinction that matters is not blocking vs non-blocking
- observation mode is a deliberate and defensible design - it is *ran and found
nothing* vs *never ran*, which must never look the same.

The first two guard TRACKED files, so "absent" cannot mean "not configured yet".
It means deleted, renamed, or an incomplete checkout, and all three are worth
stopping for.

These tests read the YAML rather than the shell, so a step can be rewritten
freely as long as it still cannot exit 0 without doing its work.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml  # noqa: F401

# A PLAIN import, for the reason spelled out in test_data_watch_workflow.py:
# pytest.importorskip would let these tests SKIP in CI if PyYAML fell out of
# requirements-test.txt, so a guard against a silent check would itself be
# silent.

_ROOT = Path(__file__).resolve().parents[1]
_GATES = _ROOT / ".github" / "workflows" / "gates.yml"
_PRE_PUSH = _ROOT / ".githooks" / "pre-push"

# Steps that are non-blocking BY DESIGN and must stay that way. Campaign
# section 7 finding 6: a gate earns blocking status from an observed
# false-positive rate, so these exit 0 on a finding on purpose. They are exempt
# from the "must fail" rule below and are listed by name, so promoting or
# demoting one is a visible edit here rather than a silent change of policy.
_DELIBERATELY_NON_BLOCKING = {
    "Output grounding (OBSERVATION ONLY — never fails the build)",
    # "Dev server boots" was here until #929 was fixed. It was non-blocking
    # because the defect it names — two handlers claiming /sitemap.xml, which
    # `next dev` refuses and `next build` tolerates — was live, and a gate that
    # blocks every merge on an unrepaired defect gets deleted rather than
    # obeyed. The step's own comment said to flip it in the PR that fixes #929;
    # this is that PR, so the promotion is recorded here as the visible edit
    # this list exists to force.
}


def _steps() -> list[dict]:
    wf = yaml.safe_load(_GATES.read_text(encoding="utf-8"))
    return [s for job in wf["jobs"].values() for s in job.get("steps", [])]


def _code(run: str) -> str:
    """A step's run block with comment lines dropped.

    Written after the first version of this file failed on its own subject: the
    comment EXPLAINING that a warning was replaced contains the word
    ``::warning::``. These assertions are about what the step DOES, so a rule
    that a prose description can violate is the wrong rule — it pushes the next
    author to delete the explanation rather than keep the behaviour.
    """
    return "\n".join(ln for ln in run.splitlines()
                     if not ln.lstrip().startswith("#"))


def test_the_workflow_parses_at_all():
    """Cheap, and it has caught real breakage: every assertion below would pass
    vacuously against a file that GitHub itself refuses to load."""
    wf = yaml.safe_load(_GATES.read_text(encoding="utf-8"))
    assert wf["jobs"], "gates.yml declares no jobs"


def test_no_step_announces_that_it_is_not_enforcing_and_passes_anyway():
    """The exact regression this file exists to prevent.

    A step may print ``NOT enforced`` only if it also stops. Today none of them
    do either, so the assertion is that the phrase has left the file entirely
    except where a step exits non-zero in the same breath.
    """
    offenders = []
    for step in _steps():
        if step.get("name") in _DELIBERATELY_NON_BLOCKING:
            continue
        run = _code(step.get("run") or "")
        if not re.search(r"NOT enforced", run, re.IGNORECASE):
            continue
        # Printing it is only acceptable alongside a hard stop.
        if "exit 1" not in run and "::error::" not in run:
            offenders.append(step.get("name"))
    assert offenders == [], (
        "these steps say they are not enforcing and then exit 0, which is "
        f"indistinguishable from a pass on the PR page: {offenders}"
    )


@pytest.mark.parametrize("step_name,guarded_paths", [
    ("Mutation-count baselines (counts never drop)",
     ("mutation-baselines.json", "scripts/check_test_baselines.py")),
    ("Brief field-coverage ratchet",
     ("scripts/brief_field_coverage_ratchet.py",)),
])
def test_a_missing_tracked_input_fails_the_step(step_name, guarded_paths):
    """Absent means deleted, not unconfigured, so it must stop the build."""
    step = next((s for s in _steps() if s.get("name") == step_name), None)
    assert step is not None, f"step '{step_name}' is gone — rename or removal?"
    run = step["run"]
    for path in guarded_paths:
        assert path in run, f"{step_name} no longer checks for {path}"
    assert "exit 1" in run, (
        f"'{step_name}' does not exit non-zero when its input is missing — "
        "a ratchet that cannot run is reporting a pass"
    )


@pytest.mark.parametrize("path", [
    "mutation-baselines.json",
    "scripts/check_test_baselines.py",
    "scripts/brief_field_coverage_ratchet.py",
])
def test_the_files_those_steps_guard_actually_exist(path):
    """The premise of the two tests above.

    If one of these is genuinely gone, the fix is to delete its step in a PR
    that says why — not to leave a step that now fails every build, and not to
    put the warning back.
    """
    assert (_ROOT / path).exists(), (
        f"{path} is missing, so the gates.yml step guarding it will now fail "
        "every run. Remove the step deliberately or restore the file."
    )


def test_a_jscpd_that_could_not_run_is_a_failure_not_a_warning():
    """Distinguishes the two non-zero exits.

    jscpd exits non-zero both when duplication breaches the threshold and when
    it cannot run at all. The second used to warn and pass, so a broken or
    unreachable tool looked exactly like a clean ratchet for as long as it
    stayed broken.
    """
    step = next((s for s in _steps() if s.get("name") == "jscpd"), None)
    assert step is not None, "the jscpd step is gone"
    run = _code(step["run"])
    assert "could not run" in run, "the tool-failure branch has been removed"
    # Two distinct error exits: the breach, and the non-run.
    assert run.count("::error::") >= 2, (
        "jscpd should ::error:: on BOTH a threshold breach and a failure to "
        "run; one of the two has gone back to warning"
    )
    assert "::warning::" not in run
    assert run.count("exit 1") >= 2


def test_observation_mode_steps_are_still_allowed_to_pass():
    """The counterweight, so this file cannot be read as 'everything must block'.

    Non-blocking is fine. Silently-not-running is not. If one of these is ever
    promoted the name comes out of _DELIBERATELY_NON_BLOCKING, which is a
    deliberate edit rather than a drift.
    """
    names = {s.get("name") for s in _steps()}
    present = _DELIBERATELY_NON_BLOCKING & names
    assert present, (
        "no deliberately non-blocking step remains; if observation mode was "
        "removed, remove this test with it rather than leaving it vacuous"
    )
    for step in _steps():
        if step.get("name") in present:
            assert step.get("continue-on-error") is True, (
                f"'{step['name']}' is listed as observation-only but no longer "
                "carries continue-on-error — it now blocks, silently"
            )


# ── The pre-push rationale ───────────────────────────────────────────────────
# A comment is not usually worth a test. This one is, because it was the STATED
# REASON a gate is scoped the way it is, it outlived its own withdrawal by ten
# days, and it was still being printed to the operator at the moment of decision.


def test_the_withdrawn_false_positive_prior_is_not_quoted_anywhere():
    """"~1 in 3 wrong" was withdrawn 2026-08-06 (meta-session-prompt-template).

    Measured after it: 08-06 lane 1, 16 rounds, most findings real; 08-16,
    7 findings, 7 real. A stale prior in the code that acts on it is worse than
    no prior, because it is read as evidence at exactly the moment a real
    finding is being waved through.
    """
    text = _PRE_PUSH.read_text(encoding="utf-8")
    stale = re.findall(
        r"(wrong roughly 1 time in 3|one finding in three has been invalid"
        r"|is wrong roughly 1 in 3)", text, re.IGNORECASE)
    assert stale == [], f"the withdrawn prior is still quoted: {stale}"


def test_no_base_rate_is_printed_to_the_operator_at_all():
    """Stricter, and aimed at where the damage happened.

    The comment may explain WHICH prior was withdrawn — the history is worth
    keeping and a rule that forbids naming it just gets the explanation deleted.
    What must not happen is a base rate reaching the screen at the moment
    somebody is deciding whether to wave a finding through. Any such number is
    stale the day it is written; the measured one is a command away.
    """
    echoed = [ln for ln in _PRE_PUSH.read_text(encoding="utf-8").splitlines()
              if ln.lstrip().startswith("echo ")]
    pattern = re.compile(
        r"(\b1 ?(time )?in ?3\b|\bone in three\b|\b1/3\b|\bone third\b"
        r"|\d+ ?% of findings)", re.IGNORECASE)
    offenders = [ln.strip() for ln in echoed if pattern.search(ln)]
    assert offenders == [], (
        "a base rate is being printed to the operator; that is exactly how the "
        f"last one survived its withdrawal: {offenders}"
    )


def test_the_override_path_records_a_verdict():
    """The override is the only moment a human judges a finding.

    Until 2026-08-16 it was echoed to the terminal and discarded, so the
    false-positive rate campaign section 7 finding 6 needs had an input of zero
    after 114 recorded findings across 40 branches.
    """
    text = _PRE_PUSH.read_text(encoding="utf-8")
    assert "--record-verdict" in text, (
        "SOL_OVERRIDE no longer records a verdict — the promotion path's only "
        "input is being thrown away again"
    )
    assert "$SOL_OVERRIDE" in text.split("--record-verdict")[1][:120], (
        "--record-verdict is present but is not being given the operator's "
        "own reason"
    )


def test_the_operator_is_told_how_to_make_an_override_countable():
    """An unprefixed override is deliberately NOT guessed into a bucket, so the
    prefix has to be visible at the moment it is needed or no verdict is ever
    scored."""
    text = _PRE_PUSH.read_text(encoding="utf-8")
    assert 'SOL_OVERRIDE=\\"wrong:' in text or 'SOL_OVERRIDE="wrong:' in text
    assert "UNREVIEWED" in text, (
        "the hook no longer explains that an unprefixed reason proves nothing"
    )
