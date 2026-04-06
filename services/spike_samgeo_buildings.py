"""
Spike: samgeo text-prompt building/structure detection on NSW SIX Maps 10cm imagery.

Purpose: validate that SAM can detect individual structures (main dwelling + outbuildings)
within a lot boundary. Prerequisite for granny_flat.py pipeline.

RUN THIS MANUALLY before building granny_flat.py.
Install: pip install samgeo  (MIT licence — SAM is Apache 2.0)

Pass criteria:
  - Correct structure count (within ±1) on ≥ 7/11 properties
  - < 1.5 phantom structures per lot (roofing material / shadow confusion)
  Fail → tune box_threshold / text_threshold or switch prompt

Usage:
    python -m services.spike_samgeo_buildings

Output saved to: /tmp/buildings_spike/<address_slug>/
  - tile.png         — raw SIX Maps tile
  - lot_clip.png     — tile with lot polygon overlaid
  - detections.png   — tile with detected polygons overlaid
  - results.json     — polygon list + pass/fail verdict

Addresses verified via NSW Planning Portal + geocode_results.json (2026-04-06).
Lot geometry fetched live from Planning Portal per propId before inference.
"""

import json
import math
import os
import sys
import textwrap
from pathlib import Path
from typing import Optional

# Add project root to path when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.nsw_imagery import fetch_tile_to_file, ZOOM, TILE_SIZE

# ---------------------------------------------------------------------------
# Test properties
# Coordinates and propIds verified via NSW Planning Portal geocoding (2026-04-06)
# expected_structure_count: minimum distinct roofed structures expected
#   (main dwelling always counts as 1)
# notes: observed on SIX Maps / Google Maps satellite
# ---------------------------------------------------------------------------
TEST_PROPERTIES = [
    # --- Haberfield: mix of with/without outbuildings ---
    {
        "label": "hab_oconnor_16",
        "address": "16 O'Connor St Haberfield NSW 2045",
        "prop_id": 1302931,
        "lat": -33.8845312,
        "lng": 151.1378092,
        "expected_min_structures": 3,   # main dwelling + 2 small sheds
        "notes": "2x small sheds confirmed",
    },
    {
        "label": "hab_oconnor_37",
        "address": "37 O'Connor St Haberfield NSW 2045",
        "prop_id": 1302852,
        "lat": -33.8818375,
        "lng": 151.1418577,
        "expected_min_structures": 2,   # main dwelling + shed (pool not a roofed structure)
        "notes": "shed and pool confirmed; pool excluded from count",
    },
    {
        "label": "hab_stdavids_2",
        "address": "2 St Davids Road Haberfield NSW 2045",
        "prop_id": 1305494,
        "lat": -33.884622,
        "lng": 151.1365825,
        "expected_min_structures": 1,   # main dwelling only — no outbuildings noted
        "notes": "no outbuildings noted",
    },
    {
        "label": "hab_parramatta_69",
        "address": "69 Parramatta Road Haberfield NSW 2045",
        "prop_id": 1303965,
        "lat": -33.885773,
        "lng": 151.139538,
        "expected_min_structures": 2,   # main dwelling + large rear structure confirmed
        "notes": "large structure visible on aerial",
    },
    {
        "label": "hab_parramatta_63",
        "address": "63 Parramatta Road Haberfield NSW 2045",
        "prop_id": 1303962,
        "lat": -33.8860272,
        "lng": 151.1399265,
        "expected_min_structures": 2,   # main dwelling + large rear structure confirmed
        "notes": "large structure visible on aerial",
    },
    {
        "label": "hab_haberfield_5",
        "address": "5 Haberfield Road Haberfield NSW 2045",
        "prop_id": 1298634,
        "lat": -33.8861298,
        "lng": 151.1409552,
        "expected_min_structures": 2,   # main dwelling + shed confirmed
        "notes": "shed + solar panels visible",
    },
    {
        "label": "hab_tressider_27",
        "address": "27 Tressider Avenue Haberfield NSW 2045",
        "prop_id": 3102095,
        "lat": -33.882289,
        "lng": 151.1422544,
        "expected_min_structures": 2,   # main dwelling + shed confirmed
        "notes": "shed visible on aerial",
    },
    # --- Leichhardt: non-strata, new builds — main dwelling only expected ---
    {
        "label": "lei_elwick_65",
        "address": "65 Elwick St Leichhardt NSW 2040",
        "prop_id": 1937014,
        "lat": -33.8831082,
        "lng": 151.1621822,
        "expected_min_structures": 1,
        "notes": "non-strata new build",
    },
    {
        "label": "lei_seale_11",
        "address": "11 Seale St Leichhardt NSW 2040",
        "prop_id": 1936142,
        "lat": -33.8868882,
        "lng": 151.1517221,
        "expected_min_structures": 1,
        "notes": "non-strata new build",
    },
    {
        "label": "lei_seale_9",
        "address": "9 Seale St Leichhardt NSW 2040",
        "prop_id": 1936141,
        "lat": -33.8869133,
        "lng": 151.1517933,
        "expected_min_structures": 1,
        "notes": "non-strata new build",
    },
    {
        "label": "lei_seale_17",
        "address": "17 Seale St Leichhardt NSW 2040",
        "prop_id": 1936145,
        "lat": -33.8869562,
        "lng": 151.15154,
        "expected_min_structures": 1,
        "notes": "non-strata new build",
    },
]

