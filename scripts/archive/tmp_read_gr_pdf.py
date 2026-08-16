import fitz
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Georges River Low Density
pdf_path = r"C:\Users\lawre\.claude\projects\C--Users-lawre-Downloads-solvyra-projects-compliance-engine-compliance-engine\3824ed99-ec70-4ddc-9a8a-a415cfe60a28\tool-results\webfetch-1778491263342-b1kato.pdf"

doc = fitz.open(pdf_path)
print(f"Pages: {len(doc)}")

for page_num in range(min(len(doc), 30)):
    page = doc[page_num]
    text = page.get_text()
    if any(word in text.lower() for word in ['setback', 'side boundary', 'rear boundary', 'front boundary']):
        print(f"\n=== Page {page_num + 1} ===")
        print(text[:1500])

doc.close()
