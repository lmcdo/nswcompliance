import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('scripts/bayside_dcp.pdf')

for i in range(len(doc)):
    text = doc[i].get_text()
    if 'site coverage' in text.lower() and '%' in text:
        print(f'\n{"="*60}')
        print(f'PAGE {i+1}')
        print(f'{"="*60}')
        print(text[:2000])

doc.close()
