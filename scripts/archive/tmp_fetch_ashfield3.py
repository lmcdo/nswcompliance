import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'C:\Users\lawre\.claude\projects\C--Users-lawre-Downloads-solvyra-projects-compliance-engine-compliance-engine\3824ed99-ec70-4ddc-9a8a-a415cfe60a28\tool-results\webfetch-1778492360852-30q4m4.pdf'
doc = fitz.open(pdf_path)

# Multi dwelling housing starts at page 24, RFB at page 38
# Read pages 24-55 for multi-dwelling and RFB setbacks
for i in range(23, 55):
    text = doc[i].get_text()
    if 'setback' in text.lower():
        print(f'\n{"="*60}')
        print(f'PAGE {i+1}')
        print(f'{"="*60}')
        print(text[:3000])

doc.close()
