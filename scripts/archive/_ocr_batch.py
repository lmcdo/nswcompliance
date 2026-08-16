#!/usr/bin/env python3
"""OCR multiple council parking chapters and extract parking tables."""
import os, sys, json
sys.stdout.reconfigure(encoding='utf-8')
try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral
from dotenv import load_dotenv
load_dotenv()

client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])

COUNCILS = {
    "georges_river": {
        "url": "https://www.georgesriver.nsw.gov.au/Development/Planning-Controls/Development-Control-Plans/Georges-River-Development-Control-Plan-2021/-/media/Files/Development/Strategic%20Planning/Amd-6-GRDCP-Part-3-General-Planning-Considerations-NEW.pdf",
        "label": "GRDCP Part 3 General Planning Considerations",
    },
    "hornsby": {
        "url": "https://www.hornsby.nsw.gov.au/files/assets/public/v/2/property/building-and-development/policies-and-guidelines/hornsby-development-control-plan/documents/hdcp-part-1-final-23-june-2025.pdf",
        "label": "Hornsby DCP 2024 Part 1 General",
    },
    "sutherland": {
        "url": "https://www.sutherlandshire.nsw.gov.au/__data/assets/pdf_file/0018/6714/36-vehicular-access-traffic-parking-am-6-to-publish-pdf-20210310.pdf",
        "label": "Sutherland DCP 2015 Chapter 36 Vehicular Access Traffic Parking",
    },
    "randwick": {
        "url": "https://www.randwick.nsw.gov.au/__data/assets/pdf_file/0020/13736/Randwick-Comprehensive-DCP-Volume-1-Parts-A-C.pdf",
        "label": "Randwick DCP 2013 Volume 1 Parts A-C",
    },
}

council_name = sys.argv[1] if len(sys.argv) > 1 else None
if council_name and council_name not in COUNCILS:
    print(f"Unknown council: {council_name}. Options: {list(COUNCILS.keys())}")
    sys.exit(1)

targets = {council_name: COUNCILS[council_name]} if council_name else COUNCILS

for name, info in targets.items():
    print(f"\n{'='*70}")
    print(f"OCR: {name} — {info['label']}")
    print(f"URL: {info['url'][:80]}...")
    print('='*70)

    try:
        result = client.ocr.process(
            model='mistral-ocr-latest',
            document={'type': 'document_url', 'document_url': info['url']},
            include_image_base64=False,
        )
        print(f'Pages: {len(result.pages)}')

        # Search for parking rate tables
        parking_pages = []
        for p in result.pages:
            md = p.markdown.lower()
            if ('parking rate' in md or 'spaces per dwelling' in md
                or 'car parking requirement' in md or 'parking provision' in md
                or ('table' in md and ('parking' in md or 'car space' in md))):
                parking_pages.append(p.index + 1)

        if parking_pages:
            print(f'Parking content on pages: {parking_pages}')
            for p in result.pages:
                if (p.index + 1) in parking_pages:
                    print(f'\n--- PAGE {p.index + 1} ---')
                    print(p.markdown)
        else:
            # Show TOC
            print('No parking tables found. TOC (page 1):')
            print(result.pages[0].markdown[:2000] if result.pages else "Empty")
    except Exception as e:
        print(f'ERROR: {e}')
