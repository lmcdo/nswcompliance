"""Finding a NEW council document needed only a hub URL, and was gated on having a
per-chapter one. Ten of 32 councils were locked out by that.

Governing doc: ~/.claude/plans/ce-dcp-new-source-discovery-gap-2026-09-27.md §5,
items 1-3. Each cause below was measured on production, not inferred.

WHY THIS MATTERS MORE THAN ITS SIZE
-----------------------------------
There are two detection layers and only one of them can see a new document:

  hash a known URL   -- did the file we already track change in place?
  re-read the hub    -- did the council PUBLISH something we have never seen?

The second is the only one that can catch a new edition, and it is the one that was
broken. Randwick DCP 2025 (Stage 2) commenced 27 July 2026 and was found BY HAND on
15 September -- seven weeks. Hashing could not have caught it: the council left the
old file byte-identical. Randwick's hub returned 403, which under the old code took
the whole council's change detection down with it, so randwick had
`url_last_checked = NULL` on both chapters and had never once been swept.

MEASURED, BEFORE AND AFTER (production, 2026-09-28)
---------------------------------------------------
    councils hub-scraped:  9 -> 19    of 32 active.  None lost.
    recovered: bayside, burwood, camden, canada_bay, cumberland, fairfield, ryde,
               sutherland_shire, the_hills, the_hills_shire

THE THREE CAUSES
----------------
1. The loop's own query said `WHERE is_active AND council_url IS NOT NULL`. Eight
   councils carry a registered scraper and a `council_page_url` on EVERY active
   chapter, and `council_url` on NONE -- so they never entered the council grouping
   and their hub page was never read. One predicate.

2. The hub URL was read from `council_chapters[0]`, the lowest `sort_order` among
   rows that SURVIVED that filter. Cumberland records its hub URL on the row with no
   `council_url` and its per-chapter URL on a different row, so the survivor list
   began with a NULL hub URL and the council was skipped while a usable URL sat on a
   sibling row. Widening the query alone does not fix this: `sort_order` is NULL on
   both cumberland rows, so which one lands at index 0 is not even deterministic.

3. `HUB_SCRAPERS` was keyed `sutherland`; the registry slug is `sutherland_shire`.
   The alias existed for `the_hills`/`the_hills_shire` and was missed here, so
   `scrape_sutherland` was unreachable.

AND THE ONE THAT CAUSED THE SEVEN-WEEK MISS
-------------------------------------------
`except HubScrapeError: ... continue` -- the `continue` skipped the per-chapter hash
checks as well. A hub page failing says NOTHING about whether the chapters behind it
changed. `WAFBlockError` already existed in this file with the right doctrine
("infrastructure problem, not data") and the per-chapter path already honoured it;
only the hub path turned a 403 into a whole-council skip.
"""
from __future__ import annotations

import ast
import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Stub heavy AWS deps so the pure helpers import without boto3, matching
# tests/test_r2_monitor_alerting.py.
sys.modules.setdefault("boto3", MagicMock())
sys.modules.setdefault("botocore", MagicMock())
if "botocore.exceptions" not in sys.modules:
    _m = types.ModuleType("botocore.exceptions")

    class ClientError(Exception):
        pass

    _m.ClientError = ClientError
    sys.modules["botocore.exceptions"] = _m

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# r2_monitor reads its R2 credentials AT IMPORT with a bare `os.environ[...]`, and a
# git worktree carries no .env of its own -- so importing it raises KeyError before a
# single test collects. setdefault, not set: a real value in the environment is left
# alone, and nothing here ever reaches R2 (boto3 is the MagicMock stubbed above, and
# every test below reads source text or calls a pure function).
for _k in ("R2_ACCOUNT_ID", "R2_BUCKET_NAME", "R2_ACCESS_KEY_ID",
           "R2_SECRET_ACCESS_KEY", "DATABASE_URL"):
    os.environ.setdefault(_k, "test-placeholder-not-a-credential")

from hub_scrapers import HUB_SCRAPERS  # noqa: E402
from r2_monitor import is_waf_denial, pick_hub_row  # noqa: E402

MONITOR_SRC = (ROOT / "scripts" / "r2_monitor.py").read_text(encoding="utf-8")


def _hub_except_block(code_only: bool = True) -> str:
    """The `except HubScrapeError` body, optionally with comments stripped.

    code_only matters and its absence made two of these tests fail on their first
    run: the new code EXPLAINS what it removed, so the comment text contains the very
    words the tests search for -- `continue` and `len(council_chapters)`. A source
    scan that reads prose as code cannot tell a fix from a description of the fix.
    """
    block = MONITOR_SRC[MONITOR_SRC.index("except HubScrapeError as exc:"):]
    block = block[:block.index("# ── Per-chapter hash check")]
    if not code_only:
        return block
    out = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        out.append(line.split("  #")[0] if "  #" in line else line)
    return "\n".join(out)


