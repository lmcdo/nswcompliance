#!/bin/bash
# Extract actionable pages from priority SEPPs (444 pages total)
# Transport & Infrastructure (262) + Biodiversity (72) + Housing (110)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/pdf-exports"
ARCHIVE_DIR="$PROJECT_ROOT/archive/2026-01-extraction-outputs/extraction_outputs/sepps"

echo "🚀 SEPP Priority Extraction - Actionable Pages Only"
echo "===================================================="
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# ============================================================
# 1. Transport & Infrastructure 2021 (262 actionable pages)
# ============================================================
echo "📦 1/3: Transport & Infrastructure SEPP"
echo "   Actionable pages: 262 (out of 289 total)"
echo ""

PDF_TRANSPORT="$ARCHIVE_DIR/State Environmental Planning Policy (Transport and Infrastructure) 2021 - NSW Legislation/auto/State Environmental Planning Policy (Transport and Infrastructure) 2021 - NSW Legislation_origin.pdf"

if [ -f "$PDF_TRANSPORT" ]; then
  cd "$PROJECT_ROOT/frontend-nextjs"
  node scripts/get-sepp-actionable-pages.js "Transport and Infrastructure" | \
    python3 "$SCRIPT_DIR/extract-sepp-pdf-pages.py" \
      --pdf "$PDF_TRANSPORT" \
      --slug "sepp-transport-infrastructure-2021" \
      --output "$OUTPUT_DIR" \
      --pages-stdin \
      --dpi 150
  cd "$PROJECT_ROOT"
  echo "✅ Transport & Infrastructure complete"
else
  echo "❌ PDF not found: $PDF_TRANSPORT"
fi

echo ""

# ============================================================
# 2. Biodiversity & Conservation 2021 (72 actionable pages)
# ============================================================
echo "📦 2/3: Biodiversity & Conservation SEPP"
echo "   Actionable pages: 72 (out of 109 total)"
echo ""

PDF_BIODIVERSITY="$ARCHIVE_DIR/State Environmental Planning Policy (Biodiversity and Conservation) 2021 - NSW Legislation/auto/State Environmental Planning Policy (Biodiversity and Conservation) 2021 - NSW Legislation_origin.pdf"

if [ -f "$PDF_BIODIVERSITY" ]; then
  cd "$PROJECT_ROOT/frontend-nextjs"
  node scripts/get-sepp-actionable-pages.js "Biodiversity" | \
    python3 "$SCRIPT_DIR/extract-sepp-pdf-pages.py" \
      --pdf "$PDF_BIODIVERSITY" \
      --slug "sepp-biodiversity-conservation-2021" \
      --output "$OUTPUT_DIR" \
      --pages-stdin \
      --dpi 150
  cd "$PROJECT_ROOT"
  echo "✅ Biodiversity & Conservation complete"
else
  echo "❌ PDF not found: $PDF_BIODIVERSITY"
fi

echo ""

# ============================================================
# 3. Housing 2021 (110 actionable pages)
# ============================================================
echo "📦 3/3: Housing SEPP"
echo "   Actionable pages: 110 total"
echo ""

PDF_HOUSING="$ARCHIVE_DIR/State Environmental Planning Policy (Housing) 2021 - NSW Legislation/auto/State Environmental Planning Policy (Housing) 2021 - NSW Legislation_origin.pdf"

if [ -f "$PDF_HOUSING" ]; then
  cd "$PROJECT_ROOT/frontend-nextjs"
  node scripts/get-sepp-actionable-pages.js "Housing" | \
    python3 "$SCRIPT_DIR/extract-sepp-pdf-pages.py" \
      --pdf "$PDF_HOUSING" \
      --slug "sepp-housing-2021" \
      --output "$OUTPUT_DIR" \
      --pages-stdin \
      --dpi 150
  cd "$PROJECT_ROOT"
  echo "✅ Housing complete"
else
  echo "❌ PDF not found: $PDF_HOUSING"
fi

echo ""
echo "===================================================="
echo "✅ Priority SEPP Extraction Complete"
echo ""
echo "📊 Summary:"
echo "   Transport & Infrastructure: 262 pages"
echo "   Biodiversity & Conservation: 72 pages"
echo "   Housing: 110 pages"
echo "   Total: 444 actionable pages extracted"
echo ""
echo "📁 Output directory: $OUTPUT_DIR"
echo ""
echo "📤 Next Step: Copy to frontend public folder"
echo "   cp -r $OUTPUT_DIR/* frontend-nextjs/public/pdf-pages/"
echo ""
echo "📤 Or upload to R2:"
echo "   wrangler r2 object put plotdetect-pdfs/pdf-pages --file=$OUTPUT_DIR --recursive"
echo ""
