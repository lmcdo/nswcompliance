"""Tests for the terrain hillshade renderer (services/terrain_analysis._render_hillshade_png).

The renderer's contract is failure-safety: it turns the in-memory DEM into a
presentation PNG and must NEVER raise — any problem returns None so the terrain
metrics are unaffected. The None-safety tests always run; the real-render tests
are skipped where numpy/matplotlib/PIL are mocked/absent (the suite stubs native
deps when they aren't installed).
"""
import pytest

from services.terrain_analysis import _render_hillshade_png


def _real_viz() -> bool:
    """True only when numpy, matplotlib and PIL are genuinely importable.

    conftest_mocks installs a MagicMock for numpy when the real package is
    missing; a mock array's type name is not 'ndarray', which distinguishes it.
    """
    try:
        import numpy as np
        if type(np.zeros((2, 2))).__name__ != "ndarray":
            return False
        from matplotlib.colors import LightSource  # noqa: F401
        from PIL import Image  # noqa: F401
        return True
    except Exception:
        return False


# --- Always-on: the None-safety contract (no real deps required) -------------

def test_none_input_returns_none_no_raise():
    assert _render_hillshade_png(None) is None


def test_non_array_input_returns_none_no_raise():
    assert _render_hillshade_png("not an array") is None
    assert _render_hillshade_png(123) is None
    assert _render_hillshade_png({"a": 1}) is None


# --- Real-render behaviour (skipped when deps are mocked/absent) --------------

@pytest.mark.skipif(not _real_viz(), reason="needs real numpy + matplotlib + PIL")
def test_real_dem_returns_png_data_uri():
    import numpy as np
    dem = np.tile(np.linspace(10.0, 40.0, 48, dtype=np.float64), (48, 1))
    uri = _render_hillshade_png(dem)
    assert uri is not None
    assert uri.startswith("data:image/png;base64,")
    assert len(uri) < 400_000  # stays small enough to inline in the brief


@pytest.mark.skipif(not _real_viz(), reason="needs real numpy + matplotlib + PIL")
def test_all_nodata_returns_none():
    import numpy as np
    dem = np.full((48, 48), np.nan, dtype=np.float64)
    assert _render_hillshade_png(dem) is None


@pytest.mark.skipif(not _real_viz(), reason="needs real numpy + matplotlib + PIL")
def test_partial_nodata_still_renders():
    import numpy as np
    dem = np.tile(np.linspace(10.0, 40.0, 48, dtype=np.float64), (48, 1))
    dem[:8, :8] = np.nan  # a corner of nodata
    uri = _render_hillshade_png(dem)
    assert uri is not None
    assert uri.startswith("data:image/png;base64,")


@pytest.mark.skipif(not _real_viz(), reason="needs real numpy + matplotlib + PIL")
def test_flat_dem_does_not_crash():
    import numpy as np
    dem = np.full((48, 48), 12.5, dtype=np.float64)  # vmax == vmin
    uri = _render_hillshade_png(dem)
    assert uri is None or uri.startswith("data:image/png;base64,")


@pytest.mark.skipif(not _real_viz(), reason="needs real numpy + matplotlib + PIL")
def test_one_dimensional_input_returns_none():
    import numpy as np
    assert _render_hillshade_png(np.arange(50, dtype=np.float64)) is None
