#!/usr/bin/env python3
"""Read Canterbury-Bankstown LEP PDF and extract land use tables."""
import fitz
import re
import sys

pdf_path = sys.argv[1] if len(sys.argv) > 1 else '/c/Users/lawre/Downloads/canterbury bankstown epi-2023-0336.pdf'
doc = fitz.open(pdf_path)
print(f'Pages: {len(doc)}')

# Get full text
full_text = ''
for i in range(len(doc)):
    full_text += doc[i].get_text() + '\n'

# Show first few pages
for i in range(min(3, len(doc))):
    text = doc[i].get_text()
    print(f'\n=== Page {i+1} ({len(text)} chars) ===')
    print(text[:500])

# Find zone headings
print(f'\n=== Zone headings ===')
# Normalize
text = full_text.replace('\xa0', ' ')
text = re.sub(r'(Zone\s+[A-Z][A-Z]?\d?[A-Z]?)\s*\n\s*(?=[A-Z])', r'\1   ', text)

zone_pattern = re.compile(r'^Zone\s+([A-Z][A-Z]?\d[A-Z]?)\s{2,}(.+)$', re.MULTILINE)
matches = list(zone_pattern.finditer(text))
print(f'Found {len(matches)} zones')
for m in matches[:10]:
    print(f'  {m.group(1)} - {m.group(2).strip()[:50]}')

# Also try simpler pattern
print(f'\n=== Simple Zone pattern ===')
simple = list(re.finditer(r'Zone\s+([A-Z][A-Z]?\d[A-Z]?)', text))
print(f'Found {len(simple)} "Zone X" occurrences')
seen = set()
for m in simple[:30]:
    code = m.group(1)
    if code not in seen:
        seen.add(code)
        ctx = text[m.start():m.start()+80].replace('\n', ' ')
        print(f'  {code}: {ctx}')
