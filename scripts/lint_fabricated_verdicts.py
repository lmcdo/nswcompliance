#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no existing check asks whether a
# user-facing VERDICT is backed by data the emitting component actually receives.
# Near neighbours opened and rejected:
#   * scripts/liability_language_check.py — scans new user-facing lines for hedging
#     words ("safe", "compliant", "guaranteed"). It flags WORDING; a fabricated
#     verdict can be perfectly hedged in tone and still assert a conclusion that
#     was never computed. Orthogonal axis, deliberately not merged into it.
#   * scripts/lint_hardcoded_zone_codes.py — hardcoded REGULATORY VALUES, not
#     hardcoded conclusions. Its shape (findings + named escape) is copied here.
#   * scripts/validate_schema_contract.py — code vs DB catalog, not output vs input.
#   * scripts/lint_brief_failsoft.py — silent-false-negative guard on the brief's
#     service layer; never inspects rendered strings.
"""Flag a definitive verdict emitted where the component has no matching input.

WHY THIS EXISTS
---------------
DQ-36. `components/pdf/ContextSection.tsx` printed, for every property:

    Transport Oriented Development: ✗ Not applicable - Property not within 400m
    of metro station or 800m of strategic centre

The component is passed no TOD or LMR data at all, so no input could ever have
changed that line. For any property inside a catchment the report stated a
confident conclusion about a site it had never assessed. Four more SEPPs in the
same table had the same shape.

This is not a data-quality bug. It is a fabricated verdict, and it attacks the
one thing that distinguishes this product from a retrieval system: a retrieval
system does not invent a conclusion it never computed.

WHAT IT FLAGS
-------------
A string literal that reads as a VERDICT ("Not applicable", "Does not apply",
"Applies", "Eligible", "Not required", "None identified", "Complies", a ✓/✗
glyph) which is:
  * emitted with NO interpolation — nothing about it can vary, and
  * not inside a conditional — no branch can produce a different answer, and
  * carries a SITE-CLAIM cue ("property", "site", "land", "lot", "within",
    "this development") — i.e. it says something about THIS property rather than
    describing a rule's scope.

The site-claim cue is what separates DQ-36 from the four sibling SEPP lines that
were merely worded badly. "Applies to development over $30M CIV" describes the
rule. "Property not within 400m of a metro station" describes the site.

THREE STATES, NEVER TWO
-----------------------
  OK            a verdict that varies with data (interpolated or conditional)
  FABRICATED    a site-claim verdict with no interpolation and no conditional
  UNDETERMINED  a verdict with a site cue that IS conditional, but on something
                this checker cannot resolve — reported, never silently passed

Heuristic by nature. The escape is a comment, exactly like the zone-code lint:

    {/* verdict-ok: <why this is not a fabricated verdict> */}
    // verdict-ok: <why>

An escape with no reason after the colon is rejected, so silencing costs a
sentence of justification.

EXIT CODES
----------
  0  no FABRICATED findings
  1  at least one FABRICATED finding
  2  scope missing / unreadable — a blocker, never reported as a pass
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Bounded on purpose (see the PR): the surfaces a paying customer reads.
DEFAULT_SCOPE = (
    "frontend-nextjs/components/pdf",
    "frontend-nextjs/lib/pdf",
    # The conveyancing PDF is generated in Python, not React, and is the surface a
    # paying conveyancer reads. Same class of defect, different language.
    "scripts/generate_conveyancing_report.py",
    "scripts/conveyancing_db.py",
    "services/conveyancing.py",
)

# Phrases that state a conclusion rather than describe something.
_VERDICT = re.compile(
    r"(✓|✗|\bNot applicable\b|\bDoes not apply\b|\bN/?A\b|\bEligible\b|"
    r"\bNot eligible\b|\bNot required\b|\bNone identified\b|\bNo constraints\b|"
    r"\bComplies\b|\bNon-compliant\b|\bNot affected\b|\bNot listed\b)",
    re.I,
)

# Cues that the sentence is about THIS site, not about a rule's scope. Without one
# of these, a phrase like "Applies to development over $30M" is a scope statement
# and is out of scope for this check.
_SITE_CLAIM = re.compile(
    # `within <number>` sits OUTSIDE the \b(...)\b group on purpose: inside it, the
    # trailing \b landed between the digits and "within 400m" never matched — the
    # exact phrasing of the founding case, missed by its own cue list.
    r"\bwithin\s+\d"
    r"|\b(propert(y|ies)|site|land|lot|parcel|dwelling|premises|"
    r"this development|the development|subject site|address)\b",
    re.I,
)

# Wording that already tells the truth about not knowing — never a finding.
_HONEST = re.compile(
    r"\b(not assessed|unknown|unavailable|not determined|cannot be determined|"
    r"depends on the proposal|not checked|no data)\b",
    re.I,
)

# The reason must start with a LETTER. `\S+` accepted `{/* verdict-ok: */}`,
# where the "reason" was the closing `*/}` — a bare silencer with no argument,
# which is exactly what this escape is meant to cost you.
_ESCAPE = re.compile(r"verdict-ok:\s*[A-Za-z]")

# A rendered string can vary if it interpolates, or if a branch chooses it.
# `${...}` is TS interpolation; `{...}` inside a Python f-string is the same idea.
# Both mean the rendered text can vary with data.
_INTERPOLATED = re.compile(r"\$\{|\{[A-Za-z_][A-Za-z0-9_.\[\]'\"]*\}")
# Branch forms in BOTH languages. The first version knew only `if (` and `?`,
# which is TypeScript-shaped, so every Python `if is_strata:` block read as
# unconditional and produced four false positives in the conveyancing report.
_CONDITIONAL_NEARBY = re.compile(
    r"(\?|&&|\bif\s*\(|\bswitch\b"                   # TypeScript
    r"|^[ \t]*(?:if|elif|else)\b|\bif\b.+\belse\b)",  # Python statement + ternary
    re.M,
)


def _literals(src: str):
    """Yield (text, line) for JSX text nodes and quoted strings."""
    for m in re.finditer(r">([^<>{}]{12,400})<", src, re.S):
        yield m.group(1), src.count("\n", 0, m.start()) + 1
    for m in re.finditer(r"[`'\"]([^`'\"\n]{12,400})[`'\"]", src):
        yield m.group(1), src.count("\n", 0, m.start()) + 1


def _window(lines: list[str], idx: int, before: int = 14, after: int = 2) -> str:
    """Lines around a finding, used for the branch test and the escape comment.

    14 lines back, not 6: a JSX ternary that renders two long strings puts the
    second branch well below the comment that annotates the block, and a 6-line
    window left it flagged while its sibling was cleared.
    """
    return "\n".join(lines[max(0, idx - before): idx + after])


def scan_file(path: Path) -> list[dict]:
    src = path.read_text(encoding="utf-8", errors="replace")
    lines = src.splitlines()
    seen: set[tuple[int, str]] = set()
    out: list[dict] = []

    for text, line in _literals(src):
        flat = " ".join(text.split())
        if not _VERDICT.search(flat) or not _SITE_CLAIM.search(flat):
            continue
        if _HONEST.search(flat):
            continue
        key = (line, flat[:60])
        if key in seen:
            continue
        seen.add(key)

        # Two DIFFERENT windows, deliberately.
        #
        # The escape comment is placed ABOVE a block, sometimes well above when the
        # block renders two long branches — so it gets a wide window.
        #
        # The branch test gets a TIGHT one. A wide window asked "is there a
        # conditional anywhere near?", and the answer is almost always yes in dense
        # JSX — which downgraded the founding DQ-36 line to a non-blocking
        # UNDETERMINED because an unrelated ternary sat ten lines above it. What
        # matters is whether a branch can select THIS literal, so the branch test
        # sees only the 6 lines that can plausibly guard it. Tuned against both
        # reference cases: at 5 the strata blocks (guarded 3 lines up, through a
        # dict literal) still false-positived; at 6 they clear while the founding
        # DQ-36 line, whose nearest branch is ~10 lines up, still blocks.
        escape_win = _window(lines, line - 1)
        if _ESCAPE.search(escape_win):
            continue
        win = _window(lines, line - 1, before=6, after=1)
        # Interpolation is checked on the LITERAL ONLY, never the window. Checking
        # the window meant a neighbouring line's `${...}` masked its neighbour: the
        # first version of this lint reported PASSED on the very file DQ-36 came
        # from, because the Housing SEPP line above the TOD line interpolated. A
        # check that cannot catch its own founding case is worthless.
        varies = bool(_INTERPOLATED.search(text))
        branched = bool(_CONDITIONAL_NEARBY.search(win))

        if varies:
            continue                       # OK: the text itself depends on data
        state = "UNDETERMINED" if branched else "FABRICATED"
        out.append({"line": line, "text": flat[:150], "state": state})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scope", action="append", help="Directory to scan (repeatable).")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    # The findings quote ✓/✗ glyphs — which is the point, they are the verdict —
    # and a Windows console defaults to cp1252, where printing one raises. A lint
    # that crashes instead of reporting is a lint that gets disabled.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    repo = Path(__file__).resolve().parent.parent
    scopes = [repo / s for s in (args.scope or DEFAULT_SCOPE)]
    missing = [s for s in scopes if not s.exists()]
    if missing:
        print(f"ERROR: scope not found: {[str(m) for m in missing]}. Nothing was "
              f"checked, which is not a pass.", file=sys.stderr)
        return 2

    fabricated: list[tuple[str, dict]] = []
    undetermined: list[tuple[str, dict]] = []
    n_files = 0
    for scope in scopes:
        # A scope entry may be a single file (the conveyancing generators) or a
        # directory (the React PDF components).
        candidates = [scope] if scope.is_file() else sorted(scope.rglob("*"))
        for path in candidates:
            if path.suffix not in (".ts", ".tsx", ".py") or not path.is_file():
                continue
            n_files += 1
            rel = path.relative_to(repo).as_posix()
            for f in scan_file(path):
                (fabricated if f["state"] == "FABRICATED" else undetermined).append((rel, f))

    print(f"\n=== fabricated-verdict lint: {n_files} files in "
          f"{[s.name for s in scopes]} ===")
    print(f"  FABRICATED   {len(fabricated)}   <- site verdict, no interpolation, no branch")
    print(f"  UNDETERMINED {len(undetermined)}   <- site verdict behind a branch this "
          f"check cannot resolve; NOT a pass")

    if fabricated and not args.quiet:
        print("\n-- FABRICATED --")
        for rel, f in fabricated:
            print(f"  {rel}:{f['line']}\n      {f['text']}")
    if undetermined and not args.quiet:
        print("\n-- UNDETERMINED (verify by hand) --")
        for rel, f in undetermined:
            print(f"  {rel}:{f['line']}\n      {f['text']}")

    print("\nA verdict must be computed from data this component actually receives.")
    print("If a finding is wrong, annotate it and say why:")
    print("    {/* verdict-ok: <reason> */}   or   // verdict-ok: <reason>")

    if fabricated:
        print(f"\nFAILED: {len(fabricated)} verdict(s) asserted with no input that could "
              f"change them.")
        return 1
    print("\nPASSED: no fabricated verdicts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
