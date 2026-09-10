"""A retired zone code must not be STORED, not merely cleaned up afterwards.

REAL FINDING, measured 2026-09-10. Six freshly-written ku_ring_gai provisions were
tagged `B2` — a code NSW retired in 2022. Nothing is zoned B2 any more, so those rows
can never match a current-zone lookup: they are served, and unreachable.

They were NEW rows. DQ-30 was declared fixed on 2026-08-12, and that repair cleaned
the rows that existed then. Nothing guarded the write, so the next extraction made
more. That is the whole shape of the bug — the same shape as the precinct keys, and
the same shape DQ-30 had the first time.

WHY THE TAGGER PRODUCES THEM
    scripts/backfill_invalid_zone_codes.py records the cause: the blind text-regex
    fallback matches "Part B3" in DCP prose as zone B3. It also records why
    re-running the tagger repairs 0 of 241 such rows — it reproduces its own output.
    That is the same self-comparison that let the old "0% drift" check report success
    while 112 live rows stayed broken.

WHAT IS PINNED HERE
  - a dead code is dropped, and the row falls back to the existing honest 'ALL'
  - a real code is untouched (the confusable negative — a guard that eats good data
    is worse than the bug)
  - mixed input keeps the good and drops the dead, rather than discarding the row
  - THE SAFETY CASE: an LGA with no complete scrape is left ALONE. Absence of ground
    truth is not evidence a code is wrong, and emptying a council's zones over a
    coverage gap would be the guard doing the damage it exists to prevent.
  - the tagger's SELECT actually reads source_council, without which it cannot know
    which LGA to check and the guard silently never fires
"""
import os
import sys

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://x")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from enrichment.pipeline import keep_only_zones_valid_in_lga as keep  # noqa: E402
from enrichment.config.zone_taxonomy import LEGACY_ZONES  # noqa: E402

# A realistic current-vocabulary set. Deliberately NOT a hardcoded NSW zone table —
# it is a fixture standing in for whatever lep_zone_coverage returns at runtime.
KG = {"R2", "R3", "E1", "E2", "MU1", "C2", "C4", "RE1", "SP2"}  # noqa: zone-codes


class TestTheDefect:
    def test_a_retired_code_is_dropped(self):
        """['B2'] is the exact live value on all six rows found 2026-09-10."""
        assert keep(["B2"], KG) == ["ALL"]

    def test_every_retired_business_code_is_dropped(self):
        for dead in LEGACY_ZONES:
            assert keep([dead], KG) == ["ALL"], f"{dead} survived"

    def test_all_dead_collapses_to_the_existing_undetermined_value(self):
        """'ALL' is not a new semantic invented here. It is what the tagger already
        stores when it finds no zone evidence, and what backfill_invalid_zone_codes
        stores when nothing survives — so downstream sees a value it already knows."""
        assert keep(["B1", "B2", "B3"], KG) == ["ALL"]  # noqa: zone-codes


class TestConfusableNegatives:
    """A guard that eats good data is worse than the bug it fixes."""

    @pytest.mark.parametrize("good", [["R2"], ["E1"], ["MU1"], ["R2", "R3"], ["SP2"]])  # noqa: zone-codes
    def test_a_real_zone_is_untouched(self, good):
        assert keep(good, KG) == good

    def test_the_wildcard_survives_even_though_it_is_not_a_zone(self):
        """'ALL' is not in lep_zone_coverage and must not be filtered out — it is the
        undetermined marker, not a code.

        keep(["ALL"]) alone is NOT sufficient evidence: drop the wildcard clause and
        'ALL' is filtered out, kept becomes empty, and the fallback puts ['ALL'] back
        — an identical result from broken logic. Mutation testing caught exactly that
        (the mutant survived). The mixed case is the one that can actually fail.
        """
        assert keep(["ALL"], KG) == ["ALL"]
        assert keep(["ALL", "R2"], KG) == ["ALL", "R2"], (
            "the wildcard must be preserved alongside a real zone; without the "
            "explicit wildcard clause this collapses to ['R2']"
        )
        assert keep(["R2", "ALL"], KG) == ["R2", "ALL"]

    def test_mixed_keeps_the_good_and_drops_the_dead(self):
        """The row is not discarded because one code was wrong."""
        assert keep(["R2", "B2"], KG) == ["R2"]  # noqa: zone-codes
        assert keep(["B4", "E1", "B2", "MU1"], KG) == ["E1", "MU1"]  # noqa: zone-codes

    def test_case_is_not_a_reason_to_drop_a_real_zone(self):
        assert keep(["r2"], KG) == ["r2"]


