#!/usr/bin/env python3
"""
Upload LEP PDF page images to Cloudflare R2 storage.

This uploads the newly extracted LEP images (iwlep_clause_*.png) to R2.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import requests

# Load environment variables from root .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# LEP images to upload (the 6 new ones we just extracted)
NEW_LEP_IMAGES = [
    'iwlep_clause_6_29_page_84.png',
    'iwlep_clause_6_32_page_87.png',
    'iwlep_clause_6_33_page_87.png',
    'iwlep_clause_6_1_page_60.png',
    'iwlep_clause_6_5_page_62.png',
    'iwlep_clause_6_6_page_63.png',
]

class R2Uploader:
    """Upload LEP images to Cloudflare R2 storage."""

    def __init__(self):
        """Initialize R2 client with credentials from .env."""
        self.account_id = os.getenv('R2_ACCOUNT_ID')
        self.access_key = os.getenv('R2_ACCESS_KEY_ID')
        self.secret_key = os.getenv('R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('R2_BUCKET_NAME', 'nsw-planning-pdfs')
        self.public_url = os.getenv('R2_PUBLIC_URL', 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev')

        # Validate credentials
        if not all([self.account_id, self.access_key, self.secret_key]):
            raise ValueError(
                "Missing R2 credentials in .env file. Required:\n"
                "  R2_ACCOUNT_ID\n"
                "  R2_ACCESS_KEY_ID\n"
                "  R2_SECRET_ACCESS_KEY"
            )

        # Initialize boto3 S3 client for R2
        self.s3 = boto3.client(
            's3',
            endpoint_url=f'https://{self.account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name='auto'
        )

    def upload_lep_image(self, filename: str, local_dir: Path):
        """
        Upload a single LEP image to R2.

        Args:
            filename: Image filename (e.g., 'iwlep_clause_6_29_page_84.png')
            local_dir: Local directory containing the image

        Returns:
            (success: bool, url_or_error: str)
        """
        local_path = local_dir / filename
        r2_key = f'pdf-pages/{filename}'  # Store in pdf-pages/ directory
        public_url = f'{self.public_url}/{r2_key}'

        # Check local file exists
        if not local_path.exists():
            return False, f"Local file not found: {local_path}"

        # Upload to R2
        try:
            file_size_kb = local_path.stat().st_size // 1024
            print(f"  Uploading {filename} ({file_size_kb} KB)...", end=' ')

            self.s3.upload_file(
                str(local_path),
                self.bucket_name,
                r2_key,
                ExtraArgs={'ContentType': 'image/png'}
            )

            # Verify upload
            try:
                response = requests.head(public_url, timeout=10)
                if response.status_code == 200:
                    print(f"✅ OK")
                    return True, public_url
                else:
                    print(f"❌ FAIL (HTTP {response.status_code})")
                    return False, f"Verification failed: HTTP {response.status_code}"
            except requests.RequestException as e:
                print(f"❌ FAIL (verification error)")
                return False, f"Verification error: {e}"

        except ClientError as e:
            error_msg = f"R2 upload failed: {e}"
            print(f"❌ FAIL")
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"❌ FAIL")
            return False, error_msg


def main():
    """Upload all new LEP images to R2."""

    print('=' * 80)
    print('UPLOAD LEP IMAGES TO CLOUDFLARE R2')
    print('=' * 80)
    print()

    # Local directory with LEP images
    local_dir = Path(__file__).parent.parent / 'frontend-nextjs' / 'public' / 'pdf-pages'

    if not local_dir.exists():
        print(f'❌ ERROR: Local directory not found: {local_dir}')
        sys.exit(1)

    print(f'📁 Local directory: {local_dir}')
    print(f'📤 Uploading {len(NEW_LEP_IMAGES)} new LEP images')
    print()

    # Initialize uploader
    try:
        uploader = R2Uploader()
        print(f'✅ Connected to R2 bucket: {uploader.bucket_name}')
        print(f'🌐 Public URL: {uploader.public_url}')
        print()
    except ValueError as e:
        print(f'❌ ERROR: {e}')
        sys.exit(1)

    # Upload each image
    print('Uploading images:')
    print('-' * 80)

    succeeded = []
    failed = []

    for filename in NEW_LEP_IMAGES:
        success, url_or_error = uploader.upload_lep_image(filename, local_dir)

        if success:
            succeeded.append({'filename': filename, 'url': url_or_error})
        else:
            failed.append({'filename': filename, 'error': url_or_error})

    # Summary
    print()
    print('=' * 80)
    print('UPLOAD SUMMARY')
    print('=' * 80)
    print()

    if succeeded:
        print(f'✅ Successfully uploaded: {len(succeeded)} images')
        for item in succeeded:
            print(f'   {item["filename"]}')
            print(f'   → {item["url"]}')
            print()

    if failed:
        print(f'❌ Failed: {len(failed)} images')
        for item in failed:
            print(f'   {item["filename"]}')
            print(f'   → {item["error"]}')
            print()
        sys.exit(1)

    print('=' * 80)
    print('✅ ALL UPLOADS SUCCESSFUL!')
    print('=' * 80)
    print()
    print('Next step: Update frontend to use R2 URLs instead of local paths')
    print('LEP images are now available at:')
    print(f'  {uploader.public_url}/pdf-pages/iwlep_clause_*.png')


if __name__ == '__main__':
    main()
