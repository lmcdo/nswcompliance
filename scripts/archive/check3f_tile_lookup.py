"""Diagnose why Leichhardt gets NaN from Tessera for 2017-2023."""
import pandas as pd, numpy as np

df = pd.read_parquet("C:/Users/lawre/AppData/Local/geotessera/registry.parquet")

# Check the actual tile coordinates geotessera would use for Leichhardt
# lat=-33.882, lon=151.165
# geotessera tiles at 0.1 degree; what tile centers are in registry near Leichhardt?

leich_lat, leich_lon = -33.882, 151.165
mark_lat, mark_lon = -33.9139, 151.1554

print("=== Registry tiles near Leichhardt (-33.882, 151.165) ===")
nearby = df[
    (abs(df['lat'] - leich_lat) < 0.15) &
    (abs(df['lon'] - leich_lon) < 0.15)
]
print(f"Tiles within 0.15 deg: {len(nearby)}")
by_year = nearby.groupby(['lat', 'lon', 'year']).size().reset_index(name='count')
pivot = by_year.pivot_table(index=['lat','lon'], columns='year', values='count', fill_value=0)
print(pivot.to_string())

print("\n=== Exact tile coordinates in registry near Leichhardt ===")
unique_coords = nearby[['lat', 'lon']].drop_duplicates().sort_values(['lat', 'lon'])
print(unique_coords.to_string())

print("\n=== Registry tiles near Marrickville (-33.9139, 151.1554) ===")
mark_nearby = df[
    (abs(df['lat'] - mark_lat) < 0.08) &
    (abs(df['lon'] - mark_lon) < 0.08)
]
mark_coords = mark_nearby[['lat', 'lon', 'year']].drop_duplicates()
mark_pivot = mark_coords.pivot_table(index=['lat','lon'], columns='year', values='year', aggfunc='count', fill_value=0)
print(mark_pivot.to_string())
