# Exempt & Complying Codes - Complete Diagnosis

**Date:** 2025-10-01
**Context:** Analyzing current codebase to determine what's needed for exempt/complying workflow

---

## Executive Summary

**Database Status:** ✅ Canonical system working (Phase 1/2A complete)
- 20,111 canonical provisions (88.8%)
- 2,537 duplicates marked (11.2%)
- 2,198 canonical exempt/complying provisions exist

**Workflow Status:** ⚠️ **PARTIALLY FUNCTIONAL** with 1 critical issue

**Critical Issue:** 522 orphaned controls (11.6%) point to non-canonical provisions

**Frontend Status:** ✅ UI correctly displays exempt/complying badges

---

## Current Database State

### 1. Provisions
```
Total provisions:        22,648
├─ Canonical:           20,111 (88.8%)
└─ Duplicates:           2,537 (11.2%)

Exempt/Complying SEPP:
├─ Total:                2,223
└─ Canonical:            2,198 (1% duplicates)
```

**Finding:** Canonical system is working. Duplicates properly marked.

### 2. Development Permissions
```
Total permissions:         246
├─ permitted:              97
├─ consent:                78
├─ prohibited:             46
├─ complying:              23
└─ exempt:                  2
```

**Finding:** Only 25 total exempt/complying records. This is expected - most zones default to standard LEP permissibility.

**Sample Permissions:**
- R2 + general → complying
- R2 + complying_development → complying
- B1 + general → complying
- E3 + general → exempt

### 3. Development Controls
```
Total controls:          4,508
├─ Linked to canonical:  3,986 (88.4%)
└─ Orphaned (point to duplicates): 522 (11.6%)  ⚠️ ISSUE
```

**Finding:** 522 controls point to non-canonical provisions. When API queries use `regulatory_provisions_canonical` view, these controls appear orphaned.

**Examples of Orphaned Controls:**
- ID 93: Setback control → points to provision 228 (duplicate of 219)
- ID 119: Setback control → points to provision 838 (duplicate of 586)
- ID 189: Setback control → points to provision 6450 (duplicate of 6353)

### 4. Zone Coverage
```
Top zones by provision count:
R2:    9,567 provisions
C1:    1,404
E2:    1,345
B1:      741
C2:      651
```

**Finding:** Good coverage across residential, commercial, environmental zones.

### 5. Development Type Coverage
```
Top development types:
complying_development:    272 provisions
development_application:  255
apartment:                180
multi_dwelling:            69
commercial:                64
dwelling_house:            21
```

**Finding:** Provisions are tagged with development_type field. This enables filtering.

---

## Frontend Architecture

### User Flow (ComplianceDashboard.tsx)

```
User enters: Property Address
             ↓
System extracts: Zone (e.g., "R2"), LGA (e.g., "Inner West")
             ↓
User selects: Development Type (e.g., "dwelling_house")
             ↓
Frontend calls: /api/compliance/constraints
             ↓
API queries: development_permissions + regulatory_provisions + development_controls
             ↓
Returns: permission_status + constraints
             ↓
Frontend displays:
├─ Permission Status Badge (green/blue/orange)
│  ├─ Exempt (green) - "No DA required if standards met"
│  ├─ Complying (blue) - "CDC pathway available"
│  └─ Consent Required (orange) - "Full DA required"
└─ Compliance Constraints (SEPP/LEP/DCP hierarchy)
```

**Finding:** Frontend architecture is correct. Badges implemented (lines 574-617 of ComplianceDashboard.tsx).

---

## API Logic (route.ts)

### Permission Determination Logic

```typescript
Step 1: Check LEP base permissibility
  Query: development_permissions WHERE zone = X AND development_type = Y
  Result: permitted | prohibited | consent

Step 2: If permitted, check SEPP exempt/complying
  Query: development_permissions WHERE source_type LIKE '%exempt%'
  Result: exempt | complying | (none)

Step 3: Determine final status
  If prohibited → "consent_required"
  If permitted + SEPP exempt → "exempt"
  If permitted + SEPP complying → "complying"
  If permitted + no SEPP → "consent_required"
  If no LEP data → "consent_required" (conservative default)
```

**Finding:** API logic is architecturally correct. It properly cascades from LEP→SEPP.

### Development Type Normalization (lines 179-186)

```typescript
const DEV_TYPE_NORMALIZER = {
  'secondary_dwelling': 'dwelling_house',
  'multi_dwelling': 'multi_dwelling_housing',
  'shop_top_housing': 'business_premises',
  'residential_flat': 'residential_flat_building',
  'child_care': 'information_and_education_facility',
  'commercial': 'business_premises'
};
```

**Finding:** API normalizes UI terms to database/LEP terminology. This is correct.

---

## End-to-End Workflow Test

### Test Case: R2 Zone + dwelling_house

**Results:**
```
LEP Base Permission:     permitted (source: nsw_standard)
SEPP Status:            complying (source: SEPP_Exempt_Complying_2008)
Final Status:           complying ✅
Provisions Found:       10 provisions
Controls Attached:      3 controls (access, parking, vegetation)
```

**Workflow Status:** ✅ WORKS

**However:** Most provisions show "0 controls" - this is expected for complying development (prescriptive standards in provision_text, not extracted as discrete controls).

---

## Critical Issue: 522 Orphaned Controls

### The Problem

```sql
-- Example:
provision 228 (Building setbacks):
  is_canonical: FALSE
  canonical_provision_id: 219

development_controls.control_id = 93:
  provision_id: '228'

-- When API queries canonical view:
SELECT * FROM regulatory_provisions_canonical rp
JOIN development_controls dc ON dc.provision_id = rp.id::text

-- Result: Provision 228 filtered out (not canonical)
-- Control 93 appears orphaned (no matching provision)
```

