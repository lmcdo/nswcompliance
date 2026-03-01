# LEP Enrichment Option C - Implementation Guide
**Hybrid Approach: HCA Table + LEP Schedule 5 Extraction**

**Status:** Ready for Implementation
**Estimated Time:** 10-15 hours total
**Priority:** High value for Ashfield/Leichhardt users

---

## Overview

**Goal:** Provide heritage context enrichment for properties in Ashfield and Leichhardt by cross-referencing HCA locations with LEP heritage significance statements.

**Approach:**
1. Extract LEP Schedule 5 (Heritage) from PDF
2. Fix spatial matching (bbox or geometry_json)
3. Implement `/api/heritage/enrich` endpoint
4. Integrate with GeneralDCPSection component

---

## Phase 1: LEP Schedule 5 Extraction (4-6 hours)

### Files Created:
- ✅ `extract_lep_schedule5.py` - Main extraction script
- ✅ `test_lep_extraction_quality.py` - Quality verification
- ✅ `import_lep_schedule5.py` - Database import

### Execution Steps:

```bash
# Step 1: Extract Schedule 5 from LEP PDF
python extract_lep_schedule5.py

# Step 2: Verify extraction quality
python test_lep_extraction_quality.py

# Step 3: Import to database
python import_lep_schedule5.py

# Expected output: ~50-100 heritage items imported
```

### What Gets Extracted:
- Heritage item/area name
- Heritage significance statement
- Location description
- Legislative clause (Schedule 5 Item X)
- Category (Conservation Area / Heritage Item)

---

## Phase 2: Spatial Matching Fix (2-3 hours)

### Files Created:
- ✅ `test_spatial_matching.py` - Diagnostic script
- ✅ `fix_bbox_coordinates.py` - Coordinate correction (if needed)
- ✅ `implement_json_point_in_polygon.py` - Fallback method

### Execution Steps:

```bash
# Step 1: Test current bbox matching
python test_spatial_matching.py

# Step 2A: If bbox broken, fix coordinates
python fix_bbox_coordinates.py

# Step 2B: If bbox unfixable, implement JSON method
python implement_json_point_in_polygon.py

# Step 3: Re-test matching
python test_spatial_matching.py
```

### Expected Outcome:
- Spatial query returns HCA for test Marrickville coordinate
- Match rate: >80% for Inner West properties

---

## Phase 3: Enrichment API Implementation (4-6 hours)

### Files Created:
- ✅ `frontend-nextjs/app/api/heritage/enrich/route.ts` - API endpoint
- ✅ `frontend-nextjs/lib/heritage-enrichment.ts` - Helper functions
- ✅ `test_heritage_enrichment_api.py` - API testing

### API Specification:

**Endpoint:** `POST /api/heritage/enrich`

**Request:**
```json
{
  "address": "40 Lackey Street, Marrickville",
  "coordinates": { "lat": -33.9111, "lon": 151.1543 },
  "formerCouncil": "Ashfield",
  "requirementCategory": "heritage"
}
```

**Response:**
```json
{
  "success": true,
  "enrichment": {
    "source": "LEP Schedule 5",
    "hca_name": "Ashfield Heritage Conservation Area C27",
    "significance": "The area contains predominantly Federation and Inter-War buildings that demonstrate the historical development of Ashfield as a residential suburb...",
    "significance_level": "Local",
    "legislative_clause": "Schedule 5, Item 127",
    "provisions": [
      {
        "id": 12345,
        "ref_number": "Schedule 5, Item 127",
        "section_header": "Heritage Conservation Area C27",
        "provision_text": "[full LEP text]"
      }
    ]
  },
  "cache_ttl": 604800
}
```

### Execution Steps:

```bash
# Step 1: Deploy API endpoint
# (Copy route.ts to correct location)

# Step 2: Test API
python test_heritage_enrichment_api.py

# Step 3: Verify caching works
# (Run test twice, second should be faster)
```

---

## Phase 4: UI Integration (2-3 hours)

### Files Modified:
- ✅ `frontend-nextjs/components/compliance/GeneralDCPSection.tsx`
- ✅ `frontend-nextjs/components/compliance/HeritageEnrichmentCard.tsx` (new)

### Integration Points:

**1. RequirementCard Enhancement:**
```typescript
{requirement.category === 'heritage' && !requirement.heritage_context && (
  <HeritageEnrichmentCard
    propertyAddress={propertyAddress}
    propertyCoordinates={propertyCoordinates}
    formerCouncil={formerCouncil}
  />
)}
```

**2. Display Logic:**
- Show enrichment automatically for heritage requirements
- Display "Heritage context from LEP Schedule 5" badge
- Link to full LEP text
- Cache enrichment results per property

