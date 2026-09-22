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
        ([],                 ["E4"],        "narrowed_from_all"),
        (None,               ["E4"],        "narrowed_from_all"),
        # --- gaining members: noise, never a hidden control ---
        (["R2", "R3"],       ["R1", "R2", "R3"], "widened"),  # noqa: zone-codes
        (["E4"],             ["ALL"],       "widened_to_all"),
        # --- neither a subset nor a superset: loses at least one member ---
        (["food_and_drink_premises"], ["warehouse"], "swapped"),
        # --- no movement ---
        (["R2"],             ["R2"],        "same"),
        (["ALL"],            ["ALL"],       "same"),
        ([],                 ["ALL"],       "same"),
        (None,               ["ALL"],       "same"),
        # order is not a change; these columns are sets in meaning
        (["R3", "R2"],       ["R2", "R3"],  "same"),  # noqa: zone-codes
    ])
    def test_it_names_the_direction(self, before, after, expected):
        assert classify(before, after) == expected

    def test_empty_and_ALL_are_the_same_state(self):
        """`[]` and `['ALL']` both mean "applies to everything" to the serving
        query (`v2_applicable_dev_types IS NULL OR 'ALL' = ANY(...)`). Treating
        `[]` as an empty set instead would call `[] -> ['E4']` a WIDENING -- the
        exact inversion that lets a hidden control through unexamined."""
        assert classify([], ["E4"]) == classify(["ALL"], ["E4"])
        assert classify([], ["E4"]) in NARROWING

    def test_a_swap_counts_as_a_narrowing(self):
        """It loses `food_and_drink_premises`, so some property stops seeing the
        row. Only the gained members are new; the lost one is the risk."""
        assert classify(["food_and_drink_premises"], ["warehouse"]) in NARROWING

    def test_widening_is_never_a_narrowing(self):
        for before, after in ((["R2"], ["R2", "R3"]), (["E4"], ["ALL"]),  # noqa: zone-codes
                              (["R2"], ["R2"])):
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
