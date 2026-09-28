"""A ratchet that can only rise, on a number that rises by design, fails for ever.

WHAT HAPPENED, 2026-09-28
-------------------------
`scripts/check_satellite_manifests.py` counts reports carrying no execution manifest
and its rule is that the count may only FALL. A flood report for 38 Park Rd Bowral was
created at 01:52 UTC and took flood from 143 to 144, which failed the `gates` workflow
on EVERY open PR. Main's previous run had passed at 143.

Nothing in the report path was wrong. The row was a CACHE HIT: `run_date = 2026-07-24`
against `created_at = 2026-09-28`, i.e. a new row written for a new report id carrying
the 24 July computation's inputs and date across verbatim. `services/flood_truth.py`
does that deliberately, and says why -- a re-derived manifest "would claim inputs the
cached numbers never came from".

So the copy of a pre-manifest report has no manifest either, permanently, and cannot
be given one without fabricating it. Every future view of such an address raised the
count by one. The check was therefore guaranteed to fail eventually, and then stay
failed, which is why it also prints of itself:

    "target": "every NEW report carries a manifest; NOT enforced --
               observation mode until false-positive behaviour is known"

This IS that false-positive behaviour, now known.

THE RULE
--------
A row's missing manifest is only that row's fault when the row is its own computation.
`run_date >= created_at::date` keeps originals and excuses copies.

MEASURED THE SAME DAY, across all four counted products: 810 rows carry no manifest and
exactly ONE is a copy. So this excuses precisely the row it is meant to and no others,
and the baseline does not move -- flood returns to 143 rather than being raised to 144.
That distinction is the whole point: raising the baseline would have hidden a real
regression the next time one happened.
"""
from __future__ import annotations

import ast
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_SRC = (ROOT / "scripts" / "check_satellite_manifests.py").read_text(
    encoding="utf-8")
FLOOD_SRC = (ROOT / "services" / "flood_truth.py").read_text(encoding="utf-8")

#: The counted products, as the check itself lists them.
PRODUCTS = ("flood", "shadow", "solar-yield", "bushfire")


def _property_reports_query() -> str:
    """The SELECT over property_reports, normalised to one line."""
    i = CHECK_SRC.index("FROM property_reports")
    start = CHECK_SRC.rindex("SELECT product", 0, i)
    end = CHECK_SRC.index("GROUP BY product", i)
    return " ".join(CHECK_SRC[start:end].split())


class TestTheCounterExcludesACachedCopy:
    def test_the_query_filters_on_run_date_against_created_at(self):
        q = _property_reports_query()
        assert "run_date >= created_at::date" in q, (
            "the counter no longer excludes cached copies, so a copy of any "
            "pre-manifest report raises a count that may only fall -- the check is "
            "guaranteed to fail and then stay failed"
        )

    def test_it_still_counts_the_four_products(self):
        q = _property_reports_query()
        for product in PRODUCTS:
            assert f"'{product}'" in q, (
                f"{product} dropped out of the count, which lowers the number for a "
                f"reason that is not an improvement"
            )

    def test_it_still_asks_about_the_manifest_key(self):
        """The exclusion must narrow WHICH ROWS are counted, never what is counted
        about them. Dropping the manifest test would make every row pass."""
        q = _property_reports_query()
        assert "inputs ? 'execution_manifest'" in q

    def test_the_exclusion_is_on_property_reports_not_granny_flat(self):
        """granny_flat_reports is counted by a separate query with no run_date/
        created_at pair. A blanket edit would have broken it."""
        i = CHECK_SRC.index("FROM granny_flat_reports")
        start = CHECK_SRC.rindex("SELECT", 0, i)
        assert "run_date" not in CHECK_SRC[start:i]


class TestTheRuleItself:
    """`run_date >= created_at::date` decides whether a gap is the row's own.
    Exercised as the predicate, on the shapes that actually occur."""

    @staticmethod
    def _is_own_computation(run_date: date, created_at: date) -> bool:
        return run_date >= created_at

    def test_a_fresh_run_is_its_own_computation(self):
        assert self._is_own_computation(date(2026, 7, 24), date(2026, 7, 24)) is True

    def test_the_bowral_shape_is_a_copy(self):
        """The exact row that failed the gate: computed 24 July, written 28 September."""
        assert self._is_own_computation(date(2026, 7, 24), date(2026, 9, 28)) is False

    def test_a_copy_made_one_day_later_is_still_a_copy(self):
        assert self._is_own_computation(date(2026, 7, 24), date(2026, 7, 25)) is False

    def test_a_run_date_in_the_future_is_treated_as_its_own(self):
        """Not a copy of anything. It would be a different defect -- a freshness lie --
        and excusing it here would hide it behind the wrong check."""
        assert self._is_own_computation(date(2026, 9, 29), date(2026, 9, 28)) is True


