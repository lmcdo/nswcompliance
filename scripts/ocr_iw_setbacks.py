#!/usr/bin/env python3
"""
OCR Marrickville and Leichhardt DCP setback sections using Mistral.
Extracts DH and SD setback controls for insertion into dcp_setback_controls.
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

PDFS = {
    'marrickville': (
        'https://www.innerwest.nsw.gov.au/sites/default/files/2026-01/'
        'Marrickville%20DCP%202011%20-%204.1%20Low%20Density%20Residential%20Development.pdf'
    ),
    'leichhardt_g': (
        'https://www.innerwest.nsw.gov.au/sites/default/files/2026-03/'
        'Leichhardt%20DCP%202013%20-%2012%20-%20Part%20G%20Section%201-12%20-%20Amdt%2019%20-%20Nov%202023.pdf'
    ),
}

def fetch_and_ocr(name, url, pages=None):
    print(f"\n{'='*60}")
    print(f"Downloading {name} ...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=90) as resp:
        pdf_bytes = resp.read()
    print(f"  {len(pdf_bytes)/1_048_576:.1f} MB")

    b64 = base64.standard_b64encode(pdf_bytes).decode()
    data_uri = f'data:application/pdf;base64,{b64}'

    kwargs = dict(
        model='mistral-ocr-latest',
        document={'type': 'document_url', 'document_url': data_uri},
        include_image_base64=False,
    )
    if pages:
        kwargs['pages'] = pages

    print(f"  OCR pages={pages or 'all'} ...")
    resp = client.ocr.process(**kwargs)
    return '\n\n'.join(p.markdown for p in resp.pages)


# ── Marrickville 4.1 Low Density Residential ──────────────────────────────────
mville_text = fetch_and_ocr('marrickville_4_1', PDFS['marrickville'])

print("\n── Marrickville: searching for setback / secondary / front / rear / side ──")
lower = mville_text.lower()
for keyword in ['setback', 'secondary dwelling', 'front', 'side setback', 'rear setback']:
    idx = lower.find(keyword)
    if idx >= 0:
        print(f"\n[{keyword}] found at char {idx}:")
        print(mville_text[max(0, idx-50):idx+600])
        print("...")
        break

# Show first 5000 chars raw
print("\n── Marrickville raw (first 5000 chars) ──")
print(mville_text[:5000])

# ── Leichhardt Part G ─────────────────────────────────────────────────────────
# Part G has many sections — scan first 10 pages for residential/setback
leich_text = fetch_and_ocr('leichhardt_part_g', PDFS['leichhardt_g'], pages=list(range(0, 15)))

print("\n── Leichhardt Part G: searching for setback ──")
lower2 = leich_text.lower()
idx2 = lower2.find('setback')
if idx2 >= 0:
    print(leich_text[max(0, idx2-100):idx2+2000])
else:
    print("'setback' not found in pages 0-14")
    idx2 = lower2.find('dwelling')
    if idx2 >= 0:
        print(leich_text[max(0, idx2-50):idx2+2000])
    else:
        print("No dwelling reference found. Raw first 3000:")
        print(leich_text[:3000])
