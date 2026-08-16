#!/usr/bin/env python3
"""Convert Canterbury-Bankstown LEP PDF to text file for the scraper."""
import fitz
import sys

pdf_path = sys.argv[1] if len(sys.argv) > 1 else 'C:/Users/lawre/Downloads/canterbury bankstown epi-2023-0336.pdf'
out_path = 'data/lep-html/canterbury-bankstown-lep.html'

doc = fitz.open(pdf_path)
print(f'Pages: {len(doc)}')

# Wrap text in minimal HTML so BeautifulSoup can parse it
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('<html><body>\n')
    for i in range(len(doc)):
        text = doc[i].get_text()
        # Normalize zone headings: "Zone R2 Low Density" → "Zone R2   Low Density"
        # so the HTML parser's \s{2,} pattern matches (PDF only has single spaces)
        import re
        text = re.sub(r'(Zone\s+[A-Z][A-Z]?\d[A-Z]?) ([A-Z])', r'\1   \2', text)
        # Strip PDF page headers/footers
        text = re.sub(r'Page \d+ of \d+', '', text)
        text = re.sub(r'Canterbury-Bankstown Local Environmental Plan 2023 \[NSW\]', '', text)
        text = re.sub(r'Current version for.*?\)', '', text)
        # Escape HTML entities
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        f.write(f'<div class="page" data-page="{i+1}">\n<pre>{text}</pre>\n</div>\n')
    f.write('</body></html>\n')

import os
size = os.path.getsize(out_path)
print(f'Written {size:,} bytes to {out_path}')
