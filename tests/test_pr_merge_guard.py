"""The merge guard must see every way a PR gets merged, and block on any doubt.

Incident replay: PR #902 was merged while no CI run existed (2026-08-10).
The gate said NOT-RUN; the merge went ahead because nothing called it.
"""
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "pr-merge-guard.py"
_spec = importlib.util.spec_from_file_location("pr_merge_guard", _HOOK)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


@pytest.mark.parametrize("command, expected", [
    ("gh pr merge 902 --squash", ["902"]),
    ("gh pr merge --squash 902", ["902"]),
    ("gh  pr   merge   902", ["902"]),
    ("gh pr merge #902", ["902"]),
    ("gh pr merge https://github.com/o/r/pull/902 --squash", ["902"]),
    ("gh pr merge -R owner/repo 902", ["902"]),
    ("gh pr merge --subject 'x y' 902", ["902"]),
    ("gh pr merge 902 --auto --squash", ["902"]),
    ("gh pr merge feat/x", ["feat/x"]),
    ("gh pr merge", [None]),
    ("gh pr merge --squash --delete-branch", [None]),
    ("cd \"C:/repo\" && gh pr merge 902 --squash", ["902"]),
    ("python scripts/check_pr_gates.py 1; gh pr merge 1", ["1"]),
    ("gh pr merge 1 && gh pr merge 2", ["1", "2"]),
    ("gh.exe pr merge 902", ["902"]),
    ("gh -R o/r pr merge 902", ["902"]),
    ("gh api -X PUT repos/o/r/pulls/902/merge", ["902"]),
    ("gh api repos/{owner}/{repo}/pulls/902/merge --method PUT -f merge_method=squash", ["902"]),
    ("curl -X PUT -H 'Authorization: x' https://api.github.com/repos/o/r/pulls/902/merge", ["902"]),
])
def test_every_merge_shape_is_found(command, expected):
    assert guard.find_merges(command) == expected


@pytest.mark.parametrize("command", [
    "gh pr view 902",
    "gh pr list --search merge",
    "git merge origin/main",
    "python scripts/check_pr_gates.py 902",
    "gh pr checks 902",
    'git commit -m "next: gh pr merge 902 after the gate"',
    "gh pr create --title 't' --body 'then gh pr merge 1'",
    "git commit -F - <<'EOF'\nrun gh pr merge 902 later\nEOF",
])
def test_non_merges_are_not_gated(command):
    assert guard.find_merges(command) == []


def _run(monkeypatch, payload, gate_rc=1, number=902):
    calls = []
    monkeypatch.setattr(guard, "run_gate", lambda pr, root: (calls.append(pr), (gate_rc, "NOT-RUN  no gates run"))[1])
    monkeypatch.setattr(guard, "resolve_number",
                        lambda sel, cwd: int(sel) if sel and sel.isdigit() else number)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.delenv("TOOL_INPUT", raising=False)
    return guard.main(), calls


def test_incident_902_merge_without_a_run_is_blocked(monkeypatch, capsys):
    rc, calls = _run(monkeypatch, {"tool_name": "Bash",
                                   "tool_input": {"command": "gh pr merge 902 --squash"}})
    assert rc == 2 and calls == [902]
    assert "NOT-RUN" in capsys.readouterr().err


def test_ready_pr_is_allowed(monkeypatch):
    rc, calls = _run(monkeypatch, {"tool_input": {"command": "gh pr merge 5 --squash"}}, gate_rc=0)
    assert rc == 0 and calls == [5]


def test_powershell_tool_is_gated_too(monkeypatch):
    rc, _ = _run(monkeypatch, {"tool_name": "PowerShell",
                               "tool_input": {"command": "gh pr merge 902 --squash"}})
    assert rc == 2


def test_second_of_two_merges_is_checked(monkeypatch):
    results = iter([(0, "READY"), (1, "FAILED")])
    monkeypatch.setattr(guard, "run_gate", lambda pr, root: next(results))
    monkeypatch.setattr(guard, "resolve_number", lambda sel, cwd: int(sel))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"tool_input": {"command": "gh pr merge 1 && gh pr merge 2"}})))
    assert guard.main() == 2


def test_unresolvable_pr_fails_closed(monkeypatch):
    monkeypatch.setattr(guard, "resolve_number", lambda sel, cwd: None)
    monkeypatch.setattr(guard, "run_gate", lambda pr, root: pytest.fail("must not reach the gate"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": "gh pr merge"}})))
    assert guard.main() == 2


def test_missing_gate_script_fails_closed(tmp_path):
    rc, msg = guard.run_gate(1, str(tmp_path))
    assert rc != 0 and "missing" in msg


def test_override_with_reason_is_allowed_and_recorded(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "OVERRIDE_LOG", tmp_path / "overrides.jsonl")
    monkeypatch.setattr(guard, "run_gate", lambda pr, root: pytest.fail("override skips the gate"))
    cmd = 'MERGE_GATE_OVERRIDE="CI runner offline, checks run by hand" gh pr merge 9'
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"cwd": str(tmp_path), "tool_input": {"command": cmd}})))
    assert guard.main() == 0
    log = (tmp_path / "overrides.jsonl").read_text(encoding="utf-8")
    assert "CI runner offline" in log


def test_override_without_a_real_reason_is_refused(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "OVERRIDE_LOG", tmp_path / "overrides.jsonl")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"cwd": str(tmp_path), "tool_input": {"command": "MERGE_GATE_OVERRIDE=x gh pr merge 9"}})))
    assert guard.main() == 2


def test_env_payload_still_works_when_stdin_is_empty(monkeypatch):
    monkeypatch.setattr(guard, "run_gate", lambda pr, root: (1, "FAILED"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    monkeypatch.setenv("TOOL_INPUT", json.dumps({"command": "gh pr merge 3"}))
    assert guard.main() == 2


def test_hook_is_registered_for_bash_and_powershell():
    settings = json.loads((_HOOK.parents[1] / "settings.json").read_text(encoding="utf-8"))
    entries = [e for e in settings["hooks"]["PreToolUse"]
               if any("pr-merge-guard.py" in h["command"] for h in e["hooks"])]
    assert entries, "the guard exists but nothing runs it"
    matcher = entries[0]["matcher"].split("|")
    assert "Bash" in matcher and "PowerShell" in matcher
