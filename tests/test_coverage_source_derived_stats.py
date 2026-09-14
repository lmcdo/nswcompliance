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

WHAT IS DELIBERATELY NOT HERE: riskLayers. See the last test.
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


def test_risk_layers_is_the_one_number_with_no_source():
    """riskLayers: 8 is a HEADLINE stat on the homepage and on two audience pages,
    and nothing in this repo produces an 8.

    Searched: the homepage's own CLIMATE_HAZARDS (4), the /climate-risk hazards
    section (5), the open-data dataset catalogue (7), the capability tiles, and
    every table whose name contains 'risk'. None is 8, and no table matches at all.

    This test does NOT assert a value, because inventing one would be exactly the
    defect: a number that reads as measured because somebody wrote a query that
    returns it. It asserts the number is still 8 and therefore still unverified,
    so that the open decision -- ground it against a real list, or retire it --
    stays visible instead of ageing into apparent fact.
    """
    assert published()["riskLayers"] == 8, (
        "riskLayers changed. If it now has a real source, replace this test with a "
        "check against that source. If it was edited to a different guess, do not: "
        "an unverifiable number should be grounded or removed, not adjusted."
    )
    ts = COVERAGE_TS.read_text(encoding="utf-8")
    assert "riskLayers" in ts and "UNVERIFIED" in ts, (
        "coverage.ts must say in the comment block that riskLayers has no source"
    )


# ── the ratchet: no published number may be checked by nothing ───────────────
# riskLayers is the ONE key allowed to have no source check, and only because it
# has its own test above keeping that fact visible. Adding to this set is a
# deliberate act that shows up in review; forgetting to write a check is not.
UNGROUNDED_BY_DECISION = {"riskLayers"}

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
    assert UNGROUNDED_BY_DECISION == {"riskLayers"}, (
        "the ungrounded set changed. Each member must have a test keeping its "
        "open decision visible, like test_risk_layers_is_the_one_number_with_no_source."
    )
