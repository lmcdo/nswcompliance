import sys
from geotessera import GeoTessera
import numpy as np

gt=GeoTessera()
years=sorted(gt.registry.get_available_years())
counts=gt.registry.get_tile_counts_by_year()
print(f"Available years: {years}")
for yr in years:
    print(f"  {yr}: {counts.get(yr,'?')} tiles")
sys.stdout.flush()

# AU spot check — small embedding fetch
print("Fetching 2023 embedding at Marrickville...")
emb=gt.sample_embeddings_at_points([(151.1554,-33.9139)],year=2023)
print(f"Shape: {emb.shape}  NaN: {np.isnan(emb).any()}  mean: {emb.mean():.4f}")
print("Fetching 2017 embedding...")
emb17=gt.sample_embeddings_at_points([(151.1554,-33.9139)],year=2017)
print(f"Shape: {emb17.shape}  NaN: {np.isnan(emb17).any()}  mean: {emb17.mean():.4f}")
sim=float(np.dot(emb[0],emb17[0])/(np.linalg.norm(emb[0])*np.linalg.norm(emb17[0])))
print(f"Cosine similarity 2017 vs 2023: {sim:.4f}")
sys.stdout.flush()
