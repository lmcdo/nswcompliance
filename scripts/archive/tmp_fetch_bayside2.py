import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('scripts/bayside_dcp.pdf')

# Based on TOC, look at the residential sections - likely Part 5 (Residential)
# Let's search for dwelling house / low density setback controls
# Check pages around 100-200 for residential built form controls
setback_pages = []
for i in range(len(doc)):
    text = doc[i].get_text().lower()
    if ('setback' in text and ('dwelling' in text or 'residential' in text or 'dual occupancy' in text)):
        if any(kw in text for kw in ['metre', 'meter', 'minimum', 'boundary', 'front', 'side', 'rear']):
            setback_pages.append(i)

print(f'Found {len(setback_pages)} candidate pages')
for i in setback_pages[:30]:
    text = doc[i].get_text()
    print(f'\n{"="*60}')
    print(f'PAGE {i+1}')
    print(f'{"="*60}')
    print(text[:3000])

doc.close()
