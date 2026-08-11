"""
Modal GPU inference service — LangSAM text-prompt detection.

Deployed separately to Modal (not Railway):
    modal deploy services/modal_inference.py

Two web endpoints:
    POST /detect-panels    — Solar Yield: detect "solar panel"
    POST /detect-structures — Granny Flat: detect "building" / "shed" / "garage"

Railway calls these via HTTP using MODAL_PANELS_URL / MODAL_STRUCTURES_URL env vars.
No Modal SDK needed on Railway — plain requests.post().

Pricing: ~$0.03–0.05 per inference on T4 GPU (Modal free tier = $30/mo credit).

Model loading: LangSAM is loaded ONCE at container startup via @modal.enter().
Warm runs (within scaledown_window) skip model load entirely — just inference.
"""

import base64
import io
import logging
from typing import Optional

import modal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Modal app + image
# ---------------------------------------------------------------------------

app = modal.App("plotdetect-inference")

inference_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install(["libgl1", "libglib2.0-0"])  # OpenCV deps
    .pip_install(["numpy==1.26.4"])           # pin numpy<2 before segment-geospatial can upgrade it
    .pip_install([
        "rasterio==1.3.11",                   # pin to avoid backtracking to source-only versions
        "groundingdino-py",                   # pre-install so samgeo doesn't do it at runtime
        "transformers>=4.26.0,<5.0",          # groundingdino incompatible with transformers 5.x
        "segment-geospatial",
        "torch==2.4.0",                       # 2.4+ supports numpy 2.x
        "torchvision==0.19.0",
        "Pillow==10.4.0",
        "opencv-python-headless>=4.10.0",     # >=4.10 compiled against numpy 2.x
        "fastapi[standard]",
    ])
)

# ---------------------------------------------------------------------------
# Shared helpers (run inside Modal container)
# ---------------------------------------------------------------------------

def _decode_image(image_b64: str):
    """Decode base64 PNG/JPEG to PIL Image."""
    from PIL import Image
    data = base64.b64decode(image_b64)
    return Image.open(io.BytesIO(data))


def _save_temp(img) -> str:
    """Save PIL Image to a temp file, return path. LangSAM needs a file path."""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img.save(tmp.name)
    return tmp.name


def _compute_iou(a, b) -> float:
    import numpy as np
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter / union) if union > 0 else 0.0


def _masks_to_structures(masks_with_prompts: list, w: int, h: int, iou_threshold: float = 0.5, min_area_px: int = 150) -> list[dict]:
    """IoU dedup + area filter + convert to serialisable dicts."""
    import numpy as np

    masks_with_prompts.sort(key=lambda x: x[0].sum(), reverse=True)

    kept = []
    for mask_np, prompt in masks_with_prompts:
        if not any(_compute_iou(mask_np, k[0]) > iou_threshold for k in kept):
            kept.append((mask_np, prompt))

    structures = []
    for mask_np, prompt in kept:
        area_px = int(mask_np.sum())
        if area_px < min_area_px:
            continue
        ys, xs = np.where(mask_np)
        structures.append({
            "area_px": area_px,
            "bbox_pixel": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "matched_prompt": prompt,
        })

    return structures


# ---------------------------------------------------------------------------
# Endpoint 1: Solar panel detection
# Model loaded ONCE at container startup — warm runs skip this entirely
# ---------------------------------------------------------------------------

