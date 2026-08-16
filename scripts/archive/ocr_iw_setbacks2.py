#!/usr/bin/env python3
"""
OCR targeted pages of Marrickville s4.1.6.2 and Leichhardt Part C setbacks.
"""
import os, sys, base64, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])

def fetch_pdf(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()

def ocr(pdf_bytes, pages=None):
    b64 = base64.standard_b64encode(pdf_bytes).decode()
    kwargs = dict(
        model='mistral-ocr-latest',
        document={'type': 'document_url', 'document_url': f'data:application/pdf;base64,{b64}'},
        include_image_base64=False,
    )
    if pages:
        kwargs['pages'] = pages
    r = client.ocr.process(**kwargs)
    return '\n\n'.join(p.markdown for p in r.pages)

# ── Marrickville 4.1 — pages 3-12 (setbacks + secondary dwelling) ─────────────
print("=== MARRICKVILLE 4.1 — pages 3-12 ===")
url_m = ('https://www.innerwest.nsw.gov.au/sites/default/files/2026-01/'
         'Marrickville%20DCP%202011%20-%204.1%20Low%20Density%20Residential%20Development.pdf')
pdf_m = fetch_pdf(url_m)
print(f"  {len(pdf_m)/1e6:.1f} MB — OCR pages 3-12...")
text_m = ocr(pdf_m, pages=list(range(3, 13)))
print(text_m)

# ── Leichhardt Part C Section 1 — full (residential setbacks BLZ) ─────────────
print("\n\n=== LEICHHARDT PART C SECTION 1 ===")
url_l = ('https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/'
         'Leichhardt%20DCP%202013%20-%205%20-%20%20Part%20C%20Place%20Section%201%20-%20with%20IWLEP%202022%20amendments%20March%2023.pdf')
pdf_l = fetch_pdf(url_l)
print(f"  {len(pdf_l)/1e6:.1f} MB — OCR pages 0-20...")
text_l = ocr(pdf_l, pages=list(range(0, 20)))

# Find setback/BLZ content
lower = text_l.lower()
for kw in ['setback', 'building line', 'blz', 'front', 'side setback', 'rear']:
    idx = lower.find(kw)
    if idx >= 0:
        print(f"\n[found: '{kw}' at char {idx}]")
        print(text_l[max(0, idx-100):idx+3000])
        break
else:
    print("No setback keywords found. Raw output:")
    print(text_l[:5000])
