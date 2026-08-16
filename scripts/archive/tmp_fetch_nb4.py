import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('scripts/warringah_dcp.pdf')

# Search for rear boundary setback section
for i in range(30, 50):
    text = doc[i].get_text()
    if 'rear' in text.lower() and ('setback' in text.lower() or 'boundary' in text.lower()):
        print(f'\n{"="*60}')
        print(f'PAGE {i+1}')
        print(f'{"="*60}')
        print(text[:3000])

doc.close()
