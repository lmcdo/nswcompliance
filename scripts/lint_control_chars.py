"""Fail when a source file contains an invisible control character.

`\b` written through a shell heredoc or a non-raw string becomes a backspace (0x08). Twice on
2026-10-19 that turned a regex word boundary into a character that never matches, silently:
the dwelling-house pattern in services/constraint_arithmetic.py, and the "In <place>" pattern in
scripts/address_audit/flag_packets.py (missed for weeks). Nothing visible in a diff shows it.

Allowed: tab, newline, carriage return. Usage:
    python scripts/lint_control_chars.py            # every tracked source file
    python scripts/lint_control_chars.py --staged   # staged files only (pre-commit)
Exit 1 with file:line for each hit.

prior-art-checked: no existing lint looks for control characters (grep 'x08|control char' scripts/).
"""
from __future__ import annotations

import re
import subprocess
import sys

BAD = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
EXT = (".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".sql", ".sh", ".json", ".md", ".yml", ".yaml")


def files(staged: bool) -> list[str]:
    cmd = (["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"] if staged else ["git", "ls-files"])
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.split("\n")
    return [f for f in out if f.endswith(EXT) and "node_modules/" not in f]


def main(argv: list[str]) -> int:
    hits = []
    for f in files("--staged" in argv):
        try:
            data = open(f, "rb").read()
        except OSError:
            continue
        for n, line in enumerate(data.split(b"\n"), 1):
            m = BAD.search(line)
            if m:
                hits.append(f"{f}:{n}: control character 0x{m.group(0)[0]:02x} (write \b etc. as a raw string)")
    for h in hits:
        print(h)
    if hits:
        print(f"FAILED: {len(hits)} invisible control character(s) in source.")
        return 1
    print("OK: no control characters in source.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
