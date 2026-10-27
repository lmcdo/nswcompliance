"""Every hook in .claude/settings.json must react to an input it exists to stop.

Incident (found 2026-10-27): pre-commit-gate.py, push-retry-needs-full-output.py
and no-unreferenced-new-file.py read the command from a TOOL_INPUT environment
variable. Claude Code never sets one; it sends the payload as JSON on stdin.
Each hook saw "{}", exited 0, and had likely never blocked anything. Nothing
noticed, because a hook that allows everything looks exactly like a hook that
had nothing to block. The first two now read stdin; pre-commit-gate.py was
deleted, because .githooks/pre-commit already checks the QA report at commit
time and, unlike it, lets a branch's first commit through.

So this test sends each hook ONE input it must block (or, for a warn-only hook,
must warn about), the way Claude Code sends it: JSON on stdin, no TOOL_INPUT.
The command run is the one written in settings.json, so a hook re-pointed at a
different file is tested as registered. A hook added to settings.json without a
case here fails `test_every_registered_hook_has_a_case`.
"""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / ".claude" / "settings.json"

# Hooks that read no input at all, so "ignores its input" cannot happen to them.
# Each must say why; adding one here is a decision, not a default.
INPUT_FREE = {
    "session-capability-index.py": "SessionStart banner; scans files, reads no payload",
    "session-applicability-status.py": "SessionStart banner; queries the DB, reads no payload",
    "done-when-template.py": "prints a fixed reminder on every prompt",
    "live-numbers.py": "prints DB numbers on every prompt, reads no payload",
    "npx tsc --noEmit": "type-checks the whole frontend; ignores the payload by design",
}


def _registered() -> list[tuple[str, str, str]]:
    """(event, matcher, command) for every hook in settings.json."""
    hooks = json.loads(SETTINGS.read_text(encoding="utf-8")).get("hooks", {})
    return [(event, m.get("matcher") or "", h["command"])
            for event, matchers in hooks.items()
            for m in matchers for h in m.get("hooks", [])]


def _key(command: str) -> str:
    for name in INPUT_FREE:
        if name in command:
            return name
    for part in shlex.split(command):
        if part.endswith(".py"):
            return Path(part).name
    return command


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _repo(tmp: Path) -> Path:
    _git(tmp, "init", "-q", "-b", "feat/x")
    _git(tmp, "config", "user.email", "t@t")
    _git(tmp, "config", "user.name", "t")
    (tmp / "README.md").write_text("x\n")
    _git(tmp, "add", ".")
    _git(tmp, "commit", "-q", "-m", "init")
    return tmp


def _head(tmp: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp, check=True,
                          capture_output=True, text=True).stdout.strip()


def _run(command: str, payload: dict, cwd: Path, project_dir: Path) -> subprocess.CompletedProcess:
    """Run a hook as Claude Code does: payload on stdin, TOOL_INPUT unset.

    The script path comes from ROOT, the hook's working state from project_dir,
    so a hook writes its state files into the temp dir and not this checkout.
    """
    argv = shlex.split(command.replace("$CLAUDE_PROJECT_DIR", ROOT.as_posix()))
    if argv[0] == "python":
        argv[0] = sys.executable
    env = {k: v for k, v in os.environ.items() if k != "TOOL_INPUT"}
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(argv, input=json.dumps(payload), cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=120)


def _bash(command: str) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": command}}


# --- one must-react setup per hook -------------------------------------------
# Each returns (payload, cwd, project_dir, expected) where expected is
# "block" (exit 2) or "warn" (exit 0 with a message).

def case_pre_edit_guard(tmp):
    return ({"tool_name": "Edit", "tool_input": {"file_path": str(tmp / ".env"),
             "old_string": "a", "new_string": "b"}}, tmp, tmp, "block")


def case_prior_art_guard(tmp):
    # "flood" is a known existing data source; a new fetcher for it must stop.
    fp = (tmp / "services" / "flood_level_fetcher.py").as_posix()
    return ({"tool_name": "Write", "tool_input": {"file_path": fp,
             "content": "def fetch_flood_level(lat, lon):\n    pass\n"}}, tmp, tmp, "block")


def case_push_retry_needs_full_output(tmp):
    # Second push of the same unlanded commit, with output cut by `tail`.
    repo = _repo(tmp)
    (repo / ".claude").mkdir()
    (repo / ".claude" / ".push-attempts.json").write_text(
        json.dumps({"feat/x": {"sha": _head(repo), "attempts": 1}}))
    return (_bash("git push 2>&1 | tail -5"), repo, repo, "block")


