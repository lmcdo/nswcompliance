#!/usr/bin/env python3
"""
Re-parse existing SEPP markdown files to extract page numbers
- Reads MD files from docs/sepps/extracted/
- Extracts page numbers from "## Page X" markers
- Outputs JSON with provision-to-page mappings
"""
import json
import re
from pathlib import Path
from collections import defaultdict

MD_DIR = Path("docs/sepps/extracted")
OUTPUT_FILE = "sepp_page_mappings.json"

def extract_page_mappings(md_file):
    """Extract provision text and their page numbers from markdown"""
    print(f"\nProcessing: {md_file.name}")

    content = md_file.read_text(encoding='utf-8')

    # Split by page markers
    page_pattern = r'^## Page (\d+)$'

    provisions_with_pages = []
    current_page = None

    lines = content.split('\n')
    provision_buffer = []

    for line in lines:
        # Check for page marker
        page_match = re.match(page_pattern, line)
        if page_match:
            # Save previous provision if exists
            if provision_buffer and current_page:
                provision_text = '\n'.join(provision_buffer).strip()
                if len(provision_text) > 50:  # Ignore headers/short text
                    provisions_with_pages.append({
                        'text_preview': provision_text[:200],
                        'full_text_hash': hash(provision_text),
                        'page': current_page,
                        'length': len(provision_text)
                    })

            current_page = int(page_match.group(1))
            provision_buffer = []
            continue

        # Add to buffer if we're on a page
        if current_page is not None:
            provision_buffer.append(line)

    # Save last provision
    if provision_buffer and current_page:
        provision_text = '\n'.join(provision_buffer).strip()
        if len(provision_text) > 50:
            provisions_with_pages.append({
                'text_preview': provision_text[:200],
                'full_text_hash': hash(provision_text),
                'page': current_page,
                'length': len(provision_text)
            })

    print(f"  Found {len(provisions_with_pages)} text blocks with page numbers")
    return provisions_with_pages

def main():
    print("="*60)
    print("SEPP PAGE NUMBER EXTRACTION")
    print("="*60)

    # Find all markdown files
    md_files = list(MD_DIR.glob("*.md"))
    print(f"\nFound {len(md_files)} markdown files")

    all_mappings = {}

    for md_file in md_files:
        # Skip metadata files
        if 'metadata' in md_file.name.lower():
            continue

        doc_name = md_file.stem
        mappings = extract_page_mappings(md_file)

        all_mappings[doc_name] = {
            'source_file': str(md_file),
            'total_text_blocks': len(mappings),
            'text_blocks': mappings
        }

    # Save results
    output_path = Path(OUTPUT_FILE)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(all_mappings, f, indent=2)

    print("\n" + "="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)

    total_blocks = sum(len(m['text_blocks']) for m in all_mappings.values())
    print(f"\nTotal documents: {len(all_mappings)}")
    print(f"Total text blocks with pages: {total_blocks}")
    print(f"Output: {OUTPUT_FILE}")

    # Show sample
    if all_mappings:
        first_doc = list(all_mappings.values())[0]
        if first_doc['text_blocks']:
            print("\n" + "="*60)
            print("SAMPLE")
            print("="*60)
            sample = first_doc['text_blocks'][0]
            print(f"Page: {sample['page']}")
            print(f"Length: {sample['length']} chars")
            print(f"Preview: {sample['text_preview']}...")

if __name__ == "__main__":
    main()
