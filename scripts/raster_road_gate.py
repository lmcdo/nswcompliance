"""Road mask and the road-share gate for the raster figure fitter (scripts/fit_cb_raster_centres.py).

prior-art-checked: split out of fit_cb_raster_centres.py, not new logic. The fitter imports OpenCV and PyMuPDF; the CI
test job installs neither on purpose (requirements-test.txt), so the gate lives here in numpy only and its test can run.

The fitter scores a fit by how many NSW road centreline points land on the figure's road pixels. That score only means
something when roads are a minority of the image: on a white-background figure with hairline roads (Warringah G3
Belrose) the mask covered 88% and a wrong fit scored 1.0. Accepted figures measured 18-34% (2026-10-20), so a fit is
refused above ROAD_SHARE_MAX.
"""
from __future__ import annotations

import numpy as np

ROAD_SHARE_MAX = 0.60


def road_mask(img: np.ndarray, band: list | None = None) -> np.ndarray:
    """Map road pixels (white; or grey in [lo, hi] when a centre sets road_band), widened 2 px so a centreline inside a
    carriageway counts. The 5x5 widening is the same as cv2.dilate with a 5x5 kernel of ones (outside the image counts
    as not-road)."""
    m = (img >= 249) if band is None else ((img >= band[0]) & (img <= band[1]))
    m = m.astype(np.uint8)
    p = np.pad(m, 2)
    h, w = m.shape
    out = np.zeros_like(m)
    for dy in range(5):
        for dx in range(5):
            out = np.maximum(out, p[dy:dy + h, dx:dx + w])
    return out


def road_share(img: np.ndarray, band: list | None = None) -> float:
    """Share of the figure's pixels the road mask (as scored) covers."""
    return float(road_mask(img, band).mean())
