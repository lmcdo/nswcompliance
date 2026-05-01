"""
Railway startup script: download Hawkesbury FRMSP 2025 AEP rasters from R2.

Called by Dockerfile.python before uvicorn starts.
Downloads to /tmp/hawkesbury_rasters/ (writable on Railway ephemeral disk).
Skips files that are already present and correct size (fast restarts).

Exits 0 always — missing rasters degrade gracefully in flood_truth.py
(returns None for Hawkesbury raster fields rather than crashing).
"""
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

R2_ACCOUNT_ID        = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID     = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME       = os.environ.get("R2_BUCKET_NAME", "")
R2_PREFIX            = "hawkesbury-rasters"

DEST_DIR = Path(os.environ.get("HAWKESBURY_RASTER_DIR", "/tmp/hawkesbury_rasters"))

AEP_FILES = [
    "2AEP_Floodstudy_Stretched.tif",
    "5AEP_Floodstudy_Stretched.tif",
    "10AEP_Floodstudy_Stretched.tif",
    "20AEP_Floodstudy_Stretched.tif",
    "50AEP_Floodstudy_Stretched.tif",
    "100AEP_Floodstudy_Stretched.tif",
    "200AEP_Floodstudy_Stretched.tif",
    "500AEP_Floodstudy_Stretched.tif",
    "PMF_Floodstudy_Stretched.tif",
]


def main():
    if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME]):
        log.warning("[raster-dl] R2 env vars not set — skipping Hawkesbury raster download")
        return

    try:
        import boto3
    except ImportError:
        log.warning("[raster-dl] boto3 not installed — skipping")
        return

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    for filename in AEP_FILES:
        dest = DEST_DIR / filename
        r2_key = f"{R2_PREFIX}/{filename}"

        # Check remote size first
        try:
            head = s3.head_object(Bucket=R2_BUCKET_NAME, Key=r2_key)
            remote_size = head["ContentLength"]
        except Exception as e:
            log.warning(f"[raster-dl] {filename}: head_object failed — {e}")
            continue

        # Skip if local file already correct
        if dest.exists() and dest.stat().st_size == remote_size:
            log.info(f"[raster-dl] {filename} already present ({remote_size / 1_048_576:.1f} MB) — skip")
            continue

        size_mb = remote_size / 1_048_576
        log.info(f"[raster-dl] downloading {filename} ({size_mb:.1f} MB)...")
        try:
            s3.download_file(R2_BUCKET_NAME, r2_key, str(dest))
            log.info(f"[raster-dl] {filename} done")
        except Exception as e:
            log.warning(f"[raster-dl] {filename}: download failed — {e}")
            if dest.exists():
                dest.unlink()  # remove partial file

    present = sum(1 for f in AEP_FILES if (DEST_DIR / f).exists())
    log.info(f"[raster-dl] {present}/{len(AEP_FILES)} raster files ready in {DEST_DIR}")


if __name__ == "__main__":
    main()
