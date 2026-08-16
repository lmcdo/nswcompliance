import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open('scripts/warringah_dcp.pdf')
print(f'Total pages: {len(doc)}')

# Check if text can be extracted at all
for i in range(min(10, len(doc))):
    text = doc[i].get_text()
    if text.strip():
        print(f'Page {i+1}: {len(text)} chars - {text[:200]}')
    else:
        print(f'Page {i+1}: EMPTY (image-based?)')

# Try broader search
print('\n=== Searching for "setback" ===')
count = 0
for i in range(len(doc)):
    text = doc[i].get_text()
    if 'setback' in text.lower():
        count += 1
        print(f'Page {i+1}: {text[:200]}')
        if count > 10:
            break

if count == 0:
    print('No text found - PDF is likely image-based')

doc.close()