### Impact

| Affected | Count | Impact |
|----------|-------|--------|
| Orphaned controls | 522 | Missing from UI |
| Control types | setback, height, FSR, vegetation, signage | Incomplete compliance data |
| Properties affected | ~11.6% | Partial controls shown |

**User sees:** Provision text but missing numeric controls (setbacks, heights, etc.)

---

## What's Missing / What's Needed

### ✅ Already Working

1. **Canonical system:** Duplicates properly marked with `is_canonical` flag
2. **Database schema:** Phase 1/2A migrations complete
3. **Frontend UI:** Permission status badges implemented
4. **API logic:** Proper LEP→SEPP cascade
5. **Data quality:** 2,198 exempt/complying provisions exist
6. **Development type normalization:** UI terms map to database terms

### ⚠️ Needs Fixing

**Issue #1: Orphaned Controls (CRITICAL)**

**Fix:** Update foreign keys to point to canonical provisions

```sql
-- Phase 2.5 Migration (15 minutes)
UPDATE development_controls dc
SET provision_id = rp_canonical.id::text
FROM regulatory_provisions rp_dup
JOIN regulatory_provisions rp_canonical
  ON rp_canonical.id = rp_dup.canonical_provision_id
WHERE dc.provision_id = rp_dup.id::text
  AND rp_dup.is_canonical = FALSE
  AND rp_dup.canonical_provision_id IS NOT NULL;

-- Expected: Update 522 controls
```

**Risk:** 2/10 (safe, reversible with backup)
**Impact:** HIGH - Fixes 11.6% of controls immediately

### Optional Enhancements

**Enhancement #1: More Exempt/Complying Permissions**

Current state: Only 25 exempt/complying permissions in database.

Options:
- Extract more from SEPP Exempt & Complying Codes 2008 PDFs
- Add specific development types (deck, fence, shed, etc.)
- Currently defaults to "general" for most zones

Impact: LOW - Current permissions work for common cases (dwelling_house, general development)

**Enhancement #2: Control Extraction**

Current state: Most exempt/complying provisions have 0 controls attached.

Reason: Complying development has prescriptive standards in provision_text (not extracted as discrete numeric controls).

Example provision text:
```
"Clause 3C.11(4): Minimum side setback is 900mm for lots <15m width,
1200mm for lots 15-18m, 1500mm for lots >18m"
```

This is already in the provision text - extraction to discrete controls is optional.

Impact: LOW - Users can read standards in full text

---

## Architectural Assessment

### Is the Architecture Sound? **YES**

**Strengths:**
1. ✅ Canonical flag pattern (industry best practice for soft-delete/deduplication)
2. ✅ LEP→SEPP cascade logic (architecturally correct)
3. ✅ Separation of concerns: provisions vs controls vs permissions
4. ✅ Frontend displays hierarchy (SEPP → LEP → DCP)
5. ✅ Development type normalization handles UI vs database terminology

**Weaknesses:**
1. ❌ Foreign keys not updated when canonical system introduced
2. ⚠️ No referential integrity constraints (allows orphaned controls)
3. ⚠️ No unique constraint on canonical provisions (allows duplicate canonicals)

**Overall:** 8/10 - Good architecture with one implementation gap

---

## Recommended Actions

### Priority 1: Fix Orphaned Controls (NOW)

**What:** Run Phase 2.5 migration to update foreign keys
**Why:** Fixes 522 orphaned controls (11.6% of all controls)
**Risk:** 2/10 (safe with backup)
**Time:** 15 minutes
**Impact:** HIGH - Restores full compliance data display

### Priority 2: Add Referential Integrity (AFTER Priority 1)

**What:** Add proper foreign key constraints
**Why:** Prevents future orphaned controls
**Risk:** 5/10 (schema change)
**Time:** 30 minutes
**Impact:** MEDIUM - Future-proofing

### Priority 3: Optional Enhancements (LATER)

**What:** Extract more exempt/complying permissions
**Why:** Expand coverage beyond "general" development
**Risk:** 3/10 (data quality depends on extraction)
**Time:** 2-4 hours
**Impact:** LOW-MEDIUM - Nice to have, not critical

---

## Testing Checklist

After fixing orphaned controls, verify:

```sql
-- Test 1: No orphaned controls
SELECT COUNT(*)
FROM development_controls dc
WHERE dc.provision_id IN (
    SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
);
-- Expected: 0

-- Test 2: All controls join to canonical view
SELECT
    COUNT(DISTINCT rp.id) as provisions_with_controls,
    COUNT(*) as total_controls
FROM regulatory_provisions_canonical rp
JOIN development_controls dc ON dc.provision_id = rp.id::text;
-- Expected: 4,508 controls matched

-- Test 3: Exempt/complying workflow
SELECT
    zone,
    development_type,
    permission_status
FROM development_permissions
WHERE zone = 'R2' AND development_type = 'dwelling_house';
-- Expected: complying
```

Frontend test:
1. Navigate to property in R2 zone
2. Select "Dwelling House" development type
3. Verify blue "Complying Development" badge shows
4. Verify setback/height controls display
5. Click "View Details" on controls - verify provision text loads

---

## Conclusion

**Current State:**
- ✅ Canonical system functional (duplicates fixed)
- ✅ Frontend UI implemented
- ✅ API logic correct
- ⚠️ 522 orphaned controls (11.6%)

**Recommended Fix:**
Run Phase 2.5 migration (15 minutes) to update foreign keys to canonical provisions.

**After Fix:**
System will be fully functional for exempt/complying code workflow. Optional enhancements can be added later as needed.

**Priority:** HIGH - Fix orphaned controls now to restore full functionality.
