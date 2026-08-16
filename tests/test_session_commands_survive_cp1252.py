"""The commands every session is told to run must not crash on Windows.

prior-art-checked: no existing test covers this. Swept tests/ for cp1252,
win32, UnicodeEncodeError and reconfigure — zero hits — and for any test
enumerating the session-critical scripts (check_data_watch_freshness,
verify_coverage_stats) — zero hits. tests/test_ledger_has_no_control_chars.py
is the nearest neighbour and is deliberately NOT extended: it constrains what
may be WRITTEN into the ledger (control characters), whereas this constrains
what the readers can SURVIVE printing. U+26A0 is legal ledger content and
passes that test; it is what crashed the reader.

ORIGIN, 2026-08-16. `python scripts/dq_check.py --report` — the first command
CURRENT-AIM tells every session to run — aborted part-way through with
UnicodeEncodeError on Windows. stdout is cp1252 in both PowerShell and Git
Bash on the dev machine (PYTHONUTF8 and PYTHONIOENCODING both unset), and
.claude/dq_checks.json carries U+26A0 in two notes.

WHY THIS TEST IS BEHAVIOURAL AND NOT STRUCTURAL. Three earlier attempts to
decide "is this file protected?" by looking at its SHAPE were each wrong, and
each was wrong in the direction that reports a broken file as fine:

  1. A grep for `win32` said six files lacked the guard. Three of those were
     already protected — they use an unconditional call with no platform
     branch.
  2. An AST matcher for `sys.stdout.reconfigure(...)` walked the whole tree,
     so a call moved into a function nobody calls still counted. Measured: a
     source whose only call sat inside `def configure():` was reported present.
  3. The same matcher accepted any encoding containing "utf" — including
     utf-16, utf-7, and `not-utf`, which is not a codec and raises LookupError
     the moment the script starts. It ALSO missed scripts/dq_check.py, which
     is protected through `_reconfigure = getattr(sys.stdout, "reconfigure")`
     (added by #964) and matches no `sys.stdout.reconfigure` pattern at all.

So this does not inspect the code. It imports each script in a subprocess whose
stdout really is cp1252, prints the characters that crashed it, and checks the
process survived. Any idiom that works passes; any that does not, fails. That
is the property we actually want, rather than a proxy for it.

VERIFIED ABLE TO FAIL, against the real pre-fix code at origin/main:
dq_probe_live, verify_coverage_stats, check_data_watch_freshness, cross_review
and qa_gate each raised `UnicodeEncodeError: 'charmap' codec can't encode
character '\\u26a0'` and now survive. dq_check.py survived even before this
branch — it was already fixed by #964 — which is why this branch adds nothing
to it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

#: The seven distinct scripts named by CURRENT-AIM's "ASK THESE, DO NOT ASK
#: THIS FILE" table (read 2026-08-17), plus two more:
#:
#:   - dq_probe_live.py, which the same file reaches for outside the table
#:     ("Run the DQ-32 probe for the current counts") and which dq_check.py
#:     drives per row to enforce a status; and
#:   - qa_gate.py, which is not a session command at all but runs inside
#:     .githooks/pre-push, where a crash fails the push for the wrong reason.
#:
#: What the last two have in common with cross_review.py is the reason all
#: three are here: they print text they do not author — a report's prose, a
#: probe's message, a finding from another model — so they cannot predict the
#: characters they will be asked to encode.
SESSION_COMMANDS = [
    "scripts/dq_check.py",
    "scripts/dq_probe_live.py",
    "scripts/check_dcp_as_at_coverage.py",
    "scripts/check_satellite_manifests.py",
    "scripts/verify_coverage_stats.py",
    "scripts/check_data_watch_freshness.py",
    "scripts/check_served_answer_quality.py",
    "scripts/cross_review.py",
    "scripts/qa_gate.py",
]

#: The three that actually turned up in .claude/dq_checks.json and in review
#: findings: a warning sign, an arrow and a tick. None encode in cp1252.
CRASHING_CHARS = "⚠ → ✓"

#: Imports the target by path with a genuinely cp1252 stdout, then prints the
#: characters that crashed the real run. Exits 0 only if both survive.
#:
#: `errors="strict"` is the point — it reproduces the console default rather
#: than a forgiving stand-in. Without it every script would pass regardless.
_PROBE = '''
import importlib.util, io, pathlib, sys
sys.path.insert(0, sys.argv[2])
sys.path.insert(0, str(pathlib.Path(sys.argv[1]).resolve().parent))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="cp1252", errors="strict")
spec = importlib.util.spec_from_file_location("_probe_target", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print({chars!r})
'''


def _run_probe(script: Path) -> subprocess.CompletedProcess:
    """Import `script` under a cp1252 stdout and try to print the bad chars."""
    return subprocess.run(
        [sys.executable, "-c", _PROBE.format(chars=CRASHING_CHARS), str(script), str(REPO)],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.parametrize("rel", SESSION_COMMANDS)
def test_session_command_survives_a_cp1252_console(rel: str) -> None:
    path = REPO / rel
    assert path.exists(), (
        f"{rel} is listed as a session command but does not exist. Either the "
        f"script was renamed and this list is stale, or CURRENT-AIM now names "
        f"a command nobody can run."
    )

    result = _run_probe(path)

    assert "UnicodeEncodeError" not in result.stderr, (
        f"{rel} dies on a cp1252 console — the default in both PowerShell and "
        f"Git Bash on the machine these commands are run from. One character "
        f"outside cp1252 (an arrow, a tick, a warning sign, in text this "
        f"script may not even author) aborts the run part-way through, which "
        f"reads as a short report rather than as a crash.\n"
        f"    Add, at module level, after `import sys`:\n"
        f'        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")\n'
        f"    stderr tail: {result.stderr.strip()[-400:]}"
    )
    assert result.returncode == 0, (
        f"{rel} could not be imported at all, so whether it survives a cp1252 "
        f"console is unknown — which is NOT the same as passing.\n"
        f"    stderr tail: {result.stderr.strip()[-400:]}"
    )


def test_the_probe_can_fail() -> None:
    """A test that cannot fail asserts nothing. Prove this one can.

    Written as a script with no reconfigure at all — the exact state the five
    fixed files were in at origin/main — and confirmed to reproduce the real
    error, not merely a non-zero exit.
    """
    unprotected = REPO / "tests" / "_tmp_unprotected_probe_target.py"
    unprotected.write_text("VALUE = 1\n", encoding="utf-8")
    try:
        result = _run_probe(unprotected)
        assert result.returncode != 0, "the probe passed a script with no guard"
        assert "UnicodeEncodeError" in result.stderr, (
            f"the probe failed for the wrong reason: {result.stderr.strip()[-400:]}"
        )
    finally:
        unprotected.unlink()


def test_the_probe_requires_a_real_import() -> None:
    """A script that cannot be imported must not be recorded as surviving.

    The failure mode that makes a green suite meaningless: the probe crashes
    early, never reaches the print, and "no UnicodeEncodeError" then looks
    exactly like success. The returncode assertion above is what separates
    them, so it is pinned here.
    """
    broken = REPO / "tests" / "_tmp_broken_probe_target.py"
    broken.write_text("raise RuntimeError('cannot import')\n", encoding="utf-8")
    try:
        result = _run_probe(broken)
        assert result.returncode != 0
        assert "UnicodeEncodeError" not in result.stderr
        assert "cannot import" in result.stderr
    finally:
        broken.unlink()
