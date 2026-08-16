import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('C:/Users/lawre/.claude/projects/C--Users-lawre-Downloads-solvyra-projects-compliance-engine-compliance-engine/3824ed99-ec70-4ddc-9a8a-a415cfe60a28/tool-results/webfetch-1778499971599-d1r5w4.pdf')
print(f"Waverley DCP 2022 Part C — {len(doc)} pages\n")

for i in range(len(doc)):
    text = doc[i].get_text()
    lower = text.lower()
    if any(kw in lower for kw in ['landscap', 'deep soil', 'site coverage', 'building footprint', 'soft landscap']):
        if any(kw in lower for kw in ['%', 'percent', 'minimum', 'maximum', 'sqm', 'sq.m']):
            print(f'\n{"="*60}')
            print(f'PAGE {i+1}')
            print(f'{"="*60}')
            print(text[:3000])

doc.close()
