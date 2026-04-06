"""
Spike: samgeo text-prompt solar panel detection on NSW SIX Maps 10cm imagery.

RUN THIS MANUALLY before building the solar_yield pipeline.
Install: pip install samgeo  (MIT licence — SAM is Apache 2.0)

Pass criteria:
  - Panels detected correctly on ≥ 3/5 known addresses
  - < 2 false positives per roof (Colorbond light steel confusion)
  Fail → fall back to Brisbane AU weights fine-tune (see plan 1B)

Usage:
    python -m services.spike_solar_samgeo

Output saved to: /tmp/solar_spike/<address_slug>/
  - tile.png        — raw SIX Maps tile
  - detections.png  — tile with detected polygons overlaid
  - results.json    — polygon list + pass/fail verdict
"""

import json
import os
import sys
import textwrap
from pathlib import Path

# Add project root to path when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.nsw_imagery import fetch_tile_to_file

# ---------------------------------------------------------------------------
# Test addresses — mix of known has-panels / no-panels
# Verify on SIX Maps viewer (maps.six.nsw.gov.au) or Google Maps satellite
# All Leichhardt or nearby is fine — roof type diversity matters more than geography
# Format: (label, address_string, expected_has_panels)
# ---------------------------------------------------------------------------
TEST_ADDRESSES = [
    ("has_panels_1",  "50 Junior St Leichhardt NSW 2040",       True),
    ("has_panels_2",  "15 O'Connor St Haberfield NSW 2045",     True),
    ("has_panels_3",  "23 St Davids Road Haberfield NSW 2045",  True),
    ("no_panels_1",   "21 St Davids Road Haberfield NSW 2045",  False),
    ("no_panels_2",   "22 O'Connor St Haberfield NSW 2045",     False),
]

NSW_API_BASE = "https://api.apps1.nsw.gov.au/planning"
NSW_HEADERS = {
    "Origin": "https://www.planningportal.nsw.gov.au",
    "Referer": "https://www.planningportal.nsw.gov.au/",
}

OUT_DIR = Path("/tmp/solar_spike")


