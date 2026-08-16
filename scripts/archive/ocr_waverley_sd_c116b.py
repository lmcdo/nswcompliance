#!/usr/bin/env python3
import os, sys, base64, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
try:
    from mistralai import Mistral
except Exception:
    from mistralai.client import Mistral

URL = 'https://www.waverley.nsw.gov.au/media/documents/building_and_development/dcp/WDCP_2022_updated.pdf'
print("Downloading...")
req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=60) as resp:
    pdf_bytes = resp.read()
b64 = base64.standard_b64encode(pdf_bytes).decode()
data_uri = f'data:application/pdf;base64,{b64}'

client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])

# C1.16 is at DCP page 189 — try pages 196-205
resp = client.ocr.process(
    model='mistral-ocr-latest',
    document={'type': 'document_url', 'document_url': data_uri},
    pages=list(range(196, 210)),
    include_image_base64=False,
)
text = '\n\n'.join(p.markdown for p in resp.pages)
idx = text.lower().find('secondary')
if idx >= 0:
    print(text[max(0, idx-100):idx+5000])
else:
    print("Not found in 196-209, showing raw:")
    print(text[:4000])
