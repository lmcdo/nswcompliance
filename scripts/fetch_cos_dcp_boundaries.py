#!/usr/bin/env python3
"""
City of Sydney DCP 2012 — Fetch precinct/locality boundary GeoJSON
===================================================================
Downloads three layers from the CoS public ArcGIS FeatureServer:
  - Layer 11: Locality areas   (111 features)
  - Layer 15: Specific areas   (12 features)
  - Layer 16: Specific sites   (48 features)

Outputs three GeoJSON files ready for QGIS or DB import.

Usage:
    python3 scripts/fetch_cos_dcp_boundaries.py
    python3 scripts/fetch_cos_dcp_boundaries.py --out-dir data/boundaries/city-of-sydney
"""

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = (
    "https://services1.arcgis.com/cNVyNtjGVZybOQWZ/arcgis/rest/services"
    "/Sydney_Development_Control_Plan_2012/FeatureServer"
)

LAYERS = [
    {"id": 11, "name": "locality_areas",  "label": "Locality Areas"},
    {"id": 15, "name": "specific_areas",  "label": "Specific Areas"},
    {"id": 16, "name": "specific_sites",  "label": "Specific Sites"},
]

PAGE_SIZE = 100  # ArcGIS default max per request


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_all_features(layer_id: int, label: str) -> list[dict]:
    """Paginate through all features, returning a flat list of GeoJSON features."""
    features = []
    offset = 0

    while True:
        params = urllib.parse.urlencode({
            "where":         "1=1",
            "outFields":     "*",
            "outSR":         "4326",   # WGS84
            "f":             "geojson",
            "resultOffset":  offset,
            "resultRecordCount": PAGE_SIZE,
        })
        url = f"{BASE_URL}/{layer_id}/query?{params}"

        try:
            data = fetch_json(url)
        except urllib.error.URLError as e:
            print(f"  [ERROR] {e}", file=sys.stderr)
            break

        page_features = data.get("features", [])
        features.extend(page_features)
        print(f"  {label}: fetched {len(features)} / ... (page offset={offset})")

        # ArcGIS signals last page by returning fewer than PAGE_SIZE
        if len(page_features) < PAGE_SIZE:
            break

        offset += PAGE_SIZE
        time.sleep(0.3)  # be polite

    return features


def build_geojson(features: list[dict]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": features,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch City of Sydney DCP boundary GeoJSON")
    parser.add_argument(
        "--out-dir",
        default="data/boundaries/city-of-sydney",
        help="Output directory (default: data/boundaries/city-of-sydney)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for layer in LAYERS:
        layer_id = layer["id"]
        name     = layer["name"]
        label    = layer["label"]

        print(f"\n[Layer {layer_id}] {label}")
        features = fetch_all_features(layer_id, label)

        if not features:
            print(f"  [WARN] No features returned — skipping")
            continue

        geojson = build_geojson(features)
        out_path = out_dir / f"cos_dcp_{name}.geojson"
        out_path.write_text(json.dumps(geojson, indent=2))
        print(f"  Saved {len(features)} features -> {out_path}")

        # Print field names from first feature so you know what's available
        if features:
            props = list(features[0].get("properties", {}).keys())
            print(f"  Fields: {props}")

    print("\nDone.")


if __name__ == "__main__":
    main()
