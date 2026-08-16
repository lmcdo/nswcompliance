#!/usr/bin/env python3
"""OCR Woollahra B3 pages 8-20 to extract Figure 5A/5B setback tables."""
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])

URL = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/woollahra/v1.0-baseline/chapter-b3-general-development.pdf'

print("OCR-ing Woollahra B3 pages 8-25...")
response = client.ocr.process(
    model='mistral-ocr-latest',
    document={'type': 'document_url', 'document_url': URL},
    include_image_base64=False,
    pages=list(range(7, 25)),  # 0-indexed: pages 8-25
)
print(f"Got {len(response.pages)} pages\n")

for p in response.pages:
    text = p.markdown.strip()
    if re.search(r'Figure 5|setback|side.*setback|rear.*setback|900mm|1\.5m\|0\.9m', text, re.IGNORECASE):
        print(f"\n{'='*60}")
        print(f"PAGE {p.index + 1}")
        print('='*60)
        print(text[:3000])