class TestCause1TheQueryNoLongerGatesDiscoveryOnChangeDetection:
    def test_the_query_admits_a_hub_url_alone(self):
        assert "council_url IS NOT NULL OR council_page_url IS NOT NULL" in MONITOR_SRC, (
            "the chapter query is gated on council_url again, so a council with only a "
            "hub URL cannot be discovered from -- the defect that locked out eight "
            "councils"
        )

    def test_the_old_gate_is_gone(self):
        """Specifically the bare form. A council whose chapters have no per-chapter
        URL still has a hub page, and a hub scrape needs only that."""
        lines = [ln.strip() for ln in MONITOR_SRC.splitlines()]
        assert "AND council_url IS NOT NULL" not in lines, (
            "the bare `AND council_url IS NOT NULL` gate is back in the chapter query"
        )

    def test_a_hub_only_chapter_is_skipped_not_failed(self):
        """A chapter with no council_url cannot be hash-checked. It must be counted
        as skipped, never reported as a content failure -- `head_request(None)` would
        raise and be logged as though the council's document were broken."""
        assert 'results["skipped_no_url"] += 1' in MONITOR_SRC, (
            "skipped_no_url is still never incremented, so hub-only chapters now "
            "admitted by the widened query will be reported as real failures"
        )

    def test_the_skip_happens_before_the_head_request(self):
        """Order matters: the guard is worthless after head_request(None) has raised."""
        guard = MONITOR_SRC.index('results["skipped_no_url"] += 1')
        head = MONITOR_SRC.index("head = head_request(url)")
        assert guard < head, (
            "the no-url guard sits after the HEAD request, so it cannot prevent it"
        )


class TestCause2TheHubUrlComesFromAnyRowNotRowZero:
    def test_a_hub_url_on_a_later_row_is_found(self):
        """Cumberland's exact shape: the hub URL is NOT on the first row."""
        rows = [
            {"chapter_key": "part-b", "council_page_url": None},
            {"chapter_key": "part-g3", "council_page_url": "https://c.example/dcp"},
        ]
        assert pick_hub_row(rows)["council_page_url"] == "https://c.example/dcp"

    def test_a_blank_string_does_not_count_as_a_hub_url(self):
        """An empty string is how a row gets a column without a value. Treating it as
        present would hand the scraper "" and fail inside the request."""
        rows = [
            {"chapter_key": "a", "council_page_url": "   "},
            {"chapter_key": "b", "council_page_url": "https://c.example/dcp"},
        ]
        assert pick_hub_row(rows)["council_page_url"] == "https://c.example/dcp"

    def test_row_zero_still_wins_when_it_has_one(self):
        """No behaviour change for the nine councils that already worked."""
        rows = [
            {"chapter_key": "a", "council_page_url": "https://first.example/dcp"},
            {"chapter_key": "b", "council_page_url": "https://second.example/dcp"},
        ]
        assert pick_hub_row(rows)["council_page_url"] == "https://first.example/dcp"

    def test_no_hub_url_anywhere_falls_back_to_row_zero(self):
        """So the caller's `if scraper and hub_url` still decides, rather than this
        raising StopIteration on a council that simply has no hub page."""
        rows = [{"chapter_key": "a", "council_page_url": None}]
        assert pick_hub_row(rows) is rows[0]

    def test_all_three_hub_values_come_from_the_same_row(self):
        """A count from one row compared against another row's URL is a comparison
        between two different things, and would read as drift that is not there."""
        assert "hub_row.get(\"hub_expected_count\")" in MONITOR_SRC
        assert "hub_row.get(\"hub_last_pdf_count\")" in MONITOR_SRC
        assert "council_chapters[0].get(\"hub_expected_count\")" not in MONITOR_SRC

    def test_the_caller_actually_uses_it(self):
        """THE MUTATION THAT SURVIVED. pick_hub_row can be perfect while the loop
        ignores it: reverting `hub_url` to `council_chapters[0]` broke no test, because
        the rule was restated in this file rather than imported. Now it is imported --
        and this asserts the caller reads from the row it returns."""
        assert "hub_row = pick_hub_row(council_chapters)" in MONITOR_SRC
        assert 'hub_url = (hub_row.get("council_page_url") or "").strip() or None' \
            in MONITOR_SRC, (
            "hub_url is no longer derived from pick_hub_row's row, so the selection "
            "is decorative and index zero is back in charge"
        )
        assert 'council_chapters[0].get("council_page_url")' not in MONITOR_SRC


