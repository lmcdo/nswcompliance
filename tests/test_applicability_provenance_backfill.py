"""The rule that decides whether an ALREADY-TAGGED row gets a provenance written.

SEPARATE FILE ON PURPOSE. tests/test_applicability_provenance.py covers the
TAGGER — that a source is derived correctly when a row is first tagged. That
file arrived with #857, which added these columns and deliberately left
existing rows NULL, on the stated grounds that inventing a source for them
would fabricate the very fact the column exists to record.

This file covers the opposite end: the 10,103 served rows tagged BEFORE those
columns existed, and the rule for recovering their source without inventing
one. #857's reasoning is the constraint, not an obstacle — a source is written
only where today's config still REPRODUCES the stored tags, which demonstrates
the tag rather than asserting it. A disagreement refuses the row and leaves it
counted.

WHY THE EXISTING PHASE COULD NOT DO THIS. `--phase applicability` selects on
`v2_applicable_zones IS NULL`; none of those rows match, so it reports
"Processed: 0" and reads as a no-op rather than a miss.

`tags_reproduce` is pure precisely so the rule deciding 20,948 live writes can
be tested without a database.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from enrichment.pipeline import tags_reproduce  # noqa: E402


class TestAccepts:
    def test_identical(self):
        assert tags_reproduce(["zone_a"], ["dwelling_house"],
                              ["zone_a"], ["dwelling_house"])

    def test_order_is_not_disagreement(self):
        """Array order carries no meaning; a reordering must not refuse a row."""
        assert tags_reproduce(["zone_a", "zone_b"], ["a", "b"],
                              ["zone_b", "zone_a"], ["b", "a"])

    def test_all_reproducing_all(self):
        assert tags_reproduce(["ALL"], ["ALL"], ["ALL"], ["ALL"])

    def test_null_and_empty_are_the_same_absence(self):
        """A row cannot disagree with itself over which kind of empty it used."""
        assert tags_reproduce(None, None, [], [])
        assert tags_reproduce([], [], None, None)


class TestRefuses:
    def test_a_narrower_recompute_is_a_mismatch_not_a_refinement(self):
        """THE ONE THAT MATTERS.

        Stored ALL, config now says retail_premises. That is not an improvement
        to record — the product currently SERVES ALL, and writing a source here
        would attach a justification to a claim the config contradicts. 1,390
        real rows are in this state and every one is refused.
        """
        assert not tags_reproduce(["ALL"], ["ALL"], ["ALL"], ["retail_premises"])

    def test_a_broader_recompute_is_also_a_mismatch(self):
        assert not tags_reproduce(["ALL"], ["retail_premises"], ["ALL"], ["ALL"])

    def test_zones_disagreeing_refuses_even_when_dev_types_match(self):
        """Both axes must reproduce. Checking only dev_types would write a
        source onto a row whose zone tag we can no longer derive."""
        assert not tags_reproduce(["zone_a"], ["ALL"], ["zone_b"], ["ALL"])

    def test_dev_types_disagreeing_refuses_even_when_zones_match(self):
        assert not tags_reproduce(["zone_a"], ["a"], ["zone_a"], ["b"])

    def test_a_subset_is_not_equality(self):
        assert not tags_reproduce(["ALL"], ["a", "b"], ["ALL"], ["a"])
        assert not tags_reproduce(["ALL"], ["a"], ["ALL"], ["a", "b"])


def test_the_rule_can_say_no():
    """Control case.

    Every assertion in TestRefuses is `not tags_reproduce(...)`, which a
    function stubbed to `return False` would satisfy completely — and a rule
    that always refused would write nothing and look like a clean run over
    20,948 rows. So assert it also says yes, or the refusal tests prove nothing.
    """
    assert tags_reproduce(["zone_a"], ["dwelling_house"],
                          ["zone_a"], ["dwelling_house"])
    assert not tags_reproduce(["zone_a"], ["dwelling_house"], ["zone_a"], ["ALL"])


def test_the_phase_writes_only_provenance_columns():
    """The invariant the docstring promises, asserted against the source.

    A future edit that adds v2_applicable_dev_types to that UPDATE would turn a
    provenance backfill into a mass rewrite of live applicability — the exact
    failure the refusal path exists to prevent, and the exact thing #857
    declined to do. Reading the source is crude, but it is the only thing that
    fails when the guarantee is broken.
    """
    src = (_ROOT / "enrichment" / "pipeline.py").read_text(encoding="utf-8")
    start = src.index("def run_applicability_provenance(")
    end = src.index("def run_layer_tagging(", start)
    body = src[start:end]
    update = body[body.index("UPDATE regulatory_provisions"):]
    update = update[:update.index("WHERE id = %s")]
    assert "v2_zone_source" in update and "v2_dev_type_source" in update
    for forbidden in ("v2_applicable_zones", "v2_applicable_dev_types",
                      "provision_text", "v2_is_actionable"):
        assert forbidden not in update, (
            f"{forbidden} appears in the provenance UPDATE. This phase must "
            f"write ONLY the two source columns — see its docstring."
        )
