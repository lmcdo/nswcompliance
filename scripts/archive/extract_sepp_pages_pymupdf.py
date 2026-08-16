#!/usr/bin/env python
"""Extract specific pages from SEPP Housing 2021 PDF using PyMuPDF"""

import fitz  # PyMuPDF
import os

# Pages to extract based on provision references
PAGES_TO_EXTRACT = {
    35: 'provision_597_infill_affordable_parking',
    47: 'provision_765_seniors_independent_living_parking', 
    72: 'provision_1189_tod_affordable_parking'
}

def extract_pages(pdf_path, output_dir='sepp-housing-2021-pages'):
    """Extract specific pages from PDF as PNG images"""
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    print(f"Total pages: {len(doc)}")
    
    # Extract specific pages
    for page_num, filename in PAGES_TO_EXTRACT.items():
        print(f"\nExtracting page {page_num}...")
        
        # PyMuPDF uses 0-based indexing
        page = doc[page_num - 1]
        
        # Render page to image (zoom factor for quality)
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for good quality
        pix = page.get_pixmap(matrix=mat)
        
        output_path = os.path.join(output_dir, f'page-{page_num}_{filename}.png')
        pix.save(output_path)
        print(f"✓ Saved to {output_path}")
        
        # Get file size
        size_kb = os.path.getsize(output_path) / 1024
        print(f"  Size: {size_kb:.1f} KB")
    
    # Search for Schedule 10 in later pages
    print("\n\nSearching for Schedule 10 (Dictionary - Accessible Area definition)...")
    
    # Search for "accessible area means" in PDF text
    for page_num in range(100, min(120, len(doc))):
        page = doc[page_num]
        text = page.get_text()
        
        if 'accessible area means' in text.lower() or 'schedule 10' in text.lower():
            print(f"\n✓ Found on page {page_num + 1}!")
            
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            
            output_path = os.path.join(output_dir, f'page-{page_num + 1}_schedule_10_accessible_area.png')
            pix.save(output_path)
            print(f"✓ Saved to {output_path}")
            
            size_kb = os.path.getsize(output_path) / 1024
            print(f"  Size: {size_kb:.1f} KB")
            break
    
    doc.close()
    print("\n✓ All pages extracted!")
    print(f"\nFiles saved in: {output_dir}/")

if __name__ == '__main__':
    pdf_path = 'sepp_housing_2021.pdf'
    extract_pages(pdf_path)
