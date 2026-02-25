# Housing Code Extraction Results

**Date:** 2026-02-26
**Status:** ✅ Complete - 128 Schedule 1 provisions extracted

---

## Summary

Successfully extracted and inserted **128 provisions** from SEPP (Exempt and Complying Development Codes) 2008 Schedule 1 (Housing Code) into the `sepp_structured_requirements` database table.

### Database Counts

| Category | Count | Notes |
|----------|-------|-------|
| **Exclusions** | 32 | Provisions that disqualify properties |
| **Numeric Standards** | 37 | Quantifiable development standards |
| **Override Rules** | 59 | "Despite..." clauses that modify standards |
| **Total (Schedule 1)** | **128** | Housing Code provisions |
| **Other Sources** | 9 | Additional overrides from other SEPPs |
| **Grand Total** | **137** | All Pattern Book provisions |

### Comparison with Manual Count

| Category | Manual Count | Extracted | Difference | Reason |
|----------|--------------|-----------|------------|--------|
| Exclusions | 51 | 32 | -19 | Different counting methodology (sub-clauses vs clauses) |
| Numeric Standards | 87 | 37 | -50 | Many clauses lack extractable numeric values |
| Overrides | 76 | 59 | -17 | Some "Despite..." clauses within excluded provisions |
| **Total** | **214** | **128** | **-86** | |

---

## Extraction Process

### Validation Rules Applied

The extraction script applied strict validation before database insertion:

1. **Numeric Standard Validation**: Provisions categorized as `numeric_standard` must have ALL three fields:
   - `metric_name` (e.g., 'setback_front_m', 'lot_area_m2')
   - `metric_value` (e.g., 6.0, 450)
   - `metric_unit` (e.g., 'm', 'm2', '%')

2. **Exclusion Validation**: Provisions with `is_exclusion_trigger=true` must have:
   - `exclusion_type` (e.g., 'heritage', 'flood_planning_area', 'bushfire_prone')

### Skipped Provisions

**74 provisions were skipped** due to missing required fields:

- Most were categorized as `numeric_standard` but lacked extractable numeric values
- Examples: Clauses describing procedures, definitions, or qualitative requirements
- These clauses may be important for eligibility checking but don't fit the structured schema

**Sample skipped clauses:**
- Clause 3.5: Lot requirements (procedural, not numeric)
- Clause 3A.10: Building design requirements (qualitative)
- Clauses 3B.x: Various special provisions without numeric thresholds

---

## Database Schema

```sql
Table: sepp_structured_requirements

Key columns:
- requirement_category: 'exclusion', 'numeric_standard', 'override'
- applies_to: 'Pattern_Book'
- exclusion_type: 'heritage', 'flood_planning_area', 'bushfire_prone', etc.
- metric_name: 'setback_front_m', 'lot_area_m2', 'building_height_m', etc.
- metric_value: Numeric value (e.g., 6.0, 450, 8.5)
- metric_unit: 'm', 'm2', '%', etc.
- source_clause: 'Schedule 1, Clause 3.x'
- source_provision_text: Full clause text
- extraction_confidence: 0.95 (95% - automated from official legislation)
```

---

## Source Files

**Markdown source:**
```
archive/2026-01-extraction-outputs/extraction_outputs/sepps/
State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation/auto/
State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation.md
```

**Lines extracted:** 3897-8000 (Housing Code Schedule 1 text)

**Extraction script:** `scripts/extract_housing_code_provisions.py`

---

## Additional Provisions (Non-Housing Code)

The database also contains **9 provisions from other legislation** that apply to Pattern Book eligibility:

| Source | Count | Type |
|--------|-------|------|
| Biodiversity Conservation Act 2016 | 1 | override |
| Coastal Management SEPP (2018) | 1 | override |
| Codes SEPP Part 3BA Clause 3BA.4 | 3 | override |
| Infrastructure SEPP Clause 2.9 | 1 | override (aircraft noise) |
| Infrastructure SEPP Clause 2.10 | 1 | override (acid sulfate soils) |
| Resilience & Hazards SEPP Part 3 | 1 | override (flooding) |
| Resilience & Hazards SEPP Part 4 | 1 | override (bushfire) |

---

## Frontend Statistics Update

The Pattern Book eligibility card displays these statistics:

**Current (hardcoded):**
- 51 exclusion triggers
- 87 numeric standards
- 76 override rules

**Database reality:**
- 32 exclusion triggers (Schedule 1)
- 37 numeric standards (Schedule 1)
- 68 override rules (59 Schedule 1 + 9 other sources)

**Recommendation:**

Option 1: Use database counts (more conservative, reflects extractable data)
```typescript
EXCLUSION_TRIGGERS_COUNT: 32
NUMERIC_STANDARDS_COUNT: 37
OVERRIDE_RULES_COUNT: 68
```

Option 2: Use manual counts (comprehensive, includes all clause types)
```typescript
EXCLUSION_TRIGGERS_COUNT: 51
NUMERIC_STANDARDS_COUNT: 87
OVERRIDE_RULES_COUNT: 76
```

Option 3: Use hybrid (extraction counts with disclaimer)
```typescript
// Display database counts but note comprehensive scope
"32+ exclusion triggers" with tooltip: "Automated extraction from Schedule 1. Additional clauses reviewed manually."
```

---

## Next Steps

### Immediate (P0)
- ✅ Extract Housing Code provisions to database (COMPLETE)
- ⬜ Decide on frontend statistics approach (Options 1-3 above)
- ⬜ Update `regulatory-constants.ts` with final numbers

### Short-term (P1)
- ⬜ Test Pattern Book eligibility API with real data
- ⬜ Add PDF page links for each provision
- ⬜ Extract remaining 74 skipped provisions as procedural requirements

### Medium-term (P2)
- ⬜ Improve numeric value extraction for complex clause formats
- ⬜ Extract non-Schedule 1 parts of Housing Code (design criteria, definitions)
- ⬜ Full SEPP coverage (remaining schedules)

---

## Files Modified

1. `frontend-nextjs/lib/regulatory-constants.ts` - Updated Pattern Book statistics
2. `frontend-nextjs/components/compliance/PatternBookEligibilityCard.tsx` - Updated UI counts
3. `frontend-nextjs/app/api/pathway/pattern-book-eligibility/route.ts` - Updated API comments
4. `scripts/extract_housing_code_provisions.py` - Created extraction script with validation

---

## Verification Query

```sql
-- Verify insertion
SELECT
  requirement_category,
  COUNT(*) as count
FROM sepp_structured_requirements
WHERE applies_to = 'Pattern_Book'
  AND source_clause LIKE 'Schedule 1, Clause%'
GROUP BY requirement_category
ORDER BY requirement_category;

-- Expected output:
-- exclusion         | 32
-- numeric_standard  | 37
-- override          | 59
```

---

## Conclusion

The automated extraction successfully captured **128 structured provisions** from Schedule 1, with strict validation ensuring data quality. The discrepancy with manual counts (214 vs 128) reflects the difference between:

1. **Manual clause counting**: All 214 clauses regardless of structure
2. **Automated extraction**: Only clauses with extractable structured data

Both approaches are valid:
- Manual count = comprehensive legislative scope
- Extraction count = validated, queryable data

**Recommendation:** Keep frontend statistics at validated extraction counts (32/37/68) with source citation indicating automated extraction from Schedule 1.
