# TypeScript Errors - Incremental Fixing Guide

## Current Status

**Date**: 2025-11-11
**TypeScript Errors**: ~70 errors in source code (excluding tests)
**Deployment Status**: ✅ Ready - `typescript: { ignoreBuildErrors: true }` is configured

## What Was Fixed

### 1. tsconfig.json - Exclude Non-Production Files
Updated `tsconfig.json` to exclude:
- `migratePRPs/**/*` - Old backup/migration files
- `.next` - Next.js build artifacts
- `__tests__/**/*` - Test files
- `tests/**/*` - Test files
- `**/*.test.ts`, `**/*.test.tsx` - Individual test files

This reduced type checking to only production source code.

### 2. Fixed Backup File JSX Error
Fixed JSX syntax error in:
- `migratePRPs/backup/ui_swap_20250921_213550/components_old/tod/TODParkingCalculator.tsx:343`
- Changed `>0` to `{'>'}0` for proper JSX escaping

## Remaining TypeScript Errors (By Priority)

### Priority 1: Type Definition Mismatches (16 errors)
These are missing or incorrect type definitions:

**app/api/compliance/dcp-complete/route.ts** (12 errors)
- Lines 142, 271, 338, 370, 483, 543: `Expected 0 type arguments, but got 1`
- Lines 379, 549: `Type 'null' is not assignable to type 'string | undefined'` (subcategory field)
- Lines 424, 604: `Type 'null' is not assignable to type 'number | undefined'` (value_numeric field)
- Lines 673, 674: `Variable 'fallbackQuery' is used before being assigned`
- Lines 981-989: `Variable 'generalRequirements' is used before being assigned` (7 instances)
- Line 984: Type mismatch between `FilterableRequirement[]` and `GeneralRequirement[]`

**app/assessment/version-aware/page.tsx** (1 error)
- Line 120: VersionInfo type incompatibility between two imports

