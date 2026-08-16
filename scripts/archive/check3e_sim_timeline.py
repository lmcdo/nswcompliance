"""Compute Marrickville similarity timeline from already-cached tiles."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))

import numpy as np
from geotessera import GeoTessera

gt = GeoTessera()
LAT, LON = -33.9139, 151.1554

embs = {}
for year in range(2017, 2026):
    try:
        e = gt.sample_embeddings_at_points([(LON, LAT)], year=year)
        if not np.isnan(e).any():
            embs[year] = e[0]
    except Exception:
        pass

print("Year-on-year cosine similarity (Marrickville):")
print(f"  {'Year':>9}  {'Sim':>8}  Level")
years = sorted(embs.keys())
for i in range(1, len(years)):
    p, c = years[i-1], years[i]
    ep, ec = embs[p], embs[c]
    sim = float(np.dot(ep, ec) / (np.linalg.norm(ep) * np.linalg.norm(ec)))
    level = "stable" if sim >= 0.95 else "minor" if sim >= 0.85 else "moderate" if sim >= 0.70 else "MAJOR"
    print(f"  {p}->{c}  {sim:.4f}  {level}")

sys.stdout.flush()
