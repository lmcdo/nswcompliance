"""Tests for the structure-detection recall measurement.

These test the MATCHING, which is the part that can silently produce a
flattering number. The database join is not tested here; it is exercised when
the script runs against real labels.

The failure this guards against is specific: if matching were many-to-one, a
single detection covering a whole backyard would "find" every structure on it
and recall would read 100% while the detector had located nothing in
particular. test_one_large_prediction_does_not_match_everything is the test
that would go red if someone relaxed that.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "recall_mod",
    Path(__file__).parent.parent / "scripts" / "measure_structure_detection_recall.py",
)
recall = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(recall)


def box(x0, y0, x1, y1):
    return {"bbox_pixel": [x0, y0, x1, y1]}


# --- IoU ------------------------------------------------------------------

def test_identical_boxes_are_fully_overlapping():
    assert recall.iou([0, 0, 10, 10], [0, 0, 10, 10]) == pytest.approx(1.0)


def test_disjoint_boxes_do_not_overlap():
    assert recall.iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0


def test_touching_edges_do_not_count_as_overlap():
    # Sharing a border is not sharing area. Without this, two adjacent sheds
    # would each "match" the other.
    assert recall.iou([0, 0, 10, 10], [10, 0, 20, 10]) == 0.0


def test_partial_overlap_is_intersection_over_union():
    # 50 overlap, union 150 -> 1/3
    assert recall.iou([0, 0, 10, 10], [5, 0, 15, 10]) == pytest.approx(1 / 3)


def test_boxes_drawn_backwards_are_normalised():
    # A human dragging right-to-left produces x1 < x0. Without normalisation
    # the width goes negative and every such label silently scores zero.
    assert recall.iou([10, 10, 0, 0], [0, 0, 10, 10]) == pytest.approx(1.0)


def test_zero_area_box_cannot_match():
    assert recall.iou([5, 5, 5, 5], [0, 0, 10, 10]) == 0.0


# --- matching -------------------------------------------------------------

def test_perfect_agreement():
    truth = [box(0, 0, 10, 10), box(20, 20, 30, 30)]
    pred = [box(0, 0, 10, 10), box(20, 20, 30, 30)]
    assert recall.match_boxes(truth, pred) == (2, 0, 0)


def test_a_missed_structure_is_counted_as_missed():
    truth = [box(0, 0, 10, 10), box(20, 20, 30, 30)]
    pred = [box(0, 0, 10, 10)]
    matched, missed, spurious = recall.match_boxes(truth, pred)
    assert (matched, missed, spurious) == (1, 1, 0)


def test_a_hallucinated_structure_is_counted_as_spurious():
    truth = [box(0, 0, 10, 10)]
    pred = [box(0, 0, 10, 10), box(50, 50, 60, 60)]
    assert recall.match_boxes(truth, pred) == (1, 0, 1)


def test_empty_lot_agreed_by_both_is_all_zeroes():
    # "Nothing here" agreed on both sides must not invent a match.
    assert recall.match_boxes([], []) == (0, 0, 0)


def test_detector_finds_nothing_on_a_lot_with_structures():
    truth = [box(0, 0, 10, 10), box(20, 20, 30, 30)]
    assert recall.match_boxes(truth, []) == (0, 2, 0)


def test_a_sprawling_prediction_scores_nothing_when_it_matches_nothing_well():
    """A box covering the whole yard overlaps each structure only slightly.

    NOTE what this does and does not prove. Both IoUs here are ~0.11, under the
    0.30 mark, so nothing is matched and the ONE-TO-ONE rule is never reached.
    This test covers the threshold, not the one-to-one guard — see
    test_one_prediction_cannot_claim_two_structures_it_genuinely_covers for
    that. Recorded explicitly because an earlier version of this file claimed
    this test guarded one-to-one matching, and a planted many-to-one defect
    left the whole suite green.
    """
    truth = [box(0, 0, 10, 10), box(20, 20, 30, 30)]
    one_big = [box(0, 0, 30, 30)]
    matched, missed, spurious = recall.match_boxes(truth, one_big)
    assert (matched, missed, spurious) == (0, 2, 1)


def test_one_prediction_cannot_claim_two_structures_it_genuinely_covers():
    """The load-bearing test for one-to-one matching.

    Two adjacent structures, and one prediction spanning both. The overlap with
    EACH is 0.5 — comfortably over the 0.30 mark — so both pairs are candidates
    and the one-to-one rule is what decides the outcome. A correct matcher
    credits the prediction with finding one structure and records the other as
    missed.

    If this reports matched=2, matching has become many-to-one: one detection
    would be credited with finding every structure it happens to span, and
    every recall figure produced afterwards is inflated. Verified to fail by
    planting exactly that defect (removing the `pi in used_p` guard).
    """
    truth = [box(0, 0, 10, 10), box(10, 0, 20, 10)]
    pred = [box(0, 0, 20, 10)]

    # Both candidate pairs clear the threshold — this is what makes the test
    # exercise the guard rather than the threshold.
    assert recall.iou(truth[0]["bbox_pixel"], pred[0]["bbox_pixel"]) >= recall.IOU_MATCH
    assert recall.iou(truth[1]["bbox_pixel"], pred[0]["bbox_pixel"]) >= recall.IOU_MATCH

    matched, missed, spurious = recall.match_boxes(truth, pred)
    assert matched == 1, "one prediction must claim at most one structure"
    assert missed == 1
    assert spurious == 0


def test_two_predictions_cannot_both_claim_one_structure():
    """The mirror case: precision must not be inflated either.

    Two overlapping detections of the same shed are one find and one false
    positive, not two finds.
    """
    truth = [box(0, 0, 10, 10)]
    pred = [box(0, 0, 10, 10), box(1, 1, 11, 11)]
    matched, missed, spurious = recall.match_boxes(truth, pred)
    assert (matched, missed, spurious) == (1, 0, 1)


def test_greedy_matching_prefers_the_better_overlap():
    # The prediction sits mostly over the second truth box; it should claim
    # that one, leaving the first missed, not the other way round.
    truth = [box(0, 0, 10, 10), box(9, 0, 19, 10)]
    pred = [box(9, 0, 19, 10)]
    matched, missed, spurious = recall.match_boxes(truth, pred)
    assert (matched, missed, spurious) == (1, 1, 0)


def test_below_threshold_overlap_is_not_a_match():
    # 10% overlap is under the committed 0.30 mark.
    truth = [box(0, 0, 10, 10)]
    pred = [box(9, 9, 19, 19)]
    assert recall.match_boxes(truth, pred) == (0, 1, 1)


# --- the committed thresholds --------------------------------------------

def test_thresholds_are_the_committed_values():
    """If these change, the change must be deliberate and explained.

    The point of a pre-committed mark is that it cannot be quietly moved to
    fit a disappointing result. This test makes moving it a visible act.
    """
    assert recall.RECALL_FLOOR == 0.70
    assert recall.PRECISION_FLOOR == 0.60
    assert recall.IOU_MATCH == 0.30
    assert recall.MIN_LABELLED == 40
