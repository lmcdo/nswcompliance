#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print raw OCR text around the Secondary Dwellings section in Leichhardt part-c-s3-residential."""
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])

URL = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/leichhardt/v1.1-2026-03-02/part-c-s3-residential.pdf'

print("OCR-ing Leichhardt part-c-s3-residential (34 pages)...")
response = client.ocr.process(
    model='mistral-ocr-latest',
    document={'type': 'document_url', 'document_url': URL},
    include_image_base64=False,
)
print(f"Got {len(response.pages)} pages\n")

full_text = '\n'.join(f'[PAGE {p.index + 1}]\n{p.markdown}' for p in response.pages)

# Find Secondary Dwellings section
match = re.search(r'secondary\s+dwell', full_text, re.IGNORECASE)
if not match:
    print("Section not found!")
    sys.exit(1)

# Print 3000 chars from section start
section_text = full_text[match.start(): match.start() + 4000]
print("=== SECONDARY DWELLINGS SECTION (raw OCR) ===")
print(section_text)
