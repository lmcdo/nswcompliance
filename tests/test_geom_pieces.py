"""services/geom_pieces.py: loaders store broken or huge shapes as valid pieces
under the same keys the 2026-10-29 repair used, so a re-run never re-adds the original."""
import sys
from pathlib import Path

import pytest

shapely = pytest.importorskip("shapely")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from services import geom_pieces as gp  # noqa: E402
from shapely import wkt  # noqa: E402

BOWTIE = "POLYGON((0 0, 1 1, 1 0, 0 1, 0 0))"  # self-crossing: invalid
SQUARE = "POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))"


def row(oid, w):
    return ("K", "LGA", "flood", "1%AEP", None, None, oid, w)


def test_a_valid_small_shape_is_stored_unchanged():
    assert gp.explode_rows([row(7, SQUARE)], 6, 7) == [row(7, SQUARE)]


def test_a_broken_shape_becomes_valid_pieces_with_piece_keys():
    out = gp.explode_rows([row(7, BOWTIE)], 6, 7)
    assert out and all(wkt.loads(r[7]).is_valid for r in out)
    assert [r[6] for r in out] == [gp.PIECE_OID_BASE + 7 * 100000 + n for n in range(1, len(out) + 1)]


def test_a_huge_shape_is_split_to_capped_pieces_and_keeps_its_area():
    circle = shapely.Point(0, 0).buffer(1, quad_segs=40000)  # ~80k points
    out = gp.explode_rows([row(3, circle.wkt)], 6, 7)
    assert len(out) > 1
    assert max(len(shapely.get_coordinates(wkt.loads(r[7]))) for r in out) <= gp.MAX_POINTS
    assert abs(sum(wkt.loads(r[7]).area for r in out) - circle.area) / circle.area < 1e-9


def test_a_mid_size_valid_shape_is_not_split():
    circle = shapely.Point(0, 0).buffer(1, quad_segs=2000)  # ~4k points, under the split rule
    assert gp.explode_rows([row(3, circle.wkt)], 6, 7)[0][6] == 3


def test_a_row_without_a_key_is_left_alone():
    assert gp.explode_rows([row(None, BOWTIE)], 6, 7) == [row(None, BOWTIE)]


def test_the_split_is_the_same_every_run():
    a = gp.explode_rows([row(9, BOWTIE)], 6, 7)
    assert a == gp.explode_rows([row(9, BOWTIE)], 6, 7)
