#!/usr/bin/env python3
"""
Upload SEPP PDF images to Cloudflare R2 bucket

Usage:
    python scripts/upload-sepp-images-to-r2.py [--dry-run]

Requirements:
    pip install boto3 python-dotenv
"""

import os
import sys
from pathlib import Path
import boto3
from botocore.config import Config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# R2 Configuration from .env
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL')

# Validate credentials
if not all([R2_ACCOUNT_ID, R2_BUCKET_NAME, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]):
    print("ERROR: Missing R2 credentials in .env file")
    print("Required: R2_ACCOUNT_ID, R2_BUCKET_NAME, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY")
    sys.exit(1)

# R2 endpoint (AWS S3-compatible)
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Initialize S3 client for R2
s3_client = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version='s3v4'),
    region_name='auto'
)

def upload_directory(local_dir: Path, s3_prefix: str, dry_run: bool = False):
    """
    Upload all files from local directory to R2 bucket

    Args:
        local_dir: Local directory path
        s3_prefix: Prefix for S3 keys (e.g., "pdf-pages/sepp-housing-2021")
        dry_run: If True, only print what would be uploaded
    """
    if not local_dir.exists():
        print(f"ERROR: Directory not found: {local_dir}")
        return 0, 0

    files = list(local_dir.glob("*.png"))
    total_files = len(files)
    uploaded = 0
    skipped = 0

    print(f"\n{'DRY RUN: ' if dry_run else ''}Uploading from: {local_dir}")
    print(f"S3 prefix: {s3_prefix}")
    print(f"Total files: {total_files}\n")

    for file_path in files:
        # S3 key: pdf-pages/sepp-housing-2021/sepp-housing-2021_page_1.png
        s3_key = f"{s3_prefix}/{file_path.name}"

        if dry_run:
            print(f"  [DRY RUN] Would upload: {file_path.name} -> {s3_key}")
            uploaded += 1
        else:
            try:
                # Check if file already exists
                try:
                    s3_client.head_object(Bucket=R2_BUCKET_NAME, Key=s3_key)
                    print(f"  [SKIP] Already exists: {file_path.name}")
                    skipped += 1
                    continue
                except:
                    pass  # File doesn't exist, upload it

                # Upload file
                s3_client.upload_file(
                    str(file_path),
                    R2_BUCKET_NAME,
                    s3_key,
                    ExtraArgs={
                        'ContentType': 'image/png',
                        'CacheControl': 'public, max-age=31536000'  # 1 year cache
                    }
                )
                print(f"  [OK] Uploaded: {file_path.name}")
                uploaded += 1

            except Exception as e:
                print(f"  [ERROR] Failed to upload {file_path.name}: {e}")

    return uploaded, skipped


def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("="*60)
        print("DRY RUN MODE - No files will be uploaded")
        print("="*60)

    print(f"\nCloudflare R2 Upload")
    print(f"Account: {R2_ACCOUNT_ID}")
    print(f"Bucket: {R2_BUCKET_NAME}")
    print(f"Public URL: {R2_PUBLIC_URL}")

    # Base directory for SEPP images
    base_dir = Path(__file__).parent.parent / "frontend-nextjs" / "public" / "pdf-pages"

    # SEPP directories to upload
    sepps = [
        {
            'name': 'Transport & Infrastructure 2021',
            'local_dir': base_dir / 'sepp-transport-infrastructure-2021',
            's3_prefix': 'pdf-pages/sepp-transport-infrastructure-2021'
        },
        {
            'name': 'Biodiversity & Conservation 2021',
            'local_dir': base_dir / 'sepp-biodiversity-conservation-2021',
            's3_prefix': 'pdf-pages/sepp-biodiversity-conservation-2021'
        },
        {
            'name': 'Housing 2021',
            'local_dir': base_dir / 'sepp-housing-2021',
            's3_prefix': 'pdf-pages/sepp-housing-2021'
        },
        {
            'name': 'Exempt & Complying',
            'local_dir': base_dir / 'sepp-exempt-complying',
            's3_prefix': 'pdf-pages/sepp-exempt-complying'
        },
        {
            'name': 'Housing (legacy)',
            'local_dir': base_dir / 'sepp-housing',
            's3_prefix': 'pdf-pages/sepp-housing'
        },
        {
            'name': 'Resilience & Hazards',
            'local_dir': base_dir / 'sepp-resilience-hazards',
            's3_prefix': 'pdf-pages/sepp-resilience-hazards'
        },
        {
            'name': 'Sustainable Buildings',
            'local_dir': base_dir / 'sepp-sustainable-buildings',
            's3_prefix': 'pdf-pages/sepp-sustainable-buildings'
        },
        {
            'name': 'Transport 2021 (legacy)',
            'local_dir': base_dir / 'sepp-transport-2021',
            's3_prefix': 'pdf-pages/sepp-transport-2021'
        }
    ]

    total_uploaded = 0
    total_skipped = 0

    for sepp in sepps:
        print(f"\n{'='*60}")
        print(f"SEPP: {sepp['name']}")
        print(f"{'='*60}")

        uploaded, skipped = upload_directory(
            sepp['local_dir'],
            sepp['s3_prefix'],
            dry_run
        )

        total_uploaded += uploaded
        total_skipped += skipped

    print(f"\n{'='*60}")
    print(f"Summary")
    print(f"{'='*60}")
    print(f"{'Would upload' if dry_run else 'Uploaded'}: {total_uploaded} files")
    print(f"Skipped: {total_skipped} files")
    print(f"Total processed: {total_uploaded + total_skipped} files")

    if not dry_run:
        print(f"\nImages accessible at:")
        print(f"  {R2_PUBLIC_URL}/pdf-pages/sepp-{{slug}}/sepp-{{slug}}_page_{{number}}.png")
        print(f"\nExample:")
        print(f"  {R2_PUBLIC_URL}/pdf-pages/sepp-housing-2021/sepp-housing-2021_page_1.png")
    else:
        print(f"\nRun without --dry-run to actually upload files:")
        print(f"  python scripts/upload-sepp-images-to-r2.py")


if __name__ == '__main__':
    main()
