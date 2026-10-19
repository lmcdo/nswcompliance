"""One producer per fact — ratchet against NEW copies of code that derives a shared fact.

Rule (user ruling 2026-10-19): common data is served through ONE common pipeline. Today most shared
facts have several producers (docs/page_integrity/PRODUCER_MAP.md: 26 of 27 facts, ~241 sites) —
that is how the yield box and the DCP tab disagreed on one page. Consolidation is Phase 5 of
~/.claude/plans/ce-page-integrity-check-PLAN-2026-10-19.md. Until then this lint stops it growing:

  - patterns: scripts/page_integrity/producer_patterns.json  {fact: {ts: [regex], py: [regex]}}
    (regexes match producer DEFINITIONS/derivations, from the producer map's LINT PATTERNS)
  - baseline: scripts/page_integrity/producer_baseline.json  {fact: {file: hit_count}}

RED (exit 1) when any file's hit count for a fact rises, or a new file starts producing a fact.
A count that FALLS is reported as "released" — run with --update to lock the lower number in
(shrink-only: --update refuses to raise any count unless --allow-raise is given with a reason).
Exit 2 if a scope directory is missing (could not look; never a pass).

prior-art-checked: no producer-duplication lint exists; scripts/check_test_quarantine.py is the
ratchet pattern followed here.

Usage:
    python scripts/page_integrity/lint_producers.py            # check
    python scripts/page_integrity/lint_producers.py --update   # lock in released counts
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATTERNS = HERE / "producer_patterns.json"
BASELINE = HERE / "producer_baseline.json"

SCOPES = {
    "ts": (["frontend-nextjs/app", "frontend-nextjs/lib", "frontend-nextjs/components", "frontend-nextjs/hooks"],
           (".ts", ".tsx")),
    "py": (["services", "scripts/conveyancing_db.py", "scripts/generate_conveyancing_report.py"], (".py",)),
}
EXCLUDE = re.compile(r"(^|/)(node_modules|__tests__|archive|\.next)(/|$)|\.test\.|spike|RELEVANCE_DRAFT|\.backup$")


def _files(root: Path, lang: str) -> list[Path]:
    dirs, exts = SCOPES[lang]
    out: list[Path] = []
    for d in dirs:
        p = root / d
        if not p.exists():
            raise FileNotFoundError(f"scope missing: {d}")
        cands = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file()]
        for f in cands:
            rel = f.relative_to(root).as_posix()
            if f.suffix in exts and not EXCLUDE.search(rel):
                out.append(f)
    return out


def count_hits(root: Path, patterns: dict) -> dict[str, dict[str, int]]:
    """{fact: {file: number of lines matching any of the fact's patterns}}."""
    compiled = {fact: {lang: [re.compile(p) for p in pats] for lang, pats in by_lang.items()}
                for fact, by_lang in patterns.items()}
    hits: dict[str, dict[str, int]] = defaultdict(dict)
    for lang in SCOPES:
        for f in _files(root, lang):
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
            rel = f.relative_to(root).as_posix()
            for fact, by_lang in compiled.items():
                regs = by_lang.get(lang) or []
                if not regs:
                    continue
                n = sum(1 for line in lines if any(r.search(line) for r in regs))
                if n:
                    hits[fact][rel] = n
    return {k: dict(sorted(v.items())) for k, v in sorted(hits.items())}


def compare(baseline: dict, now: dict) -> tuple[list[str], list[str]]:
    """(grown, released) — grown makes the lint red."""
    grown, released = [], []
    for fact in sorted(set(baseline) | set(now)):
        b, n = baseline.get(fact, {}), now.get(fact, {})
        for f in sorted(set(b) | set(n)):
            was, isnow = b.get(f, 0), n.get(f, 0)
            if isnow > was:
                grown.append(f"{fact}: {f} {was} -> {isnow}")
            elif isnow < was:
                released.append(f"{fact}: {f} {was} -> {isnow}")
    return grown, released


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update", action="store_true", help="lock in released (lower) counts")
    ap.add_argument("--allow-raise", metavar="REASON", help="with --update: accept higher counts (state why)")
    a = ap.parse_args(argv)
    patterns = json.loads(PATTERNS.read_text(encoding="utf-8"))
    try:
        now = count_hits(root, patterns)
    except FileNotFoundError as e:
        print(f"COULD NOT LOOK: {e}")
        return 2
    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    grown, released = compare(baseline, now)
    total = sum(sum(v.values()) for v in now.values())
    print(f"producer sites: {total} across {len(now)} facts (target: one producer per fact)")
    if a.update:
        if grown and not a.allow_raise:
            print("REFUSED: counts rose (shrink-only). Consolidate instead, or --allow-raise 'reason'.")
            for g in grown:
                print("  +", g)
            return 1
        BASELINE.write_text(json.dumps(now, indent=1) + "\n", encoding="utf-8")
        print(f"baseline written ({len(released)} released, {len(grown)} raised)")
        return 0
    for r in released:
        print("  released (run --update):", r)
    if grown:
        print("RED: new copies of a shared-fact producer. Use the fact's existing producer instead:")
        for g in grown:
            print("  +", g)
        return 1
    print("OK: no new producer copies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
