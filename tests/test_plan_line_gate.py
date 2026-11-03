"""plan-line-gate hook, driven like Claude Code drives it, against made-up transcripts."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "plan-line-gate.py"
PLAN = "ce-dcp-section-updater-PLAN-2026-10-26.md"


def a_text(t):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}


def a_read(path, tid="r1"):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tid, "name": "Read", "input": {"file_path": path}}]}}


def read_ok(tid="r1", error=False):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tid, "content": "...", "is_error": error}]}}


def human(t):
    return {"type": "user", "origin": {"kind": "human"}, "message": {"content": t}}


def not_human(t, kind="task-notification"):
    return {"type": "user", "origin": {"kind": kind}, "message": {"content": t}}


def tool_result():
    return {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}}


def run(tmp_path, entries, tool="Edit", tool_input=None):
    t = tmp_path / "t.jsonl"
    t.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")
    payload = {"tool_name": tool, "transcript_path": str(t),
               "tool_input": tool_input or {"file_path": str(ROOT / "scripts" / "dcp_extract_changed.py")}}
    plans = tmp_path / "plans"                       # CI has no ~/.claude/plans: bring our own
    plans.mkdir(exist_ok=True)
    (plans / PLAN).write_text("# test plan\n", encoding="utf-8")
    env = {**os.environ, "CLAUDE_PLANS_DIR": str(plans)}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), text=True,
                          capture_output=True, timeout=30, env=env)


READ_PLAN_CALL = a_read(f"/tmp/whatever/plans/{PLAN}")   # matched by name under a /plans/ folder


def test_todays_case_no_plan_line_is_blocked_and_shows_the_plans(tmp_path):
    r = run(tmp_path, [human("make it quicker"), a_text("building a skip")])
    assert r.returncode == 2 and "no PLAN: line" in r.stderr


def test_plan_read_named_and_answered_is_allowed(tmp_path):
    r = run(tmp_path, [READ_PLAN_CALL, read_ok(), a_text(f"PLAN: {PLAN} -- step 3 section reader"), human("yes")])
    assert r.returncode == 0, r.stderr


def test_a_plan_named_but_never_opened_is_blocked(tmp_path):
    r = run(tmp_path, [a_text(f"PLAN: {PLAN} -- step 3"), human("yes")])
    assert r.returncode == 2 and "not opened with Read" in r.stderr


def test_no_answer_yet_is_blocked(tmp_path):
    r = run(tmp_path, [READ_PLAN_CALL, read_ok(), a_text(f"PLAN: {PLAN} -- step 3"), tool_result()])
    assert r.returncode == 2 and "has not answered" in r.stderr


def test_a_notification_or_hook_feedback_is_not_an_answer(tmp_path):
    for kind in ("task-notification", "hook"):
        r = run(tmp_path, [READ_PLAN_CALL, read_ok(), a_text(f"PLAN: {PLAN}"), not_human("done", kind)])
        assert r.returncode == 2, kind


def test_an_answer_given_before_the_plan_line_does_not_count(tmp_path):
    r = run(tmp_path, [human("do the things"), READ_PLAN_CALL, read_ok(), a_text(f"PLAN: {PLAN}")])
    assert r.returncode == 2


def test_a_newer_plan_line_needs_a_new_answer(tmp_path):
    r = run(tmp_path, [READ_PLAN_CALL, read_ok(), a_text(f"PLAN: {PLAN}"), human("yes"), a_text("PLAN: none -- other thing")])
    assert r.returncode == 2


def test_plan_none_answered_is_allowed(tmp_path):
    assert run(tmp_path, [a_text("**PLAN: none** -- guardrails"), human("y")]).returncode == 0


def test_mentioning_a_plan_line_in_a_sentence_is_not_a_plan_line(tmp_path):
    r = run(tmp_path, [a_text("I will post a `PLAN:` line first."), human("ok")])
    assert r.returncode == 2 and "no PLAN: line" in r.stderr


def test_a_bash_write_to_a_pipeline_file_is_gated_too(tmp_path):
    r = run(tmp_path, [], tool="Bash",
            tool_input={"command": "sed -i 's/a/b/' scripts/dcp_extract_changed.py"})
    assert r.returncode == 2


def test_reading_a_pipeline_file_is_not_gated(tmp_path):
    r = run(tmp_path, [], tool="Bash", tool_input={"command": "grep -n def scripts/dcp_extract_changed.py"})
    assert r.returncode == 0


def test_touching_the_transcript_is_blocked(tmp_path):
    cmd = "echo '{}' >> ~/.claude/projects/x/abc.jsonl"
    r = run(tmp_path, [], tool="Bash", tool_input={"command": cmd})
    assert r.returncode == 2 and "transcripts" in r.stderr


def test_a_non_pipeline_edit_is_free(tmp_path):
    r = run(tmp_path, [], tool_input={"file_path": str(ROOT / "README.md")})
    assert r.returncode == 0


def test_a_none_field_does_not_crash_the_gate_open(tmp_path):
    """A crashed hook exits 1, which does NOT block. None in a field must still block."""
    t = tmp_path / "t.jsonl"
    t.write_text("")
    payload = {"tool_name": "Bash", "transcript_path": None,
               "tool_input": {"command": "sed -i 's/a/b/' scripts/dcp_extract_changed.py", "file_path": None}}
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), text=True,
                       capture_output=True, timeout=30)
    assert r.returncode == 2, r.stderr


import pytest  # noqa: E402


@pytest.mark.parametrize("cmd", [
    "truncate -s 0 scripts/dcp_extract_changed.py",
    "perl -pi -e 's/a/b/' scripts/dcp_extract_changed.py",
    "dd if=/dev/null of=scripts/ai_extractor.py",
    "git checkout -- scripts/dcp_commit_approved.py",
    "python fix.py scripts/r2_monitor.py",
    "cat scripts/dcp_extract_changed.py > /tmp/x; cp /tmp/x scripts/dcp_extract_changed.py",
    "grep x scripts/dcp_extract_changed.py | tee scripts/dcp_extract_changed.py",
])
def test_writers_outside_any_list_are_gated(tmp_path, cmd):
    """Sol review: a list of writing commands always misses one, so only read-only passes."""
    assert run(tmp_path, [], tool="Bash", tool_input={"command": cmd}).returncode == 2, cmd


@pytest.mark.parametrize("cmd", [
    "grep -n def scripts/dcp_extract_changed.py",
    "sed -n 1,20p scripts/ai_extractor.py | head -5",
    "git diff origin/main -- scripts/dcp_extract_changed.py",
    "python -m pytest tests/test_dcp_extract_all_mode.py && git log -1 -- scripts/r2_monitor.py",
])
def test_read_only_looks_are_free(tmp_path, cmd):
    assert run(tmp_path, [], tool="Bash", tool_input={"command": cmd}).returncode == 0, cmd


def test_a_relative_transcript_path_is_blocked_too(tmp_path):
    cmd = "echo '{}' >> .claude/projects/x/session.jsonl"
    assert run(tmp_path, [], tool="Bash", tool_input={"command": cmd}).returncode == 2


def test_a_quoted_plan_line_is_not_a_plan_line(tmp_path):
    r = run(tmp_path, [a_text("You said earlier:\n> PLAN: none"), human("ok")])
    assert r.returncode == 2


def test_a_read_that_failed_is_not_a_read(tmp_path):
    r = run(tmp_path, [READ_PLAN_CALL, read_ok(error=True), a_text(f"PLAN: {PLAN} -- step 3"), human("yes")])
    assert r.returncode == 2 and "not opened" in r.stderr


def test_a_plan_that_does_not_exist_is_refused(tmp_path):
    fake = "ce-made-up-PLAN-2099.md"
    r = run(tmp_path, [a_read(os.path.expanduser(f"~/.claude/plans/{fake}")), read_ok(),
                       a_text(f"PLAN: {fake} -- step 1"), human("yes")])
    assert r.returncode == 2 and "exists" in r.stderr
