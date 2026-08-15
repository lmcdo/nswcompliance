import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('scripts/warringah_dcp.pdf')

# Read pages 15-25 for side setback and front setback controls
for i in range(14, 30):
    text = doc[i].get_text()
    print(f'\n{"="*60}')
    print(f'PAGE {i+1}')
    print(f'{"="*60}')
    print(text)

doc.close()
