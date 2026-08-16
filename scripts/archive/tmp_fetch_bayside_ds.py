import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('scripts/bayside_dcp.pdf')

for i in range(92, 100):
    text = doc[i].get_text()
    print(f'\n{"="*60}')
    print(f'PAGE {i+1}')
    print(f'{"="*60}')
    print(text[:3000])

doc.close()
