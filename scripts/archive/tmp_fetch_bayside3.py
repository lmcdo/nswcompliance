import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('scripts/bayside_dcp.pdf')

# Section 5.2.1 Low-density starts page 197, 5.2.2 Dual Occ page 206, 5.2.3 Medium density page 208, 5.2.4 High density page 213
# Read pages 197-230 to get all residential setback controls
for i in range(196, 230):
    text = doc[i].get_text()
    if 'setback' in text.lower():
        print(f'\n{"="*60}')
        print(f'PAGE {i+1}')
        print(f'{"="*60}')
        print(text[:4000])

doc.close()
