"""
Railway startup script: download Redbank Creek Flood Study 2025 rasters from R2.

prior-art-checked: reuse not viable because the prior art is
scripts/download_hawkesbury_rasters.py (read in full, deliberately mirrored) —
it hardcodes a flat 9-file Hawkesbury list, its own R2 prefix and env var, and
is COPY'd standalone into Dockerfile.python where no shared module exists;
Redbank needs subdirectories (design/historical) and a 24-file set.
DownloadPdfButton.tsx (guard's suggestion) is a frontend PDF button, unrelated.

Called by Dockerfile.python before uvicorn starts (same pattern as
scripts/download_hawkesbury_rasters.py). Downloads to /tmp/redbank_rasters/design
and /historical subdirectories, matching the FLOOD_STUDIES redbank template
paths in services/flood_truth.py. Skips files that are already present and
correct size (fast restarts).

Exits 0 always — missing rasters degrade gracefully in flood_truth.py
(the redbank study is skipped rather than crashing).

Grids are DEFLATE-compressed GeoTIFFs (224 MB total for 24 files),
losslessly recompressed from the NSW Flood Data Portal BIL originals.
"""
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

R2_ACCOUNT_ID        = os.environ.get("R2_ACCOUNT_ID") or ""
R2_ACCESS_KEY_ID     = os.environ.get("R2_ACCESS_KEY_ID") or ""
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY") or ""
R2_BUCKET_NAME       = os.environ.get("R2_BUCKET_NAME") or ""
R2_PREFIX            = "redbank-rasters"

DEST_DIR = Path(os.environ.get("REDBANK_RASTER_DIR", "/tmp/redbank_rasters"))

_DESIGN_EVENTS = [
    "20pcAEP", "10pcAEP", "5pcAEP", "2pcAEP", "1pcAEP",
    "1in200AEP", "1in500AEP", "1in1000AEP", "1in2000AEP", "1in5000AEP", "PMF",
]

# Relative paths mirror the FLOOD_STUDIES redbank design/historical templates.
RASTER_FILES = [
    f"design/RedbankCk_DES_{event}_{t}_Max_ProcessedOutput.tif"
    for event in _DESIGN_EVENTS
    for t in ("d", "h")
] + [
    f"historical/RedBank_DES_Hist_March2022_{t}_Max_ProcessedOutput.tif"
    for t in ("d", "h")
]


def main():
    if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME]):
        log.warning("[redbank-dl] R2 env vars not set — skipping Redbank raster download")
        return

    try:
        import boto3
    except ImportError:
        log.warning("[redbank-dl] boto3 not installed — skipping")
        return

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    for rel_path in RASTER_FILES:
        dest = DEST_DIR / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        r2_key = f"{R2_PREFIX}/{rel_path}"

        # Check remote size first
        try:
            head = s3.head_object(Bucket=R2_BUCKET_NAME, Key=r2_key)
            remote_size = head["ContentLength"]
        except Exception as e:
            log.warning(f"[redbank-dl] {rel_path}: head_object failed — {e}")
            continue

        # Skip if local file already correct
        if dest.exists() and dest.stat().st_size == remote_size:
            log.info(f"[redbank-dl] {rel_path} already present ({remote_size / 1_048_576:.1f} MB) — skip")
            continue

        size_mb = remote_size / 1_048_576
        log.info(f"[redbank-dl] downloading {rel_path} ({size_mb:.1f} MB)...")
        try:
            s3.download_file(R2_BUCKET_NAME, r2_key, str(dest))
            log.info(f"[redbank-dl] {rel_path} done")
        except Exception as e:
            log.warning(f"[redbank-dl] {rel_path}: download failed — {e}")
            if dest.exists():
                dest.unlink()  # remove partial file

    present = sum(1 for f in RASTER_FILES if (DEST_DIR / f).exists())
    log.info(f"[redbank-dl] {present}/{len(RASTER_FILES)} raster files ready in {DEST_DIR}")


if __name__ == "__main__":
    main()
