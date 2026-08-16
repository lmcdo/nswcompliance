#!/usr/bin/env python3
"""Lint: detect hardcoded NSW zone-code lists in staged Python/TypeScript diffs.

prior-art-checked: this is a CI/pre-commit lint script, not a data source or
capability — the guard's suggested matches (upzoning-check, CDC/duplex check
routes, services/upzoning_check.py) are unrelated live features that matched
only on generic words ("check", "zone", "line"). The actual prior art for
THIS script's shape is scripts/lint_bracket_access.py (same staged-diff /
--all dual-mode pattern, same `# noqa:` suppression convention), already
investigated in DQ-30 (.claude/DATA_QUALITY_TRACKER.md) and followed here
deliberately rather than reused directly (different regex/target).

DQ-30: this class of bug happened twice independently in this codebase before
a shared source of truth existed — `dcp_general_requirements`/
zone-translation.ts (Nov 2025) and the DCP applicability tagger + ~20 other
call sites (2026-07). Both times, a hardcoded zone-code array quietly went
stale after the April 2023 NSW Employment Zones Reform retired B1-B8/IN1-IN4
in favour of E1-E5/MU1. This check exists so a third instance fails at commit
time instead of shipping.

Only checks NEW lines (+ lines in git diff) in staged .py/.ts/.tsx files.
Flags: an array/set/tuple literal containing >=2 NSW zone-code tokens,
UNLESS the same file already imports the shared taxonomy source
(shared/zone-taxonomy.json via zone-translation.ts or
enrichment/config/zone_taxonomy.py) or the array is assigned to a
part/chapter/section-labelled key (those are DCP structure keys, not zone
codes — see the Waverley `universalPartKeys: ["B1"..."B17"]` false positive
this check was specifically designed not to flag).

Suppress per-line with:  # noqa: zone-codes  /  // noqa: zone-codes

Exit 0 = clean, exit 1 = violations found.
"""

import os
import re
import subprocess
import sys

ZONE_TOKEN_RE = re.compile(
    r'\b(?:R[1-5]|RU[1-6]|B[1-8]|IN[1-4]|E[1-5]|MU1|C[1-4]|W[1-4]|SP[1-5]|RE[1-2])\b'
)

SHARED_SOURCE_IMPORT_RE = re.compile(
    r'zone[-_]translation|zone_taxonomy|zone-taxonomy\.json|regulatory-constants'
)

# DCP structure keys (Part/Chapter/Section numbering) collide in shape with
# zone codes — "B1".."B17" as Waverley DCP Part numbers, not zone codes.
# Match the assignment target, not the array contents, since the array
# contents alone can't distinguish "B1" the zone from "B1" the DCP part.
PART_KEY_RE = re.compile(
    r'(PartKey|ChapterKey|SectionKey|part_key|chapter_key|section_key)',
    re.IGNORECASE,
)

SUPPRESS_RE = re.compile(r'#\s*noqa:\s*zone-codes|//\s*noqa:\s*zone-codes')

SKIP_LINE_RE = re.compile(r'^\s*(import |from |#|//|\*)')


def get_staged_diff_lines() -> list[tuple[str, int, str]]:
    """Return (filepath, lineno, line_text) for new lines in staged .py/.ts/.tsx files."""
    try:
        diff = subprocess.check_output(
            ["git", "diff", "--cached", "-U0", "--diff-filter=ACM",
             "--", "*.py", "*.ts", "*.tsx"],
            text=True, encoding="utf-8",
        )
    except subprocess.CalledProcessError:
        return []

    results = []
    current_file = None
    current_line = 0

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            # scripts/archive/ holds retired one-off scripts nothing runs, kept
            # so they survive the laptop they lived on. Backing up a years-old
            # throwaway is not authoring a new hardcoded zone list, and this
            # lint cannot tell those apart — 31 archived files tripped it on a
            # pure backup, 2026-08-16. Same exemption, same reasoning and same
            # single directory as the QA gate's content scanners; live code
            # under scripts/ proper is unaffected, and
            # tests/test_archive_is_not_live_code.py fails if anything outside
            # the archive ever imports from it.
            if "scripts/archive/" in current_file.replace("\\", "/"):
                current_file = None
            continue
        if line.startswith("@@"):
            m = re.search(r'\+(\d+)', line)
            if m:
                current_line = int(m.group(1))
            continue
        if line.startswith("+") and not line.startswith("+++"):
            if current_file:
                results.append((current_file, current_line, line[1:]))
            current_line += 1
        elif not line.startswith("-"):
            current_line += 1

    return results


