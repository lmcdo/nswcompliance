# Provision Title Display - Generic Implementation

## Problem Solved

**Before:**
- Cards showed ugly machine-generated IDs:
  - `Provision_531`
  - `table_in_Marrickville_DCP_2011__4.1_Low_Density_Residential_Development_0`
- Inconsistent title formatting across components
- No fallback strategy for missing `section_header`

**After:**
- Clean, human-readable titles extracted from `document_id`
- Generic utility functions that work for ANY provision type
- Consistent display across all components

## Implementation

### 1. Created Generic Utility (`lib/provision-title-utils.ts`)

**Core Function:**
```typescript
getProvisionDisplayTitle(provision: ProvisionContent): string
```

**Priority Order:**
1. **`section_header`** (if exists and not empty) → Use directly
2. **Extract from `document_id`**:
   - `Marrickville_DCP_2011__4.1_Low_Density_Residential_Development`
   - → `"4.1 Low Density Residential Development"`
3. **Pattern matching on `ref_number`**:
   - `table_in_X` → "Section X - Table"
   - `Provision_123` → Use document section
   - `4.3` → "Clause 4.3"
4. **Fallback** → Cleaned `ref_number` or document section

**Helper Functions:**
- `extractSectionFromDocumentId()` - Extracts section after `__`
- `getProvisionShortTitle()` - Compact version (removes "Clause " prefix)
- `formatConstraintValue()` - Smart value formatting for cards
- `isMachineGeneratedId()` - Detects machine-generated IDs

### 2. Applied to Components

#### **LegalTextPanel** (Legal Text Slide-Out)
**File:** `frontend-nextjs/components/compliance/LegalTextPanel.tsx`

**Changed:**
```typescript
// Before: Complex inline parsing for specific cases
{provision.ref_number.startsWith('table_in_') ? (
  // 20 lines of inline parsing logic...
) : ...}

// After: Single utility call
{getProvisionDisplayTitle(provision)}
```

**Result:**
- `table_in_Marrickville_DCP_2011__4.1_Low_Density_Residential_Development_0`
- → `4.1 Low Density Residential Development - Table`

#### **ConstraintCard** (Constraint Display Cards)
**File:** `frontend-nextjs/components/compliance/ConstraintCard.tsx`

**Changed:**

1. **Card Title** (Main value display):
```typescript
// Uses formatConstraintValue() to extract clean titles from provision data
const formattedValue = formatConstraintValue(val, provision);
```

2. **Card Subtitle** (Clause line):
```typescript
// Hides machine-generated IDs like "Provision_531"
{constraint.type.charAt(0).toUpperCase() + constraint.type.slice(1)}
{!constraint.source.clause.match(/^[Pp]rovision_\d+$/) && (
  <> • {constraint.source.clause}</>
)}
```

**Result:**
- **Before**: `Setback • provision_531`
- **After**: `Setback` (clause hidden because it's a machine ID)

### 3. Extraction Logic

**Key Insight:** The `document_id` field contains the human-readable context:

```
Document ID Structure:
Marrickville_DCP_2011__4.1_Low_Density_Residential_Development
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                      Section name (after __)
```

**Extraction:**
```typescript
function extractSectionFromDocumentId(documentId: string): string | null {
  const match = documentId.match(/__(.+)$/);  // Get everything after "__"
  if (!match) return null;

  return match[1]
    .replace(/_/g, ' ')       // Replace underscores
    .replace(/\s+/g, ' ')     // Normalize spaces
    .trim();
}
```

**Examples:**
- `Marrickville_DCP_2011__4.1_Low_Density_Residential_Development`
  - → `"4.1 Low Density Residential Development"`

- `Leichhardt_DCP_2013__Part_C_Heritage`
  - → `"Part C Heritage"`

## Benefits

### ✅ Generic Solution
- Works for ANY provision type (tables, clauses, sections)
- Single source of truth for title extraction
- Easy to extend with new patterns

### ✅ Consistent Display
- Same logic across all components
- Predictable user experience
- Easier to maintain

### ✅ Fallback Strategy
```
1. section_header (if available)
   ↓
2. Extract from document_id
   ↓
3. Pattern match ref_number
   ↓
4. Clean ref_number
```

### ✅ Pattern Matching
Handles all these cases automatically:
- `Provision_531` → "4.1 Low Density Residential Development"
- `table_in_X` → "Section X - Table"
- `4.3` or `9.29.3` → "Clause 4.3"
- `Schedule_1` → "Schedule 1"

## Testing

**Refresh your browser and check:**

1. **LegalTextPanel** (slide-out):
   - Open "Full Text" for Marrickville DCP setback
   - Should show: `4.1 Low Density Residential Development - Table`
   - NOT: `table_in_Marrickville_DCP_2011__4.1_Low_Density_Residential_Development_0`

2. **ConstraintCard** (cards):
   - DCP setback card should show clean title
   - Subtitle should be: `Setback` (not `Setback • provision_531`)
   - Main value should show section name

## Files Modified

### Created:
- `frontend-nextjs/lib/provision-title-utils.ts` (NEW) - Generic utility functions

### Modified:
- `frontend-nextjs/components/compliance/LegalTextPanel.tsx`
  - Added import: `getProvisionDisplayTitle`
  - Replaced inline parsing with utility call (line 939)

- `frontend-nextjs/components/compliance/ConstraintCard.tsx`
  - Added import: `getProvisionShortTitle`, `formatConstraintValue`
  - Updated card title logic (line 325)
  - Updated card subtitle to hide machine IDs (line 359)

## Future Enhancements

If new provision patterns emerge, add to `getProvisionDisplayTitle()`:

```typescript
// Example: New pattern for figures
if (provision.ref_number.match(/^figure_in_/)) {
  return docSection ? `${docSection} - Figure` : 'Figure';
}
```

## Database Schema Reference

**Provision Fields Used:**
- `id` - Unique identifier
- `ref_number` - Clause/provision reference (may be machine-generated)
- `section_header` - Human-readable title (often empty)
- `document_id` - Contains section context after `__`
- `provision_text` - Full legal text

**Machine-Generated Patterns:**
- `Provision_123` - Generic provision ID
- `table_in_XXX` - Table provision
- Any other underscore-heavy pattern

**Clean Patterns:**
- `4.3` - LEP clause
- `9.29.3` - DCP clause
- `Schedule 1` - SEPP schedule

## Summary

This implementation provides a **generic, maintainable solution** for displaying provision titles across the entire application. Instead of hardcoding logic for specific cases, it uses a **priority-based extraction strategy** that works for any provision type.

The utility functions can be reused anywhere provisions are displayed, ensuring **consistency and reducing code duplication**.
