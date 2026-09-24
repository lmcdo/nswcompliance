#!/usr/bin/env python3
# prior-art-checked: neighbours opened, not guessed from their names.
#   scripts/lint_hardcoded_zone_codes.py   the shape this follows: a pre-commit lint
#       with an inline suppression comment and an --all reporting mode. Its regex is
#       for a different target, so the detection here is AST, not reused.
#   scripts/check_test_quarantine.py       the closest RATCHET in spirit -- it fails
#       when an exclusion list grows without a reason AND when a listed item starts
#       passing, so amnesty is released rather than left standing. Same idea, applied
#       to extraction defaults and per-council exceptions.
#   .githooks/pre-commit                   where this is wired. It is ALSO wired into
#       .github/workflows/gates.yml, because a pre-commit hook is bypassable with
#       --no-verify and the whole point of this file is a check that cannot quietly
#       stop running.
"""Keep intelligent extraction on, keep its deterministic proof mandatory.

WHAT THIS GUARDS, AND WHY IT EXISTS
-----------------------------------
The DCP pipeline was decided in July 2026 as: read the document with an LLM, then
PROVE the result against the council's own PDF before serving it. Both halves were
built. Both spent months switched off or optional, and the gap was filled by
hand-written per-council pattern exceptions.

  * `AI_EXTRACTION` was opt-in and stayed off for the two months AFTER the extractor
    had been hand-verified on marrickville's worst chapter -- 49 of 49 controls, every
    section number correct.
  * `enforce_fidelity` originally ABSTAINED on a batch with no verdicts, printing
    "not judged" and committing anyway, which made the proof optional in practice.
  * In their place, scripts/dcp_extract_changed.py accumulated EIGHT per-council
    exception tables. Four heading overrides were added one at a time -- woollahra
    2026-05, marrickville 2026-08, ku_ring_gai, northern_beaches 2026-09-21 -- each
    after something broke downstream, never because a check found the class.

Every one of those changes passed every other hook: tests, mutation testing, the QA
gate, the liability scan. The existing machinery verifies that a change is CORRECT.
Nothing asked whether it was the right KIND of change. That is this file's job.

NOT A BAN
---------
A council may genuinely need an exception, and the proof may genuinely be
unavailable. Say so on the line:

    "some_council": ...,  # council-exception-justified: <why the general path cannot>

Same escape shape as `# noqa: zone-codes` next door. This exists so the decision is
deliberate and visible in the diff, not so it is impossible.
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys

EXTRACT = "scripts/dcp_extract_changed.py"
GUARD = "scripts/dcp_supersede_guard.py"

#: Functions that must read their flag as OPT-OUT. A capability that is off by
#: default is a capability nobody turns on -- measured twice in this repo.
MUST_BE_OPT_OUT = {
    EXTRACT: ["ai_extraction_enabled", "fidelity_gate_enabled"],
}
#: The "no proof, no commit" branch. Without it a batch the fidelity gate never
#: touched commits exactly like a verified one.
MUST_CONTAIN = {
    GUARD: [
        ("if approved and graded == 0:",
         "the no-proof-no-commit branch is gone -- an unchecked batch can commit again"),
    ],
}
#: Exceptions the guard must actually RAISE. Checked as AST, not as text: commenting
#: the statement out left the words "raise FidelityRefused" in the file and a
#: substring check happily passed it.
MUST_RAISE = {GUARD: ["FidelityRefused", "SectionLossRefused", "LegibilityRefused"]}
#: Module-level dicts/sets keyed by council slug. Adding a key is the event.
WATCHED_TABLES = {
    EXTRACT: [
        "COUNCIL_SECTION_RE_OVERRIDES", "COUNCIL_COLUMN_CONFIGS",
        "GEOMETRIC_COLUMN_COUNCILS", "UPRIGHT_ONLY_COUNCILS",
        "TOC_DRIVEN_COUNCILS", "MAP_LABEL_COUNCILS",
        "MULTI_HEADING_COUNCILS", "COUNCIL_SUBSECTION_PATTERNS",
    ],
}
SUPPRESS = "council-exception-justified:"
DOC = "docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md"
#: Values that mean "off". A function reading its flag against THESE is opt-out;
#: one reading it against ("1", "true", "yes") is opt-in, which is the defect.
OFF_WORDS = {"0", "false", "no", "off"}


def git(*args: str) -> str | None:
    """stdout as UTF-8. Explicit encoding because these files carry em dashes and a
    Windows shell decodes as cp1252 by default -- the first version of this lint
    crashed in a reader thread rather than reporting anything, which is the worst
    possible failure for a check whose job is to not stop running."""
    r = subprocess.run(["git", *args], capture_output=True,
                       encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else None


def is_opt_out(source: str, func: str) -> bool | None:
    """True when `func` treats its env var as opt-out. None when not found."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == func):
            continue
        # Only the RETURNED EXPRESSION, never the docstring. Scanning the whole
        # function body let a mutation flip the code to opt-in and still pass,
        # because the docstring explaining opt-out still contained the words
        # "0", "false", "no", "off". Caught by planting exactly that mutation.
        for ret in (n for n in ast.walk(node) if isinstance(n, ast.Return)):
            if ret.value is None:
                continue
            literals = {c.value.lower() for c in ast.walk(ret.value)
                        if isinstance(c, ast.Constant) and isinstance(c.value, str)}
            if not literals:
                continue
            # Opt-out compares the env var against the OFF words and negates;
            # opt-in compares it against the ON words. The presence of an OFF word
            # in the comparison is the signature, and `not in` makes it a default-on.
            if OFF_WORDS & literals:
                return True
            if {"1", "true", "yes"} & literals:
                return False
        return None
    return None


