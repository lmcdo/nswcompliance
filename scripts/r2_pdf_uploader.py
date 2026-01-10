#!/usr/bin/env python3
"""
Upload SEPP PDF pages to Cloudflare R2 storage.

This utility uploads extracted PDF page images to R2 using boto3.
It uses R2 credentials from the root .env file.

Usage:
    # Upload a single page
    python scripts/r2_pdf_uploader.py sepp-resilience-hazards 23
    
    # Upload multiple pages
    python scripts/r2_pdf_uploader.py sepp-housing-2021 35 47 72 115

Requirements:
    - boto3
    - python-dotenv
    - R2 credentials in .env (R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY)

Output:
    - Uploads to R2 bucket: nsw-planning-pdfs
    - Path format: pdf-pages/{sepp_name}/page-{num}.png
    - Returns public URLs for verification
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import requests

# Load environment variables from root .env
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


class R2Uploader:
    """Upload PDF pages to Cloudflare R2 storage."""
    
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
    
    def upload_page(self, sepp_name: str, page_num: int) -> Tuple[bool, str]:
        """
        Upload a single PDF page to R2.
        
        Args:
            sepp_name: SEPP identifier (e.g., 'sepp-resilience-hazards')
            page_num: Page number to upload
            
        Returns:
            (success: bool, url_or_error: str)
        """
        # Construct paths
        local_path = Path(f'frontend-nextjs/public/pdf-pages/{sepp_name}/page-{page_num}.png')
        r2_key = f'pdf-pages/{sepp_name}/page-{page_num}.png'
        public_url = f'{self.public_url}/{r2_key}'
        
        # Check local file exists
        if not local_path.exists():
            return False, f"Local file not found: {local_path}"
        
        # Upload to R2
        try:
            print(f"  Uploading {local_path.name} ({local_path.stat().st_size // 1024} KB)...", end=' ')
            
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
                    print(f"OK Uploaded and verified")
                    return True, public_url
                else:
                    print(f"FAIL Upload succeeded but verification failed (HTTP {response.status_code})")
                    return False, f"Verification failed: HTTP {response.status_code}"
            except requests.RequestException as e:
                print(f"FAIL Upload succeeded but verification failed: {e}")
                return False, f"Verification error: {e}"
                
        except ClientError as e:
            error_msg = f"R2 upload failed: {e}"
            print(f"FAIL {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"FAIL {error_msg}")
            return False, error_msg
    
    def upload_pages(self, sepp_name: str, page_nums: List[int]) -> dict:
        """
        Upload multiple PDF pages to R2.
        
        Args:
            sepp_name: SEPP identifier
            page_nums: List of page numbers to upload
            
        Returns:
            Results dict with 'succeeded' and 'failed' lists
        """
        results = {
            'succeeded': [],
            'failed': []
        }
        
        print(f"\nUploading {len(page_nums)} pages for {sepp_name}:")
        print("=" * 60)
        
        for page_num in page_nums:
            success, url_or_error = self.upload_page(sepp_name, page_num)
            
            if success:
                results['succeeded'].append({
                    'page': page_num,
                    'url': url_or_error
                })
            else:
                results['failed'].append({
                    'page': page_num,
                    'error': url_or_error
                })
        
        return results


def main():
    """CLI entry point."""
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nError: Missing arguments")
        print("Usage: python scripts/r2_pdf_uploader.py <sepp-name> <page-num> [<page-num> ...]")
        print("\nExample: python scripts/r2_pdf_uploader.py sepp-resilience-hazards 23")
        sys.exit(1)
    
    sepp_name = sys.argv[1]
    
    # Parse page numbers
    try:
        page_nums = [int(arg) for arg in sys.argv[2:]]
    except ValueError:
        print(f"Error: Invalid page number in arguments: {sys.argv[2:]}")
        sys.exit(1)
    
    # Upload
    try:
        uploader = R2Uploader()
        results = uploader.upload_pages(sepp_name, page_nums)
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"OK Successfully uploaded: {len(results['succeeded'])} pages")
        if results['succeeded']:
            for item in results['succeeded']:
                print(f"  Page {item['page']}: {item['url']}")
        
        if results['failed']:
            print(f"\nFAIL Failed: {len(results['failed'])} pages")
            for item in results['failed']:
                print(f"  Page {item['page']}: {item['error']}")
            sys.exit(1)
        
        print("\nAll uploads successful!")
        
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
