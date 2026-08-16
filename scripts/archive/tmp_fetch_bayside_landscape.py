import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('scripts/bayside_dcp.pdf')

# Search for landscaping, deep soil, site coverage in residential sections
for i in range(len(doc)):
    text = doc[i].get_text()
    lower = text.lower()
    if any(kw in lower for kw in ['landscaped area', 'deep soil', 'site coverage', 'building footprint']):
        if any(kw in lower for kw in ['%', 'percent', 'minimum', 'maximum']):
            if any(kw in lower for kw in ['dwelling', 'residential', 'r2', 'r3', 'low density', 'medium density']):
                print(f'\n{"="*60}')
                print(f'PAGE {i+1}')
                print(f'{"="*60}')
                print(text[:3000])

doc.close()
