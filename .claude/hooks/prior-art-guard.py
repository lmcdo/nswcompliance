#!/usr/bin/env python3
"""
Prior-art guard — PreToolUse(Write) hook for Claude Code.

Purpose: stop the LLM re-implementing capability that already exists (the structural
"build new instead of discover+reuse" failure mode). Runs as CODE, not a rule the model
must remember to follow.

Behaviour: when a NEW code file is being created under a watched dir, it extracts the
file's "concern" (filename/route segments + top-level symbol names), searches the repo
for existing implementations of that concern, and — if it finds strong candidates —
BLOCKS the write (exit 2) and surfaces the candidates (file:line) to the model.

Escape hatch (forced acknowledgment): the write is allowed if the new file's content
contains a line matching `prior-art-checked:` — i.e. the model has SEEN the candidates
and explicitly decided to extend none of them / justified a new file. This guarantees
discovery happened; it doesn't rely on discipline.

Fail-open: any internal error -> exit 0 (never block legitimate work on a hook bug).
"""
import json
import os
import re
import subprocess
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("tool_name") != "Write":
    sys.exit(0)

ti = data.get("tool_input") or {}
fp = (ti.get("file_path") or "").replace("\\", "/")
content = ti.get("content") or ""
low = fp.lower()

# Only NEW files (overwrites of existing files are not net-new capability).
if not fp or os.path.exists(fp):
    sys.exit(0)

# Only watched code dirs / extensions; skip tests + the hook dir itself.
# Normalise to a leading-slash form so both absolute and repo-relative paths match.
low_m = "/" + low.lstrip("/")
WATCH = (
    "/services/", "/scripts/", "/frontend-nextjs/app/api/",
    "/frontend-nextjs/components/", "/frontend-nextjs/lib/", "/src/",
)
if not any(w in low_m for w in WATCH):
    sys.exit(0)
if not re.search(r"\.(py|ts|tsx)$", low_m):
    sys.exit(0)
if "/tests/" in low_m or "__tests__" in low_m or "test" in os.path.basename(low_m):
    sys.exit(0)

# Forced-acknowledgment escape hatch.
if re.search(r"prior-art-checked", content, re.I):
    sys.exit(0)

STOP = {
    "route", "index", "page", "api", "service", "services", "util", "utils",
    "helper", "helpers", "main", "app", "lib", "libs", "component", "components",
    "test", "tests", "type", "types", "model", "models", "config", "client",
    "handler", "handlers", "data", "core", "base", "common", "shared", "schema",
    "schemas", "from", "with", "this", "that", "self", "none", "true", "false",
}


def tokens(s):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)  # camelCase split
    parts = re.split(r"[^a-zA-Z0-9]+", s)
    return {p.lower() for p in parts if len(p) >= 4 and p.lower() not in STOP}


# Concern = filename (or route dir segments) + top-level symbol names.
base = os.path.basename(fp)
concern = tokens(re.sub(r"\.(py|ts|tsx)$", "", base))
if base == "route.ts":  # Next.js API route — the concern is the parent dir(s).
    segs = [s for s in fp.split("/") if s]
    concern |= tokens(" ".join(segs[-3:-1]))
head = content[:6000]
for m in re.findall(r"(?:def|class)\s+([A-Za-z_]\w+)", head):
    concern |= tokens(m)
for m in re.findall(r"export\s+(?:async\s+)?(?:function|const)\s+([A-Za-z_]\w+)", head):
    concern |= tokens(m)

concern = {t for t in concern if len(t) >= 4}
if not concern:
    sys.exit(0)
# Bound the regex (most-specific-ish: longest tokens first).
concern = set(sorted(concern, key=len, reverse=True)[:14])

root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
alt = "|".join(re.escape(t) for t in concern)

# New file's repo-relative path (to exclude from its own candidate list).
new_rel = fp
if os.path.isabs(fp) and fp.replace("\\", "/").startswith(root.replace("\\", "/")):
    new_rel = fp.replace("\\", "/")[len(root.replace("\\", "/")):].lstrip("/")

# One `git grep` pass (git is always present; auto-excludes node_modules via .gitignore;
# repo-relative forward-slash paths). Word-boundary, case-insensitive, only-matching.
# Output lines look like "path:token". Build file -> set(matched concern tokens).
file_tokens = {}
try:
    proc = subprocess.run(
        ["git", "grep", "-o", "-i", "-w", "-I", "-E", "--untracked", alt, "--",
         "*.py", "*.ts", "*.tsx",
         ":!**/tests/**", ":!**/__tests__/**", ":!*.test.*",
         ":!.claude/**", ":!**/node_modules/**"],
        cwd=root, capture_output=True, text=True, timeout=12,
    )
except Exception:
    sys.exit(0)  # fail-open

for line in proc.stdout.splitlines()[:8000]:
    if ":" not in line:
        continue
    path, tok = line.split(":", 1)
    path = path.replace("\\", "/")
    tok = tok.strip().lower()
    if tok in concern and path != new_rel:
        file_tokens.setdefault(path, set()).add(tok)

if not file_tokens:
    sys.exit(0)

# Score: path-token overlap (high signal) weighted heavily + distinct content tokens.
scored = []
for path, toks in file_tokens.items():
    path_overlap = len(concern & tokens(path))
    score = path_overlap * 5 + len(toks)
    strong = path_overlap >= 1 or len(toks) >= 3
    scored.append((score, strong, path_overlap, path, toks))

scored.sort(key=lambda x: x[0], reverse=True)
strong_hits = [s for s in scored if s[1]]

if not strong_hits:
    sys.exit(0)  # only weak keyword co-occurrence — allow silently.

# Strong candidates exist -> BLOCK and surface them. (paths are repo-relative already)
top = strong_hits[:6]
lines = []
for _, _, _, path, toks in top:
    lines.append(f"  - {path}  (shares: {', '.join(sorted(toks))})")
msg = (
    "PRIOR-ART GUARD: a new file at "
    f"{new_rel} appears to overlap existing code.\n"
    f"Concern tokens: {', '.join(sorted(concern))}\n"
    "Possible existing implementations of this concern:\n"
    + "\n".join(lines)
    + "\n\nBefore creating a NEW file: open these and REUSE/EXTEND them if they cover this.\n"
    "If a new file is genuinely justified, add a line to the file content:\n"
    "  prior-art-checked: <reuse not viable because ...; extends none of the above>\n"
    "and re-issue the Write. (This guard runs as code; it cannot be skipped silently.)"
)
print(msg, file=sys.stderr)
sys.exit(2)
