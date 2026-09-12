"""What a candidate passage is allowed to be before a model reads it as evidence.

Every test here is a real failure this harness produced against production text
on 2026-09-12, not a hypothetical. The two that matter most:

  * a 49,000-character "provision" truncated at a flat 6,000 characters, so 10 of
    100 candidates arrived with the keyword that selected them cut off;
  * a window that kept a number but lost the unit, because the windowing step
    tested "is there a number" rather than the predicate that did the selecting.

Both were silent. Neither is now.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dcp_control_candidates import (  # noqa: E402
    EXCLUDED_TOPICS, MAX_CANDIDATE_CHARS, NUMERIC_POOR_TOPICS,
    SCOPE_RISK_TOPICS, WIDE_WINDOW_CHARS, broken_candidates, wanted,
    window_around)


# --------------------------------------------------------------------------
# wanted() -- and the confusable negatives that must NOT pass it
# --------------------------------------------------------------------------

def test_keyword_and_number_together_is_a_candidate():
    assert wanted("A minimum deep soil zone of 15% of the site area.",
                  "deep_soil_min")


def test_keyword_without_a_number_is_not_a_candidate():
    assert not wanted("Deep soil planting is encouraged across the site.",
                      "deep_soil_min")


def test_number_without_the_keyword_is_not_a_candidate():
    assert not wanted("A minimum of 15% of the site area must be landscaped.",
                      "deep_soil_min")


def test_max_height_needs_a_height_unit_not_merely_any_number():
    """The confusable negative that reached production text.

    "maximum height" beside a percentage states no height at all. It satisfies
    MEASURABLE, which is why MEASURABLE alone was never enough.
    """
    assert not wanted("The maximum height of any sign is 50% of the facade.",
                      "max_height")
    assert wanted("The maximum building height is 8.5m.", "max_height")


def test_secondary_setback_needs_the_word_setback():
    assert not wanted("Corner lots shall address both streets over 12m.",
                      "secondary_street_setback")
    assert wanted("On corner lots the secondary street setback is 3m.",
                  "secondary_street_setback")


# --------------------------------------------------------------------------
# window_around() -- the truncation bug
# --------------------------------------------------------------------------

def test_window_keeps_a_keyword_that_a_flat_truncation_would_have_cut():
    """The 2026-09-12 regression, in its exact shape.

    A provision of ~40k characters whose only deep-soil clause sits at the very
    end. `text[:6000]` returns a passage with no deep soil in it; the model then
    reads pure noise as evidence and the real control is lost silently.
    """
    provision = ("Background narrative about the locality. " * 1000 +
                 "A minimum deep soil zone of 15% of the site area is required.")
    assert len(provision) > 40000
    assert "deep soil" not in provision[:6000]

    kept = window_around(provision, "deep_soil_min")
    assert kept is not None
    assert "deep soil" in kept
    assert "15%" in kept
    assert wanted(kept, "deep_soil_min")


def test_window_never_exceeds_the_ceiling():
    provision = ("deep soil 15% " + "filler " * 400) * 40
    kept = window_around(provision, "deep_soil_min")
    assert kept is not None
    assert len(kept) <= MAX_CANDIDATE_CHARS + len(
        "\n\n[... omitted: no mention of this control ...]\n\n") * 10


def test_window_marks_what_it_dropped():
    """An elision must be visible. A reader cannot judge text that silently
    pretends to be continuous."""
    far = "x" * (WIDE_WINDOW_CHARS + 5000)
    provision = ("deep soil minimum 15% of site area." + far +
                 "deep soil planting of 20% in the rear.")
    kept = window_around(provision, "deep_soil_min")
    assert kept is not None
    assert "omitted" in kept


def test_window_refuses_when_the_number_is_nowhere_near_the_keyword():
    """Not a keep-anyway and not a silent drop: None, which the caller counts."""
    provision = ("deep soil planting is encouraged. " + "x" * 40000 +
                 " a setback of 6m applies.")
    assert window_around(provision, "deep_soil_min") is None


def test_window_applies_the_full_predicate_not_merely_a_number():
    """The second real failure: a max_height window that kept "50%" and lost the
    metres. Testing only for a number let it through; the post-condition caught
    it downstream. The window must apply exactly the test that selected it."""
    provision = ("The maximum building height is 8.5m in this zone. " +
                 "x" * 40000 +
                 " The maximum height of any sign is 50% of the facade.")
    kept = window_around(provision, "max_height")
    assert kept is None or wanted(kept, "max_height")


# --------------------------------------------------------------------------
# the post-condition
# --------------------------------------------------------------------------

def test_post_condition_detects_a_candidate_that_lost_its_keyword():
    """Force the guard to fail. A guard never shown to fire is not a guard."""
    found = [
        {"council": "parramatta", "chapter": "c", "page": 1,
         "text": "A minimum deep soil zone of 15% of the site area."},
        {"council": "parramatta", "chapter": "c", "page": 2,
         "text": "Background narrative about the locality with 15% in it."},
    ]
    broken = broken_candidates(found, "deep_soil_min")
    assert len(broken) == 1
    assert broken[0]["page"] == 2


def test_post_condition_is_silent_on_clean_candidates():
    found = [{"council": "parramatta", "chapter": "c", "page": 1,
              "text": "A minimum deep soil zone of 15% of the site area."}]
    assert broken_candidates(found, "deep_soil_min") == []


# --------------------------------------------------------------------------
# the standing decision about which topics are worth mining
# --------------------------------------------------------------------------

@pytest.mark.parametrize("topic", ["heritage", "building_form", "site_analysis"])
def test_the_numeric_poor_topics_stay_excluded(topic):
    """A measured decision, kept in code so it cannot be quietly undone.

    Measured across all 12,124 live provisions: heritage 14%, building_form 12%,
    site_analysis 12% carry any measurable value, against 49% for setbacks and
    48% for height. heritage is simultaneously the LARGEST topic in the corpus,
    so mining it is the worst yield-per-effort trade available.

    If a future run wants one of these, it should delete this test deliberately
    and say why -- not discover the exclusion after spending the run.
    """
    assert topic in NUMERIC_POOR_TOPICS
    assert topic in EXCLUDED_TOPICS


def test_precinct_is_excluded_for_scope_not_for_yield():
    """The distinction is load-bearing.

    Precinct clauses are number-rich and their numbers are right. They are
    excluded because a precinct control served LGA-wide overrides the council's
    real general answer -- measured on two hornsby Pound Road rows that had to be
    re-scoped by hand. Collapsing this into "numeric-poor" would lose the reason
    and invite someone to re-include them on yield grounds.
    """
    assert "precinct" in SCOPE_RISK_TOPICS
    assert "precinct" not in NUMERIC_POOR_TOPICS
    assert "precinct" in EXCLUDED_TOPICS
