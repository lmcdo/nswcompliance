#!/usr/bin/env python3
"""Download PDFs locally then OCR via Mistral base64 upload."""
import os, sys, tempfile, base64
sys.stdout.reconfigure(encoding='utf-8')
try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral
import requests
from dotenv import load_dotenv
load_dotenv()

client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
}

# Planning Portal S3 mirrors + direct council URLs
COUNCILS = {
    "hornsby": "https://shared-drupal-s3fs.s3-ap-southeast-2.amazonaws.com/master-test/fapub_pdf/001_00GX_0J190SOQ28SB_LXKVQRWF.PDF",
    "randwick": "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/_R15/Randwick%20DCP%202013%20-%20including%20Amendment%20adopted%2012%20Apr%202016.pdf",
    "sutherland": "https://www.sutherlandshire.nsw.gov.au/__data/assets/pdf_file/0018/6714/36-vehicular-access-traffic-parking-am-6-to-publish-pdf-20210310.pdf",
    "georges_river": "https://www.georgesriver.nsw.gov.au/-/media/Files/Development/Strategic%20Planning/Amd-6-GRDCP-Part-3-General-Planning-Considerations-NEW.pdf",
}

council = sys.argv[1] if len(sys.argv) > 1 else None
if not council or council not in COUNCILS:
    print(f"Usage: python _ocr_local.py <council>")
    print(f"Options: {list(COUNCILS.keys())}")
    sys.exit(1)

url = COUNCILS[council]
print(f"Downloading {council} from {url[:80]}...")
resp = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
print(f"HTTP {resp.status_code}, {len(resp.content)} bytes, content-type: {resp.headers.get('content-type','?')}")

if resp.status_code != 200:
    print(f"ERROR: HTTP {resp.status_code}")
    sys.exit(1)

if len(resp.content) < 5000:
    print(f"WARNING: File too small, probably not a PDF. First 500 bytes:")
    print(resp.content[:500])
    sys.exit(1)

# OCR via base64
print(f"OCR'ing {len(resp.content)} bytes...")
pdf_b64 = base64.standard_b64encode(resp.content).decode('utf-8')

result = client.ocr.process(
    model='mistral-ocr-latest',
    document={
        'type': 'document_url',
        'document_url': f'data:application/pdf;base64,{pdf_b64}'
    },
    include_image_base64=False,
)

print(f'Pages: {len(result.pages)}')

# Search for parking
parking_pages = []
for p in result.pages:
    md = p.markdown.lower()
    if ('parking rate' in md or 'spaces per dwelling' in md
        or 'car parking requirement' in md
        or ('table' in md and 'parking' in md)
        or 'spaces per' in md):
        parking_pages.append(p.index + 1)

if parking_pages:
    print(f'Parking content on pages: {parking_pages}')
    for p in result.pages:
        if (p.index + 1) in parking_pages:
            print(f'\n{"="*60}')
            print(f'PAGE {p.index + 1}')
            print('='*60)
            print(p.markdown)
else:
    print('No parking tables found. TOC (page 1):')
    if result.pages:
        print(result.pages[0].markdown[:3000])