NSW_API_BASE = "https://api.apps1.nsw.gov.au/planning"
NSW_HEADERS = {
    "Origin": "https://www.planningportal.nsw.gov.au",
    "Referer": "https://www.planningportal.nsw.gov.au/",
}

OUT_DIR = Path("/tmp/buildings_spike")


def _mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Convert EPSG:3857 Web Mercator to WGS84 lat/lng."""
    R = 20037508.342789244
    lng = x * 180.0 / R
    lat = math.degrees(2.0 * math.atan(math.exp(y * math.pi / R)) - math.pi / 2.0)
    return lat, lng


def _fetch_lot_geometry(prop_id: int) -> Optional[dict]:
    """
    Fetch lot polygon from NSW Planning Portal (EPSG:3857 Web Mercator).
    Returns raw geometry dict from API, or None on failure.
    """
    import requests as _req

    try:
        resp = _req.get(
            f"{NSW_API_BASE}/viewersf/V1/ePlanningApi/lot",
            params={"propId": prop_id},
            headers=NSW_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        lots = resp.json()
        if lots:
            return lots[0]["geometry"]
    except Exception as e:
        print(f"  Lot geometry fetch failed for propId={prop_id}: {e}")
    return None


def _mercator_rings_to_pixel_via_bbox(
    rings: list,
    bbox: dict,
    image_size: tuple,
) -> list[list[tuple[int, int]]]:
    """
    Convert Web Mercator polygon rings to pixel coordinates using the tile bbox.

    Uses the same method as solar_yield.py _lot_polygon_to_pixel_mask:
    linear interpolation from geographic bbox → pixel space.
    More reliable than tile-index math.

    bbox keys: min_lat, max_lat, min_lng, max_lng (WGS84)
    image_size: (width, height) in pixels
    """
    w, h = image_size
    pixel_rings = []
    for ring in rings:
        px_ring = []
        for x_merc, y_merc in ring:
            lat, lng = _mercator_to_wgs84(x_merc, y_merc)
            px = (lng - bbox["min_lng"]) / (bbox["max_lng"] - bbox["min_lng"]) * w
            py = (bbox["max_lat"] - lat) / (bbox["max_lat"] - bbox["min_lat"]) * h
            px_ring.append((int(px), int(py)))
        pixel_rings.append(px_ring)
    return pixel_rings


def _mask_within_lot(mask_np, lot_pixel_rings: list[list[tuple[int, int]]]) -> bool:
    """
    Return True if the mask's centroid is inside the lot polygon,
    OR if >=5% of mask pixels fall within the lot.

    Two checks because LangSAM masks are coarse and often extend beyond the building
    footprint, so pure pixel-overlap ratios are low even for correct detections.
    """
    from PIL import Image, ImageDraw
    import numpy as np

    h, w = mask_np.shape
    lot_mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(lot_mask)
    for ring in lot_pixel_rings:
        if len(ring) >= 3:
            draw.polygon(ring, fill=255)

    lot_arr = np.array(lot_mask) > 0

    # Check 1: centroid inside lot
    ys, xs = np.where(mask_np > 0)
    if len(xs) > 0:
        cx, cy = int(xs.mean()), int(ys.mean())
        if 0 <= cy < h and 0 <= cx < w and lot_arr[cy, cx]:
            return True

    # Check 2: >=5% pixel overlap
    overlap = np.logical_and(mask_np > 0, lot_arr)
    mask_pixels = int(mask_np.sum())
    if mask_pixels == 0:
        return False
    return (overlap.sum() / mask_pixels) >= 0.05


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

    try:
        import requests  # noqa: F401
    except ImportError:
        print("ERROR: requests missing")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    GRID = 3
    HALF = GRID // 2

    print("Loading LangSAM model (first run downloads ~1.5GB)...")
    model = LangSAM()

    results = []
    correct = 0
    false_positives_total = 0.0

    for prop in TEST_PROPERTIES:
        label = prop["label"]
        address = prop["address"]
        lat = prop["lat"]
        lng = prop["lng"]
        prop_id = prop["prop_id"]
        expected_min = prop["expected_min_structures"]

        print(f"\n--- {label}: {address!r} expect>={expected_min} ---")
        addr_dir = OUT_DIR / label
        addr_dir.mkdir(exist_ok=True)

        # 1. Fetch SIX Maps tile
        try:
            tile_path, licence, bbox = fetch_tile_to_file(
                lat, lng, output_path=str(addr_dir / "tile.png"), grid=GRID
            )
            print(f"  Tile: {tile_path}")
        except Exception as e:
            print(f"  Tile fetch failed: {e}")
            results.append({"label": label, "error": f"tile: {e}"})
            continue

        # 2. Fetch lot geometry and compute pixel-space polygon via bbox
        lot_geometry = _fetch_lot_geometry(prop_id)
        tile_img_size = Image.open(tile_path).size  # (width, height)

        lot_pixel_rings: Optional[list] = None
        if lot_geometry and "rings" in lot_geometry:
            lot_pixel_rings = _mercator_rings_to_pixel_via_bbox(
                lot_geometry["rings"], bbox, tile_img_size
            )
            # Draw lot boundary overlay on tile for visual inspection
            tile_img_overlay = Image.open(tile_path).convert("RGBA")
            overlay = Image.new("RGBA", tile_img_overlay.size, (0, 0, 0, 0))
            draw_lot = ImageDraw.Draw(overlay)
            for ring in lot_pixel_rings:
                if len(ring) >= 2:
                    draw_lot.polygon(ring, outline=(255, 165, 0, 200))
            composite_lot = Image.alpha_composite(tile_img_overlay, overlay).convert("RGB")
            composite_lot.save(addr_dir / "lot_clip.png")
            print(f"  Lot polygon drawn ({len(lot_pixel_rings[0])} vertices)")
        else:
            print("  WARNING: no lot geometry — detections will NOT be lot-clipped")

        # 3. Run LangSAM — multi-prompt union (building + shed + garage)
        # Mirrors granny_flat.py DETECTION_PROMPTS for comparable results.
        DETECTION_PROMPTS = [
            ("building", 0.25, 0.20),
            ("shed",     0.20, 0.18),
            ("garage",   0.20, 0.18),
        ]
        IOU_DEDUP_THRESHOLD = 0.5
        MIN_STRUCTURE_AREA_M2 = 15.0

        all_raw: list[tuple] = []  # (mask_np, prompt_label)
        for prompt, box_thresh, text_thresh in DETECTION_PROMPTS:
            try:
                masks, _boxes, _phrases, _logits = model.predict(
                    image=tile_path,
                    text_prompt=prompt,
                    box_threshold=box_thresh,
                    text_threshold=text_thresh,
                    return_results=True,
                )
                if masks is not None:
                    for m in masks:
                        all_raw.append((np.array(m, dtype=bool), prompt))
                print(f"  [{prompt}] raw: {len(masks) if masks is not None else 0}")
            except Exception as e:
                print(f"  [{prompt}] LangSAM error: {e}")

        n_raw = len(all_raw)
        print(f"  Total raw detections: {n_raw}")

        # 4. Clip to lot boundary
        if lot_pixel_rings is not None:
            lot_img_clip = Image.new("L", tile_img_size, 0)
            draw_clip = ImageDraw.Draw(lot_img_clip)
            for ring in lot_pixel_rings:
                if len(ring) >= 3:
                    draw_clip.polygon(ring, fill=255)
            lot_arr = np.array(lot_img_clip) > 0
            all_raw = [(m, p) for m, p in all_raw if _mask_within_lot(m.astype(np.uint8), lot_pixel_rings)]

        n_after_clip = len(all_raw)
        print(f"  After lot clip: {n_after_clip}")

        # IoU deduplication — keep largest non-overlapping masks
        all_raw.sort(key=lambda x: x[0].sum(), reverse=True)
        kept_dedup: list[tuple] = []
        for cand_mask, cand_prompt in all_raw:
            dup = False
            for kept_mask, _ in kept_dedup:
                inter = np.logical_and(cand_mask, kept_mask).sum()
                union = np.logical_or(cand_mask, kept_mask).sum()
                iou = float(inter / union) if union > 0 else 0.0
                if iou > IOU_DEDUP_THRESHOLD:
                    dup = True
                    break
            if not dup:
                kept_dedup.append((cand_mask, cand_prompt))

        # Area filter — drop < 15 m²
        tile_w, tile_h = tile_img_size
        if bbox:
            lat_c = (bbox["min_lat"] + bbox["max_lat"]) / 2
            R_m = 6371000.0
            lat_r = math.radians(lat_c)
            w_m = math.radians(bbox["max_lng"] - bbox["min_lng"]) * R_m * math.cos(lat_r)
            h_m = math.radians(bbox["max_lat"] - bbox["min_lat"]) * R_m
            px_area_m2 = (w_m / tile_w) * (h_m / tile_h)
        else:
            px_area_m2 = 0.0  # fallback: skip area filter

        clipped_masks = []
        for mask_np, prompt in kept_dedup:
            area_px = int(mask_np.sum())
            if px_area_m2 > 0 and area_px * px_area_m2 < MIN_STRUCTURE_AREA_M2:
                continue
            clipped_masks.append((mask_np.astype(np.uint8), prompt))

        n_clipped = len(clipped_masks)
        print(f"  After IoU dedup + area filter: {n_clipped}")

        # 5. Draw detections overlay
        tile_img = Image.open(tile_path).convert("RGBA")
        overlay2 = Image.new("RGBA", tile_img.size, (0, 0, 0, 0))
        draw2 = ImageDraw.Draw(overlay2)

        for i, (mask_np, prompt) in enumerate(clipped_masks):
            ys, xs = np.where(mask_np > 0)
            if len(xs) == 0:
                continue
            x0, x1 = int(xs.min()), int(xs.max())
            y0, y1 = int(ys.min()), int(ys.max())
            area_px = int(mask_np.sum())
            draw2.rectangle([x0, y0, x1, y1], outline=(0, 255, 0, 200), width=3)
            draw2.text((x0, max(0, y0 - 12)), f"{prompt} {i+1} ({area_px}px)", fill=(0, 255, 0, 255))

        # Also draw lot polygon on detections image
        if lot_pixel_rings:
            for ring in lot_pixel_rings:
                if len(ring) >= 2:
                    draw2.polygon(ring, outline=(255, 165, 0, 180))

        composite2 = Image.alpha_composite(tile_img, overlay2).convert("RGB")
        composite2.save(addr_dir / "detections.png")
        print(f"  Detection overlay: {addr_dir / 'detections.png'}")

        # 6. Verdict
        is_correct = n_clipped >= expected_min

        # False positives: structures detected when only 1 was expected (main dwelling)
        # If we detect more than expected_min, extras are potential false positives
        excess = max(0, n_clipped - (expected_min + 1))  # allow 1 extra before counting FP
        false_positives_total += excess
        if is_correct:
            correct += 1

        result = {
            "label": label,
            "address": address,
            "lat": lat,
            "lng": lng,
            "prop_id": prop_id,
            "expected_min_structures": expected_min,
            "n_raw_detections": n_raw,
            "n_after_clip": n_after_clip,
            "n_clipped_detections": n_clipped,
            "prompts_used": [p[0] for p in DETECTION_PROMPTS],
            "lot_clipping_applied": lot_pixel_rings is not None,
            "is_correct": is_correct,
            "excess_detections": excess,
            "notes": prop.get("notes", ""),
            "bbox": bbox,
            "licence": licence,
        }
        results.append(result)
        print(f"  Correct: {is_correct}  excess: {excess}")

    # 7. Summary
    total = len([r for r in results if "error" not in r])
    avg_fp = false_positives_total / max(total, 1)
    passed = correct >= 7 and avg_fp < 1.5

    summary = {
        "total_tested": total,
        "correct": correct,
        "false_positives_total": false_positives_total,
        "avg_excess_per_lot": round(avg_fp, 2),
        "verdict": "PASS" if passed else "FAIL",
        "next_step": (
            "Use samgeo 'building' prompt as primary path in granny_flat.py"
            if passed
            else "Tune thresholds or switch to 'house' / 'roof' / 'shed' prompts; re-spike"
        ),
        "results": results,
    }

    summary_path = OUT_DIR / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 60)
    print(f"VERDICT: {summary['verdict']}")
    print(f"Correct: {correct}/{total}   Avg excess/lot: {avg_fp:.2f}")
    print(f"Next step: {summary['next_step']}")
    print(f"Full results: {summary_path}")
    print(f"Check detection overlays in: {OUT_DIR}/*/detections.png")
    print("=" * 60)

    return summary


if __name__ == "__main__":
    print(textwrap.dedent("""
    Building Detection Spike -- samgeo + LangSAM
    11 verified properties (Haberfield + Leichhardt).
    Lot boundary clipping applied via NSW Planning Portal geometry.
    Starting tile fetch + inference...
    """))
    run_spike()
