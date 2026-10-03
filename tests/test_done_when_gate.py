"""The gate that stops a work turn ending without a completion criterion.

Written because the format was proposed, used once, and silently abandoned four
turns later in the same session. CLAUDE.md and MEMORY.md already hold ~60
behavioural rules and the drift happened anyway, so this is the machine half of
incident -> rule -> MACHINE (memory/feedback-incident-rule-machine.md).

The two things that make a gate like this fail in practice are both tested
here, because each has already happened to a different check in this repo:

  * FIRING ON TURNS IT SHOULD NOT. A gate that nags after "what does this
    function do" gets switched off within a day -- the whitespace false alarm
    in test_railway_cron_drift.py is the recorded instance.
  * NEVER FIRING. A guard nobody has seen go red is not known to work
    (memory/feedback-detect-a-guard-by-forcing-its-failure.md, and DQ-30's
    "0% drift" verification that could not fail in any circumstance).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / ".claude" / "hooks" / "done-when-gate.py"

EDIT = {"type": "tool_use", "name": "Edit", "input": {}}
READ = {"type": "tool_use", "name": "Read", "input": {}}
GREP = {"type": "tool_use", "name": "Bash", "input": {"command": "grep -rn foo ."}}
COMMIT = {"type": "tool_use", "name": "Bash", "input": {"command": "git commit -m x"}}
APPLY = {"type": "tool_use", "name": "Bash",
         "input": {"command": "python scripts/dcp_commit_approved.py --apply"}}

GOOD = "DQ-115: 141 (was 176).\nDONE WHEN: the probe prints 0."


def _run(tmp_path: Path, tool: dict, text: str, stop_hook_active: bool = False) -> int:
    transcript = tmp_path / "t.jsonl"
    rows = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "do the thing"}]}},
        {"type": "assistant", "message": {"content": [tool]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}},
    ]
    transcript.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    payload = json.dumps({"transcript_path": str(transcript),
                          "stop_hook_active": stop_hook_active})
    proc = subprocess.run([sys.executable, str(GATE)], input=payload,
                          capture_output=True, text=True)
    return proc.returncode


def test_the_hook_file_exists_and_is_wired_into_settings():
    """A hook on disk that settings.json does not call is not a control."""
    assert GATE.exists(), f"{GATE} is missing"
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    stop = settings.get("hooks", {}).get("Stop")
    assert stop, "no Stop hook configured -- the gate never runs"
    assert any("done-when-gate.py" in h.get("command", "")
               for group in stop for h in group.get("hooks", [])), stop


# -- it must FIRE --------------------------------------------------------------

@pytest.mark.parametrize("tool,label", [(EDIT, "an Edit"), (COMMIT, "a git commit"),
                                        (APPLY, "a --apply run")])
def test_a_work_turn_without_a_criterion_is_blocked(tmp_path, tool, label):
    assert _run(tmp_path, tool, f"I made good progress with {label}.") == 2


def test_a_criterion_without_a_number_is_still_blocked(tmp_path):
    """"DONE WHEN: the probe prints zero" is the format without the measurement.

    The whole point is the number. Accepting the words alone would make the gate
    satisfiable by typing a phrase, which is the shape of a check that cannot
    fail.
    """
    assert _run(tmp_path, EDIT, "Rewrote it.\nDONE WHEN: the probe prints zero.") == 2


def test_a_number_buried_below_the_opening_is_blocked(tmp_path):
    """Number FIRST. A figure in paragraph six is not a report."""
    body = "I looked at several things and formed a view.\n" * 12 + "\nDONE WHEN: x prints 0."
    assert _run(tmp_path, EDIT, body) == 2


# -- it must NOT fire ----------------------------------------------------------

def test_a_work_turn_with_both_passes(tmp_path):
    assert _run(tmp_path, EDIT, GOOD) == 0


@pytest.mark.parametrize("tool,label", [(READ, "a Read"), (GREP, "a grep")])
def test_a_read_only_turn_is_exempt(tmp_path, tool, label):
    """Answering a question is not a work turn.

    A gate that demands a completion criterion for "what does this function do"
    is noise, and noise is how a check gets ignored.
    """
    assert _run(tmp_path, tool, "That function parses the table of contents.") == 0


def test_a_blocked_turn_cannot_loop(tmp_path):
    """stop_hook_active means this hook already blocked once. Never twice."""
    assert _run(tmp_path, EDIT, "no criterion here", stop_hook_active=True) == 0


# -- it must fail open ---------------------------------------------------------

@pytest.mark.parametrize("payload", ["", "not json", '{"transcript_path": "/nope/missing.jsonl"}'])
def test_bad_input_never_blocks(payload):
    """A bug in the gate must never be able to stop real work."""
    proc = subprocess.run([sys.executable, str(GATE)], input=payload,
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
