"""The ledger must not contain control characters.

WHY
---
DQ-76's note documents a defect whose signature is a set of TeX command names.
Written in a Python string, "\\frac" is a formfeed followed by "rac", "\\ast" is
a bell followed by "st", and "\\bullet" is a backspace followed by "ullet". The
note then no longer contains the tokens it claims to record, and a search for
the actual defect signature misses the very row that documents it.

This happened twice: once when the note was first written, and again when I
swept the file clean and then REWROTE the note in Python, reintroducing them.
A guard costs less than remembering.

NO C0 control character is allowed, tab and newline included. That looks strict
until you see the failure it catches: "\\textrm" single-escaped becomes a TAB
followed by "extrm", and "\\newline" becomes a NEWLINE followed by "ewline". An
allowance for whitespace is therefore an allowance for exactly the tokens
beginning t, r, n and v - which is most of the ones worth documenting.

JSON's own formatting whitespace sits BETWEEN string values, not inside them,
so nothing about the file's readability depends on this. Measured before
tightening: zero control characters currently appear inside any string value in
the ledger, so the rule costs nothing today.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / ".claude" / "dq_checks.json"

#: Deliberately empty. A tab inside a string VALUE means a TeX token lost its
#: backslash - there is no benign source of one in this file.
ALLOWED: set[str] = set()


def _strings(obj, path="$"):
    """Every string in the document, with a path for a readable failure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def test_ledger_contains_no_control_characters():
    doc = json.loads(LEDGER.read_text(encoding="utf-8"))
    offenders = []
    for path, s in _strings(doc):
        bad = {c for c in s if ord(c) < 32 and c not in ALLOWED}
        if bad:
            offenders.append((path, sorted(hex(ord(c)) for c in bad)))
    assert not offenders, (
        "control characters in the ledger - a TeX token was single-escaped in "
        "the JSON source, so it no longer reads as the command it documents:\n"
        + "\n".join(f"  {p}: {codes}" for p, codes in offenders))


def test_dq76_note_still_names_the_refused_commands():
    """The note's value IS the token list; assert it survived encoding."""
    doc = json.loads(LEDGER.read_text(encoding="utf-8"))
    note = doc["checks"]["DQ-76"]["note"]
    backslash = chr(92)
    for token in ("div", "frac", "phantom", "cdot", "ast", "begin", "dag"):
        assert backslash + token in note, (
            f"{token!r} lost its backslash in the DQ-76 note, so the recorded "
            f"signature no longer matches the defect")


def test_the_guard_can_fail():
    """Prove the check is not vacuously true."""
    sample = {"note": "a tab here:" + chr(9) + "extrm"}   # 	extrm mis-escaped
    offenders = [p for p, s in _strings(sample)
                 if any(ord(c) < 32 and c not in ALLOWED for c in s)]
    assert offenders, "the guard would not notice a real control character"
