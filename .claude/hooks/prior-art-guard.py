#!/usr/bin/env python3
"""Prior-art guard — PreToolUse(Write|Edit) hook for Claude Code.

Stops the LLM re-implementing capability that already exists (the structural
"build new instead of discover+reuse" failure). Runs as CODE, not a rule.

TWO triggers:
 1. NEW code file (Write) under a watched dir — concern = filename + symbols.
 2. EDIT (or overwrite) that ADDS a data-source signature — a new fetcher def,
    an HTTP/DB call, or an external data URL. This closes the hole that let an
    ANEF fetcher be added to an EXISTING file (intelligence_brief.py) with no
    check at all — the v1 hook only fired on net-new files.

On either trigger it searches the whole repo (frontend + backend) for existing
implementations of the concern, cross-checks a known-constraint registry, and
BLOCKS (exit 2) surfacing the candidates (file:line). Forced-ack escape: a
`prior-art-checked:` line in the added content. Every block is appended to
.claude/prior-art-decisions.log so any override is visible/auditable.

Fail-open: any internal error -> exit 0 (never block legitimate work on a bug).
"""
import datetime
import json
import os
import re
import subprocess
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool = data.get("tool_name")
if tool not in ("Write", "Edit"):
    sys.exit(0)

ti = data.get("tool_input") or {}
fp = (ti.get("file_path") or "").replace("\\", "/")
if not fp:
    sys.exit(0)

if tool == "Write":
    added = ti.get("content") or ""
    is_new = not os.path.exists(fp)
else:  # Edit
    added = ti.get("new_string") or ""
    is_new = False

# Watched code dirs / extensions; skip tests + the hook dir itself.
low_m = "/" + fp.lower().lstrip("/")
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
if re.search(r"prior-art-checked", added, re.I):
    sys.exit(0)

STOP = {
    "route", "index", "page", "api", "service", "services", "util", "utils",
    "helper", "helpers", "main", "app", "lib", "libs", "component", "components",
    "test", "tests", "type", "types", "model", "models", "config", "client",
    "handler", "handlers", "data", "core", "base", "common", "shared", "schema",
    "schemas", "from", "with", "this", "that", "self", "none", "true", "false",
    "value", "field", "fetch", "query", "result", "return", "async", "await",
    "const", "function", "import", "export", "https", "http", "json",
}


def tokens(s):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)  # camelCase split
    parts = re.split(r"[^a-zA-Z0-9]+", s)
    return {p.lower() for p in parts if len(p) >= 4 and p.lower() not in STOP}


# Registry-lite: concerns that are KNOWN to already have a data source in this
# codebase. If a change's concern hits one of these, it is almost certainly a
# duplicate of an existing fetcher/route — block even on weak file matches.
KNOWN = {
    "anef", "riparian", "wetlands", "biodiversity", "flood", "bushfire",
    "heritage", "contaminated", "contamination", "subsidence", "coastal",
    "drinking", "acid", "sulfate", "strata", "cadastre", "valuation", "shadow",
    "solar", "terrain", "climate", "sepp", "setback", "zoning", "overlay",
    "tod", "lmr", "eligibility", "geocode", "geocoding",
}

concern = set()

if tool == "Write" and is_new:
    mode = "new-file"
    base = os.path.basename(fp)
    concern = tokens(re.sub(r"\.(py|ts|tsx)$", "", base))
    if base == "route.ts":  # Next.js API route — concern is the parent dir(s).
        segs = [s for s in fp.split("/") if s]
        concern |= tokens(" ".join(segs[-3:-1]))
    head = added[:6000]
    for m in re.findall(r"(?:def|class)\s+([A-Za-z_]\w+)", head):
        concern |= tokens(m)
    for m in re.findall(r"export\s+(?:async\s+)?(?:function|const)\s+([A-Za-z_]\w+)", head):
        concern |= tokens(m)
