#!/bin/bash
# Batch extract all SEPP PDF pages and upload to R2

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PDF_DIR="$PROJECT_ROOT/docs/sepps"
OUTPUT_DIR="$PROJECT_ROOT/pdf-exports"

echo "🚀 SEPP PDF Page Extraction & R2 Upload"
echo "========================================"
echo "PDF Directory: $PDF_DIR"
echo "Output Directory: $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Counter
total_pdfs=0
total_pages=0

# Find all SEPP PDFs
while IFS= read -r pdf_path; do
    pdf_name=$(basename "$pdf_path")
    echo "📄 Processing: $pdf_name"

    # Extract pages
    python3 "$SCRIPT_DIR/extract-sepp-pdf-pages.py" \
        --pdf "$pdf_path" \
        --output "$OUTPUT_DIR" \
        --dpi 150

    ((total_pdfs++))
    echo ""
done < <(find "$PDF_DIR" -name "*.pdf" -type f)

echo "========================================"
echo "✅ Extraction Complete"
echo "   PDFs processed: $total_pdfs"
echo ""
echo "📤 Next Step: Upload to R2"
echo "   Run: wrangler r2 object put plotdetect-pdfs/pdf-pages --file=$OUTPUT_DIR --recursive"
echo ""
