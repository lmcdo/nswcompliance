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

WHY A STRUCTURAL TEST AND NOT A REPRO. By the time it was investigated the
crash no longer reproduced — not because it was fixed, but because both notes
holding the character belong to RESOLVED rows and --report only prints
unresolved ones. A regression test pinned to that data would go green for the
same accidental reason. So this asserts the RECONFIGURE exists, which does not
depend on which rows happen to be open today.

WHAT IT DOES NOT ASSERT: the form. Two idioms are in use here — unconditional
(the three check_* scripts) and `if sys.platform == "win32":` (the Fly monitor,
add_new_chapter). Both fix the crash, so both pass. Asserting one idiom failed
three correctly-protected files on the first run of this test.

The check is AST-based on purpose. A text search would match the explanatory
comment sitting directly above each call and pass on a file whose call had
been deleted — the precise false positive that hit the unit-order guard on
2026-08-16 (see tests/test_numeric_extractor_unit_order.py). Comments are not
in the AST, so they cannot satisfy this.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

#: Every script CURRENT-AIM's "ASK THESE, DO NOT ASK THIS FILE" table names,
#: plus the two pieces of push-hook infrastructure that print text they do not
#: author (a review finding, a report's prose) and so cannot predict the
#: characters they must encode.
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


def _is_sys_stdout_reconfigure(node: ast.AST) -> bool:
    """True for a call to ``sys.stdout.reconfigure(...)`` asking for UTF-8."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "reconfigure":
        return False
    stdout = func.value
    if not isinstance(stdout, ast.Attribute) or stdout.attr != "stdout":
        return False
    if not isinstance(stdout.value, ast.Name) or stdout.value.id != "sys":
        return False
    # A reconfigure() that does not set a UTF-8 encoding does not fix this.
    for kw in node.keywords:
        if kw.arg == "encoding" and isinstance(kw.value, ast.Constant):
            return "utf" in str(kw.value.value).lower()
    return False


def reconfigure_lineno(source: str) -> int | None:
    """Line of the stdout reconfigure call, or None if there isn't one.

    Structural, so an explanatory comment naming ``reconfigure`` cannot satisfy
    it — comments never reach the AST.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    lines = [n.lineno for n in ast.walk(tree) if _is_sys_stdout_reconfigure(n)]
    return min(lines) if lines else None


def _import_sys_lineno(tree: ast.Module) -> int | None:
    lines = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "sys"
    ]
    return min(lines) if lines else None


@pytest.mark.parametrize("rel", SESSION_COMMANDS)
def test_session_command_configures_stdout(rel: str) -> None:
    path = REPO / rel
    assert path.exists(), (
        f"{rel} is listed as a session command but does not exist. Either the "
        f"script was renamed and this list is stale, or CURRENT-AIM now names "
        f"a command nobody can run."
    )
    assert reconfigure_lineno(path.read_text(encoding="utf-8")) is not None, (
        f"{rel} prints to a stdout that is cp1252 on Windows and never "
        f"reconfigures it. One character outside cp1252 — an arrow, a tick, a "
        f"warning sign, in text this script may not even author — aborts the "
        f"run with UnicodeEncodeError instead of printing.\n"
        f"    Add, after `import sys`:\n"
        f'        sys.stdout.reconfigure(encoding="utf-8", errors="replace")'
    )


@pytest.mark.parametrize("rel", SESSION_COMMANDS)
def test_reconfigure_comes_after_import_sys(rel: str) -> None:
    """A reconfigure above `import sys` raises NameError before it can help."""
    source = (REPO / rel).read_text(encoding="utf-8")
    tree = ast.parse(source)
    sys_line = _import_sys_lineno(tree)
    call_line = reconfigure_lineno(source)
    assert sys_line is not None, f"{rel}: reconfigure needs `import sys`"
    assert call_line is not None and call_line > sys_line, (
        f"{rel}: reconfigure is at line {call_line}, not below `import sys` "
        f"at line {sys_line} — it would raise NameError at import."
    )


def test_the_detector_can_fail() -> None:
    """The detector must be able to return None, or it asserts nothing."""
    assert reconfigure_lineno("import sys\nprint('hi')\n") is None
    # Both idioms in use in this repo must pass.
    assert reconfigure_lineno(
        'import sys\nsys.stdout.reconfigure(encoding="utf-8", errors="replace")\n'
    ) == 2
    assert reconfigure_lineno(
        'import sys\n'
        'if sys.platform == "win32":\n'
        '    sys.stdout.reconfigure(encoding="utf-8")\n'
    ) == 3


def test_reconfigure_without_utf8_is_not_enough() -> None:
    """Calling reconfigure while leaving the encoding alone fixes nothing."""
    assert reconfigure_lineno(
        'import sys\nsys.stdout.reconfigure(line_buffering=True)\n'
    ) is None
    assert reconfigure_lineno(
        'import sys\nsys.stdout.reconfigure(encoding="cp1252")\n'
    ) is None


def test_a_comment_naming_reconfigure_is_not_a_call() -> None:
    """The false positive a text search would produce, pinned.

    Every protected file in this repo carries a comment explaining the call.
    A grep-based check would pass on this source, which has the words and none
    of the behaviour — and a grep is exactly how the first audit for this fix
    mis-classified three files.
    """
    source = (
        "import sys\n"
        "# We would normally sys.stdout.reconfigure(encoding='utf-8') here\n"
        '# because sys.platform == "win32" means cp1252. We do not, yet.\n'
        "print('hi')\n"
    )
    assert "reconfigure" in source and "utf-8" in source
    assert reconfigure_lineno(source) is None
