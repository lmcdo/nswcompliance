#!/usr/bin/env python3
"""PreToolUse hook -- a throwaway script may not write the rule tables.

WHY THIS EXISTS
---------------
2026-10-29 and 2026-11-02: 122 rows of dcp_setback_controls were rewritten by scratchpad
scripts (write_batch1.py ... write_batch5.py, repage.py) that picked a sentence off the PDF
and UPDATEd source_text directly, then released the rows. None of it went through the
extractor, so none of it could say which run made it. 73 rows were rolled back 2026-11-03.
No hook looked at database writes: a hook sees `python x.py`, not the SQL inside x.py.

WHAT IT DOES
------------
For a Bash/PowerShell command that runs Python, it reads what Python will run:
  * a .py file that is NOT tracked in this repo (scratchpad, temp, Downloads...), or
  * inline code (`python - <<EOF`, `python -c "..."`)
and BLOCKS it when that code writes dcp_setback_controls, regulatory_provisions or
dcp_chapter_registry (UPDATE / INSERT INTO / DELETE FROM / TRUNCATE).

Tracked repo scripts are allowed: they are reviewed code, and migration 121's trigger logs
every write they make (run or no run). Rule writes belong in the pipeline:
dcp_extract_changed.py --review -> review queue -> dcp_commit_approved.py.

Override, for a decided and recorded emergency only: put RULE_WRITE_OK="<reason>" in the
command. It is appended to .claude/.rule-write-overrides.log.

Exit codes:  0 = allow   2 = block (message on stderr)
"""
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TABLES = r"(?:public\.)?(?:dcp_setback_controls|regulatory_provisions|dcp_chapter_registry)"
WRITE = re.compile(rf"\b(?:update\s+{TABLES}\b|insert\s+into\s+{TABLES}\b|"
                   rf"delete\s+from\s+{TABLES}\b|truncate\s+(?:table\s+)?{TABLES}\b)", re.I)
PYTHON = re.compile(r"(?:^|[\s;&|(])(?:python3?|py)(?:\.exe)?\s+(.*)", re.I)
OVERRIDE = re.compile(r"RULE_WRITE_OK=(['\"])(.+?)\1")


def _payload() -> dict:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def _repo() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def _tracked(path: Path, repo: Path) -> bool:
    try:
        rel = path.resolve().relative_to(repo)
    except ValueError:
        return False                       # outside the repo: never reviewed code
    r = subprocess.run(["git", "ls-files", "--error-unmatch", str(rel)], cwd=repo,
                       capture_output=True, text=True, timeout=10)
    return r.returncode == 0


def _scripts(command: str) -> list[str]:
    """The .py paths a command hands to Python."""
    found = []
    for m in PYTHON.finditer(command):
        try:   # posix=False: posix mode eats the backslashes in C:\Users\... paths
            words = shlex.split(m.group(1), posix=False)
        except ValueError:
            words = m.group(1).split()
        for w in (x.strip("'\"") for x in words):
            if w.startswith("-"):
                continue
            if w.lower().endswith(".py"):
                found.append(w)
            break                          # only the first operand is the script
    return found


def _resolve(word: str, cwd: Path) -> Path:
    w = os.path.expandvars(os.path.expanduser(word))
    if re.match(r"^/[a-zA-Z]/", w):        # git-bash /c/Users/... -> C:/Users/...
        w = w[1].upper() + ":" + w[2:]
    p = Path(w)
    return p if p.is_absolute() else cwd / p


def verdict(command: str, cwd: Path, repo: Path) -> str | None:
    """None to allow, else the reason to block."""
    if not PYTHON.search(command):
        return None
    inline = re.search(r"(?:python3?|py)(?:\.exe)?\s+(?:-\s|-c\b|-\s*<<|-$)", command, re.I | re.M)
    if inline and WRITE.search(command):   # `python - <<EOF` / `python -c` carrying the SQL
        return "inline Python in this command writes a rule table"
    for word in _scripts(command):
        path = _resolve(word, cwd)
        if not path.is_file() or _tracked(path, repo):
            continue
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if WRITE.search(src):
            return f"{path} is not a tracked repo script and it writes a rule table"
    return None


def main() -> int:
    data = _payload()
    if data.get("tool_name") not in ("Bash", "PowerShell"):
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    repo = _repo()
    cwd = Path(data.get("cwd") or os.getcwd())
    reason = verdict(command, cwd, repo)
    if reason is None:
        return 0
    ov = OVERRIDE.search(command)
    if ov:
        log = repo / ".claude" / ".rule-write-overrides.log"
        with log.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()}\t{ov.group(2)}\t{reason}\t{command[:300]}\n")
        return 0
    print(
        f"BLOCKED (scratchpad-rule-write-guard): {reason}.\n"
        "Rule text, numbers, pages, proofs and registry rows change only through the pipeline "
        "(dcp_extract_changed.py --review -> review queue -> dcp_commit_approved.py), so every "
        "row can name the run that made it. Scripts may MEASURE and PROPOSE; they never write.\n"
        "If this is a decided emergency (e.g. restoring a backup), add RULE_WRITE_OK=\"<reason>\" "
        "to the command; it is logged.",
        file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
