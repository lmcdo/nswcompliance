"""The re-tag script counted every change as a narrowing, so nobody could see one.

`scripts/retag_applicability_slug_docids.py` printed two numbers named
`served_zone_narrowed` and `served_devtype_narrowed`. Both were incremented on
`zones != old_z` -- inequality, not direction. On 2026-09-22 a dry run with
canterbury_bankstown added printed "served rows narrowed -- zones 83, dev types
140" and the run was held back as unsafe. Classified properly on 2026-09-23 the
same plan held **zero** zone narrowings and **eight** dev-type ones, which is a
morning's adjudication rather than a wall.

That is the failure in `feedback-counting-is-not-comparing`: a repair and a new
break cancel inside a count, and here a widening and a narrowing did too. The
direction is the entire risk, because both applicability columns are HARD
filters on the served answer -- a widened row is noise, a narrowed row is gone.

MUTATION NOTE. Every case below has a confusable negative sitting next to it:
  narrowed          vs widened          (same shape, opposite direction)
  narrowed_from_all vs widened_to_all   (ALL on the other side)
  swapped           vs same             (both are "not a subset either way")
A classifier that returns "narrowed" for everything fails the widening cases; one
that returns "same" for everything fails all of them; one that treats ALL as an
ordinary member calls ['ALL'] -> ['R2'] a swap and misses the only case that can
hide a whole chapter.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.retag_applicability_slug_docids import NARROWING, classify  # noqa: E402


class TestDirectionIsRead:
    @pytest.mark.parametrize("before,after,expected", [
        # --- losing members: the liability direction ---
        (["R1", "R2", "R3"], ["R2", "R3"],  "narrowed"),  # noqa: zone-codes (fixture values for a direction test, not a lookup table)
        (["ALL"],            ["E4"],        "narrowed_from_all"),
        # `'ALL' = ANY(col)` is MEMBERSHIP: a mixed array is universal too, so
        # losing the ALL is losing universality, not an ordinary narrowing.
        (["ALL", "R1"],      ["R1"],        "narrowed_from_all"),  # noqa: zone-codes
        (["ALL", "R1"],      ["ALL"],       "same"),  # noqa: zone-codes
        (["R1"],             ["ALL", "R1"], "widened_to_all"),  # noqa: zone-codes
        (None,               ["E4"],        "narrowed_from_all"),   # NULL is universal
        (None,               [],            "narrowed_from_all"),   # every property -> none
        (["ALL"],            [],            "narrowed_from_all"),
        # --- gaining members: noise, never a hidden control ---
        (["R2", "R3"],       ["R1", "R2", "R3"], "widened"),  # noqa: zone-codes
        (["E4"],             ["ALL"],       "widened_to_all"),
        (["E4"],             None,          "widened_to_all"),   # NULL is universal
        ([],                 ["E4"],        "widened"),          # nothing -> something
        ([],                 ["ALL"],       "widened_to_all"),
        # --- neither a subset nor a superset: loses at least one member ---
        (["food_and_drink_premises"], ["warehouse"], "swapped"),
        # --- no movement ---
        (["R2"],             ["R2"],        "same"),  # noqa: zone-codes
        (["ALL"],            ["ALL"],       "same"),
        (None,               ["ALL"],       "same"),
        (None,               None,          "same"),
        ([],                 [],            "same"),
        # order is not a change; these columns are sets in meaning
        (["R3", "R2"],       ["R2", "R3"],  "same"),  # noqa: zone-codes
    ])
    def test_it_names_the_direction(self, before, after, expected):
        assert classify(before, after) == expected

    def test_NULL_and_an_empty_array_are_OPPOSITE_states(self):
        """The serving clause is `col && $q OR col IS NULL OR 'ALL' = ANY(col)`.
        NULL matches every query; an empty array matches NOTHING. They are
        opposite ends, not synonyms.

        This test used to assert the reverse -- that `[]` and `['ALL']` were the
        same state, "because that is how the serving query reads them" -- which
        misread `IS NULL` as covering `= '{}'`. The cross-review caught it on
        2026-09-23. Nothing had been misclassified in practice (0 served rows
        hold NULL and 0 hold an empty array in either column, measured the same
        day), but the wrong reason was written down where the next person would
        copy it, and NULL -> [] hides a row from every property while scoring
        `same`.
        """
        assert classify(None, ["E4"]) in NARROWING      # universal -> one zone
        assert classify(None, []) in NARROWING          # universal -> nothing
        assert classify([], ["E4"]) not in NARROWING    # nothing -> one zone
        assert classify([], ["E4"]) == "widened"
        assert classify(None, []) != classify([], None)

    def test_a_swap_counts_as_a_narrowing(self):
        """It loses `food_and_drink_premises`, so some property stops seeing the
        row. Only the gained members are new; the lost one is the risk."""
        assert classify(["food_and_drink_premises"], ["warehouse"]) in NARROWING

    def test_widening_is_never_a_narrowing(self):
        for before, after in ((["R2"], ["R2", "R3"]), (["E4"], ["ALL"]),  # noqa: zone-codes
                              (["R2"], ["R2"]), ([], ["E4"]), (["E4"], None)):  # noqa: zone-codes
            assert classify(before, after) not in NARROWING


class TestTheApplyGateRefuses:
    """The dry run is only a safety feature if `--apply` cannot skip past it."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "scripts/retag_applicability_slug_docids.py", *args],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
            env={**__import__("os").environ, "DATABASE_URL": "", "SUPABASE_DB_URL": ""},
        )

    def test_it_refuses_to_run_with_no_database_url_rather_than_reporting_clean(self):
        """Nothing checked is not a pass -- the script says so itself and exits 2."""
        done = self._run("--councils", "campbelltown")
        assert done.returncode == 2
        assert "DATABASE_URL not set" in done.stderr

    def test_expect_narrowings_is_a_named_argument_not_a_flag(self):
        """`--expect-narrowings` has to carry the COUNT. A bare flag would let an
        operator acknowledge narrowings without having read how many there are,
        which is the same as not having a gate."""
        done = self._run("--help")
        assert "--expect-narrowings EXPECT_NARROWINGS" in done.stdout

    def test_the_council_list_is_an_argument(self):
        """It was hardcoded to three councils, so every number it printed --
        including "no_config served" -- was silently scoped to those three while
        reading like a global measurement."""
        done = self._run("--help")
        assert "--councils" in done.stdout