class TestTheCopyNowSaysSoInTheRow:
    """The counter should not have to infer a copy from date arithmetic."""

    def test_the_helper_exists(self):
        assert "def _cached_inputs_with_provenance(" in FLOOD_SRC, (
            "the cache branch no longer records that its inputs are a copy, so the "
            "only evidence is the run_date/created_at comparison"
        )

    def test_the_cache_branch_uses_it(self):
        assert "_cached_inputs_with_provenance(cached, req)" in FLOOD_SRC

    def test_it_adds_provenance_when_inputs_exist_without_a_manifest(self):
        """The gap the old code left. It only added a note when the cached inputs were
        entirely EMPTY -- a pre-manifest row holding {"lat":..., "lng":...} was copied
        verbatim, so the copy looked exactly like a fresh computation that had failed to
        record a manifest. That is the 38 Park Rd Bowral shape."""
        fn = FLOOD_SRC[FLOOD_SRC.index("def _cached_inputs_with_provenance("):]
        fn = fn[:fn.index("def _write_report(")]
        assert "if MANIFEST_KEY not in inputs:" in fn
        assert "inputs_provenance" in fn

    def test_it_never_writes_a_manifest(self):
        """A note about provenance is a fact. A re-derived manifest would be a claim
        about inputs the cached numbers never came from."""
        fn = FLOOD_SRC[FLOOD_SRC.index("def _cached_inputs_with_provenance("):]
        fn = fn[:fn.index("def _write_report(")]
        assert "build_manifest" not in fn, (
            "the cache path builds a manifest, which fabricates provenance for numbers "
            "that were computed under different inputs"
        )
        assert re.search(r"inputs\[MANIFEST_KEY\]\s*=", fn) is None

    def test_the_empty_inputs_case_is_kept(self):
        """The original behaviour for a row with no inputs at all must survive: say so,
        rather than presenting the new request's coordinates as the old run's record."""
        fn = FLOOD_SRC[FLOOD_SRC.index("def _cached_inputs_with_provenance("):]
        fn = fn[:fn.index("def _write_report(")]
        assert "original inputs not recorded (pre-manifest report)" in fn

    def test_it_does_not_mutate_the_cached_row(self):
        """`dict(cached.get("inputs") or {})` -- a copy. Mutating the cached dict would
        write a provenance note into whatever else holds a reference to it."""
        fn = FLOOD_SRC[FLOOD_SRC.index("def _cached_inputs_with_provenance("):]
        fn = fn[:fn.index("def _write_report(")]
        assert 'inputs = dict(cached.get("inputs") or {})' in fn


class TestTheHelperBehaviour:
    """Imported and run, not just read. Uses a stub request rather than the real
    FloodRequest so this needs none of the service's dependencies."""

    @staticmethod
    def _call(cached, lat=-34.5, lng=150.4):
        import types
        src = FLOOD_SRC[FLOOD_SRC.index("def _cached_inputs_with_provenance("):]
        src = src[:src.index("def _write_report(")]
        ns = {"MANIFEST_KEY": "execution_manifest"}
        exec(compile(src, "flood_truth_helper", "exec"), ns)
        req = types.SimpleNamespace(lat=lat, lng=lng)
        return ns["_cached_inputs_with_provenance"](cached, req)

    def test_empty_inputs_get_the_not_recorded_note(self):
        out = self._call({"inputs": {}, "run_date": date(2026, 7, 24)})
        assert out["inputs_provenance"] == (
            "original inputs not recorded (pre-manifest report)")
        assert out["lat"] == -34.5

    def test_the_bowral_shape_gets_a_copy_note_naming_the_date(self):
        out = self._call({"inputs": {"lat": -34.488, "lng": 150.43},
                          "run_date": date(2026, 7, 24)})
        assert "2026-07-24" in out["inputs_provenance"]
        assert "no execution manifest" in out["inputs_provenance"]
        assert out["lat"] == -34.488, "the ORIGINAL coordinates must be preserved"

    def test_a_cached_row_that_has_a_manifest_is_left_alone(self):
        """No note, nothing added. The copy's provenance is the original's manifest."""
        cached = {"inputs": {"lat": 1.0, "execution_manifest": {"deploy_sha": "abc"}},
                  "run_date": date(2026, 9, 1)}
        out = self._call(cached)
        assert "inputs_provenance" not in out
        assert out["execution_manifest"] == {"deploy_sha": "abc"}

    def test_an_unrecorded_run_date_is_stated_not_guessed(self):
        out = self._call({"inputs": {"lat": 1.0}, "run_date": None})
        assert "unrecorded date" in out["inputs_provenance"]

    def test_the_cached_dict_is_not_mutated(self):
        cached = {"inputs": {"lat": 1.0}, "run_date": date(2026, 7, 24)}
        self._call(cached)
        assert "inputs_provenance" not in cached["inputs"]


class TestTheBaselineWasNotRaised:
    """The wrong fix was available and is asserted against: bumping flood to 144 would
    have cleared the gate and destroyed the ratchet's only guarantee."""

    def test_the_committed_baseline_still_says_143_for_flood(self):
        import json
        baseline = json.loads(
            (ROOT / ".claude" / "manifest_coverage_baseline.json").read_text(
                encoding="utf-8"))
        per_key = baseline.get("per_key", baseline)
        assert per_key["flood"] == 143, (
            "the flood baseline moved. If it ROSE, a real regression has been "
            "accommodated rather than fixed -- the one thing this ratchet exists to "
            "prevent."
        )

    def test_the_may_only_fall_rule_is_still_stated(self):
        assert "Lower it with --baseline --update when work lands." in CHECK_SRC


class TestBothFilesStillParse:
    def test_the_check_parses(self):
        ast.parse(CHECK_SRC)

    def test_flood_truth_parses(self):
        ast.parse(FLOOD_SRC)