def case_no_unreferenced_new_file(tmp):
    # A new script nothing names.
    repo = _repo(tmp)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "check_once_and_forget.py").write_text("print(1)\n")
    _git(repo, "add", ".")
    return (_bash('git commit -m "add check"'), repo, repo, "block")


def case_surface_prior_art_guard(tmp):
    # No .prior-art-surfaces.json marker in the project.
    return ({"tool_name": "Artifact", "tool_input": {"file_path": "x.html"}}, tmp, tmp, "block")


def case_pr_merge_guard(tmp):
    # An override with a too-short reason is refused before any network call.
    return (_bash('MERGE_GATE_OVERRIDE="x" gh pr merge 1 --squash'), tmp, tmp, "block")


def case_post_edit_quality(tmp):
    fp = (tmp / "frontend-nextjs" / "lib" / "db.ts").as_posix()
    return ({"tool_name": "Edit", "tool_input": {"file_path": fp, "old_string": "a",
             "new_string": "const pool = new Pool({})"}}, tmp, tmp, "block")


def case_done_when_gate(tmp):
    # A turn that wrote a file and ended with no number and no DONE WHEN line.
    transcript = tmp / "t.jsonl"
    lines = [
        {"type": "user", "message": {"content": "fix it"}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Write", "input": {"file_path": "a.py"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Fixed it."}]}},
    ]
    transcript.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return ({"hook_event_name": "Stop", "stop_hook_active": False,
             "transcript_path": str(transcript)}, tmp, tmp, "block")


def case_gitignore_trap_guard(tmp):
    # A new file under a whitelist-ignored directory, not tracked.
    repo = _repo(tmp)
    (repo / ".gitignore").write_text("scripts/*\n")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "new_tool.py").write_text("x\n")
    return ({"tool_name": "Write", "tool_input": {
             "file_path": str(repo / "scripts" / "new_tool.py"), "content": "x\n"}},
            repo, repo, "warn")


def case_capability_audit_trigger(tmp):
    return ({"hook_event_name": "UserPromptSubmit",
             "prompt": "what data source should the architecture use"}, tmp, ROOT, "warn")


CASES = {
    "pre-edit-guard.py": case_pre_edit_guard,
    "prior-art-guard.py": case_prior_art_guard,
    "push-retry-needs-full-output.py": case_push_retry_needs_full_output,
    "no-unreferenced-new-file.py": case_no_unreferenced_new_file,
    "surface-prior-art-guard.py": case_surface_prior_art_guard,
    "pr-merge-guard.py": case_pr_merge_guard,
    "post-edit-quality.py": case_post_edit_quality,
    "done-when-gate.py": case_done_when_gate,
    "gitignore-trap-guard.py": case_gitignore_trap_guard,
    "capability-audit-trigger.py": case_capability_audit_trigger,
}


def test_every_registered_hook_has_a_case():
    missing = [cmd for _, _, cmd in _registered()
               if _key(cmd) not in CASES and _key(cmd) not in INPUT_FREE]
    assert not missing, f"hooks with no must-react case and no INPUT_FREE reason: {missing}"


@pytest.mark.parametrize("event, matcher, command",
                         [r for r in _registered() if _key(r[2]) in CASES],
                         ids=lambda v: _key(v) if isinstance(v, str) and ".py" in v else None)
def test_hook_reacts_to_stdin_payload(event, matcher, command, tmp_path):
    payload, cwd, project_dir, expected = CASES[_key(command)](tmp_path)
    payload.setdefault("hook_event_name", event)
    payload.setdefault("cwd", str(cwd))
    result = _run(command, payload, cwd, project_dir)
    said = (result.stdout + result.stderr).strip()
    if expected == "block":
        assert result.returncode == 2, (
            f"{_key(command)} let a must-block input through "
            f"(exit {result.returncode}); output: {said[:400]!r}")
    else:
        assert result.returncode == 0 and said, (
            f"{_key(command)} said nothing on a must-warn input "
            f"(exit {result.returncode}); output: {said[:400]!r}")


@pytest.mark.parametrize("event, matcher, command",
                         [r for r in _registered() if "Bash" in r[1].split("|")],
                         ids=lambda v: _key(v) if isinstance(v, str) and ".py" in v else None)
def test_bash_hook_allows_a_harmless_command(event, matcher, command, tmp_path):
    """Waking a hook must not turn it into one that blocks everything."""
    repo = _repo(tmp_path)
    result = _run(command, _bash("git status"), repo, repo)
    assert result.returncode == 0, f"{_key(command)} blocked `git status`: {result.stderr[:300]!r}"
