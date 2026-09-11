"""The published numbers that come from SOURCE FILES, not the database.

`scripts/verify_coverage_stats.py` verifies everything in `coverage.ts` that a SQL
query can answer. Three published figures cannot be reached that way, and until
this file they were verified by nothing at all:

    govDataSources             the DATA_SOURCES list rendered on the homepage
    secondaryDwellingCouncils  a generated file, sourced from an EXTERNAL project
    dcpFullCouncils            councils with a structured DCP config

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


def test_dcp_full_councils_matches_the_configs_that_exist():
    """7 = 3 Inner West + 4 distinct councils in COUNCIL_CONFIGS.

    The registry has SIX keys and four councils -- `sydney_dcp` and `ku-ring-gai`
    are aliases whose values are the same config object as their siblings. Counting
    keys would publish 9. This counts distinct config OBJECTS, which is what
    "councils with a structured config" means.
    """
    src = CONFIG_INIT.read_text(encoding="utf-8")
    m = re.search(r"COUNCIL_CONFIGS:\s*dict\[str,\s*dict\]\s*=\s*\{(.*?)\n\}", src, re.S)
    assert m, "COUNCIL_CONFIGS not found"
    distinct_configs = set(re.findall(r":\s*(\w+_CONFIG)", m.group(1)))
    inner_west = {"ASHFIELD_CONFIG", "LEICHHARDT_CONFIG", "MARRICKVILLE_CONFIG"}
    for name in inner_west:
        assert name in src, f"{name} is no longer imported by enrichment/config"
    expected = len(distinct_configs) + len(inner_west)
    assert published()["dcpFullCouncils"] == expected, (
        f"coverage.ts publishes dcpFullCouncils={published()['dcpFullCouncils']} but "
        f"{expected} configs exist: {sorted(distinct_configs)} plus Inner West's "
        f"{sorted(inner_west)}"
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
