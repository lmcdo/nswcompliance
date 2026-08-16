import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('scripts/warringah_dcp.pdf')

# Search for landscaping and site coverage pages
for i in range(len(doc)):
    text = doc[i].get_text()
    lower = text.lower()
    if ('landscap' in lower or 'site coverage' in lower or 'deep soil' in lower) and '%' in text:
        print(f'\n{"="*60}')
        print(f'PAGE {i+1}')
        print(f'{"="*60}')
        print(text[:2000])

doc.close()
