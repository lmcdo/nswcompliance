"""A battleaxe detector must reject shapes that merely LOOK narrow at one end.

Reported 2026-08-26 from a live report: a TRIANGULAR lot was labelled a
battleaxe with a "2.65m x 26.33m access way", and the page then told the owner
their lot failed SEPP Housing 2021 because that access way was under the 3m
minimum. The access way does not exist. The eligibility failure was invented.

Cause: the detector recognised a handle by ONE property - being narrow relative
to the widest slice - and a triangle's pointed end has that property. Every
other test passed too: narrow, consecutive, a minority of the lot's length.

The fix is a taper check. A real access handle is roughly parallel-sided; a
wedge narrows continuously. These tests exist so the detector is always run
against shapes CONFUSABLE with the thing it detects, not only against the thing
itself and obvious non-matches.
"""
import pytest

from services.lot_dimensions import _detect_battleaxe


def densify(vertices, per_edge=40):
    """Walk each edge so the slicer sees a cadastre-like vertex count."""
    out = []
    for i, (x1, y1) in enumerate(vertices):
        x2, y2 = vertices[(i + 1) % len(vertices)]
        for k in range(per_edge):
            t = k / per_edge
            out.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
    return out


TRIANGLE = [(0, 0), (60, 0), (0, 60)]
WEDGE = [(0, 0), (50, 0), (35, 60), (15, 60)]
REAL_BATTLEAXE = [(18, 0), (22, 0), (22, 30), (40, 30), (40, 70), (0, 70), (0, 30), (18, 30)]
IRREGULAR_HANDLE = [(18, 0), (23, 0), (22.5, 30), (40, 30), (40, 70), (0, 70), (0, 30), (18, 30)]


@pytest.mark.parametrize("name,shape", [("triangle", TRIANGLE), ("wedge", WEDGE)])
def test_a_taper_is_not_an_access_handle(name, shape):
    """The exact false positive that reached a customer's report."""
    assert _detect_battleaxe(densify(shape)) is None, (
        f"{name} reported as a battleaxe; its narrow END is a taper, not a handle"
    )


@pytest.mark.parametrize(
    "name,shape,expected_width",
    [("parallel 4m handle", REAL_BATTLEAXE, 4.0),
     ("handle tapering 5.0->4.5", IRREGULAR_HANDLE, 4.5)],
)
def test_real_battleaxes_still_detected(name, shape, expected_width):
    """The taper check must not throw out the shape it exists to protect."""
    result = _detect_battleaxe(densify(shape))
    assert result is not None, f"{name} no longer detected — the fix over-reached"
    assert result["access_way_width_m"] == pytest.approx(expected_width, abs=0.6)


def test_the_probe_can_tell_the_two_apart():
    """Guards the guard.

    If densify() or the detector broke such that EVERYTHING returned None, the
    rejection tests above would pass while proving nothing. Requiring a positive
    and a negative in the same test pins both directions.
    """
    assert _detect_battleaxe(densify(REAL_BATTLEAXE)) is not None
    assert _detect_battleaxe(densify(TRIANGLE)) is None
