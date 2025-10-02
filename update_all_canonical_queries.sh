#!/bin/bash
################################################################################
# Update ALL frontend queries to use regulatory_provisions_canonical view
################################################################################

cd "frontend-nextjs" || exit 1

echo "Updating all queries to use canonical view..."

# Files to update (remaining ones)
FILES=(
  "app/api/clause/[id]/route.ts"
  "app/api/provisions/[id]/complete/route.ts"
  "lib/database/client.ts"
)

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "  Updating: $file"

    # Replace FROM regulatory_provisions with FROM regulatory_provisions_canonical
    sed -i 's/FROM regulatory_provisions\b/FROM regulatory_provisions_canonical/g' "$file"

    # Replace JOIN regulatory_provisions with JOIN regulatory_provisions_canonical
    sed -i 's/JOIN regulatory_provisions\b/JOIN regulatory_provisions_canonical/g' "$file"

    echo "    ✓ Updated"
  else
    echo "    ⚠ File not found: $file"
  fi
done

echo ""
echo "Update complete!"
echo ""
echo "Files updated:"
echo "  - postgres-compliance-client.ts (manual)"
echo "  - app/api/compliance/constraints/route.ts (manual)"
echo "  - app/api/dcp/full-text/route.ts (manual)"
echo "  - app/api/clause/[id]/route.ts (script)"
echo "  - app/api/provisions/[id]/complete/route.ts (script)"
echo "  - lib/database/client.ts (script)"
echo ""
echo "Next steps:"
echo "  1. Test: npm run dev"
echo "  2. Verify no duplicates in UI"
echo "  3. Check console for any errors"