class TestTheSafetyCase:
    def test_an_lga_with_no_ground_truth_is_left_completely_alone(self):
        """THE most important test here.

        An empty valid-set means "this LGA has not been scraped", which is NOT
        evidence that any code is wrong. If the guard treated it as such it would
        empty every zone for every un-onboarded council on the first run — the guard
        causing a far larger version of the defect it exists to prevent.
        """
        assert keep(["B2"], set()) == ["B2"]
        assert keep(["R2"], set()) == ["R2"]
        assert keep(["R2", "B2"], set()) == ["R2", "B2"]  # noqa: zone-codes

    def test_empty_and_none_inputs_pass_through_unchanged(self):
        assert keep([], KG) == []
        assert keep(None, KG) is None
        assert keep(None, set()) is None

    def test_a_non_string_entry_cannot_crash_the_run(self):
        """A malformed array must not take down a whole enrichment batch."""
        assert keep([None, "R2"], KG) == ["R2"]
        assert keep([123], KG) == ["ALL"]


class TestItIsActuallyWired:
    """A pure function nothing calls fixes nothing."""

    def test_the_tagger_reads_source_council(self):
        """Without this column the guard cannot know which LGA to check, and it
        silently never fires — the same way the repealed-source guard needed
        council_url added to its SELECT."""
        import pathlib
        src = (pathlib.Path(__file__).resolve().parent.parent
               / "enrichment" / "pipeline.py").read_text(encoding="utf-8")
        assert "SELECT id, provision_text, document_id, source_council" in src, (
            "run_applicability_tagging must select source_council"
        )

    def test_the_filter_is_applied_before_the_row_is_queued_for_write(self):
        import pathlib
        src = (pathlib.Path(__file__).resolve().parent.parent
               / "enrichment" / "pipeline.py").read_text(encoding="utf-8")
        i_filter = src.find("keep_only_zones_valid_in_lga(zones,")
        i_append = src.find("updates.append((zones, dev_types,")
        assert i_filter != -1, "the guard is not called in the tagging loop"
        assert i_append != -1, "the update-append moved; this test needs updating"
        assert i_filter < i_append, (
            "filtering AFTER the row is queued would store the unfiltered value"
        )
        # Position alone is not enough: the filter can be computed and thrown away.
        # Mutation caught this -- deleting `zones = filtered` left both finds intact
        # and the mutant survived, i.e. the guard ran and changed nothing.
        i_assign = src.find("                zones = filtered")
        assert i_assign != -1, (
            "the filtered value is never assigned back to `zones`, so the unfiltered "
            "list is what reaches updates.append -- the guard is decorative"
        )
        assert i_filter < i_assign < i_append

    def test_ground_truth_is_loaded_once_per_run_not_per_row(self):
        """Per-row loading would issue one query per provision across ~20k rows."""
        import pathlib
        src = (pathlib.Path(__file__).resolve().parent.parent
               / "enrichment" / "pipeline.py").read_text(encoding="utf-8")
        # Count CALL sites only. A naive count of the bare name also matches
        # `def _load_zone_ground_truth(conn):`, which is how the first version of
        # this test failed against correct code.
        assert src.count("= _load_zone_ground_truth(conn)") == 1

        # Scope the search to run_applicability_tagging. `while processed < total:`
        # appears in several phases of this module, and searching the whole file
        # matched an EARLIER function's loop — which is how the second version of
        # this test failed against correct code. Two false failures from sloppy
        # anchors, both caught by running it rather than assuming.
        body = src[src.index("def run_applicability_tagging("):]
        i_load = body.find("_zone_truth, _zone_slugs = _load_zone_ground_truth(conn)")
        i_loop = body.find("while processed < total:")
        assert i_load != -1, "the loader is not called inside run_applicability_tagging"
        assert i_loop != -1, "the batch loop moved; this test needs updating"
        assert i_load < i_loop, "ground truth must be loaded before the batch loop"

    def test_the_image_ships_the_checker_the_guard_imports(self):
        """A guard that fails soft must still be SHIPPED, or it protects nothing.

        enrichment/pipeline.py imports load_ground_truth and load_slug_resolution
        from scripts/validate_zone_code_validity.py. That import failing is handled
        -- it degrades to a no-op, which is right when reference data cannot be read
        -- but "handled" and "never happens in production" are different things. If
        the file is not in Dockerfile.monitors the guard is off on every nightly run
        and says so only in a warning line nobody reads.

        The same omission was found in the preceding precinct-keys PR, which is why
        it is checked here rather than assumed.
        """
        import pathlib
        dockerfile = (pathlib.Path(__file__).resolve().parent.parent
                      / "Dockerfile.monitors").read_text(encoding="utf-8")
        assert "scripts/validate_zone_code_validity.py" in dockerfile, (
            "enrichment/pipeline.py imports this at tagging time; without the COPY "
            "the zone guard is a silent no-op in production"
        )
