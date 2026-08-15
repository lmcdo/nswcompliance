#!/usr/bin/env python3
"""
Extract SEPP PDF pages as PNG images for R2 upload

Usage:
    python scripts/extract-sepp-pdf-pages.py --pdf path/to/sepp.pdf --slug sepp-housing --output ./pdf-exports

Requirements:
    pip install pdf2image pillow

System Requirements:
    - poppler-utils (for pdf2image)
    - On Windows: Download poppler from https://github.com/oschwartz10612/poppler-windows/releases
"""

import argparse
import os
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image


def slugify_document_name(pdf_name: str) -> str:
    """
    Convert PDF name to URL-safe slug

    Examples:
        'State Environmental Planning Policy (Housing) 2021.pdf' -> 'sepp-housing-2021'
        'SEPP (Exempt and Complying Development Codes) 2008.pdf' -> 'sepp-exempt-complying-2008'
    """
    # Remove .pdf extension
    name = pdf_name.replace('.pdf', '').replace(' - NSW Legislation', '')

    # Extract year if present
    import re
    year_match = re.search(r'\b(20\d{2})\b', name)
    year = year_match.group(1) if year_match else ''

    # Extract SEPP type from parentheses
    type_match = re.search(r'\((.*?)\)', name)
    sepp_type = type_match.group(1) if type_match else name.replace('State Environmental Planning Policy', '').strip()

    # Clean and slugify
    slug = sepp_type.lower()
    slug = slug.replace(' and ', '-')
    slug = slug.replace(' ', '-')
    slug = re.sub(r'[^a-z0-9-]', '', slug)

    # Add year if present
    if year:
        slug = f"sepp-{slug}-{year}"
    else:
        slug = f"sepp-{slug}"

    return slug


def extract_pdf_pages(
    pdf_path: str,
    output_dir: str,
    document_slug: str = None,
    dpi: int = 150,
    quality: int = 85,
    pages_to_extract: list = None
):
    """
    Extract all or specific pages from a PDF as PNG images

    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save PNG images
        document_slug: URL-safe slug for the document (auto-generated if None)
        dpi: Resolution for image extraction (default 150 DPI = good quality, reasonable file size)
        quality: JPEG compression quality if converting to JPG (1-100)
        pages_to_extract: List of page numbers to extract (1-indexed). If None, extracts all pages.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Auto-generate slug if not provided
    if document_slug is None:
        document_slug = slugify_document_name(pdf_path.name)

    # Create output directory: output_dir/document_slug/
    output_path = Path(output_dir) / document_slug
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Extracting pages from: {pdf_path.name}")
    print(f"Output directory: {output_path}")
    print(f"Document slug: {document_slug}")
    print(f"Config: DPI: {dpi}, Quality: {quality}")

    if pages_to_extract:
        print(f"Extracting {len(pages_to_extract)} specific pages (actionable provisions only)")
    else:
        print(f"Extracting ALL pages")
    print()

    # Convert PDF to images (only specified pages if provided)
    print("Converting PDF to images...")

    if pages_to_extract:
        # Extract only specified pages
        images = []
        for page_num in sorted(pages_to_extract):
            # pdf2image uses 1-indexed page numbers
            page_images = convert_from_path(
                pdf_path,
                dpi=dpi,
                fmt='png',
                first_page=page_num,
                last_page=page_num
            )
            if page_images:
                images.append((page_num, page_images[0]))
    else:
        # Extract all pages
        all_images = convert_from_path(
            pdf_path,
            dpi=dpi,
            fmt='png'
        )
        images = [(i + 1, img) for i, img in enumerate(all_images)]

    total_pages = len(images)
    print(f"OK: Extracted {total_pages} pages\n")

    # Save each page
    for page_num, image in images:
        # Filename format: sepp-housing-2021_page_1.png
        filename = f"{document_slug}_page_{page_num}.png"
        filepath = output_path / filename

        # Optimize PNG (reduce file size)
        # Convert to RGB if necessary (some PDFs have RGBA)
        if image.mode == 'RGBA':
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
            image = background

        # Save as optimized PNG
        image.save(filepath, 'PNG', optimize=True)

        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"  Page {page_num:3d}/{total_pages}: {filename} ({file_size_mb:.2f} MB)")

    print(f"\nExtraction complete!")
    print(f"Total pages: {total_pages}")
    print(f"Files saved to: {output_path}")

    # Print R2 upload command
    print(f"\nNext step - Upload to R2:")
    print(f"   wrangler r2 object put plotdetect-pdfs/pdf-pages/{document_slug} --file={output_path} --recursive")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Extract SEPP PDF pages as PNG images (actionable pages only)',
        epilog='Example: node get-sepp-actionable-pages.js "Transport" | python extract-sepp-pdf-pages.py --pdf infra.pdf --pages-stdin'
    )
    parser.add_argument('--pdf', required=True, help='Path to SEPP PDF file')
    parser.add_argument('--slug', help='Document slug (auto-generated if not provided)')
    parser.add_argument('--output', default='./pdf-exports', help='Output directory (default: ./pdf-exports)')
    parser.add_argument('--dpi', type=int, default=150, help='Image DPI (default: 150)')
    parser.add_argument('--quality', type=int, default=85, help='Image quality 1-100 (default: 85)')
    parser.add_argument('--pages', help='Comma-separated list of page numbers (e.g., "1,5,10-15,20")')
    parser.add_argument('--pages-stdin', action='store_true', help='Read page numbers from stdin as JSON array')

    args = parser.parse_args()

    # Parse page numbers
    pages_to_extract = None

    if args.pages_stdin:
        # Read JSON array from stdin (skip non-JSON lines like dotenv output)
        import sys
        import json
        try:
            # Read all input
            input_text = sys.stdin.read()
            # Find the JSON array (starts with '[')
            json_start = input_text.find('[')
            if json_start == -1:
                raise ValueError("No JSON array found in input")
            json_text = input_text[json_start:]
            pages_to_extract = json.loads(json_text)
            print(f"Loaded {len(pages_to_extract)} pages from stdin", file=sys.stderr)
        except Exception as e:
            print(f"❌ Error reading pages from stdin: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.pages:
        # Parse comma-separated list with ranges
        pages_to_extract = []
        for part in args.pages.split(','):
            part = part.strip()
            if '-' in part:
                # Range: "10-15"
                start, end = map(int, part.split('-'))
                pages_to_extract.extend(range(start, end + 1))
            else:
                # Single page
                pages_to_extract.append(int(part))

    extract_pdf_pages(
        pdf_path=args.pdf,
        output_dir=args.output,
        document_slug=args.slug,
        dpi=args.dpi,
        quality=args.quality,
        pages_to_extract=pages_to_extract
    )


if __name__ == '__main__':
    main()
