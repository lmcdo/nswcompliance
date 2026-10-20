"""The raster fitter refuses a figure whose road mask is not a minority (on-road scores would be noise)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import raster_road_gate as f  # noqa: E402  (numpy only: CI's test job has no OpenCV)


def _map(road_frac_rows: int) -> np.ndarray:
    img = np.full((200, 200), 128, np.uint8)  # grey land
    img[:road_frac_rows, :] = 255             # white road rows
    return img


def test_typical_map_share_below_gate():
    assert f.road_share(_map(40)) < f.ROAD_SHARE_MAX


def test_white_background_map_share_above_gate():
    img = np.full((200, 200), 255, np.uint8)
    img[::50, :] = 0  # hairline dark lines on white
    assert f.road_share(img) > f.ROAD_SHARE_MAX


def test_band_mask_counts_only_the_band():
    img = np.full((200, 200), 230, np.uint8)
    assert f.road_share(img, [222, 236]) > f.ROAD_SHARE_MAX
    assert f.road_share(img) == 0.0  # same image, white mask: no road pixels


def test_threshold_clears_measured_accepted_maximum():
    assert 0.344 < f.ROAD_SHARE_MAX < 0.884
