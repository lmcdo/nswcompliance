import fitz  # PyMuPDF
from pathlib import Path

sepp_dir = Path('docs/sepps')
sepps = list(sepp_dir.glob('*.pdf'))

print(f'Analyzing {len(sepps)} SEPP PDFs for images...\n')

for pdf_path in sepps:
    doc = fitz.open(pdf_path)
    total_images = 0
    total_pages = len(doc)

    for page_num, page in enumerate(doc):
        images = page.get_images()
        total_images += len(images)

    doc.close()

    print(f'{pdf_path.name[:70]}')
    print(f'  Pages: {total_pages:>4} | Images: {total_images:>4} | Avg: {total_images/total_pages:.2f} per page')