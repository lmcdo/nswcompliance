#!/usr/bin/env python3
"""Lint: hand-typed planning figures in shipped code and content. Named ledger, zero unlisted.

prior-art-checked: reuse not viable because this file's earlier version kept only per-file COUNTS (245 allowed on
2026-10-10, 261 by 2026-10-22) and named none of them, so nothing was ever removed; scripts/lint_hardcoded_zone_codes.py
matches zone-code lists only.

Every regulatory figure must be served from the database with its quote of the law (.claude/rules/regulatory-data.md).
A HIT is a planning number in a string, JSX text, a constant, JSON or Markdown, on a line with a planning word.

THE LEDGER (.claude/regulatory_figure_ledger.json) names every hit by file + the hit's own text:
  "open"  -- known, still to fix (read it from the database, or delete it and point to the address lookup);
  "cited" -- a verbatim quote that names its instrument AND clause on the same line (the reason says which);
  "not_regulatory" -- not a planning figure (a map bound, an image size, a price); the reason (4+ words) says what.
CI fails when: a hit is not in the ledger (a new typed figure); a ledger entry is no longer found (fixed -- remove it,
so the list stays exact); a "cited" entry's reason names no instrument + clause; the open count rises; a
`noqa: regulatory-number` carries no real reason (4+ words after "--").

    python scripts/lint_hardcoded_regulatory_numbers.py --check     # CI
    python scripts/lint_hardcoded_regulatory_numbers.py --list      # every hit, with ledger state
    python scripts/lint_hardcoded_regulatory_numbers.py --prune     # drop ledger entries that are gone (after a fix)

The target is an EMPTY open list. A green run means "no NEW typed figure and every old one is named", never "none".
The output-side proof (every served number traces to a stored rule) is a separate check.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOTS = ("frontend-nextjs/app", "frontend-nextjs/components", "frontend-nextjs/lib", "frontend-nextjs/hooks",
         "frontend-nextjs/shared", "services")
SKIP = ("__tests__", "node_modules", "/tests/", ".test.", "/test_", "/archive/", "__pycache__", ".next/")
SUFFIXES = (".ts", ".tsx", ".py", ".json", ".md", ".mdx")
LEDGER = Path(".claude") / "regulatory_figure_ledger.json"
SUPPRESS = "noqa: regulatory-number"

UNIT = r"(?:m²|m2|sqm|square metres|metres|m\b|%|spaces?|storeys?|hours?|°|degrees?)"
NUM = r"\b\d+(?:\.\d+)?"
# A number with a planning unit, an FSR ratio, a parking rate, or a number-word count.
FIGURE = (rf"{NUM}\s?{UNIT}|{NUM}\s?:\s?1\b|{NUM}\s+(?:car\s+)?(?:space|bay)s?\s+per\b"
          r"|\bper\s+\d+\s+(?:dwellings?|bedrooms?|m2|m²)"
          r"|\b(?:one|two|three|four|five)\s+(?:car\s+)?(?:spaces?|storeys?|bedrooms?)\b")
LITERAL = re.compile(rf"""(['"`][^'"`\n]*?(?:{FIGURE})[^'"`\n]*['"`])""", re.I)
JSX_TEXT = re.compile(rf""">([^<>{{}}\n]*?(?:{FIGURE})[^<>{{}}\n]*)<""", re.I)
# Markdown / JSON prose: the figure anywhere on the line (no quotes in Markdown).
PROSE = re.compile(rf"([^\n]*?(?:{FIGURE})[^\n]*)", re.I)
# Engine constants: DEFAULT_HEIGHT_M = 9.0 / maxFsr: 0.5 / MIN_LOT_AREA_M2 = 450
CONSTANT = re.compile(
    r"\b([A-Za-z_]*(?:SETBACK|HEIGHT|FSR|LOT|FRONTAGE|PARKING|COVERAGE|LANDSCAP|STOREY|SEPARATION|SOLAR|SUN)"
    r"[A-Za-z_]*\s*[:=]\s*\d+(?:\.\d+)?)", re.I)
PLANNING = re.compile(
    r"setback|height|lot|frontage|floor|FSR|parking|site area|coverage|storey|SEPP|LEP|DCP|cl\.|clause|"
    r"minimum|maximum|open space|landscap|sunlight|solar access|separation|dwelling|granny|secondary", re.I)
CITED = re.compile(r"(SEPP|LEP|DCP|Act|Regulation|Code|Guide)\b.*\b(?:s|cl|clause|section|part|schedule)\.?\s*\d", re.I)


def hits_in_text(text: str, suffix: str = ".ts") -> list[str]:
    """Every hand-typed planning figure in one file's text (each hit's text, stripped)."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("//", "#", "*", "/*")):
            continue
        if SUPPRESS in line:
            continue
        if not PLANNING.search(line):
            continue
        if suffix in (".md", ".mdx"):
            out += [m.strip() for m in PROSE.findall(line)]
            continue
        found = LITERAL.findall(line) + [t.strip() for t in JSX_TEXT.findall(line)]
        if suffix in (".py", ".ts", ".tsx"):
            found += [c for c in CONSTANT.findall(line) if not any(c in f for f in found)]
        out += found
    return [h for h in out if h]


