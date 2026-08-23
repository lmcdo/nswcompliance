#!/usr/bin/env python3
"""
Generate PDF page images for definition sources.

Creates high-resolution page images for DCP definition sections
to enable source verification in the UI.

Uses PyMuPDF (fitz) at 2x zoom following the existing pattern.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
IMAGE_OUTPUT = PROJECT_ROOT / "frontend-nextjs" / "public" / "images" / "definitions"

# PDF sources for definitions
PDF_SOURCES = {
    "marrickville": {
        "pdf_path": OUTPUT_DIR / "Marrickville DCP 2011 - 10.0 Definitions" / "Marrickville DCP 2011 - 10.0 Definitions_origin.pdf",
        "image_prefix": "marrickville_dcp_definitions",
        "pages": None,  # Extract all pages
    },
    "leichhardt": {
        "pdf_path": OUTPUT_DIR / "Leichhardt DCP 2013 - 13 - Appendix A Glossary - with IWLEP 2022 amendments" / "Leichhardt DCP 2013 - 13 - Appendix A Glossary - with IWLEP 2022 amendments_origin.pdf",
        "image_prefix": "leichhardt_dcp_definitions",
        "pages": None,
    },
    "ashfield": {
        "pdf_path": OUTPUT_DIR / "Inner West Ashfield DCP 2016 - Chapter G - Definitions - with IWLEP 2022 amendments" / "Inner West Ashfield DCP 2016 - Chapter G - Definitions - with IWLEP 2022 amendments_origin.pdf",
        "image_prefix": "ashfield_dcp_definitions",
        "pages": None,
    },
}

# R2 CDN base URL for production
R2_CDN_BASE = "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev"


def extract_page_image(
    pdf_path: Path,
    page_num: int,
    output_path: Path,
    zoom: float = 2.0
) -> Optional[int]:
    """
    Extract a single page as a PNG image.

    Args:
        pdf_path: Path to PDF file
        page_num: 1-indexed page number
        output_path: Path to save PNG
        zoom: Zoom factor (2.0 = 2x resolution)

    Returns:
        File size in bytes, or None if failed
    """
    try:
        doc = fitz.open(pdf_path)

        if page_num > len(doc) or page_num < 1:
            doc.close()
            return None

        page = doc[page_num - 1]  # 0-indexed

        # Render at specified zoom
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        # Save image
        pix.save(str(output_path))

        file_size = output_path.stat().st_size
        doc.close()

        return file_size

    except Exception as e:
        print(f"    [ERROR] Page {page_num}: {e}")
        return None


def extract_all_pages(source_key: str, source_config: dict) -> dict:
    """
    Extract all pages from a PDF as images.

    Returns:
        Dict mapping page numbers to image paths/URLs
    """
    pdf_path = source_config["pdf_path"]
    prefix = source_config["image_prefix"]

    if not pdf_path.exists():
        print(f"  [SKIP] PDF not found: {pdf_path}")
        return {}

    print(f"  Processing: {pdf_path.name}")

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    print(f"  Total pages: {total_pages}")

    page_images = {}
    total_size = 0

    for page_num in range(1, total_pages + 1):
        filename = f"{prefix}_page_{page_num}.png"
        output_path = IMAGE_OUTPUT / filename

        # Skip if already exists
        if output_path.exists():
            page_images[page_num] = {
                "local_path": str(output_path),
                "relative_url": f"/images/definitions/{filename}",
                "cdn_url": f"{R2_CDN_BASE}/pdf-pages/definitions/{filename}",
            }
            continue

        file_size = extract_page_image(pdf_path, page_num, output_path)

        if file_size:
            total_size += file_size
            page_images[page_num] = {
                "local_path": str(output_path),
                "relative_url": f"/images/definitions/{filename}",
                "cdn_url": f"{R2_CDN_BASE}/pdf-pages/definitions/{filename}",
            }

            if page_num % 5 == 0:
                print(f"    Extracted page {page_num}/{total_pages}")

    print(f"  Extracted {len(page_images)} pages ({total_size / 1024 / 1024:.1f} MB)")

    return page_images


def get_page_image_url(
    source_key: str,
    page_num: int,
    use_cdn: bool = True
) -> Optional[str]:
    """
    Get the URL for a specific page image.

    Args:
        source_key: DCP source key (marrickville, leichhardt, ashfield)
        page_num: 1-indexed page number
        use_cdn: If True, return CDN URL; otherwise return local relative URL

    Returns:
        URL string or None if source not found
    """
    if source_key not in PDF_SOURCES:
        return None

    prefix = PDF_SOURCES[source_key]["image_prefix"]
    filename = f"{prefix}_page_{page_num}.png"

    if use_cdn:
        return f"{R2_CDN_BASE}/pdf-pages/definitions/{filename}"
    else:
        return f"/images/definitions/{filename}"


def main():
    """Generate all definition page images."""
    print("=" * 70)
    print("GENERATE DEFINITION PAGE IMAGES")
    print("=" * 70)
    print()

    # Create output directory
    IMAGE_OUTPUT.mkdir(parents=True, exist_ok=True)

    all_page_images = {}
    total_pages = 0
    total_size_mb = 0

    for source_key, source_config in PDF_SOURCES.items():
        print(f"Source: {source_key}")
        page_images = extract_all_pages(source_key, source_config)
        all_page_images[source_key] = page_images
        total_pages += len(page_images)
        print()

    # Calculate total size
    for path in IMAGE_OUTPUT.glob("*.png"):
        total_size_mb += path.stat().st_size / 1024 / 1024

    print("=" * 70)
    print("COMPLETE")
    print("=" * 70)
    print(f"Total pages extracted: {total_pages}")
    print(f"Total size: {total_size_mb:.1f} MB")
    print(f"Output directory: {IMAGE_OUTPUT}")
    print()
    print("Note: For production, upload to R2 CDN:")
    print(f"  rclone sync {IMAGE_OUTPUT} r2:compliance-engine/pdf-pages/definitions/")
    print("=" * 70)

    return all_page_images


if __name__ == "__main__":
    main()
