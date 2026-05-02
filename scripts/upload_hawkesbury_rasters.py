"""
One-off script: upload Hawkesbury FRMSP 2025 AEP rasters to Cloudflare R2.

Run once locally before deploying to Railway:

  python3 scripts/upload_hawkesbury_rasters.py

Requires env vars (same as production):
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME

Files are stored under the key prefix: hawkesbury-rasters/
"""
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

R2_ACCOUNT_ID      = os.environ["R2_ACCOUNT_ID"]
R2_ACCESS_KEY_ID   = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
R2_BUCKET_NAME     = os.environ["R2_BUCKET_NAME"]
R2_PREFIX          = "hawkesbury-rasters"

RASTER_DIR = Path(__file__).parent.parent / "data" / "flood_studies" / "hawkesbury" / "rasters"

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
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    for filename in AEP_FILES:
        local_path = RASTER_DIR / filename
        r2_key = f"{R2_PREFIX}/{filename}"

        if not local_path.exists():
            print(f"  [MISSING] {local_path} — skipping")
            continue

        size_mb = local_path.stat().st_size / 1_048_576

        # Check if already uploaded (skip if same size)
        try:
            head = s3.head_object(Bucket=R2_BUCKET_NAME, Key=r2_key)
            remote_size = head["ContentLength"]
            if remote_size == local_path.stat().st_size:
                print(f"  [SKIP] {filename} already uploaded ({size_mb:.1f} MB)")
                continue
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                raise

        print(f"  [UPLOAD] {filename} ({size_mb:.1f} MB) → r2://{R2_BUCKET_NAME}/{r2_key}")
        s3.upload_file(
            str(local_path),
            R2_BUCKET_NAME,
            r2_key,
            ExtraArgs={"ContentType": "image/tiff"},
        )
        print(f"  [DONE] {filename}")

    print("\nAll done. Verify with:")
    print(f"  aws s3 ls s3://{R2_BUCKET_NAME}/{R2_PREFIX}/ --endpoint-url https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com")


if __name__ == "__main__":
    main()
