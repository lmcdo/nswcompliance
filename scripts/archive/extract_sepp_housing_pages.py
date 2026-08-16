#!/usr/bin/env python
"""Extract specific pages from SEPP Housing 2021 PDF and convert to PNG"""

from pdf2image import convert_from_path
import os

# Pages to extract based on provision references
PAGES_TO_EXTRACT = {
    35: 'provision_597_infill_affordable_parking',
    47: 'provision_765_seniors_independent_living_parking', 
    72: 'provision_1189_tod_affordable_parking'
}

# Find Schedule 10 (Dictionary) - typically near end of PDF
# We'll extract it separately after checking total pages

def extract_pages(pdf_path, output_dir='sepp-housing-2021-pages'):
    """Extract specific pages from PDF as PNG images"""
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"Extracting pages from {pdf_path}...")
    
    # Extract specific pages
    for page_num, filename in PAGES_TO_EXTRACT.items():
        print(f"\nExtracting page {page_num}...")
        
        # pdf2image uses 1-based indexing
        images = convert_from_path(
            pdf_path,
            first_page=page_num,
            last_page=page_num,
            dpi=150  # Good quality for web display
        )
        
        if images:
            output_path = os.path.join(output_dir, f'page-{page_num}_{filename}.png')
            images[0].save(output_path, 'PNG')
            print(f"✓ Saved to {output_path}")
            
            # Get file size
            size_kb = os.path.getsize(output_path) / 1024
            print(f"  Size: {size_kb:.1f} KB")
    
    # Try to extract Schedule 10 (Dictionary) - usually near the end
    # Let's extract pages 100-110 range to find it
    print("\n\nSearching for Schedule 10 (Accessible Area Definition)...")
    print("Extracting pages 100-110 to find Dictionary section...")
    
    try:
        images = convert_from_path(
            pdf_path,
            first_page=100,
            last_page=110,
            dpi=150
        )
        
        for idx, img in enumerate(images):
            page_num = 100 + idx
            output_path = os.path.join(output_dir, f'page-{page_num}_schedule_10_check.png')
            img.save(output_path, 'PNG')
            print(f"✓ Saved page {page_num} to {output_path}")
            
    except Exception as e:
        print(f"Could not extract Schedule 10 range: {e}")
    
    print("\n✓ All pages extracted!")
    print(f"\nFiles saved in: {output_dir}/")

if __name__ == '__main__':
    pdf_path = 'sepp_housing_2021.pdf'
    extract_pages(pdf_path)