def table_keys(source: str | None, names: list[str]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {n: set() for n in names}
    if not source:
        return out
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    for node in tree.body:
        # AnnAssign as well as Assign: COUNCIL_SECTION_RE_OVERRIDES carries a type
        # annotation, so handling only Assign made this blind to the very table it
        # was written for. A planted 9th exception sailed through the first version.
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, ast.Assign):
            targets = node.targets
        else:
            continue
        name = next((t.id for t in targets
                     if isinstance(t, ast.Name) and t.id in out), None)
        if name is None or node.value is None:
            continue
        val = node.value
        if isinstance(val, ast.Dict):
            out[name] = {k.value for k in val.keys
                         if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        elif isinstance(val, (ast.Set, ast.List, ast.Tuple)):
            out[name] = {e.value for e in val.elts
                         if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    return out


def read(path: str, staged: bool) -> str | None:
    return git("show", f":{path}") if staged else git("show", f"HEAD:{path}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ci", action="store_true",
                    help="check HEAD rather than the staged tree; used by gates.yml, "
                         "where a --no-verify commit still has to pass")
    args = ap.parse_args()
    staged = not args.ci
    problems: list[str] = []

    # 1. the switches must be opt-out
    for path, funcs in MUST_BE_OPT_OUT.items():
        src = read(path, staged)
        if src is None:
            continue
        for func in funcs:
            verdict = is_opt_out(src, func)
            if verdict is None:
                problems.append(f"{func}() is gone from {path} -- it is the switch that "
                                f"keeps this capability on by default")
            elif verdict is False:
                problems.append(f"{func}() is OPT-IN again in {path}. A capability that "
                                f"is off by default is one nobody turns on: this flag "
                                f"stayed off for two months after the extractor it "
                                f"guards had been hand-verified.")

    # 1b. ...and nobody reads the raw flag around the switch.
    #
    # Check 1 proved ai_extraction_enabled() opt-out while two OTHER places in the
    # same file read os.getenv("AI_EXTRACTION") as opt-in ("1"/"true"). Found
    # 2026-09-24: every council with a page map was read by the regex reader, and
    # the LLM railguards never ran on an LLM-read chapter, from #1155 until then.
    # Only the switch itself may read the env; everyone else asks the switch.
    src = read(EXTRACT, staged)
    if src:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            tree = None
        owners = {"ai_extraction_enabled"}
        for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)) if tree else ():
            for call in (c for c in ast.walk(fn) if isinstance(c, ast.Call)):
                named = [a.value for a in call.args
                         if isinstance(a, ast.Constant) and a.value == "AI_EXTRACTION"]
                if named and fn.name not in owners:
                    problems.append(
                        f"{EXTRACT}:{call.lineno} {fn.name}() reads AI_EXTRACTION itself. "
                        f"Ask ai_extraction_enabled() / llm_reader_available(): a raw read "
                        f"is how the page-map path stayed opt-in after the switch went "
                        f"opt-out.")

    # 2. the proof must stay mandatory
    for path, needles in MUST_CONTAIN.items():
        src = read(path, staged)
        if src is None:
            continue
        for needle, why in needles:
            if needle not in src:
                problems.append(f"{path}: {why}")

    # 2b. the guard must still raise, and a comment is not a raise
    for path, names in MUST_RAISE.items():
        src = read(path, staged)
        if src is None:
            continue
        try:
            raised = {n.exc.func.id for n in ast.walk(ast.parse(src))
                      if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)
                      and isinstance(n.exc.func, ast.Name)}
        except SyntaxError:
            problems.append(f"{path} does not parse")
            continue
        for name in names:
            if name not in raised:
                problems.append(f"{path} never raises {name} any more -- the guard "
                                f"reports but no longer refuses")

    # 2c. and the no-proof branch specifically must RAISE, not merely exist.
    #
    # "does the file raise FidelityRefused anywhere" is too coarse: the guard raises
    # it in two places, so commenting out the no-proof one left the other and the
    # check passed. Caught by planting exactly that. This asks whether THAT branch
    # still refuses.
    src = read(GUARD, staged)
    if src:
        try:
            tree = ast.parse(src)
        except SyntaxError:
            tree = None
        if tree is not None:
            branch_raises = False
            for node in ast.walk(tree):
                if not isinstance(node, ast.If):
                    continue
                if "approved" not in ast.dump(node.test) or "graded" not in ast.dump(node.test):
                    continue
                if any(isinstance(n, ast.Raise) for n in ast.walk(node)):
                    branch_raises = True
            if not branch_raises:
                problems.append(
                    f"{GUARD}: the no-proof branch no longer RAISES. A batch with no "
                    f"fidelity verdict at all would be reported and then committed, "
                    f"which is what made the proof optional before.")

    # 3. per-council exceptions must not grow silently
    if staged:
        for path, names in WATCHED_TABLES.items():
            now = read(path, True)
            if now is None:
                continue
            before = table_keys(read(path, False), names)
            after = table_keys(now, names)
            for name in names:
                for slug in sorted(after[name] - before[name]):
                    if any(f'"{slug}"' in ln and SUPPRESS in ln
                           for ln in now.splitlines()):
                        continue
                    problems.append(
                        f'{name}["{slug}"] adds another per-council exception. '
                        f'{DOC} section 79 specifies the general mechanism instead: '
                        f'read the document, then prove the result. If this council '
                        f'truly needs its own entry, add  # {SUPPRESS} <reason>')

    if not problems:
        return 0
    print()
    print("  EXTRACTION DEFAULTS LINT FAILED")
    print()
    for p in problems:
        print(f"    - {p}")
    print()
    print("  Intelligent extraction with deterministic proof is the decided design.")
    print("  Turning either half off, or hand-patching around it, needs a reason on")
    print("  the line -- not a quiet default.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
