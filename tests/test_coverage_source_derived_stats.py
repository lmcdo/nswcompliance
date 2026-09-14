"""The published numbers that come from SOURCE FILES, not the database.

`scripts/verify_coverage_stats.py` verifies everything in `coverage.ts` that a SQL
query can answer. Two published figures cannot be reached that way, and until
this file they were verified by nothing at all:

    govDataSources             the DATA_SOURCES list rendered on the homepage
    secondaryDwellingCouncils  a generated file, sourced from an EXTERNAL project

A third, dcpFullCouncils ("7 councils with full structured provisions"), was retired on
2026-09-14 (outreach claim OC-14): no council holds its own target set of DCP chapters.

`coverage.ts` calls this group "editorial/config-derived facts ... (not
auto-verifiable)". That was true of the mechanism, not of the facts: each is a
count of something concrete in this repo. "Editorial" was never a reason a number
could not be verified — only a reason nobody had written the check. The same
exemption is what let `lgasCovered: 130` sit on the homepage claiming more
councils than NSW contains.

A fourth, riskLayers ("8 risk layers"), was retired on 2026-09-14 (outreach claim OC-13):
nothing in the repo produced an 8.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

COVERAGE_TS = ROOT / "frontend-nextjs" / "lib" / "coverage.ts"
HOMEPAGE = ROOT / "frontend-nextjs" / "app" / "page.tsx"
SD_STATS = ROOT / "frontend-nextjs" / "lib" / "lga-data" / "secondary-dwelling-stats.ts"
CONFIG_INIT = ROOT / "enrichment" / "config" / "__init__.py"


def published() -> dict[str, int]:
    text = COVERAGE_TS.read_text(encoding="utf-8")
    m = re.search(r"export const COVERAGE\s*=\s*\{(.*?)\}\s*as const", text, re.S)
    assert m, "COVERAGE object not found"
    return {k: int(v.replace(",", "")) for k, v in re.findall(r"(\w+):\s*([\d,]+)", m.group(1))}


def test_gov_data_sources_matches_the_list_the_homepage_renders():
    """The stat and the list sit in the SAME file and could still disagree —
    the number is published from coverage.ts, the names from an array below it."""
    src = HOMEPAGE.read_text(encoding="utf-8")
    m = re.search(r"const DATA_SOURCES = \[(.*?)\];", src, re.S)
    assert m, "DATA_SOURCES array not found on the homepage"
    named = [x for x in re.findall(r"'([^']+)'", m.group(1))]
    assert published()["govDataSources"] == len(named), (
        f"coverage.ts publishes govDataSources={published()['govDataSources']} but the "
        f"homepage names {len(named)}: {named}"
    )


def test_secondary_dwelling_councils_matches_the_generated_file():
    """Verifies the published figure against the data actually shipped.

    It does NOT verify that data against the Planning Portal: the file is
    generated from a separate, separately-credentialed project and carries its own
    DATA_AS_OF stamp. Two different claims -- 'we publish what we ship' is
    checkable here; 'what we ship is current' is not, and the next test says so.
    """
    src = SD_STATS.read_text(encoding="utf-8")
    councils = set(re.findall(r"councilName:\s*'([^']+)'", src))
    if not councils:
        councils = set(re.findall(r'councilName:\s*"([^"]+)"', src))
    assert councils, "no councilName entries found in the generated stats file"
    assert published()["secondaryDwellingCouncils"] == len(councils), (
        f"coverage.ts publishes {published()['secondaryDwellingCouncils']} but the "
        f"generated file holds {len(councils)} distinct councils"
    )


def test_the_secondary_dwelling_data_states_when_it_was_generated():
    """A snapshot that does not say when it was taken reads as current.

    This does not assert freshness -- deciding an acceptable age is a product
    call. It asserts the date is PRESENT, so staleness is at least visible.
    """
    m = re.search(r"DATA_AS_OF\s*=\s*'(\d{4}-\d{2}-\d{2})'", SD_STATS.read_text(encoding="utf-8"))
    assert m, "secondary-dwelling-stats.ts no longer records DATA_AS_OF"


def test_the_retired_full_councils_figure_stays_retired():
    """dcpFullCouncils was retired on 2026-09-14 (outreach claim OC-14). A "full" council
    would have to hold its own target set of DCP chapters, and none does. Re-adding the key
    would republish a claim the user decided to stop making."""
    assert "dcpFullCouncils" not in published(), (
        "coverage.ts publishes dcpFullCouncils again; it was retired by decision (OC-14)"
    )


AUDIENCE_PAGES_WITH_STATS = [
    ROOT / "frontend-nextjs" / "app" / "for" / "homebuyers" / "page.tsx",
    ROOT / "frontend-nextjs" / "app" / "for" / "buyers-agents" / "page.tsx",
]


def test_the_retired_risk_layers_figure_stays_retired():
    """riskLayers ("8 risk layers") was retired on 2026-09-14 (outreach claim OC-13).

    It was a headline stat on the homepage and two audience pages, and nothing in this
    repo produced an 8. Searched on 2026-09-11: the homepage's CLIMATE_HAZARDS (4), the
    /climate-risk hazards section (5), the open-data catalogue (7), the capability tiles,
    and every table whose name contains 'risk'. An unsourced number is grounded or
    removed, never adjusted to another guess, so it was removed. Re-adding it, under the
    key or as a tile, would republish a number nothing can check.
    """
    # All code in coverage.ts, not only the COVERAGE object that published() parses: the first cut of this
    # retirement removed the number and left COVERAGE_DISPLAY.riskLayers = '8' exported, and only the
    # outreach gate's rendered-phrase check noticed.
    code = [line for line in COVERAGE_TS.read_text(encoding="utf-8").splitlines()
            if not line.strip().startswith(("*", "/*", "//"))]
    assert not any("riskLayers" in line for line in code), (
        "coverage.ts exports riskLayers again (COVERAGE or COVERAGE_DISPLAY); it has no source (retired, OC-13)"
    )
    for page in [HOMEPAGE, *AUDIENCE_PAGES_WITH_STATS]:
        text = page.read_text(encoding="utf-8")
        assert "riskLayers" not in text and "Risk layers" not in text, (
            f"{page.relative_to(ROOT).as_posix()} shows the retired risk layers figure"
        )


# ── the ratchet: no published number may be checked by nothing ───────────────
# A key may go unchecked only with its own test keeping that fact visible. The set
# has been empty since riskLayers was retired; adding to it is a deliberate act that
# shows up in review, while forgetting to write a check is not.
UNGROUNDED_BY_DECISION: set[str] = set()

VERIFY_SCRIPT = ROOT / "scripts" / "verify_coverage_stats.py"
THIS_TEST = Path(__file__)


def test_every_published_number_is_checked_by_something():
    """A published figure with no checker passes by OMISSION. That is how both
    known bad numbers got onto the site.

    `lgasCovered: 130` sat on the homepage claiming more councils than NSW
    contains, and `riskLayers: 8` is a headline stat nothing in the repo
    produces. Neither FAILED a check -- neither was checked at all, and the two
    checkers only verify the keys they already know about. Silence read as
    approval.

    So the rule is inverted here: every key in COVERAGE must be named by the DB
    verifier, or by this file, or by UNGROUNDED_BY_DECISION. A key in none of
    them fails, and the failure names it. Writing a new published number without
    a check now costs a red test rather than nothing at all.
    """
    keys = set(published())
    db_checked = {k for k in keys if k in VERIFY_SCRIPT.read_text(encoding="utf-8")}
    source_checked = {k for k in keys if k in THIS_TEST.read_text(encoding="utf-8")}
    unchecked = keys - db_checked - source_checked - UNGROUNDED_BY_DECISION

    assert not unchecked, (
        "published in coverage.ts and verified by nothing: " + ", ".join(sorted(unchecked)) +
        ". Add a query to scripts/verify_coverage_stats.py, or a source check to "
        "this file, or -- if it genuinely cannot be grounded -- add it to "
        "UNGROUNDED_BY_DECISION with a test that keeps that visible. Do not leave "
        "it unchecked: an unchecked number does not fail, it just never gets "
        "looked at."
    )


def test_the_ungrounded_set_stays_small_and_deliberate():
    """UNGROUNDED_BY_DECISION is an escape hatch, and an escape hatch that grows
    quietly is the exemption that let 'editorial' mean 'unverifiable' for months.
    Every member needs its own visible test, so the set is asserted by name."""
    assert UNGROUNDED_BY_DECISION == set(), (
        "the ungrounded set changed. Each member must have a test keeping its open "
        "decision visible; the last member, riskLayers, was retired rather than kept."
    )