class TestTheBackupCannotBeSilentlyStale:
    def test_the_default_name_is_not_a_fixed_string(self):
        """`CREATE TABLE IF NOT EXISTS <name> AS SELECT ...` is a NO-OP when the
        name is taken, and the guard that follows counts rows in whatever is
        already there. `regulatory_provisions_dq33_backup_20260801` has held
        22,007 rows since the first run, so any later run using the old default
        would have passed its own backup check against 2026-08-01 data and
        written with no usable rollback.
        """
        src = (ROOT / "scripts" / "retag_applicability_slug_docids.py").read_text(
            encoding="utf-8")
        assert 'default="regulatory_provisions_dq33_backup_20260801"' not in src
        assert "CREATE TABLE IF NOT EXISTS" not in src, (
            "the backup must fail on an existing table, not silently reuse it")
        assert "to_regclass" in src, "nothing checks whether the table already exists"


class TestARetiredZoneCodeCannotReachTheWrite:
    """DQ-30's rule, applied BEFORE the UPDATE instead of after it.

    On 2026-09-23 this retag was one keystroke from tagging 34 served Warringah
    rows with B1/B2/B5/B6/B7 -- business zones abolished by the 2022  # noqa: zone-codes (the retired codes the incident was about, named in prose)
    employment-zone reform. Warringah DCP 2011 predates the reform and still
    names them throughout, so the tagger read them straight out of the plan
    text. `validate_zone_code_validity.py` would have caught it, and did, but
    only in the post-commit completeness report: after the rows were live.

    What actually caught it was me reading the dry run's narrowing shapes.
    That is not a check. Forcing the regression on 2026-09-23 -- removing the
    `valid_zones` argument -- makes `retired_zone_codes` report 68 rows and
    `--apply` exit 2 with nothing written, so this one is known to fail rather
    than merely believed to.

    MUTATION NOTE. Every case has its confusable negative:
      a retired code     vs a current code in the same table
      a code not in ANY  vs 'ALL', which is not a zone code at all
      unknown council    vs known council       (skip, never a silent pass)
    A function that returns every zone fails the clean cases; one that returns
    [] always fails the retired ones; one that forgets to special-case 'ALL'
    fails on every universal row in the table.
    """

    #: Shaped like the real ones: `load_ground_truth` keys by LGA name and
    #: `load_slug_resolution` maps a council slug onto that key.
    TRUTH = {"northern beaches": {"R2", "R3", "E4", "MU1", "C4"}}  # noqa: zone-codes (a FIXTURE land-use table, deliberately fixed so the test does not move when the real taxonomy does)
    SLUGS = {"northern_beaches": "northern beaches"}

    def _bad(self, zones, council="northern_beaches"):
        from scripts.retag_applicability_slug_docids import retired_zone_codes

        return retired_zone_codes(zones, council, self.TRUTH, self.SLUGS)

    def test_a_retired_business_zone_is_reported(self):
        """The exact 2026-09-23 near-miss."""
        assert self._bad(["B1", "B2", "B5"]) == ["B1", "B2", "B5"]  # noqa: zone-codes (retired codes, fixed on purpose: the taxonomy no longer lists them, so importing them is impossible by construction)

    def test_a_current_zone_in_the_same_table_is_not(self):
        """The confusable negative. R2 and B2 are the same shape; only one of  # noqa: zone-codes (one retired, one current, same shape -- the confusable negative)
        them still exists in this council's land-use table."""
        assert self._bad(["R2", "R3", "E4"]) == []  # noqa: zone-codes (current codes, fixed to match the fixture table above)

    def test_a_mixed_row_reports_only_the_retired_codes(self):
        """A row narrowing onto R2 *and* B2 is still a bug, and naming R2 in the  # noqa: zone-codes (one retired, one current, same shape -- the confusable negative)
        error would send whoever reads it looking at the wrong half."""
        assert self._bad(["R2", "B2", "R3"]) == ["B2"]  # noqa: zone-codes (lowercase input for the case-normalisation case)

    def test_all_is_not_treated_as_a_zone_code(self):
        """`'ALL'` is the universal marker the serving query tests with
        `'ALL' = ANY(col)`. Testing it against a land-use table would abort the
        retag on every universal row -- which is most of them."""
        assert self._bad(["ALL"]) == []
        assert self._bad(["ALL", "B2"]) == ["B2"]

    def test_an_unresolvable_council_is_skipped_not_passed_or_failed(self):
        """Three-state, matching the checker this borrows ground truth from. A
        statewide instrument has no LGA land-use table; treating that as a
        violation would abort every run, and this gate is not the check that
        covers it."""
        assert self._bad(["B2"], council="camden") == []
        assert self._bad(["B2"], council=None) == []

    def test_case_is_normalised_before_comparison(self):
        """The tagger has emitted lowercase codes from plan text before. A
        case-sensitive comparison would call every one of them retired."""
        assert self._bad(["r2"]) == []
        assert self._bad(["b2"]) == ["B2"]

    def test_the_gate_is_wired_into_the_apply_path_not_just_the_dry_run(self):
        """A check that only prints is a note. `main()` must abort on it, and
        must do so BEFORE the backup table is created -- a run that aborts after
        creating one leaves a half-built artefact the next run's existence check
        then trips over.
        """
        lines = (ROOT / "scripts" / "retag_applicability_slug_docids.py").read_text(
            encoding="utf-8").splitlines()
        aborts = [i for i, ln in enumerate(lines)
                  if ln.strip() == "if invalid:"
                  and "ERROR" in "\n".join(lines[i + 1:i + 4])]
        assert aborts, "nothing aborts on invalid zones -- the gate only prints"
        abort = aborts[-1]
        backup = next(i for i, ln in enumerate(lines) if "to_regclass" in ln)
        assert abort < backup, (
            "the invalid-zone abort must come before the backup table is built")
        assert any(ln.strip() == "return 2" for ln in lines[abort:abort + 12]), (
            "the abort prints an error and carries on")

    def test_the_ground_truth_is_the_checkers_own_not_a_second_copy(self):
        """Two implementations of "is this zone real" would drift, and the drift
        would be invisible: the pre-write gate would pass rows the post-write
        report then flags, with no way to tell which one was wrong."""
        src = (ROOT / "scripts" / "retag_applicability_slug_docids.py").read_text(
            encoding="utf-8")
        assert "from validate_zone_code_validity import" in src
        assert "load_ground_truth" in src and "load_slug_resolution" in src
