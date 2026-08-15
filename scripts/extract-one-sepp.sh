#!/bin/bash
# Extract a single SEPP using temp file to avoid pipe buffering issues

SEPP_NAME="$1"
PDF_PATH="$2"
SLUG="$3"

if [ -z "$SEPP_NAME" ] || [ -z "$PDF_PATH" ] || [ -z "$SLUG" ]; then
  echo "Usage: $0 <sepp_name> <pdf_path> <slug>"
  echo "Example: $0 'Transport' '/path/to/pdf.pdf' 'sepp-transport-2021'"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TEMP_PAGES="/tmp/sepp-pages-$$.json"

# Convert PDF_PATH to absolute if it's relative
if [[ "$PDF_PATH" != /* ]]; then
  PDF_PATH="$PROJECT_ROOT/$PDF_PATH"
fi

echo "📦 Extracting: $SEPP_NAME"
echo ""

# Step 1: Get actionable pages and save to temp file
cd "$PROJECT_ROOT/frontend-nextjs"
echo "📋 Fetching actionable pages from database..."
# Disable dotenv logging by setting DEBUG=false
DEBUG=false node scripts/get-sepp-actionable-pages.js "$SEPP_NAME" > "$TEMP_PAGES" 2>&1

# Extract just the JSON array line (filter out dotenv noise which also starts with '[')
# Use pattern that matches '[' followed by a digit to get only the JSON array
grep '^\[[0-9]' "$TEMP_PAGES" > "${TEMP_PAGES}.clean" || echo "ERROR: No JSON found in output"
mv "${TEMP_PAGES}.clean" "$TEMP_PAGES"

PAGE_COUNT=$(cat "$TEMP_PAGES" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "✅ Found $PAGE_COUNT actionable pages"
echo ""

# Step 2: Extract PDF pages
echo "🔄 Extracting PDF pages..."
cat "$TEMP_PAGES" | python3 "$SCRIPT_DIR/extract-sepp-pdf-pages.py" \
  --pdf "$PDF_PATH" \
  --slug "$SLUG" \
  --output "$PROJECT_ROOT/pdf-exports" \
  --pages-stdin \
  --dpi 150

# Cleanup
rm "$TEMP_PAGES"

echo ""
echo "✅ Extraction complete: $SLUG"
