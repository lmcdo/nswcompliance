#!/usr/bin/env python3
"""
Inspect KRG PDF page layout to find the column boundary.
Prints bounding boxes of text blocks on a page with two-column Objectives|Controls layout.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import pdfplumber

# Part 12 signage PDF - provision 96299 (12.1 SIGNAGE DESIGN, two-column)
# Find the PDF
pdf_dir = Path("downloads/ku_ring_gai")
pdfs = sorted(pdf_dir.glob("*signage*")) + sorted(pdf_dir.glob("*part_12*")) + sorted(pdf_dir.glob("*part-12*"))

if not pdfs:
    # Try to find any KRG PDF
    pdfs = sorted(pdf_dir.glob("*.pdf"))[:3]
    print(f"No signage PDF found. Available: {[p.name for p in pdfs]}")
    if not pdfs:
        print(f"No PDFs in {pdf_dir}. Listing downloads/:")
        for d in sorted(Path("downloads").iterdir()):
            print(f"  {d}")
        sys.exit(1)

pdf_path = pdfs[0]
print(f"Inspecting: {pdf_path}")

with pdfplumber.open(pdf_path) as pdf:
    # Look at first few pages to find a two-column layout page
    for page_num in range(min(5, len(pdf.pages))):
        page = pdf.pages[page_num]
        print(f"\n=== Page {page_num + 1} (size: {page.width:.0f} x {page.height:.0f}) ===")

        # Get words with x-coordinates
        words = page.extract_words()
        if not words:
            print("  No words")
            continue

        # Look for "Objectives" or "Controls" keywords to find two-column pages
        word_texts = [w['text'] for w in words]
        if 'Objectives' in word_texts or 'Controls' in word_texts:
            print("  *** FOUND Objectives/Controls on this page ***")
            # Print words near the column boundary
            sorted_words = sorted(words, key=lambda w: (round(w['top'] / 10), w['x0']))
            # Find x positions of "Objectives" and "Controls" headers
            obj_word = next((w for w in words if w['text'] == 'Objectives'), None)
            ctrl_word = next((w for w in words if w['text'] == 'Controls'), None)
            if obj_word:
                print(f"  'Objectives' at x0={obj_word['x0']:.1f}, y={obj_word['top']:.1f}")
            if ctrl_word:
                print(f"  'Controls' at x0={ctrl_word['x0']:.1f}, y={ctrl_word['top']:.1f}")

            # Show x distribution of first ~30 words to understand column structure
            print(f"  First 30 words x0 positions:")
            for w in sorted_words[:30]:
                print(f"    x0={w['x0']:.0f} y={w['top']:.0f} '{w['text']}'")
            break
        else:
            x_positions = [w['x0'] for w in words]
            print(f"  x0 range: {min(x_positions):.0f} – {max(x_positions):.0f}")
            print(f"  First 5 words: {word_texts[:5]}")
