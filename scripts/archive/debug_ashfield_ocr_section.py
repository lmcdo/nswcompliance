#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dump raw OCR text for Ashfield Chapter F pages 1-40 to find setback table structure."""
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])

URL = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/ashfield/v1.1-2026-03-02/chapter-f-dev-category.pdf'

print("OCR-ing Ashfield chapter-f pages 1-40...")
response = client.ocr.process(
    model='mistral-ocr-latest',
    document={'type': 'document_url', 'document_url': URL},
    include_image_base64=False,
    pages=list(range(0, 40)),
)
print(f"Got {len(response.pages)} pages\n")

# Print pages 1-40, looking for setback controls near the secondary dwelling section
for p in response.pages:
    text = p.markdown.strip()
    # Only print pages with setback-relevant content
    if re.search(r'setback|rear|front|side|boundary|height|storey|separation', text, re.IGNORECASE):
        print(f"\n{'='*60}")
        print(f"PAGE {p.index + 1}")
        print('='*60)
        print(text[:3000])
