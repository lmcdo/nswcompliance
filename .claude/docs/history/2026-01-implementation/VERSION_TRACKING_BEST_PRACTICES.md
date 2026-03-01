# Version Tracking Best Practices

## Overview
Version tracking displays regulation year, amendment info, and staleness warnings on ALL provisions (SEPP/LEP/DCP) to meet certifier compliance requirements.

## Data Sources & Solutions

### 1. DCP Provisions (Database)
**Source:** PostgreSQL `documents` table joined with `regulatory_provisions_canonical`

**Implementation:**
- ✅ Query joins with `documents` table to fetch version metadata
- ✅ Extracts: `regulation_year`, `amendment_reference`, `amendment_date`, `last_verified_date`
- ✅ Calculates: `days_since_verified`, `staleness_level` (current/caution/stale)

**Location:**
- `frontend-nextjs/app/api/compliance/constraints/route.ts` (lines 146-194)

### 2. SEPP Provisions (Planning API)
**Source:** NSW Planning Portal API → Special Provisions layer

**Challenge:** Planning API doesn't use database, so no join with `documents` table

**CRITICAL DISTINCTION:** Planning API data is **LIVE and CURRENT** (retrieved today from NSW Government). Therefore:
- `last_verified_date` = **TODAY** (not Currency Date!)
- `days_since_verified` = **0**
- `staleness_level` = **'current'** (always)

**Solution:** Extract version data from Planning API fields:
```typescript
Planning API fields → Version Metadata
{
  'Currency Date': '1-10-2023',      → amendment_date (when NSW amended it)
  'Commenced Date': '1-10-2023',     → amendment_date (fallback)
  'Published Date': '29-8-2022',     → (reference only)
  'Amendment': 'Amendment No 11',     → amendment_reference
  'EPI Name': 'SEPP (Sustainable Buildings) 2022' → regulation_year (extract 2022)

  // Calculated fields:
  last_verified_date: new Date()     → TODAY (we just queried the API)
  days_since_verified: 0             → Just verified
  staleness_level: 'current'         → Always current for live API
}
```

**Implementation:**
- ✅ Created utility: `lib/version-metadata-utils.ts`
- ✅ Function: `extractVersionFromPlanningAPI(layerResult)`
- ✅ Used in: `components/compliance/ComplianceDashboard.tsx` (lines 166, 221, 260)

### 3. LEP Provisions (Planning API)
**Source:** NSW Planning Portal API → Height/FSR layers

**Solution:** Same as SEPP - extract from Planning API fields

**Implementation:**
- ✅ Height constraints: Extract from `Height of Buildings Map` layer (line 221)
- ✅ FSR constraints: Extract from `Floor Space Ratio Map` layer (line 260)

## UI Display

### Version Badge Component
**Component:** `ProvisionVersionInline` (`components/compliance/ProvisionVersionBadge.tsx`)

**Visual Design:**
- ✅ Colored badge with icon
- ✅ Green (current) = ≤30 days
- ⚠️ Yellow (caution) = 31-60 days
- 🚨 Red (stale) = >60 days

**Display:**
```
✓ 2022                          (current)
⚠️ 2011 • Verify (45d)          (caution)
🚨 2009 • Stale (90d)           (stale)
```

## Best Practices Summary

### ✅ DO:
1. **Always join with `documents` table** for database provisions (DCP)
2. **Use TODAY as last_verified_date** for Planning API data (SEPP/LEP) - it's live!
3. **Extract amendment info** from Planning API (Currency Date, Amendment field)
4. **Calculate staleness ONLY for database provisions** (>60 days = stale)
5. **Display prominently** with colored badges
6. **Consistent format** across all authority levels (SEPP/LEP/DCP)

### ❌ DON'T:
1. **Don't skip version metadata** - certifiers need this for legal compliance
2. **Don't use Currency Date as last_verified_date** for Planning API - that's when NSW amended it, not when we verified it!
3. **Don't mark live API data as stale** - Planning Portal data is current by definition
4. **Don't use plain text** - badges must be visually distinct
5. **Don't hide staleness warnings** on database provisions - legal liability risk

### 🚨 CRITICAL: Planning API vs Database Data

**Planning API (SEPP/LEP):**
- Data source: Live NSW Government API (queried today)
- Last verified: TODAY (always)
- Staleness: CURRENT (always)
- Amendment date: From Currency Date field (for reference)

**Database (DCP):**
- Data source: PostgreSQL (imported at some point in the past)
- Last verified: From `documents.last_verified_date`
- Staleness: Calculate from last_verified_date (>60 days = stale)
- Amendment date: From `documents.amendment_date`

## Utility Functions

### `extractVersionFromPlanningAPI()`
**Purpose:** Convert Planning API layer results to version metadata format

**Input:**
```typescript
{
  'Commenced Date': '22-11-2024',
  'Currency Date': '22-11-2024',
  'EPI Name': 'Inner West Local Environmental Plan 2022',
  'Amendment': 'Amendment No 13'
}
```

**Output:**
```typescript
{
  regulation_year: 2022,
  amendment_reference: 'Amendment No 13',
  amendment_date: '2024-11-22T00:00:00.000Z',
  version_status: 'amended',
  last_verified_date: '2024-11-22T00:00:00.000Z',
  days_since_verified: 1,
  staleness_level: 'current'
}
```

### `extractYearFromName()`
**Purpose:** Extract year from regulation name

**Examples:**
- "SEPP (Sustainable Buildings) 2022" → 2022
- "Marrickville DCP 2011" → 2011
- "Inner West LEP 2022" → 2022

## Testing Checklist

When adding version tracking to new provision types:

- [ ] Database provisions have `documents` table join
- [ ] Planning API provisions extract Currency/Commenced dates
- [ ] Version metadata added to `provisions` array in constraint
- [ ] Badge displays correctly in UI
- [ ] Staleness warnings appear for >60 day old provisions
- [ ] All three authority levels (SEPP/LEP/DCP) show badges

## Files Modified

### Core Implementation
- `frontend-nextjs/lib/version-metadata-utils.ts` - NEW utility functions
- `frontend-nextjs/app/api/compliance/constraints/route.ts` - Database query updates
- `frontend-nextjs/components/compliance/ComplianceDashboard.tsx` - Planning API extraction
- `frontend-nextjs/components/compliance/ProvisionVersionBadge.tsx` - Enhanced badge display

### Supporting Files
- `frontend-nextjs/types/provision-search.ts` - Type definitions
- `migrations/add_version_tracking.sql` - Database schema

## Legal Compliance Note

**CRITICAL:** Version tracking is required for certifier legal compliance. Displaying outdated provisions without warning creates liability risk. Always show:

1. **Regulation year** - When the regulation was enacted
2. **Last verified date** - When the data was last updated
3. **Staleness warnings** - Alert for provisions >60 days old

Certifiers must independently verify provisions before issuing certificates. Version badges provide transparency and protect against liability.
