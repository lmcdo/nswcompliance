"""Tests for the structure-detection recall measurement.

These test the MATCHING, which is the part that can silently produce a
flattering number. The database join is not tested here; it is exercised when
the script runs against real labels.

The failure this guards against is specific: if matching were many-to-one, a
single detection covering a whole backyard would "find" every structure on it
and recall would read 100% while the detector had located nothing in
particular. test_a_sprawling_prediction_can_claim_only_one_structure is the
test that goes red if someone relaxes that.

Matching is POINT-IN-BOX: the human clicks inside a structure, and a match is
that click landing inside a detector box. The iou() helper is retained and
still tested because it remains useful for diagnostics, but it no longer
decides a match — see the module docstring of the script for why the shapes
did not survive this imagery.
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


def point(x, y):
    return {"point_pixel": [x, y]}


def test_a_sprawling_prediction_can_claim_only_one_structure():
    """One detection covering the whole yard contains BOTH clicks.

    Under point-in-box this is the case the one-to-one rule exists for, and it
    is now reachable — under the old IoU matching the overlaps were ~0.11 and
    the rule was never exercised at all, which is how a planted many-to-one
    defect once left the whole suite green.

    Correct outcome: the sprawling box is credited with finding ONE structure,
    the other is recorded as missed, and there is nothing spurious because the
    single prediction was used.
    """
    truth = [point(5, 5), point(25, 25)]
    one_big = [box(0, 0, 30, 30)]
    matched, missed, spurious = recall.match_boxes(truth, one_big)
    assert matched == 1, "one box must not claim two structures"
    assert missed == 1
    assert spurious == 0


def test_a_click_outside_every_box_is_a_miss():
    truth = [point(500, 500)]
    pred = [box(0, 0, 30, 30)]
    assert recall.match_boxes(truth, pred) == (0, 1, 1)


def test_a_click_on_the_boundary_counts_as_inside():
    """Inclusive edges. A click landing exactly on the box edge is agreement,
    not a miss — the alternative punishes sub-pixel placement."""
    assert recall.point_in_box((10.0, 5.0), [0, 0, 10, 10]) is True


def test_a_legacy_box_label_converts_to_its_centroid():
    """Labels recorded before the switch must not be discarded.

    Their centroid is the same statement — 'a structure is here' — so they
    convert losslessly and keep contributing to the sample.
    """
    assert recall.label_point({"bbox_pixel": [0, 0, 10, 20]}) == (5.0, 10.0)
    assert recall.label_point({"point_pixel": [3, 4]}) == (3.0, 4.0)
    assert recall.label_point({"structure_type": "shed"}) is None


def test_a_tight_box_wins_over_a_sprawling_one_for_the_same_click():
    """Two detections contain the same click; the tighter one should claim it.

    Otherwise a lot-sized box could take the credit ahead of the detection
    that actually isolated the structure, and the sprawling box would look
    useful while the precise one was counted spurious.
    """
    truth = [point(5, 5)]
    pred = [box(0, 0, 100, 100), box(0, 0, 10, 10)]
    matched, missed, spurious = recall.match_boxes(truth, pred)
    assert (matched, missed, spurious) == (1, 0, 1)


def test_one_prediction_cannot_claim_two_structures_it_genuinely_covers():
    """The load-bearing test for one-to-one matching.

    Two adjacent structures, and one prediction spanning both. Each truth box
    converts to its centroid, and BOTH centroids fall inside the single
    prediction, so both pairs are candidates and the one-to-one rule is what
    decides the outcome. A correct matcher credits the prediction with finding
    one structure and records the other as missed.

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
    assert recall.MIN_LABELLED == 40


# --- malformed geometry ---------------------------------------------------
#
# The QA gate flagged two `float(v) for v in box` loops that assumed every
# coordinate was a number. A null in a bbox — from the labelling UI, from the
# detector, or from a hand-edited row — took the whole measurement down with a
# TypeError partway through. Coercing to 0.0 would have been worse: the box
# silently changes shape, points that were inside read as outside, and the miss
# count climbs with nothing to show anything went wrong.

def test_a_null_in_a_box_is_malformed_not_zero():
    assert recall.numeric4([10, None, 20, 30]) is None
    assert recall.numeric4([10, "20", 20, 30]) is None
    assert recall.numeric4(None) is None
    assert recall.numeric4([1, 2, 3]) is None
    assert recall.numeric4([0, 0, 10, 10]) == (0.0, 0.0, 10.0, 10.0)


def test_booleans_are_not_coordinates():
    """isinstance(True, int) is True in Python, so a bare numeric check lets
    `[True, 0, 10, 10]` through as (1.0, 0.0, 10.0, 10.0) — a real box built
    from junk."""
    assert recall.numeric4([True, 0, 10, 10]) is None


def test_a_malformed_truth_label_is_skipped_not_crashed():
    assert recall.label_point({"bbox_pixel": [10, None, 20, 30]}) is None


def test_a_malformed_prediction_counts_as_spurious_not_a_match():
    """Conservative direction on purpose.

    A prediction whose box is unusable cannot pair with anything, so it lands
    in spurious — counting against precision — rather than disappearing from
    both numerator and denominator, which would flatter the detector.
    """
    truth = [point(5, 5)]
    pred = [box(0, 0, 10, 10), {"bbox_pixel": [1, None, 9, 9]}]
    matched, missed, spurious = recall.match_boxes(truth, pred)
    assert (matched, missed, spurious) == (1, 0, 1)


def test_a_lot_of_only_malformed_predictions_finds_nothing():
    truth = [point(5, 5)]
    pred = [{"bbox_pixel": [None, None, None, None]}]
    assert recall.match_boxes(truth, pred) == (0, 1, 1)