else:
    # Edit / overwrite — only act when the added content adds a DATA-SOURCE
    # signature (a new fetcher, an external HTTP/DB call, or a data URL). This
    # keeps ordinary logic edits silent and targets the real failure mode.
    SIGNATURE = re.compile(
        r"requests\.(?:get|post|put|patch|request)\s*\(|httpx\.|aiohttp|"
        r"def\s+(?:fetch|get|query|load|lookup|detect|resolve)_\w+|"
        r"def\s+\w+_field\b|"
        r"\.execute\s*\(\s*[\"']?\s*select|psycopg2\.connect|"
        r"https?://[^\s\"'`]*(?:arcgis|mapserver|featureserver|rest/services|"
        r"environment\.nsw|spatial\.nsw|portal\.|geoscape|api\.nsw|\.gov\.au)|"
        r"fetch\s*\(\s*[\"'`]https?://",
        re.I,
    )
    if not SIGNATURE.search(added):
        sys.exit(0)
    mode = "capability-add"
    for m in re.findall(r"def\s+([A-Za-z_]\w+)", added):
        concern |= tokens(m)
    for m in re.findall(r"function\s+([A-Za-z_]\w+)", added):
        concern |= tokens(m)
    for url in re.findall(r"https?://[^\s\"'`]+", added):
        concern |= tokens(url)
    for m in re.findall(r"\bfrom\s+([a-z_][a-z0-9_]+)", added, re.I):  # python imports / SQL FROM
        concern |= tokens(m)
    concern |= tokens(added[:3000])

concern = {t for t in concern if len(t) >= 4}
if not concern:
    sys.exit(0)
concern = set(sorted(concern, key=len, reverse=True)[:18])

root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
alt = "|".join(re.escape(t) for t in concern)

rr = root.replace("\\", "/")
new_rel = fp[len(rr):].lstrip("/") if fp.startswith(rr) else fp

file_tokens = {}
try:
    proc = subprocess.run(
        ["git", "grep", "-o", "-i", "-w", "-I", "-E", "--untracked", alt, "--",
         "*.py", "*.ts", "*.tsx",
         ":!tests/**", ":!**/tests/**", ":!**/__tests__/**", ":!*.test.*",
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

known_hit = concern & KNOWN

if not file_tokens and not known_hit:
    sys.exit(0)

scored = []
for path, toks in file_tokens.items():
    path_overlap = len(concern & tokens(path))
    score = path_overlap * 5 + len(toks)
    strong = path_overlap >= 1 or len(toks) >= 3 or bool(toks & KNOWN)
    scored.append((score, strong, path_overlap, path, toks))
scored.sort(key=lambda x: x[0], reverse=True)
strong_hits = [s for s in scored if s[1]]

# A KNOWN-constraint concern blocks even with only weak file hits — it is a
# documented existing data source.
if not strong_hits and not known_hit:
    sys.exit(0)

top = strong_hits[:6]
lines = [f"  - {path}  (shares: {', '.join(sorted(toks))})" for _, _, _, path, toks in top]
known_note = ""
if known_hit:
    known_note = (
        "\nKNOWN existing data source — this concern is already wired in the codebase: "
        f"{', '.join(sorted(known_hit))}. There is almost certainly a fetcher/route to reuse."
    )
msg = (
    f"PRIOR-ART GUARD ({mode}): this change to {new_rel} looks like it adds a data "
    "source / capability that may already exist.\n"
    f"Concern tokens: {', '.join(sorted(concern))}{known_note}\n"
    "Existing implementations to REUSE/EXTEND:\n"
    + ("\n".join(lines) if lines else "  (see the known-constraint note above)")
    + "\n\nOpen these FIRST and reuse them. If a new implementation is genuinely "
    "justified, add a line:\n"
    "  prior-art-checked: <reuse not viable because ...>\n"
    "to the added content and re-issue. (Runs as code — cannot be skipped silently; "
    "every block is logged to .claude/prior-art-decisions.log.)"
)

try:
    with open(os.path.join(root, ".claude", "prior-art-decisions.log"), "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "tool": tool, "mode": mode, "file": new_rel,
            "concern": sorted(concern), "known": sorted(known_hit),
            "candidates": [p for _, _, _, p, _ in top],
        }) + "\n")
except Exception:
    pass

print(msg, file=sys.stderr)
sys.exit(2)
