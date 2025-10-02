import fitz
from pathlib import Path
from datetime import datetime

pdf_path = Path('docs/sepps/State Environmental Planning Policy (Transport and Infrastructure) 2021 - NSW Legislation.pdf')
output_dir = Path('docs/sepps/extracted')
output_file = output_dir / 'State Environmental Planning Policy (Transport and Infrastructure) 2021 - NSW Legislation.md'

print(f"Extracting Transport & Infrastructure SEPP...")
print(f"PDF: {pdf_path}")
print(f"Output: {output_file}\n")

doc = fitz.open(pdf_path)
total_pages = len(doc)

print(f"Total pages: {total_pages}")

# Extract text
full_text = []
for page_num, page in enumerate(doc):
    if page_num == 0:
        full_text.append(f"# {pdf_path.name}\n")
        full_text.append(f"Extracted: {datetime.now().strftime('%Y-%m-%d')}\n")
        full_text.append(f"Total Pages: {total_pages}\n\n")
        full_text.append("="*80 + "\n\n")

    full_text.append(f"## Page {page_num + 1}\n\n")
    full_text.append(page.get_text("text"))
    full_text.append("\n\n")

    if (page_num + 1) % 50 == 0:
        print(f"  Processed {page_num + 1}/{total_pages} pages...")

doc.close()

markdown_content = ''.join(full_text)

# Save
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(markdown_content)

print(f"\n[OK] Extraction complete!")
print(f"Output size: {len(markdown_content):,} characters")
print(f"Words: {len(markdown_content.split()):,}")
print(f"File: {output_file}")