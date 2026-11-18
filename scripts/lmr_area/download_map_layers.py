# prior-art-checked: four sweeps 2026-11-18. (1) DB: spatial_overlays already holds bushfire, heritage and coastal layers (loaded by scripts/ingest_spatial_overlays.py,
# which this does not replace); it holds NONE of the housing-reform maps below. (2) Frontend: no reader. (3) Python: services/lmr_area_inputs.LAYERS names these live
# layers and queries them per lot; scripts/lmr_area/*.py build walking files and test the check; nothing saves these maps. (4) Plans: ce-layers-own-copy-SCOPE-2026-11-18.md
# (owner approved step 1 on 2026-11-18).
"""Download the small state maps the area check asks for live, and save them with an as-at date so a later step can read our own copy first.

    python scripts/lmr_area/download_map_layers.py            # dry run: counts and sizes, writes nothing
    python scripts/lmr_area/download_map_layers.py --apply    # writes data/law/maps/<name>.geojson.gz and data/law/maps/manifest.json

Each file is the layer's features as GeoJSON in WGS84 (6 decimal places, about 0.1 m), gzipped (the repo refuses files over 2 MB; a bigger layer is split into numbered parts). The manifest records for each:
source URL, feature count, the date it was read, and the sha256 of the saved file. Nothing is written to the database. Bush fire, heritage items and the
coastal maps are NOT here: they live in the spatial_overlays table (refreshed by scripts/ingest_spatial_overlays.py).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Optional

import requests

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "data" / "law" / "maps"
REPO_FILE_LIMIT = 2 * 1024 * 1024
UA = {"User-Agent": "plotdetect-map-copy/1.0"}
_EPL = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning"
# name -> (layer url, what the area check uses it for)
LAYERS = {
    "tod_sites": (f"{_EPL}/Planning_Portal_SEPP/MapServer/752", "TOD Sites Map (s164(1)(c))"),
    "accelerated_tod": (f"{_EPL}/Planning_Portal_SEPP/MapServer/759", "Accelerated TOD Precinct map (s164(1)(l))"),
    "lmr_exclusion": (f"{_EPL}/Planning_Portal_SEPP/MapServer/776", "Low and Mid Rise Housing Exclusion Map (s164(1)(m))"),
    "hn_catchment": (f"{_EPL}/Planning_Portal_SEPP/MapServer/157", "Hawkesbury-Nepean catchment (s164(1)(f))"),
    "georges_catchment": (f"{_EPL}/Planning_Portal_SEPP/MapServer/147", "Georges River catchment (s164(1)(f1))"),
    "coastal_vuln": (f"{_EPL}/Planning_Portal_SEPP/MapServer/251", "Coastal vulnerability areas (s164(1)(b))"),
    "airport_noise": (f"{_EPL}/Planning_Portal_Protection/MapServer/235", "Airport noise contour bands (s164(1)(h))"),
    "heritage_shr": (f"{_EPL}/Planning_Portal_Principal_Planning/MapServer/221", "State Heritage Register (s164(1)(d))"),
}


def get(url: str, params: dict, tries: int = 4) -> Optional[dict]:
    """JSON from a state map service, patient (60 s, 4 tries): this runs once, not per user request. None after the last failure."""
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            r.raise_for_status()
            j = r.json()
            if isinstance(j, dict) and "error" not in j:
                return j
        except Exception as exc:  # noqa: BLE001
            print(f"    retry {i + 1}: {type(exc).__name__}", flush=True)
        time.sleep(3 * (i + 1))
    return None


def round_coords(x: Any) -> Any:
    if x is None or isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return round(float(x), 6)
    return [round_coords(v) for v in x] if isinstance(x, list) else x


def fetch_layer(url: str) -> Optional[dict]:
    """Every feature of one layer as a GeoJSON FeatureCollection, or None if any page could not be read (a partial copy is never saved)."""
    cnt = get(url + "/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})
    if cnt is None or not isinstance(cnt.get("count"), int):
        return None
    want = cnt["count"]
    feats: list[dict] = []
    offset = 0
    while offset < want:
        page = get(url + "/query", {"where": "1=1", "outFields": "*", "outSR": 4326, "f": "geojson", "resultOffset": offset,
                                    "resultRecordCount": 1000, "orderByFields": "OBJECTID"})
        got = (page or {}).get("features") if page else None
        if not got:
            return None
        feats += got
        offset += len(got)
        print(f"    {len(feats)}/{want}", flush=True)
    if len(feats) != want:
        return None
    ids = [(f.get("properties") or {}).get("OBJECTID", f.get("id")) for f in feats]
    if any(i is None for i in ids) or len(set(ids)) != len(ids):
        print("    FAILED: features missing an id or repeated (the service ignored the page offset?)", flush=True)
        return None
    for f in feats:
        g = f.get("geometry")
        if g and "coordinates" in g:
            g["coordinates"] = round_coords(g["coordinates"])
    return {"type": "FeatureCollection", "features": feats}


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    manifest: dict[str, Any] = {"read_on": date.today().isoformat(), "note": "Our copy of state map layers; read_on is the date they were downloaded.", "layers": {}}
    failed, too_big = [], []
    pending: list[tuple[str, bytes]] = []
    for name, (url, use) in LAYERS.items():
        print(f"{name}: {use}", flush=True)
        fc = fetch_layer(url)
        if fc is None:
            print("  FAILED: not saved (a partial copy is never written)")
            failed.append(name)
            continue
        feats, n_parts = fc["features"], 1
        while True:   # split into equal parts until every part is under the repo limit (the repo refuses files over 2 MB)
            size = -(-len(feats) // n_parts)
            chunks = [feats[k:k + size] for k in range(0, len(feats), size)] or [[]]
            gzs = [gzip.compress(json.dumps({"type": "FeatureCollection", "features": c}, separators=(",", ":"), ensure_ascii=False).encode("utf-8"), 9, mtime=0)
                   for c in chunks]   # mtime 0: the same data always gives the same bytes
            if all(len(g) < REPO_FILE_LIMIT for g in gzs) or n_parts >= 8 or len(feats) <= n_parts:
                break
            n_parts += 1
        if any(len(g) >= REPO_FILE_LIMIT for g in gzs):
            too_big.append(name)
            continue
        names = [f"{name}.geojson.gz"] if len(gzs) == 1 else [f"{name}.part{k + 1}of{len(gzs)}.geojson.gz" for k in range(len(gzs))]
        print(f"  {len(feats)} features, {sum(len(g) for g in gzs):,} bytes gzipped in {len(gzs)} file(s)")
        manifest["layers"][name] = {"source": url, "use": use, "features": len(feats), "files": [
            {"file": nm, "features": len(c), "bytes": len(g), "sha256": hashlib.sha256(g).hexdigest()} for nm, c, g in zip(names, chunks, gzs)]}
        pending += list(zip(names, gzs))   # written only after EVERY layer has been read and checked
    if apply and not failed and not too_big:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for nm, g in pending:
            (OUT_DIR / nm).write_bytes(g)
        (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {len(manifest['layers'])} files and manifest.json to {OUT_DIR}")
    elif not apply:
        print("DRY RUN: nothing written. Re-run with --apply.")
    if failed or too_big:
        print(f"NOT COMPLETE: failed={failed} over the 2 MB repo limit={too_big}; no manifest written")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