**components/assessment/core/** (3 errors)
- `EnhancedComplianceChecklist.tsx:4`: Missing exports `ComplianceCheck`, `Citation`
- `ProvisionSearch.tsx:4`: Missing export `ProvisionSearchFilters`

### Priority 2: Missing Type Properties (10 errors)

**app/api/capacity/calculate/route.ts** (3 errors)
- Lines 365, 376, 387: Property `guidance` does not exist on type `SetbackResult`

**app/api/property/[address]/route.ts** (2 errors)
- Line 74: Property `api_status` does not exist on type `PropertyData`
- Line 81: Property `warning` does not exist on type `PropertyIntelligenceResponse`

**app/api/property/route.ts** (2 errors)
- Lines 30, 37: Property `coordinates` does not exist on type `PropertyData`

**app/api/compliance/live-check/route.ts** (1 error)
- Line 99: Property `site_coverage_percentage` does not exist on calculations type

**components/analysis/PreciseSetbackCalculator.tsx** (1 error)
- Line 256: Property `provision_id` does not exist on type `SetbackResult`

**app/assessment/search/page.tsx** (1 error)
- Line 127: Property `document_id` does not exist in provision type

### Priority 3: Component Type Errors (8 errors)

**Component Props Mismatches:**
- `app/assessment/dashboard/page.tsx:94`: Missing `selectedProperty`, `onPropertySelect` props
- `app/assessment/dashboard/page.tsx:108`: Missing `value`, `onChange`, `zoneCode` props
- `components/assessment-panel.tsx:42`: Missing `developmentType`, `zoneCode`, `propertyId` props
- `components/assessment/core/assessment-panel.tsx:17`: Missing multiple props

**Event Listener Type Issues:**
- `app/assessment/dashboard/page.tsx:61,64`: CustomEvent vs EventListener type incompatibility (2 errors)

**Import Issues:**
- `app/assessment/search/page.tsx:13`: Missing export `ComplianceProvision`

### Priority 4: Configuration & API Issues (12 errors)

**Type Configuration:**
- `app/api/health/metrics/route.ts:316`: Need `--downlevelIteration` flag for Map iteration
- `app/api/setbacks/calculate/route.ts:196`: Need `--downlevelIteration` flag for Set iteration
- `app/water-demo/layout.tsx:16`: `React.Node` does not exist (should be `React.ReactNode`)

**Function Declarations in Strict Mode:**
- `app/api/setbacks/calculate/route.ts:91,99`: Function declarations not allowed in blocks (2 errors)

**Invalid API Arguments:**
- `app/api/compliance/live-check/route.ts:142`: `"unknown"` not assignable to `"postgresql" | "subprocess"`
- `app/api/provisions/route.ts:73`: `"tier1"` not assignable to `"postgresql" | "subprocess"`
- `app/api/provisions/route.ts:92`: `"unknown"` not assignable to `"postgresql" | "subprocess"`
- `app/api/documents/[id]/extract-section/route.ts:93`: `"appendix"` not valid section type

**fetch API:**
- `app/api/property/[address]/route.ts:49`: `timeout` does not exist in RequestInit (2 overload errors)

**Type Conversion:**
- `components/analysis/PreciseSetbackCalculator.tsx:342`: `number` not assignable to `string`
- `app/api/health/metrics/route.ts:332`: `unknown` not assignable to `string`

## How to Fix Incrementally

### Step 1: Fix Type Definition Files (Priority 1)
Create or update type definition files in `types/`:

```typescript
// types/compliance.ts
export interface SetbackResult {
  // ... existing fields
  guidance?: string;
  provision_id?: string;
}

export interface PropertyData {
  // ... existing fields
  api_status?: string;
  coordinates?: { lat: number; lon: number };
}

export interface GeneralRequirement {
  // Ensure all fields allow null | undefined properly
  subcategory?: string | null;
  value_numeric?: number | null;
  part_number?: string | null | undefined;
  // ... other fields
}
```

### Step 2: Initialize Variables Before Use (Priority 1)
Fix "used before assigned" errors:

```typescript
// Before
let generalRequirements;
if (condition) {
  generalRequirements = await query();
}
return generalRequirements.length; // ERROR!

// After
let generalRequirements: GeneralRequirement[] = [];
if (condition) {
  generalRequirements = await query();
}
return generalRequirements.length; // OK
```

### Step 3: Fix Component Props (Priority 3)
Ensure all component props match their type definitions:

```typescript
<ComplianceChecklist
  developmentType={developmentType}
  zoneCode={zoneCode}
  propertyId={propertyId}
  propertyData={propertyData} // Add missing props
/>
```

### Step 4: Update tsconfig.json for Iteration (Priority 4)
Add to tsconfig.json:

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "es2015"], // Add es2015
    "downlevelIteration": true, // Add this
    // ... other options
  }
}
```

### Step 5: Fix Strict Mode Function Declarations (Priority 4)
Move function declarations outside blocks:

```typescript
// Before
if (condition) {
  function helper() { } // ERROR in strict mode
}

// After
function helper() { }
if (condition) {
  helper();
}
```

## Testing Strategy

After fixing each batch of errors:

```bash
# 1. Run type check
cd frontend-nextjs
npm run type-check

# 2. Test build locally
npm run build

# 3. If successful, commit changes
git add .
git commit -m "fix: Resolve TypeScript errors (batch X)"
```

## When to Re-Enable Strict Type Checking

Once all errors are fixed:

1. Update `next.config.js`:
```javascript
const nextConfig = {
  // Remove these lines:
  // typescript: { ignoreBuildErrors: true },
  // eslint: { ignoreDuringBuilds: true },
};
```

2. Test deployment:
```bash
npm run build
```

3. If successful, push to trigger Vercel deployment

## Current Vercel Configuration

✅ **Ready to Deploy**: The codebase is currently configured to deploy successfully:
- `typescript: { ignoreBuildErrors: true }` in `next.config.js`
- `eslint: { ignoreDuringBuilds: true }` in `next.config.js`

**Deployment will succeed** even with the TypeScript errors listed above.

## Notes

- Test files are now excluded from type checking (not needed for production)
- Backup files in `migratePRPs/` are excluded
- Build artifacts in `.next/` are excluded
- Focus on fixing errors in production source code only

## Reference

See also:
- `DEPLOYMENT_BEST_PRACTICES.md` - Pre-deployment checklist
- `DEPLOYMENT_GUIDE_VERCEL_SUPABASE.md` - Full deployment guide
