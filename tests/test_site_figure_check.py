"""Site outline vs the chapter's own site map: the shape score and its guards (DQ-143)."""
import sys
from pathlib import Path

from shapely import affinity
from shapely.geometry import Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import site_figure_check as f  # noqa: E402

L_SHAPE = Polygon([(0, 0), (40, 0), (40, 10), (10, 10), (10, 30), (0, 30)])


def test_same_shape_scaled_rotated_and_moved_scores_one():
    moved = affinity.translate(affinity.rotate(affinity.scale(L_SHAPE, 3.7, 3.7), 33, origin="centroid"), 500, -90)
    iou, rot = f.shape_iou(L_SHAPE, moved)
    assert iou >= 0.99


def test_a_different_shape_scores_below_the_pass_mark():
    iou, _ = f.shape_iou(L_SHAPE, box(0, 0, 10, 40))
    assert iou < f.MATCH


def test_half_the_site_scores_below_the_pass_mark():
    # Milton St: either parcel alone scored ~0.6 against the map; both together 0.945.
    iou, _ = f.shape_iou(box(0, 0, 20, 10), box(0, 0, 10, 10))
    assert iou < f.MATCH


def test_unreadable_map_is_recorded_not_passed():
    m = f.map_check(None, b"", {"unreadable": "no site map"}, ["1//DP1"])
    assert m["status"] == "unreadable" and m["why"] == "no site map"


def test_no_candidate_lots_fails():
    class Page:  # never reached: no lots means fail before reading the map
        pass
    m = f.map_check(None, b"", None, [])
    assert m["status"] == "unreadable"


def test_search_rules_require_a_clear_winner():
    assert f.SEARCH_WIN >= 0.95 and f.SEARCH_MARGIN >= 0.1
    assert f.MIN_PAGE_SHARE > 0  # a legend swatch can never be the outline
