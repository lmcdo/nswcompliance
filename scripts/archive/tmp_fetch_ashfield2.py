import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'C:\Users\lawre\.claude\projects\C--Users-lawre-Downloads-solvyra-projects-compliance-engine-compliance-engine\3824ed99-ec70-4ddc-9a8a-a415cfe60a28\tool-results\webfetch-1778492360852-30q4m4.pdf'
doc = fitz.open(pdf_path)

# Search for rear setback with numeric values, and also dual occupancy / multi dwelling sections
for i in range(len(doc)):
    text = doc[i].get_text()
    lower = text.lower()
    if ('rear' in lower and 'setback' in lower) or ('dual occupancy' in lower and 'setback' in lower) or ('multi dwelling' in lower):
        print(f'\n{"="*60}')
        print(f'PAGE {i+1}')
        print(f'{"="*60}')
        print(text[:3000])

doc.close()
