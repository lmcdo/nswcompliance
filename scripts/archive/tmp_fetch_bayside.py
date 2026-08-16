import fitz, sys, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://www.bayside.nsw.gov.au/sites/default/files/2026-04/Bayside%20Development%20Control%20Plan%202022%20-%20Amendment%202.pdf'
pdf_path = 'scripts/bayside_dcp.pdf'

print('Downloading Bayside DCP...')
urllib.request.urlretrieve(url, pdf_path)
doc = fitz.open(pdf_path)
print(f'Total pages: {len(doc)}')

# Search for pages mentioning setback
print('\n=== Pages mentioning "setback" ===')
for i in range(len(doc)):
    text = doc[i].get_text()
    if 'setback' in text.lower():
        # Show page number and first 300 chars of context around "setback"
        idx = text.lower().find('setback')
        start = max(0, idx - 100)
        end = min(len(text), idx + 300)
        print(f'\n--- Page {i+1} ---')
        print(text[start:end].strip())

doc.close()