@app.cls(gpu="T4", image=inference_image, timeout=120, scaledown_window=1800)
class PanelDetector:

    @modal.enter()
    def load_model(self):
        from samgeo.text_sam import LangSAM
        self.model = LangSAM()

    @modal.fastapi_endpoint(method="POST")
    def detect(self, data: dict) -> dict:
        """
        Detect solar panels in an aerial image.

        Request body:
            image_b64: str          — base64 PNG aerial tile
            box_threshold: float    — LangSAM box confidence (default 0.20)
            text_threshold: float   — LangSAM text confidence (default 0.18)

        Response:
            panel_count: int
            masks: list[dict]       — [{area_px, bbox_pixel}]
        """
        import numpy as np

        image_b64 = data.get("image_b64", "")
        box_thresh = float(data.get("box_threshold", 0.25))
        text_thresh = float(data.get("text_threshold", 0.22))

        img = _decode_image(image_b64)
        tile_path = _save_temp(img)

        masks, _, _, _ = self.model.predict(
            image=tile_path,
            text_prompt="solar panel . photovoltaic panel . pv array . rooftop solar",
            box_threshold=box_thresh,
            text_threshold=text_thresh,
            return_results=True,
        )

        # Debug: return tile thumbnail so caller can verify correct image was analysed
        thumb = img.copy()
        thumb.thumbnail((256, 256))
        buf = io.BytesIO()
        thumb.save(buf, format="PNG")
        thumb_b64 = base64.b64encode(buf.getvalue()).decode()

        if masks is None or len(masks) == 0:
            return {"panel_count": 0, "masks": [], "debug_thumb": thumb_b64}

        # At zoom 20, pixel size ≈ 0.098m.
        # Real solar panel: 1.7–2.0 m² ≈ 175–210 px
        # Whole-roof false positive: typically >5,000 px (>48 m²) — reject these
        # Residential max system: ~40 m² ≈ 4,200 px total
        PIXEL_SIZE_M = 0.098
        MAX_MASK_M2 = 40.0  # single mask larger than this is almost certainly a roof, not panels
        MAX_MASK_PX = int(MAX_MASK_M2 / (PIXEL_SIZE_M ** 2))

        results = []
        for mask in masks:
            mask_np = np.array(mask, dtype=bool)
            area_px = int(mask_np.sum())
            if area_px < 50:           # noise filter (~0.5 m²)
                continue
            if area_px > MAX_MASK_PX:  # whole-roof false positive filter
                continue
            ys, xs = np.where(mask_np)
            results.append({
                "area_px": area_px,
                "bbox_pixel": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            })

        return {"panel_count": len(results), "masks": results}


# ---------------------------------------------------------------------------
# Endpoint 2: Structure detection (Granny Flat)
# Model loaded ONCE at container startup — warm runs skip this entirely
# ---------------------------------------------------------------------------

DETECTION_PROMPTS = [
    ("building", 0.25, 0.20),
    ("shed",     0.20, 0.18),
    ("garage",   0.20, 0.18),
]

@app.cls(gpu="T4", image=inference_image, timeout=120, scaledown_window=1800)
class StructureDetector:

    @modal.enter()
    def load_model(self):
        from samgeo.text_sam import LangSAM
        self.model = LangSAM()

    @modal.fastapi_endpoint(method="POST")
    def detect(self, data: dict) -> dict:
        """
        Detect buildings/sheds/garages in an aerial image.

        Request body:
            image_b64: str           — base64 PNG aerial tile
            iou_threshold: float     — dedup threshold (default 0.5)
            min_area_px: int         — minimum structure size in pixels (default 150)

        Response:
            structure_count: int
            structures: list[dict]   — [{area_px, bbox_pixel, matched_prompt}]
        """
        import numpy as np

        image_b64 = data.get("image_b64", "")
        iou_threshold = float(data.get("iou_threshold", 0.5))
        min_area_px = int(data.get("min_area_px", 150))

        img = _decode_image(image_b64)
        w, h = img.size
        tile_path = _save_temp(img)

        all_masks = []
        for prompt, box_thresh, text_thresh in DETECTION_PROMPTS:
            try:
                masks, _, _, _ = self.model.predict(
                    image=tile_path,
                    text_prompt=prompt,
                    box_threshold=box_thresh,
                    text_threshold=text_thresh,
                    return_results=True,
                )
                if masks is None:
                    continue
                for m in masks:
                    all_masks.append((np.array(m, dtype=bool), prompt))
            except Exception as e:
                logger.warning(f"LangSAM prompt '{prompt}' failed: {e}")

        if not all_masks:
            return {"structure_count": 0, "structures": []}

        structures = _masks_to_structures(all_masks, w, h, iou_threshold, min_area_px)
        return {"structure_count": len(structures), "structures": structures}
