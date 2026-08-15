import fitz, sys
sys.stdout.reconfigure(encoding='utf-8')

pdfs = {
    'blacktown': r'C:\Users\lawre\Downloads\Part-C-Development-in-the-Residential-Areas_01-02-2026.pdf',
    'campbelltown': r'C:\Users\lawre\Downloads\part-3-low-and-medium-desnity-residential-development-amendment-21-sept2024.pdf',
    'cb_ch5': r'C:\Users\lawre\Downloads\2026_03_12_-_DCP_2023_-_AMENDMENT_11_-_Chapter_5_1_-_Former_Bankstown_LGA_pdf (1).pdf',
    'cb_ch3_7': r'C:\Users\lawre\Downloads\2024_08_06_-_DCP_2023_-_AMENDMENT_4_-_Chapter_3_7_-_Landscape_pdf.pdf',
}

for name, path in pdfs.items():
    doc = fitz.open(path)
    print(f'\n{"#"*70}')
    print(f'# {name} — {len(doc)} pages')
    print(f'{"#"*70}')

    for i in range(len(doc)):
        text = doc[i].get_text()
        lower = text.lower()
        if any(kw in lower for kw in ['landscap', 'deep soil', 'site coverage', 'building footprint']):
            if any(kw in lower for kw in ['%', 'percent', 'minimum', 'maximum', 'sqm']):
                print(f'\n--- PAGE {i+1} ---')
                print(text[:2500])
    doc.close()
