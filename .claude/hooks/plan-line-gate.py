#!/usr/bin/env python3
"""PreToolUse hook -- no pipeline edit until the owner has answered a PLAN: line.

WHY THIS EXISTS
---------------
2026-11-03: the prior-art guard stopped an edit to scripts/dcp_extract_changed.py, and the
assistant wrote its escape line without opening the approved plan it was meant to check
(ce-dcp-section-updater-PLAN-2026-10-26.md). Third retrieve-before-acting miss that day.
A check the assistant can satisfy alone is not a gate. A message from the owner is the one
thing it cannot write: Claude Code stamps it origin.kind == "human" in the transcript.

WHAT IT DOES
------------
Before an Edit/Write to a pipeline file, or a Bash/PowerShell command that writes one:
  1. find the newest assistant line starting `PLAN:` in this session's transcript;
  2. it must name a ~/.claude/plans/*.md file that a Read call opened in this session,
     or say `PLAN: none` (no plan covers this -- the owner decides);
  3. a HUMAN message must come after that line. A newer PLAN: line needs a new answer.
Otherwise BLOCK, and print the plans that name the file, so they are in front of you.

It also blocks any command or edit that touches the transcript files themselves: forging a
human line is the obvious way round step 3.

Exit codes:  0 = allow   2 = block (message on stderr)
"""
import json
import os
import re
import sys
from pathlib import Path

PIPELINE = (
    "scripts/dcp_extract_changed.py", "scripts/ai_extractor.py", "scripts/dcp_commit_approved.py",
    "scripts/r2_monitor.py", "scripts/add_new_chapter.py", "scripts/council_quote.py",
    "scripts/council_quote_db.py", "scripts/dcp_page_repair.py", "scripts/pipeline_run.py",
    "migrations/",
)
WRITES = re.compile(r"(sed\s+-i|>\s*\S|write_text|\.write\(|open\([^)]*['\"][wa]|tee\s|cp\s|mv\s|"
                    r"Set-Content|Out-File|Add-Content)", re.I)
PLAN_LINE = re.compile(r"^[ 	*>_-]*PLAN:[*_]*\s+(.+)$", re.M)   # a line that IS a plan line, not one quoting it
PLANS_DIR = Path(os.path.expanduser("~/.claude/plans"))
TRANSCRIPTS = re.compile(r"[\\/]\.claude[\\/]projects[\\/][^\s'\"]*\.jsonl", re.I)


def _payload() -> dict:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def _norm(p: str) -> str:
    return p.replace("\\", "/")


def touched_pipeline(tool: str, ti: dict) -> list[str]:
    """Pipeline files this tool call would change."""
    if tool in ("Edit", "Write", "NotebookEdit"):
        path = _norm(ti.get("file_path", ""))
        return [p for p in PIPELINE if p in path]
    if tool in ("Bash", "PowerShell"):
        cmd = _norm(ti.get("command", ""))
        if not WRITES.search(cmd):
            return []
        return [p for p in PIPELINE if p in cmd]
    return []


def touches_transcript(tool: str, ti: dict) -> bool:
    text = ti.get("command", "") if tool in ("Bash", "PowerShell") else ti.get("file_path", "")
    return bool(TRANSCRIPTS.search(text or ""))


def _entries(transcript: str):
    try:
        with open(transcript, encoding="utf-8") as fh:
            for line in fh:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def _text(e: dict) -> str:
    c = (e.get("message") or {}).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(b.get("text", "") for b in c if b.get("type") == "text")
    return ""


def _reads(e: dict) -> list[str]:
    c = (e.get("message") or {}).get("content")
    if not isinstance(c, list):
        return []
    return [_norm((b.get("input") or {}).get("file_path", "")) for b in c
            if b.get("type") == "tool_use" and b.get("name") == "Read"]


def verdict(transcript: str) -> str | None:
    """None to allow, else the reason to block."""
    plan, plan_idx, human_after, read = None, -1, False, set()
    for i, e in enumerate(_entries(transcript)):
        if e.get("type") == "assistant":
            read.update(_reads(e))
            for m in PLAN_LINE.finditer(_text(e)):
                plan, plan_idx, human_after = m.group(1).strip(), i, False
        elif e.get("type") == "user" and (e.get("origin") or {}).get("kind") == "human" and plan_idx >= 0:
            human_after = True
    if plan is None:
        return "no PLAN: line in this session"
    if not re.match(r"none\b", plan, re.I):
        names = re.findall(r"([\w.-]+\.md)", plan)
        if not names:
            return f"the PLAN: line names no plan file ({plan[:80]!r}); name one, or write PLAN: none"
        if not any(_norm(str(PLANS_DIR / n)).lower() in {r.lower() for r in read} or
                   any(r.lower().endswith("/plans/" + n.lower()) for r in read) for n in names):
            return f"the plan named ({', '.join(names)}) was not opened with Read in this session"
    if not human_after:
        return "the owner has not answered the newest PLAN: line yet"
    return None


def plans_naming(files: list[str]) -> list[str]:
    hits = []
    for p in sorted(PLANS_DIR.glob("*.md")):
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(Path(f).name in t for f in files if not f.endswith("/")):
            hits.append(p.name)
    return hits[-8:]


def main() -> int:
    data = _payload()
    tool, ti = data.get("tool_name", ""), data.get("tool_input") or {}
    if touches_transcript(tool, ti):
        print("BLOCKED (plan-line-gate): commands and edits may not touch the session transcripts "
              "(.claude/projects/*.jsonl). The owner's answers live there.", file=sys.stderr)
        return 2
    files = touched_pipeline(tool, ti)
    if not files:
        return 0
    reason = verdict(data.get("transcript_path", ""))
    if reason is None:
        return 0
    plans = plans_naming(files)
    print(f"BLOCKED (plan-line-gate): {reason}.\n"
          f"This changes pipeline file(s): {', '.join(files)}.\n"
          "Open the approved plan, then post one line `PLAN: <plan file> -- <section it implements>`"
          " (or `PLAN: none`) and WAIT for the owner's answer.\n"
          + ("Plans that name these files:\n  " + "\n  ".join(plans) if plans else
             "No plan in ~/.claude/plans names these files."), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
