#!/bin/bash
# Organize SEPP PDF page images for frontend
#
# Usage: ./organize-sepp-images.sh <source_dir> <sepp_type> <output_dir>
# Example: ./organize-sepp-images.sh ~/Downloads/STATEE_3 transport ../frontend-nextjs/public/pdf-pages

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SOURCE_DIR="$1"
SEPP_TYPE="$2"
OUTPUT_DIR="${3:-$PROJECT_ROOT/frontend-nextjs/public/pdf-pages}"

if [ -z "$SOURCE_DIR" ] || [ -z "$SEPP_TYPE" ]; then
  echo "Usage: $0 <source_dir> <sepp_type> [output_dir]"
  echo ""
  echo "SEPP types:"
  echo "  transport    - Transport & Infrastructure (262 pages)"
  echo "  biodiversity - Biodiversity & Conservation (72 pages)"
  echo "  housing      - Housing (110 pages)"
  echo ""
  echo "Example:"
  echo "  $0 ~/Downloads/STATEE_3 transport"
  exit 1
fi

# Determine SEPP slug and page list
case "$SEPP_TYPE" in
  transport)
    SLUG="sepp-transport-infrastructure-2021"
    PAGE_LIST="/tmp/transport-pages.json"
    SEPP_NAME="Transport & Infrastructure"
    ;;
  biodiversity)
    SLUG="sepp-biodiversity-conservation-2021"
    PAGE_LIST="/tmp/biodiversity-pages.json"
    SEPP_NAME="Biodiversity & Conservation"
    ;;
  housing)
    SLUG="sepp-housing-2021"
    PAGE_LIST="/tmp/housing-pages.json"
    SEPP_NAME="Housing"
    ;;
  *)
    echo "Error: Unknown SEPP type '$SEPP_TYPE'"
    echo "Valid types: transport, biodiversity, housing"
    exit 1
    ;;
esac

# Check if page list exists
if [ ! -f "$PAGE_LIST" ]; then
  echo "Error: Page list not found: $PAGE_LIST"
  echo "Run this first:"
  echo "  cd frontend-nextjs && node scripts/get-sepp-actionable-pages.js \"$SEPP_NAME\" > $PAGE_LIST"
  exit 1
fi

# Create output directory
OUTPUT_PATH="$OUTPUT_DIR/$SLUG"
mkdir -p "$OUTPUT_PATH"

echo "========================================="
echo "SEPP Image Organization"
echo "========================================="
echo "SEPP: $SEPP_NAME"
echo "Source: $SOURCE_DIR"
echo "Output: $OUTPUT_PATH"
echo "Slug: $SLUG"
echo ""

# Count source files
SOURCE_COUNT=$(find "$SOURCE_DIR" -maxdepth 1 \( -name "*.png" -o -name "*.jpg" -o -name "*.pdf" \) | wc -l)
echo "Source files: $SOURCE_COUNT"

# Parse actionable pages
ACTIONABLE_PAGES=$(cat "$PAGE_LIST" | python3 -c "import sys, json; print(' '.join(map(str, json.load(sys.stdin))))")
ACTIONABLE_COUNT=$(echo "$ACTIONABLE_PAGES" | wc -w)
echo "Actionable pages: $ACTIONABLE_COUNT"
echo ""

# Process each actionable page
echo "Processing images..."
COPIED=0
SKIPPED=0

for PAGE_NUM in $ACTIONABLE_PAGES; do
  # Look for source file (try multiple naming patterns)
  SOURCE_FILE=""

  # Try unpadded first (0.png, 1.png, 21.png)
  for EXT in png jpg pdf PNG JPG PDF; do
    if [ -f "$SOURCE_DIR/$PAGE_NUM.$EXT" ]; then
      SOURCE_FILE="$SOURCE_DIR/$PAGE_NUM.$EXT"
      break
    fi
  done

  # If not found, try 3-digit padded (001.png, 002.png, 021.png)
  if [ -z "$SOURCE_FILE" ]; then
    PADDED=$(printf "%03d" $PAGE_NUM)
    for EXT in png jpg pdf PNG JPG PDF; do
      if [ -f "$SOURCE_DIR/$PADDED.$EXT" ]; then
        SOURCE_FILE="$SOURCE_DIR/$PADDED.$EXT"
        break
      fi
    done
  fi

  if [ -z "$SOURCE_FILE" ]; then
    echo "  Page $PAGE_NUM: Source file not found"
    ((SKIPPED++))
    continue
  fi

  # Output filename: sepp-transport-infrastructure-2021_page_21.png
  OUTPUT_FILE="$OUTPUT_PATH/${SLUG}_page_${PAGE_NUM}.png"

  # Copy/convert file
  if [[ "$SOURCE_FILE" == *.pdf ]]; then
    # Convert PDF to PNG (requires ImageMagick)
    convert -density 150 "$SOURCE_FILE" "$OUTPUT_FILE" 2>/dev/null
    if [ $? -eq 0 ]; then
      echo "  ✓ Page $PAGE_NUM (converted from PDF)"
      ((COPIED++))
    else
      echo "  ✗ Page $PAGE_NUM (PDF conversion failed - install ImageMagick)"
      ((SKIPPED++))
    fi
  else
    # Copy PNG/JPG directly
    cp "$SOURCE_FILE" "$OUTPUT_FILE"
    echo "  ✓ Page $PAGE_NUM"
    ((COPIED++))
  fi
done

echo ""
echo "========================================="
echo "Summary"
echo "========================================="
echo "Copied: $COPIED files"
echo "Skipped: $SKIPPED files"
echo "Output: $OUTPUT_PATH"
echo ""
echo "File naming format: ${SLUG}_page_{number}.png"
echo ""

if [ $COPIED -gt 0 ]; then
  echo "✅ Success! Images are ready for frontend."
  echo ""
  echo "Next steps:"
  echo "1. Verify a few images opened correctly"
  echo "2. Deploy to production or upload to R2"
  exit 0
else
  echo "❌ No files were copied. Check source directory and file formats."
  exit 1
fi
