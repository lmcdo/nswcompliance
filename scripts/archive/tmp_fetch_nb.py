import fitz, sys, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/_R15/Warringah%20DCP%202011%20-%20as%20amended%207%20May%202016.pdf'
pdf_path = 'scripts/warringah_dcp.pdf'

print('Downloading Warringah DCP...')
urllib.request.urlretrieve(url, pdf_path)
doc = fitz.open(pdf_path)
print(f'Total pages: {len(doc)}')

# Search for B5 Side Boundary Setbacks section
for i in range(len(doc)):
    text = doc[i].get_text()
    if 'side boundary setback' in text.lower() or 'b5 side' in text.lower():
        print(f'\n{"="*60}')
        print(f'PAGE {i+1}')
        print(f'{"="*60}')
        print(text[:3000])

doc.close()
