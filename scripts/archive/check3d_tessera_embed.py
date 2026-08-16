"""
Fetch Tessera embeddings for a single point (Marrickville) across all years.
First run downloads tiles — may take 1-2 min. Subsequent runs use cache.
"""
import sys, time
import numpy as np
from geotessera import GeoTessera

gt = GeoTessera()
LAT, LON = -33.9139, 151.1554  # Marrickville

print("Fetching embeddings 2017-2024 (2025 may be missing)...")
embeddings = {}
for year in range(2017, 2026):
    t0 = time.time()
    try:
        emb = gt.sample_embeddings_at_points([(LON, LAT)], year=year)
        elapsed = time.time() - t0
        if np.isnan(emb).any():
            print(f"  {year}: NaN (tile not available)  [{elapsed:.1f}s]")
        else:
            embeddings[year] = emb[0]
            print(f"  {year}: shape={emb.shape} mean={emb[0].mean():.4f} norm={np.linalg.norm(emb[0]):.4f}  [{elapsed:.1f}s]")
    except Exception as e:
        print(f"  {year}: ERROR {e}")
    sys.stdout.flush()

# Year-on-year cosine similarity
print("\nYear-on-year cosine similarity:")
years = sorted(embeddings.keys())
for i in range(1, len(years)):
    p, c = years[i-1], years[i]
    ep, ec = embeddings[p], embeddings[c]
    sim = float(np.dot(ep, ec) / (np.linalg.norm(ep) * np.linalg.norm(ec)))
    level = "stable" if sim >= 0.95 else "minor" if sim >= 0.85 else "moderate" if sim >= 0.70 else "MAJOR"
    print(f"  {p}→{c}: {sim:.4f}  [{level}]")

sys.stdout.flush()
