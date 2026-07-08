"""
Railway startup script: download NARCliM 2.0 climate-projection NetCDFs from R2.

prior-art-checked: mirrors scripts/download_hawkesbury_rasters.py (same R2 client,
head-then-skip, exit-0-always contract) — the only differences are the R2 prefix,
the file list, and that the destination must match services/climate_risk_raster.py's
DATA_DIR (both read NARCLIM_DIR).

Called by Dockerfile.python before uvicorn starts. Downloads to the dir named by
NARCLIM_DIR (set to a writable path such as /tmp/narclim on Railway). Skips files
already present at the correct size (fast restarts).

Exits 0 always — missing rasters degrade gracefully: climate_risk_score /
query_narclim catch FileNotFoundError and drop the projection component rather
than crashing.
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
R2_PREFIX            = "narclim"

# Must match services/climate_risk_raster.py DATA_DIR (both read NARCLIM_DIR).
DEST_DIR = Path(os.environ.get("NARCLIM_DIR", "/tmp/narclim"))

# The 6 NARCliM 2.0 NetCDFs the climate service reads (extreme-heat, rainfall,
# temperature × ssp245/ssp370). Keep in sync with climate_risk_raster.NARCLIM_FILES.
NARCLIM_NC_FILES = [
    "TXge35_ssp245_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
    "TXge35_ssp370_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
    "prAdjust_ssp245_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
    "prAdjust_ssp370_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
    "tas_ssp245_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
    "tas_ssp370_ACCESS-ESM1-5_NARCliM2-0-WRF412R5_NARCliM2-0-SEAus-04i.nc",
]


def main() -> None:
    if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME]):
        log.warning("[narclim-dl] R2 env vars not set — skipping NARCliM raster download")
        return

    try:
        import boto3
    except ImportError:
        log.warning("[narclim-dl] boto3 not installed — skipping")
        return

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    for filename in NARCLIM_NC_FILES:
        dest = DEST_DIR / filename
        r2_key = f"{R2_PREFIX}/{filename}"

        try:
            head = s3.head_object(Bucket=R2_BUCKET_NAME, Key=r2_key)
            remote_size = head["ContentLength"]
        except Exception as e:
            log.warning(f"[narclim-dl] {filename}: head_object failed — {e}")
            continue

        if dest.exists() and dest.stat().st_size == remote_size:
            log.info(f"[narclim-dl] {filename} already present ({remote_size / 1_048_576:.1f} MB) — skip")
            continue

        size_mb = remote_size / 1_048_576
        log.info(f"[narclim-dl] downloading {filename} ({size_mb:.1f} MB)...")
        try:
            s3.download_file(R2_BUCKET_NAME, r2_key, str(dest))
            log.info(f"[narclim-dl] {filename} done")
        except Exception as e:
            log.warning(f"[narclim-dl] {filename}: download failed — {e}")
            if dest.exists():
                dest.unlink()  # remove partial file

    present = sum(1 for f in NARCLIM_NC_FILES if (DEST_DIR / f).exists())
    log.info(f"[narclim-dl] {present}/{len(NARCLIM_NC_FILES)} raster files ready in {DEST_DIR}")


if __name__ == "__main__":
    main()
