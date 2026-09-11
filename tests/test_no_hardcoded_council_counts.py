"""A council count on a public page must come from the shared constant.

THE GAP THIS CLOSES. Every coverage check built so far reads
`frontend-nextjs/lib/coverage.ts`. A number typed as a literal string on a page
is invisible to all of them — which is exactly how `lgasCovered: 130` survived on
the homepage, and how `/for/students` came to say "28 councils have numeric
controls" while every other surface said 26.

28 and 26 are BOTH real and they are not interchangeable: 28 is the count of
active LGA rows carrying controls, 26 is the count of council AREAS once Inner
West's three former-council labels collapse into one. Measured live 2026-09-11.
Saying "28 councils" states there are 28 councils, and there are not. It is the
same defect as the "25 LGAs" corrected to 24 in the August claim audit.

WHAT THIS DOES NOT FORBID. A page may say "128 councils in NSW" — a public fact
about the state, not a claim about our coverage — and history may say "43
councils merged into 20 in 2016". Those are allowed by value and by allowlist
respectively, each with its reason recorded.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "frontend-nextjs" / "app"

#: A number immediately before "council(s)" or "LGA(s)".
COUNT = re.compile(r"(?<![\w.$])(\d[\d,]*)\s*\+?\s*(?:NSW\s+)?(councils?|LGAs?)\b", re.I)

#: A four-digit year is a date, not a count. "the 2019 council flood study" and
#: "the 2016 NSW council mergers" both matched until this was added.
YEAR = re.compile(r"^(?:19|20)\d{2}$")

#: Values that are facts about NSW rather than claims about our coverage.
#: 128 is the number of councils in the state — the ceiling, not our reach.
PUBLIC_FACTS = {"128"}

#: Files allowed to state a council count as a literal, WITH the reason.
#: An entry whose file no longer contains a count is a failure too, so this
#: cannot rot into agreeing with whatever happens to be true.
ALLOWED: dict[str, str] = {
    "blog/merged-lga-different-setback-rules/page.tsx":
        "Historical: '43 councils merged into 20 new entities' in 2016. A past event, "
        "not a coverage figure, and it must NOT move when our coverage does.",
    "open-data/page.tsx":
        "'Inner West has ~4,600 provisions; other councils have fewer' — a per-council "
        "depth illustration, explicitly uneven and deliberately approximate.",
    "how-it-works/page.tsx":
        "'~11 LGAs' is which councils uploaded flood polygons to the STATE portal. "
        "That is the portal's coverage, not ours.",
    "reports/granny-flat/page.tsx":
        "⚠ UNVERIFIED, NOT EXEMPT: 'Spatial data: 12 LGAs covered' for flood-control-lot "
        "data, in a served report. Nothing in the repo verifies 12. Tracked in the plan "
        "ledger; allowlisted only so this guard can ship, and the two-way check below "
        "keeps it visible until it is either measured or removed.",
}


def _pages() -> list[Path]:
    return sorted(APP.rglob("*.tsx"))


def _violations(path: Path) -> list[str]:
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if s.startswith(("//", "*", "/*")) or "import " in s:
            continue
        if "COVERAGE_DISPLAY." in line or "COVERAGE." in line:
            continue          # reads the shared constant: correct by construction
        for m in COUNT.finditer(line):
            raw = m.group(1).replace(",", "")
            if raw in {v.replace(",", "") for v in PUBLIC_FACTS} or YEAR.match(raw):
                continue
            out.append(f"{n}: {s[:120]}")
    return out


@pytest.mark.parametrize("path", _pages(), ids=lambda p: str(p.relative_to(APP)))
def test_no_page_hardcodes_a_council_count(path: Path):
    rel = str(path.relative_to(APP)).replace("\\", "/")
    found = _violations(path)
    if rel in ALLOWED:
        pytest.skip(f"allowed: {ALLOWED[rel]}")
    assert not found, (
        f"{rel} states a council count as a literal. Use COVERAGE_DISPLAY so it "
        f"moves with the data, or add the file to ALLOWED with the reason:\n  "
        + "\n  ".join(found)
    )


def test_every_allowlisted_file_still_states_a_count():
    """The exception list runs BOTH ways.

    An entry whose file no longer holds a literal count is either stale or was
    wrong to begin with. Left alone it becomes standing amnesty for a file
    nobody has looked at — the failure mode the DQ ledger's two-way ratchet
    exists to prevent.
    """
    stale = []
    for rel, reason in ALLOWED.items():
        p = APP / rel
        if not p.exists():
            stale.append(f"{rel}: file no longer exists")
        elif not _violations(p):
            stale.append(f"{rel}: no literal count left — remove this entry")
    assert not stale, "ALLOWED entries that no longer apply:\n  " + "\n  ".join(stale)


def test_the_two_council_figures_are_not_interchangeable():
    """Documentation as a test, because this is the trap the sweep found.

    28 = active LGA rows with controls. 26 = council AREAS, Inner West's three
    labels collapsed to one. coverage.ts publishes the AREA count, because a
    sentence saying "N councils" is a claim about councils.
    """
    ts = (ROOT / "frontend-nextjs" / "lib" / "coverage.ts").read_text(encoding="utf-8")
    m = re.search(r"dcpNumericCouncils:\s*(\d+)", ts)
    assert m, "dcpNumericCouncils not found in coverage.ts"
    assert m.group(1) == "26", (
        f"dcpNumericCouncils is {m.group(1)}. If it is now 28 it has been set to the "
        f"LABEL count, which counts Inner West three times and claims two councils "
        f"that do not exist."
    )