class TestCause3TheSutherlandSlugAlias:
    def test_the_registry_slug_resolves(self):
        assert "sutherland_shire" in HUB_SCRAPERS, (
            "the registry slug is sutherland_shire; without the alias its scraper is "
            "unreachable and the council is never discovered from"
        )

    def test_it_is_the_same_scraper_not_a_copy(self):
        assert HUB_SCRAPERS["sutherland_shire"] is HUB_SCRAPERS["sutherland"], (
            "two entries pointing at different functions is how two scrapers start "
            "disagreeing about one council"
        )

    def test_the_hills_alias_it_mirrors_is_still_there(self):
        """This alias exists because the_hills_shire's did. If that one goes, the
        pattern has changed and this should be revisited, not silently kept."""
        assert HUB_SCRAPERS["the_hills_shire"] is HUB_SCRAPERS["the_hills"]


class TestAHubFailureNoLongerCostsTheCouncilItsChangeDetection:
    def test_the_continue_is_gone(self):
        """THE seven-week bug. `continue` skipped the per-chapter hash checks too."""
        block = _hub_except_block()
        assert "continue" not in block, (
            "a hub scrape failure skips the per-chapter checks again, so one 403 on a "
            "council's document-list page costs it all change detection"
        )

    def test_a_hub_403_is_bucketed_as_infrastructure(self):
        """Excluded from n_real_failed, per WAFBlockError's stated doctrine, so a WAF
        does not page a human every single run."""
        block = _hub_except_block()
        assert 'results["waf_blocked"].append' in block
        assert "is_waf_denial(exc)" in block

    def test_a_hub_failure_no_longer_charges_every_chapter(self):
        """`failed += len(council_chapters)` counted one hub error as N chapter
        failures AND then skipped the loop that would have said otherwise. The loop
        runs now, so keeping that would double-count every chapter."""
        block = _hub_except_block()
        assert "len(council_chapters)" not in block, (
            "a hub failure still charges one failure per chapter, which double-counts "
            "now that the per-chapter loop runs"
        )

    def test_a_non_403_hub_error_is_still_a_real_failure(self):
        """The fall-through must not make every hub error free. A parse error on a
        hub page is a genuine problem and has to reach the exit code."""
        block = _hub_except_block()
        assert 'results["failed"] += 1' in block

    def test_the_alert_still_fires(self):
        block = _hub_except_block()
        assert "send_telegram(msg)" in block


class TestTheWafClassifier:
    """It decides whether a hub failure reaches the exit code, so a false positive
    hides a real content failure. Tested in both directions."""

    @pytest.mark.parametrize("msg", [
        "Hub page returned HTTP 403",
        "hub page returned http 403",
        "403 Forbidden",
        "Access denied: Forbidden",
        "unexpected status 403 from hub",
    ])
    def test_access_denials_are_recognised(self, msg):
        assert is_waf_denial(Exception(msg)) is True

    @pytest.mark.parametrize("msg", [
        "Hub page returned HTTP 500",
        "Could not parse hub page: no links found",
        "Hub returned 0 PDF links",
        "Connection reset by peer",
        "Hub page returned HTTP 404",
    ])
    def test_real_failures_are_not_excused(self, msg):
        assert is_waf_denial(Exception(msg)) is False, (
            f"{msg!r} was treated as infrastructure, so it is excluded from the exit "
            f"code and a genuine hub failure goes unreported"
        )

    def test_a_403_inside_a_url_is_not_a_denial(self):
        """The reason this matches whole tokens instead of a bare '403': a document
        name or path can contain it, and excusing a real failure is the one direction
        that must not happen."""
        assert is_waf_denial(
            Exception("Could not parse https://c.example/docs/dcp-403-part-b.pdf")
        ) is False


class TestTheModuleStillParsesAndTheContractIsIntact:
    def test_the_source_is_valid_python(self):
        ast.parse(MONITOR_SRC)

    def test_the_exit_code_contract_is_untouched(self):
        """These fixes must not change what pages a human. 1 = real failure,
        2 = changes found, 0 = clean."""
        from r2_monitor import run_exit_code
        assert run_exit_code(0, 0) == 0
        assert run_exit_code(3, 0) == 2
        assert run_exit_code(0, 1) == 1
        assert run_exit_code(3, 1) == 1