def _mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Convert EPSG:3857 Web Mercator to WGS84 lat/lng."""
    import math
    R = 20037508.342789244
    lng = x * 180.0 / R
    lat = math.degrees(2.0 * math.atan(math.exp(y * math.pi / R)) - math.pi / 2.0)
    return lat, lng


def _geocode(address: str) -> tuple[float, float]:
    """
    Geocode via NSW Planning Portal API. Returns (lat, lng) WGS84.
    Step 1: address → propId
    Step 2: propId → lot geometry (EPSG:3857) → centroid → WGS84
    """
    import requests as _req

    # Step 1: address lookup
    resp = _req.get(
        f"{NSW_API_BASE}/viewersf/V1/ePlanningApi/address",
        params={"a": address, "noOfRecords": 1},
        headers=NSW_HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise ValueError(f"No property found for: {address!r}")
    prop_id = results[0]["propId"]

    # Step 2: lot geometry → centroid (coordinates are EPSG:3857)
    lot_resp = _req.get(
        f"{NSW_API_BASE}/viewersf/V1/ePlanningApi/lot",
        params={"propId": prop_id},
        headers=NSW_HEADERS,
        timeout=10,
    )
    lot_resp.raise_for_status()
    lots = lot_resp.json()
    if not lots:
        raise ValueError(f"No lot geometry for propId={prop_id}")

    rings = lots[0]["geometry"]["rings"][0]  # outer ring, [x_mercator, y_mercator]
    cx = sum(pt[0] for pt in rings) / len(rings)
    cy = sum(pt[1] for pt in rings) / len(rings)
    return _mercator_to_wgs84(cx, cy)


def run_spike():
    try:
        import samgeo
        from samgeo.text_sam import LangSAM
    except ImportError:
        print("ERROR: samgeo not installed. Run: pip install samgeo")
        sys.exit(1)

    try:
        from PIL import Image, ImageDraw
        import numpy as np
    except ImportError:
        print("ERROR: Pillow / numpy missing")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading LangSAM model (first run downloads ~1.5GB)...")
    model = LangSAM()

    results = []
    correct = 0
    false_positives_total = 0

    for label, address, expected_panels in TEST_ADDRESSES:
        if not address.strip():
            print(f"\n--- {label} SKIPPED (no address set) ---")
            continue

        print(f"\n--- {label}: {address!r} expected_panels={expected_panels} ---")
        addr_dir = OUT_DIR / label
        addr_dir.mkdir(exist_ok=True)

        # 1. Geocode
        try:
            lat, lng = _geocode(address)
            print(f"  Geocoded: ({lat:.6f}, {lng:.6f})")
        except Exception as e:
            print(f"  Geocode failed: {e}")
            results.append({"label": label, "address": address, "error": str(e)})
            continue

        # 2. Fetch SIX Maps tile
        tile_path, licence, bbox = fetch_tile_to_file(lat, lng, output_path=str(addr_dir / "tile.png"), grid=3)
        print(f"  Tile saved: {tile_path}  bbox={bbox}")

        # 2. Run LangSAM with text prompt
        try:
            masks, boxes, phrases, logits = model.predict(
                image=tile_path,
                text_prompt="solar panel",
                box_threshold=0.3,
                text_threshold=0.25,
                return_results=True,
            )
            n_detected = len(masks) if masks is not None else 0
            print(f"  Detected {n_detected} mask(s) for 'solar panel'")
        except Exception as e:
            print(f"  LangSAM error: {e}")
            results.append({"label": label, "error": str(e)})
            continue

        # 3. Overlay detections on tile image for visual inspection
        tile_img = Image.open(tile_path).convert("RGBA")
        overlay = Image.new("RGBA", tile_img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        polygon_areas = []
        if masks is not None:
            for i, mask in enumerate(masks):
                # Convert binary mask to contour bounding box for overlay
                mask_np = np.array(mask, dtype=np.uint8)
                ys, xs = np.where(mask_np > 0)
                if len(xs) == 0:
                    continue
                x0, x1 = int(xs.min()), int(xs.max())
                y0, y1 = int(ys.min()), int(ys.max())
                area_px = int(mask_np.sum())
                polygon_areas.append(area_px)
                draw.rectangle([x0, y0, x1, y1], outline=(0, 255, 0, 200), width=3)
                draw.text((x0, max(0, y0 - 12)), f"panel {i+1} ({area_px}px)", fill=(0, 255, 0, 255))

        composite = Image.alpha_composite(tile_img, overlay).convert("RGB")
        composite.save(addr_dir / "detections.png")
        print(f"  Detection overlay saved: {addr_dir / 'detections.png'}")

        # 4. Verdict
        detected = n_detected > 0
        is_correct = detected == expected_panels
        if is_correct:
            correct += 1

        # Colorbond false-positive heuristic: if no panels expected but detected, count as FP
        fp_count = n_detected if not expected_panels else 0
        false_positives_total += fp_count

        result = {
            "label": label,
            "address": address,
            "lat": lat,
            "lng": lng,
            "expected_panels": expected_panels,
            "detected_panels": detected,
            "n_masks": n_detected,
            "polygon_area_px": polygon_areas,
            "is_correct": is_correct,
            "false_positives": fp_count,
            "bbox": bbox,
            "licence": licence,
        }
        results.append(result)
        print(f"  Correct: {is_correct}  FP: {fp_count}")

    # 5. Summary verdict
    total = len([r for r in results if "error" not in r])
    avg_fp_per_roof = false_positives_total / max(total, 1)
    passed = correct >= 3 and avg_fp_per_roof < 2

    summary = {
        "total_tested": total,
        "correct": correct,
        "false_positives_total": false_positives_total,
        "avg_fp_per_evaluated_roof": round(avg_fp_per_roof, 2),
        "verdict": "PASS" if passed else "FAIL",
        "next_step": (
            "Use samgeo as primary path in solar_yield.py"
            if passed
            else "Fall back to Brisbane AU weights fine-tune (see plan Phase 1B)"
        ),
        "results": results,
    }

    summary_path = OUT_DIR / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print(f"VERDICT: {summary['verdict']}")
    print(f"Correct: {correct}/{total}   Avg FP/roof: {avg_fp_per_roof:.2f}")
    print(f"Next step: {summary['next_step']}")
    print(f"Full results: {summary_path}")
    print(f"Check detection overlays in: {OUT_DIR}/*/detections.png")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    print(textwrap.dedent("""
    Solar Panel Detection Spike -- samgeo + LangSAM
    Addresses loaded. Starting geocode + inference...
    """))
    run_spike()