def bad_suppressions(text: str) -> list[str]:
    """`noqa: regulatory-number` lines without a reason of at least four words after '--'."""
    bad = []
    for line in text.splitlines():
        if SUPPRESS in line:
            reason = line.split(SUPPRESS, 1)[1].lstrip(" -—:")
            if len(reason.split()) < 4:
                bad.append(line.strip()[:140])
    return bad


def _files(root: Path):
    for top in ROOTS:
        for f in (root / top).rglob("*"):
            rel = f.relative_to(root).as_posix()
            if f.is_file() and f.suffix in SUFFIXES and not any(s in "/" + rel for s in SKIP):
                yield rel, f


def scan(root: Path = Path(".")) -> tuple[dict[str, list[str]], list[str]]:
    """({file: [hit, ...]}, [bad suppressions])."""
    found: dict[str, list[str]] = {}
    bad: list[str] = []
    for rel, f in _files(root):
        text = f.read_text(encoding="utf-8", errors="replace")
        hits = hits_in_text(text, f.suffix)
        if hits:
            found[rel] = hits
        bad += [f"{rel}: {b}" for b in bad_suppressions(text)]
    return found, bad


def _norm(hit: str) -> str:
    return re.sub(r"\s+", " ", hit).strip()


def _key(file: str, hit: str) -> str:
    return file + "::" + _norm(hit)


def load_ledger(path: Path = LEDGER) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def judge(found: dict[str, list[str]], ledger: dict) -> list[str]:
    """Every reason the check fails (empty = pass). Pure."""
    entries = {_key(e["file"], e["text"]): e for e in ledger["entries"]}
    now = {_key(f, h) for f, hs in found.items() for h in hs}
    problems = [f"NOT IN LEDGER (new typed figure): {k}" for k in sorted(now - entries.keys())]
    problems += [f"GONE (fixed? run --prune): {k}" for k in sorted(entries.keys() - now)]
    for k, e in entries.items():
        if e.get("fate") == "cited" and not CITED.search(e.get("reason", "")):
            problems.append(f"CITED WITHOUT INSTRUMENT + CLAUSE: {k}")
        if e.get("fate") == "not_regulatory" and len((e.get("reason") or "").split()) < 4:
            problems.append(f"NOT_REGULATORY WITHOUT A REASON: {k}")
        if e.get("fate") not in ("open", "cited", "not_regulatory"):
            problems.append(f"BAD FATE {e.get('fate')!r}: {k}")
    open_n = sum(1 for e in entries.values() if e.get("fate") == "open")
    if open_n > ledger.get("max_open", open_n):
        problems.append(f"OPEN COUNT ROSE: {open_n} > max_open {ledger['max_open']}")
    return problems


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    found, bad = scan()
    total = sum(len(h) for h in found.values())
    if "--list" in argv:
        ledger = load_ledger() if LEDGER.exists() else {"entries": []}
        fates = {_key(e["file"], e["text"]): e["fate"] for e in ledger["entries"]}
        for f, hs in sorted(found.items()):
            for h in hs:
                print(f"{fates.get(_key(f, h), 'UNLISTED'):8s} {f}: {h}")
        print(f"{total} hit(s) in {len(found)} file(s)")
        return 0
    if "--init" in argv:  # one-off: name every current hit as open
        entries = [{"file": f, "text": re.sub(r"\s+", " ", h).strip(), "fate": "open"}
                   for f, hs in sorted(found.items()) for h in dict.fromkeys(hs)]
        LEDGER.write_text(json.dumps({"_about": __doc__.split("THE LEDGER")[1].split("    python")[0].strip(),
                                      "max_open": len(entries), "entries": entries}, indent=1, ensure_ascii=False)
                          + "\n", encoding="utf-8")
        print(f"ledger written: {len(entries)} open entries")
        return 0
    try:
        ledger = load_ledger()
    except (OSError, ValueError, KeyError) as e:
        print(f"Typed planning figures: cannot read {LEDGER} ({e}) -- refusing to pass.")
        return 1
    if "--prune" in argv:
        now = {_key(f, h) for f, hs in found.items() for h in hs}
        kept = [e for e in ledger["entries"] if _key(e["file"], e["text"]) in now]
        ledger["entries"] = kept
        ledger["max_open"] = sum(1 for e in kept if e["fate"] == "open")
        LEDGER.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"pruned to {len(kept)} entries; max_open {ledger['max_open']}")
        return 0
    problems = judge(found, ledger) + [f"SUPPRESSION WITHOUT A REASON: {b}" for b in bad]
    open_n = sum(1 for e in ledger["entries"] if e["fate"] == "open")
    if problems:
        print(f"Typed planning figures: FAILED ({len(problems)} problem(s)).")
        print("  Serve the figure from the database with its quote of the law, or delete it and point to the address")
        print("  lookup. A verbatim quote that names its instrument and clause may be listed as 'cited'.")
        for p in problems[:200]:
            print(f"  {p}")
        return 1
    print(f"Typed planning figures: OK -- 0 unlisted; {open_n} open still to fix (target 0).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
