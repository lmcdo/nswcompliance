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
sys.modules["pr_merge_guard"] = guard  # dataclasses look their module up here
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


HEAD = "a" * 40


def _run(monkeypatch, payload, gate_rc=1, number=902):
    calls = []
    monkeypatch.setattr(guard, "run_gate", lambda pr, root: (calls.append(pr), (gate_rc, "NOT-RUN  no gates run"))[1])
    monkeypatch.setattr(guard, "resolve_number",
                        lambda sel, cwd: int(sel) if sel and sel.isdigit() else number)
    monkeypatch.setattr(guard, "pr_head", lambda pr, cwd: HEAD)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.delenv("TOOL_INPUT", raising=False)
    return guard.main(), calls


def test_incident_902_merge_without_a_run_is_blocked(monkeypatch, capsys):
    rc, calls = _run(monkeypatch, {"tool_name": "Bash",
                                   "tool_input": {"command": "gh pr merge 902 --squash"}})
    assert rc == 2 and calls == [902]
    assert "NOT-RUN" in capsys.readouterr().err


def test_ready_pr_pinned_to_the_checked_head_is_allowed(monkeypatch):
    cmd = f"gh pr merge 5 --squash --match-head-commit {HEAD}"
    rc, calls = _run(monkeypatch, {"tool_input": {"command": cmd}}, gate_rc=0)
    assert rc == 0 and calls == [5]


def test_ready_rest_merge_pinned_by_sha_is_allowed(monkeypatch):
    cmd = f"gh api -X PUT repos/o/r/pulls/5/merge -f sha={HEAD}"
    rc, _ = _run(monkeypatch, {"tool_input": {"command": cmd}}, gate_rc=0)
    assert rc == 0


# ── Sol findings on this branch, 2026-10-27: each is a regression test ──────
def test_sol4_ready_but_unpinned_merge_is_blocked(monkeypatch, capsys):
    """Checked at A, merged at B: without the pin a push in between merges unchecked."""
    rc, _ = _run(monkeypatch, {"tool_input": {"command": "gh pr merge 5 --squash"}}, gate_rc=0)
    assert rc == 2 and f"--match-head-commit {HEAD}" in capsys.readouterr().err


def test_sol4_pin_to_a_different_commit_is_blocked(monkeypatch):
    cmd = "gh pr merge 5 --squash --match-head-commit " + "b" * 40
    rc, _ = _run(monkeypatch, {"tool_input": {"command": cmd}}, gate_rc=0)
    assert rc == 2


def test_sol1_shell_variable_selector_fails_closed(monkeypatch):
    cmd = "PR=902; gh api -X PUT repos/o/r/pulls/$PR/merge"
    assert guard.find_merges(cmd) == ["$PR"]
    monkeypatch.setattr(guard, "resolve_number",
                        lambda sel, cwd: int(sel) if sel and sel.isdigit() else None)
    monkeypatch.setattr(guard, "run_gate", lambda pr, root: pytest.fail("must not reach the gate"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": cmd}})))
    assert guard.main() == 2


def test_sol2_override_text_elsewhere_in_the_command_is_not_an_override(monkeypatch):
    cmd = "echo 'MERGE_GATE_OVERRIDE=\"this text is not an override\"'; gh pr merge 902"
    rc, calls = _run(monkeypatch, {"tool_input": {"command": cmd}})
    assert rc == 2 and calls == [902]


def test_sol2_override_on_one_merge_does_not_cover_the_next(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "OVERRIDE_LOG", tmp_path / "o.jsonl")
    cmd = 'MERGE_GATE_OVERRIDE="CI runner offline, checked by hand" gh pr merge 1 && gh pr merge 2'
    rc, calls = _run(monkeypatch, {"tool_input": {"command": cmd}})
    assert rc == 2 and calls == [2]


def test_sol_r2_pin_inside_a_comment_is_not_a_pin(monkeypatch):
    cmd = f"gh pr merge 5 --squash # --match-head-commit {HEAD}"
    rc, _ = _run(monkeypatch, {"tool_input": {"command": cmd}}, gate_rc=0)
    assert rc == 2


@pytest.mark.parametrize("cmd", [
    "gh pr \\\nmerge 902 --squash",
    "gh pr merge \\\n  902 --squash",
    "gh pr `\nmerge 902",
])
def test_sol_r2_line_continuations_are_joined(cmd):
    assert guard.find_merges(cmd) == ["902"]


def test_sol_r2_gate_refuses_when_head_moved_between_ci_and_review(tmp_path, monkeypatch):
    sys.path.insert(0, str(_HOOK.parents[2] / "scripts"))
    import check_pr_gates as g
    monkeypatch.setattr(g, "pr_view", lambda pr: {
        "headRefOid": "b" * 40, "headRefName": "feat/x", "baseRefName": "main"})
    monkeypatch.setattr(g.review_coverage, "_git", lambda *a, **k: pytest.fail("must stop first"))
    verdict, msg = g.review_gap(1, None, expected_head="a" * 40)
    assert verdict == "NOT-RUN" and "moved" in msg


def test_sol5_override_that_cannot_be_recorded_is_blocked(monkeypatch, tmp_path):
    monkeypatch.setattr(guard, "OVERRIDE_LOG", tmp_path / "missing-dir" / "o.jsonl")
    cmd = 'MERGE_GATE_OVERRIDE="CI runner offline, checked by hand" gh pr merge 9'
    rc, _ = _run(monkeypatch, {"tool_input": {"command": cmd}})
    assert rc == 2


def test_powershell_tool_is_gated_too(monkeypatch):
    rc, _ = _run(monkeypatch, {"tool_name": "PowerShell",
                               "tool_input": {"command": "gh pr merge 902 --squash"}})
    assert rc == 2


def test_second_of_two_merges_is_checked(monkeypatch):
    results = iter([(0, "READY"), (1, "FAILED")])
    monkeypatch.setattr(guard, "run_gate", lambda pr, root: next(results))
    monkeypatch.setattr(guard, "resolve_number", lambda sel, cwd: int(sel))
    monkeypatch.setattr(guard, "pr_head", lambda pr, cwd: HEAD)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"tool_input": {"command": f"gh pr merge 1 --match-head-commit {HEAD} && gh pr merge 2"}})))
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


def test_a_merge_inside_a_double_quoted_message_substitution_is_caught():
    assert guard.find_merges('git commit -m "$(gh pr merge 902)"') == ["902"]
    assert guard.find_merges('git commit -m "`gh pr merge 903`"') == ["903"]


def test_a_merge_named_in_a_single_quoted_message_is_still_data():
    assert guard.find_merges("git commit -m '$(gh pr merge 902)'") == []
    assert guard.find_merges('git commit -m "run gh pr merge 902 next"') == []


def test_a_sha_in_the_url_query_is_not_a_pin():
    url_only = guard.parse_merges("gh api -X PUT 'repos/o/r/pulls/9/merge?sha=abc123'")
    assert url_only and url_only[0].pin is None
    field = guard.parse_merges("gh api -X PUT repos/o/r/pulls/9/merge -f sha=abc123")
    assert field[0].pin == "abc123"
    body = guard.parse_merges('curl -X PUT https://api.github.com/repos/o/r/pulls/9/merge -d \'{"sha":"abc123"}\'')
    assert body[0].pin == "abc123"