---

## Implementation Checklist

### Pre-Implementation:
- [ ] Verify LEP PDF exists in `docs/lep/`
- [ ] Check database has `heritage_conservation_areas` table (2,039 rows)
- [ ] Confirm PostgreSQL version supports JSON functions

### Phase 1 (LEP Extraction):
- [ ] Run `extract_lep_schedule5.py`
- [ ] Verify extracted JSON structure
- [ ] Run quality check (>80% items have significance text)
- [ ] Import to `regulatory_provisions` table
- [ ] Verify import (SELECT COUNT from regulatory_provisions WHERE ref_number LIKE 'Schedule 5%')

### Phase 2 (Spatial Matching):
- [ ] Run `test_spatial_matching.py`
- [ ] If failing: run `fix_bbox_coordinates.py` OR `implement_json_point_in_polygon.py`
- [ ] Re-test matching with 10 known Inner West coordinates
- [ ] Verify >80% match rate

### Phase 3 (API):
- [ ] Copy `route.ts` to `frontend-nextjs/app/api/heritage/enrich/`
- [ ] Copy `heritage-enrichment.ts` to `frontend-nextjs/lib/`
- [ ] Restart Next.js dev server
- [ ] Test API with curl/Postman
- [ ] Verify caching (Redis or in-memory)

### Phase 4 (UI):
- [ ] Add enrichment hook to RequirementCard
- [ ] Create HeritageEnrichmentCard component
- [ ] Test with Ashfield address (heritage requirement)
- [ ] Test with Leichhardt address (heritage requirement)
- [ ] Verify enrichment displays correctly

### Testing:
- [ ] Test Ashfield heritage requirement (should show LEP enrichment)
- [ ] Test Marrickville heritage requirement (should show DCP context, no enrichment)
- [ ] Test Leichhardt heritage requirement (should show LEP enrichment)
- [ ] Performance test: <500ms API response time
- [ ] Cache test: Second request <50ms

---

## Rollback Plan

If implementation fails or performance is poor:

1. **Remove API endpoint:**
   ```bash
   rm frontend-nextjs/app/api/heritage/enrich/route.ts
   ```

2. **Remove UI integration:**
   - Revert changes to GeneralDCPSection.tsx
   - Remove HeritageEnrichmentCard component

3. **Keep extracted data:**
   - LEP Schedule 5 provisions remain in database
   - Can be used for future features

---

## Success Metrics

### Quantitative:
- [ ] LEP Schedule 5 extraction: 50-100 items with significance text
- [ ] Spatial matching: >80% success rate for Inner West properties
- [ ] API response time: <500ms (P95)
- [ ] Cache hit rate: >70% after 1 week
- [ ] Enrichment display: Works for 100% of Ashfield/Leichhardt heritage requirements

### Qualitative:
- [ ] User feedback: "Heritage context is helpful"
- [ ] User behavior: >40% click-through to full LEP text
- [ ] Error rate: <1% failed enrichment requests

---

## Next Steps

**Ready to execute in order:**

1. **Now:** Run Phase 1 (LEP Extraction)
   ```bash
   python extract_lep_schedule5.py
   ```

2. **After verification:** Run Phase 2 (Spatial Matching)
   ```bash
   python test_spatial_matching.py
   ```

3. **After spatial works:** Implement Phase 3 (API)
   - Copy files to correct locations
   - Test endpoint

4. **After API works:** Integrate Phase 4 (UI)
   - Update components
   - Test with real addresses

---

## Support & Troubleshooting

### Common Issues:

**Issue:** Bbox matching returns no results
- **Fix:** Run `implement_json_point_in_polygon.py` to use geometry_json instead

**Issue:** LEP extraction gets low-quality text
- **Fix:** Adjust MinerU confidence threshold or use manual extraction for critical items

**Issue:** API response too slow (>500ms)
- **Fix:** Implement Redis caching or add database indexes

**Issue:** HCA name doesn't match LEP provision text
- **Fix:** Implement fuzzy matching (Levenshtein distance) or manual mapping table

---

## Files Reference

All implementation files created in root directory:
- `extract_lep_schedule5.py`
- `test_lep_extraction_quality.py`
- `import_lep_schedule5.py`
- `test_spatial_matching.py`
- `fix_bbox_coordinates.py`
- `implement_json_point_in_polygon.py`
- `test_heritage_enrichment_api.py`

Frontend files:
- `frontend-nextjs/app/api/heritage/enrich/route.ts`
- `frontend-nextjs/lib/heritage-enrichment.ts`
- `frontend-nextjs/components/compliance/HeritageEnrichmentCard.tsx`
