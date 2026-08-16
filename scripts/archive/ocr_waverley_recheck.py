#!/usr/bin/env python3
"""
Re-OCR the updated Waverley DCP 2022 (Amendment 5, changed 2026-03-16).
Check secondary dwelling setback section against existing dcp_setback_controls row.
"""
import os, sys, re, base64, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

from enrichment.extractors.numeric_extractor import NumericExtractor

URL = 'https://www.waverley.nsw.gov.au/media/documents/building_and_development/dcp/WDCP_2022_updated.pdf'
CHAPTER_KEY = 'waverley-dcp-2022'

extractor = NumericExtractor()

SD_HEADING_RE = re.compile(
    r'(secondary\s+dwelling|ancillary\s+dwell|granny\s+flat)',
    re.IGNORECASE,
)
FALSE_POSITIVE_RE = re.compile(
    r'\b(tree|fence|fencing|dormer|retaining\s+wall|sight.line|skylight|carport|outbuilding|play\s+area|eave|gutter)\b',
    re.IGNORECASE,
)
PLAUSIBLE = {'front_setback': (2, 15), 'side_setback': (0.5, 6), 'rear_setback': (1, 15), 'max_height': (2.4, 15)}
SETBACK_TYPES = {'setback', 'separation', 'height'}

client = Mistral(api_key=os.environ['MISTRAL_API_KEY'])

print(f"Downloading Waverley DCP from council URL...")
req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=60) as resp:
    pdf_bytes = resp.read()

mb = len(pdf_bytes) / 1_048_576
print(f"Downloaded {mb:.1f} MB")

b64 = base64.standard_b64encode(pdf_bytes).decode()
data_uri = f"data:application/pdf;base64,{b64}"

def ocr_pages(page_indices):
    resp = client.ocr.process(
        model="mistral-ocr-latest",
        document={"type": "document_url", "document_url": data_uri},
        pages=page_indices,
        include_image_base64=False,
    )
    return "\n\n".join(p.markdown for p in resp.pages)

# TOC scan first
print("\nScanning TOC (pages 0-4)...")
toc_text = ocr_pages(list(range(5)))
print(toc_text[:3000])

# Find SD section page numbers from TOC
sd_pages = []
for line in toc_text.splitlines():
    if re.search(r'secondary\s+dwell|granny', line, re.IGNORECASE):
        nums = re.findall(r'\d+', line)
        if nums:
            pg = int(nums[-1])
            sd_pages.append(pg)
            print(f"  SD TOC hit: '{line.strip()}' → page {pg}")

if not sd_pages:
    print("  No SD page found in TOC — scanning pages 20-50 for SD headings...")
    # Scan in chunks
    for start in range(20, 80, 10):
        chunk = ocr_pages(list(range(start, min(start+10, 150))))
        if SD_HEADING_RE.search(chunk):
            print(f"  SD heading found in pages {start}-{start+10}")
            sd_pages = list(range(start, min(start+8, 150)))
            break

if sd_pages:
    # OCR the SD section (±3 pages around first hit)
    target = list(range(max(0, sd_pages[0]-1), min(sd_pages[0]+6, 200)))
    print(f"\nOCR pages {target[0]}-{target[-1]} for SD controls...")
    sd_text = ocr_pages(target)
    print("\n── SD section text ──")
    print(sd_text[:4000])

    # Extract candidates
    print("\n── Extracted values ──")
    for para in re.split(r'\n{2,}', sd_text):
        result = extractor.extract(para)
        vals = [v for v in result.get('values', []) if v.get('value_type') in SETBACK_TYPES]
        if not vals:
            continue
        if FALSE_POSITIVE_RE.search(para):
            print(f"  [FP filtered] {para[:100]}")
            continue
        for v in vals:
            ct = v.get('value_type', '')
            vmin = v.get('value_min')
            vmax = v.get('value_max')
            unit = v.get('unit', 'm')
            lo, hi = PLAUSIBLE.get(ct, (0, 100))
            val = vmin or vmax
            if val and not (lo <= val <= hi):
                print(f"  [OUT OF RANGE] {ct} {val}{unit}: {para[:80]}")
                continue
            print(f"  {ct:20} min={vmin} max={vmax} {unit}")
            print(f"    → {para[:120]}")

print("\nDone. Compare against existing DB row: max_height 3.0m (not fronting laneway).")