def file_imports_shared_source(filepath: str) -> bool:
    """Check whole-file content (not just the diff) for a shared-source import —
    a file that imports the taxonomy but also has an incidental literal
    elsewhere (e.g. a golden-set test fixture) shouldn't false-positive."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return False
    return bool(SHARED_SOURCE_IMPORT_RE.search(content))


def check_line(filepath: str, lineno: int, line: str) -> list[str]:
    if SKIP_LINE_RE.match(line) or SUPPRESS_RE.search(line):
        return []

    tokens = ZONE_TOKEN_RE.findall(line)
    if len(set(tokens)) < 2:
        return []

    if PART_KEY_RE.search(line):
        return []

    if file_imports_shared_source(filepath):
        return []

    return [
        f"  {filepath}:{lineno}: hardcoded zone-code list {sorted(set(tokens))} "
        f"-- import from shared/zone-taxonomy.json (via frontend-nextjs/lib/"
        f"zone-translation.ts or enrichment/config/zone_taxonomy.py) instead "
        f"of a new literal, or add  # noqa: zone-codes  if this is genuinely "
        f"not a zone code (e.g. a DCP Part/Chapter key)"
    ]


def sweep_all() -> dict[str, int]:
    """Violations per file across the whole tree. Powers the shrink-only ratchet.

    --all already existed and already covered .ts/.tsx. It was never run
    anywhere: .githooks/pre-commit calls this script diff-scoped only, so every
    violation that ALREADY existed was invisible permanently. A rule that
    applies only to future code cleans nothing up -- which is how a live
    zone->permitted-use table (issue #928) and a hardcoded minimum-lot-size map
    in lib/setbacks/validator.ts both survived in served code.
    """
    import glob
    from collections import Counter

    files = (
        glob.glob("**/*.py", recursive=True)
        + glob.glob("**/*.ts", recursive=True)
        + glob.glob("**/*.tsx", recursive=True)
    )
    files = [f for f in files if "node_modules" not in f and ".next" not in f]
    per: Counter = Counter()
    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (OSError, UnicodeDecodeError):
            continue
        n = sum(len(check_line(filepath, i, ln)) for i, ln in enumerate(lines, 1))
        if n:
            per[filepath.replace(os.sep, "/")] = n
    return dict(per)


def run_baseline(update: bool) -> int:
    """Shrink-only: a file's count may fall, never rise.

    A hard zero would fail on 270 pre-existing violations and be deleted within
    a week, so the ratchet locks in today's number instead. Both directions are
    reported: a rise fails, and a fall is announced so the baseline gets
    lowered rather than silently drifting out of date.
    """
    import json

    path = os.path.join(".claude", "zone_code_baseline.json")
    current = sweep_all()

    if update:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        doc["total"] = sum(current.values())
        doc["per_file"] = dict(sorted(current.items()))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Zone-code baseline updated: {doc['total']} across {len(current)} files.")
        return 0

    try:
        with open(path, encoding="utf-8") as f:
            baseline = json.load(f)["per_file"]
    except (OSError, ValueError, KeyError):
        print(f"Zone-code baseline: cannot read {path} — refusing to pass.")
        return 1

    worse, better, new = [], [], []
    for filepath, count in sorted(current.items()):
        was = baseline.get(filepath)
        if was is None:
            new.append((filepath, count))
        elif count > was:
            worse.append((filepath, was, count))
        elif count < was:
            better.append((filepath, was, count))
    gone = [f for f in baseline if f not in current]

    if better or gone:
        print("Zone-code baseline: IMPROVED — lower it and commit "
              "(python scripts/lint_hardcoded_zone_codes.py --baseline --update)")
        for f, was, now in better:
            print(f"  {f}: {was} -> {now}")
        for f in gone:
            print(f"  {f}: {baseline[f]} -> 0")

    if not worse and not new:
        print(f"Zone-code baseline: OK — {sum(current.values())} violation(s), "
              "none increased.")
        return 0

    print()
    print("Zone-code baseline: FAILED — hardcoded NSW zone data increased.")
    print("  .claude/rules/regulatory-data.md: LEPs are amended regularly, so a")
    print("  hardcoded table is wrong within months. Read from the shared")
    print("  taxonomy or the database instead.")
    for f, was, now in worse:
        print(f"  {f}: {was} -> {now}")
    for f, now in new:
        print(f"  {f}: NEW file with {now} violation(s)")
    return 1


def main() -> int:
    if "--baseline" in sys.argv:
        return run_baseline(update="--update" in sys.argv)

    if "--all" in sys.argv:
        import glob
        files = (
            glob.glob("**/*.py", recursive=True)
            + glob.glob("**/*.ts", recursive=True)
            + glob.glob("**/*.tsx", recursive=True)
        )
        files = [f for f in files if "node_modules" not in f and ".next" not in f]
        all_violations = []
        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(lines, 1):
                all_violations.extend(check_line(filepath, lineno, line))

        if all_violations:
            print(f"WARNING: Zone-code lint: {len(all_violations)} hardcoded "
                  f"zone-code list(s) found across all files")
            for v in all_violations:
                print(v)
            return 1
        return 0

    # A merge commit is not authoring code. `git diff --cached` on a merge stages
    # everything arriving from the other branch, so without this the check reports
    # months of pre-existing code (which predates this guard, or was already gated
    # on its own branch) as brand-new violations and blocks every merge. Found on
    # this guard's first contact with a real merge.
    git_dir = subprocess.run(
        ["git", "rev-parse", "--git-dir"], capture_output=True, text=True
    ).stdout.strip()
    if git_dir and os.path.exists(os.path.join(git_dir, "MERGE_HEAD")):
        print("Zone-code lint: merge commit — skipped "
              "(incoming code is gated on its own branch, not authored here).")
        return 0

    diff_lines = get_staged_diff_lines()
    if not diff_lines:
        return 0

    all_violations = []
    for filepath, lineno, line in diff_lines:
        all_violations.extend(check_line(filepath, lineno, line))

    if all_violations:
        print(f"WARNING: Zone-code lint: {len(all_violations)} hardcoded NSW "
              f"zone-code list(s) in staged changes")
        print("  See .claude/DATA_QUALITY_TRACKER.md DQ-30 — this exact class")
        print("  of bug has already happened twice in this codebase.")
        print()
        for v in all_violations:
            print(v)
        print()
        print("  Suppress false positives with:  # noqa: zone-codes")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
