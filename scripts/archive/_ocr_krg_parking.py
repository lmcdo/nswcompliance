#!/usr/bin/env python3
"""Download + OCR Ku-ring-gai DCP Part 22 for parking rates."""
import base64, os, sys, io
from pathlib import Path
from dotenv import load_dotenv
import httpx
from pypdf import PdfReader, PdfWriter

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.environ["MISTRAL_API_KEY"]

urls = [
    "https://www.krg.nsw.gov.au/files/assets/public/v/3/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-ku-ring-gai-development-control-plan/kdcp-section-c-part-22-general-access-and-parking.pdf",
    "https://www.krg.nsw.gov.au/files/assets/public/v/4/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-planning-and-development/ku-ring-gai-dcp-section-c-part-22-general-access-and-parking-2022-amendment-1.pdf",
    "https://www.krg.nsw.gov.au/files/assets/public/hptrim/information-management-publications-public-website-ku-ring-gai-council-website-planning-and-development/dcp_principal_section_c_-part_22_-_parking.pdf",
]

pdf_bytes = None
for url in urls:
    print(f"Trying {url[:90]}...")
    try:
        r = httpx.get(url, timeout=60.0, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
        r.raise_for_status()
        pdf_bytes = r.content
        print(f"Downloaded {len(pdf_bytes)} bytes")
        break
    except Exception as e:
        print(f"Failed: {type(e).__name__}: {e}")

if not pdf_bytes:
    print("\nAll URLs failed. Trying S3 mirrors...")
    s3_urls = [
        "https://shared-drupal-s3fs.s3-ap-southeast-2.amazonaws.com/master-test/fapub_pdf/KU-RING-GAI/Ku-ring-gai+Development+Control+Plan.pdf",
        "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/KU-RING-GAI/Ku-ring-gai+DCP.pdf",
    ]
    for url in s3_urls:
        print(f"Trying S3: {url[:80]}...")
        try:
            r = httpx.get(url, timeout=120.0, follow_redirects=True)
            r.raise_for_status()
            pdf_bytes = r.content
            print(f"Downloaded {len(pdf_bytes)} bytes")
            break
        except Exception as e:
            print(f"Failed: {type(e).__name__}: {e}")

if not pdf_bytes:
    print("All sources exhausted")
    sys.exit(1)

reader = PdfReader(io.BytesIO(pdf_bytes))
total_pages = len(reader.pages)
print(f"Total pages: {total_pages}")

# Search for parking rate pages
for i in range(min(total_pages, 100)):
    text = reader.pages[i].extract_text() or ""
    if any(kw in text.lower() for kw in ["parking rate", "car parking", "spaces per", "table"]):
        preview = text[:150].strip().replace("\n", " ")
        print(f"Page {i}: {preview}")
