# LEP Schedule 5 Database Fields - Required for Option C Implementation

**Date:** 2025-11-02
**Purpose:** Define exact LEP data fields needed for heritage enrichment UI

---

## Database Table: `regulatory_provisions`

### Current Status:
- **Existing Schema:** ✅ Complete (35+ columns)
- **Existing Inner West LEP Schedule 5:** ❌ Only 1 provision (pages 1-50)
- **Required:** ~50-100 full Schedule 5 heritage items

### Required Fields for Each Heritage Item:

| Field | Value | Example | Required | Notes |
|-------|-------|---------|----------|-------|
| `document_id` | Document identifier | `Inner_West_Local_Environmental_Plan_2022` | ✅ | Must match existing LEP document |
| `provision_type` | Provision category | `lep_heritage` | ✅ | For filtering heritage provisions |
| `ref_number` | Legislative reference | `Schedule 5, Item 127` | ✅ | Used for API lookups |
| `section_header` | Heritage area name | `Heritage Conservation Area C27` | ✅ | Matches HCA table h_name |
| `provision_text` | Full significance statement | `The area contains predominantly Federation...` | ✅ | Core enrichment content |
| `provision_category` | Heritage type | `Heritage Conservation Area` or `Heritage Item` | ✅ | For categorization |
| `page_number` | LEP page reference | `Schedule 5` | ⚠️ | Optional but useful |
| `is_mandatory` | Whether protection is mandatory | `true` | ⚠️ | Optional |
| `created_at` | Extraction timestamp | `2025-11-02 15:30:00` | ✅ | Auto-generated |
| `extraction_method` | How extracted | `mineru_lep_schedule5` | ✅ | For traceability |

---

## Data Flow: LEP to UI

### Step 1: User views heritage requirement
```
User property: 40 Lackey Street, Marrickville
DCP requirement: "Retain original façade" (category: heritage)
Heritage context in DCP: Empty ❌
```

### Step 2: API enrichment request
```typescript
POST /api/heritage/enrich
{
  "address": "40 Lackey Street, Marrickville",
  "coordinates": { "lat": -33.9111, "lon": 151.1543 },
  "formerCouncil": "Marrickville",
  "requirementCategory": "heritage"
}
```

### Step 3: Database queries

**Query 1 - Find HCA at property:**
```sql
SELECT h_name, lga_name
FROM heritage_conservation_areas
WHERE bbox_min_x <= 151.1543 AND bbox_max_x >= 151.1543
  AND bbox_min_y <= -33.9111 AND bbox_max_y >= -33.9111
LIMIT 1;
```
**Result:** `h_name = "Marrickville Heritage Conservation Area M12"`

**Query 2 - Find LEP provision for HCA:**
```sql
SELECT id, ref_number, section_header, provision_text
FROM regulatory_provisions
WHERE document_id = 'Inner_West_Local_Environmental_Plan_2022'
  AND provision_type = 'lep_heritage'
  AND (
    section_header ILIKE '%Marrickville Heritage Conservation Area M12%'
    OR provision_text ILIKE '%Marrickville Heritage Conservation Area M12%'
  )
LIMIT 1;
```
**Result:**
```json
{
  "id": 12345,
  "ref_number": "Schedule 5, Item 89",
  "section_header": "Marrickville Heritage Conservation Area M12",
  "provision_text": "The area comprises predominantly Federation and Inter-War residential buildings that demonstrate the historical development of Marrickville as a working-class suburb established in the 1880s. The area is significant for its intact streetscapes and characteristic building forms including decorative brickwork, tiled roofs, and original timber joinery."
}
```

### Step 4: API response to UI
```json
{
  "success": true,
  "enrichment": {
    "source": "LEP Schedule 5",
    "hca_name": "Marrickville Heritage Conservation Area M12",
    "significance": "The area comprises predominantly Federation and Inter-War residential buildings...",
    "significance_level": "Local",
    "legislative_clause": "Schedule 5, Item 89",
    "provisions": [
      {
        "id": 12345,
        "ref_number": "Schedule 5, Item 89",
        "section_header": "Marrickville Heritage Conservation Area M12",
        "provision_text": "[full text above]"
      }
    ]
  },
  "cache_ttl": 604800
}
```

### Step 5: UI renders enrichment
```tsx
<HeritageEnrichmentCard>
  <Badge>Heritage Context from LEP Schedule 5</Badge>
  <p className="text-sm">
    {enrichment.significance}
  </p>
  <Link href={`/lep/schedule-5/${enrichment.legislative_clause}`}>
    View full LEP provision →
  </Link>
</HeritageEnrichmentCard>
```

---

## Extraction Requirements

### Source Document:
- **File:** `docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation.pdf`
- **Section:** Schedule 5 - Environmental Heritage
- **Expected items:** 50-100 heritage conservation areas + heritage items
- **Former councils:** Marrickville, Ashfield, Leichhardt (now Inner West)

### Extraction Logic:

**Pattern 1 - Heritage Conservation Area:**
```
Schedule 5, Item 27
Ashfield Heritage Conservation Area C27

The area contains predominantly Federation and Inter-War buildings that demonstrate the historical development of Ashfield as a residential suburb established along the railway line in the 1890s. Significant elements include:
- Original building fabric (brick, tile roofs, timber joinery)
- Intact streetscapes with consistent building scale
- Front gardens and low boundary fences
- Street trees and landscaping
```

**Extracted as:**
```python
{
    "document_id": "Inner_West_Local_Environmental_Plan_2022",
    "provision_type": "lep_heritage",
    "ref_number": "Schedule 5, Item 27",
    "section_header": "Ashfield Heritage Conservation Area C27",
    "provision_text": "The area contains predominantly Federation and Inter-War buildings...",
    "provision_category": "Heritage Conservation Area",
    "extraction_method": "mineru_lep_schedule5",
    "created_at": "2025-11-02 15:30:00"
}
```

**Pattern 2 - Individual Heritage Item:**
```
Schedule 5, Item 142
Annandale House and grounds, 12 Johnston Street, Annandale

Georgian revival mansion built 1885, designed by architect XYZ. Significant for association with early colonial development and architectural merit.
```

**Extracted as:**
```python
{
    "document_id": "Inner_West_Local_Environmental_Plan_2022",
    "provision_type": "lep_heritage",
    "ref_number": "Schedule 5, Item 142",
    "section_header": "Annandale House and grounds",
    "provision_text": "Georgian revival mansion built 1885...",
    "provision_category": "Heritage Item",
    "extraction_method": "mineru_lep_schedule5",
    "created_at": "2025-11-02 15:30:00"
}
```

---

## Matching Logic: HCA to LEP

### Challenge:
HCA table `h_name` may not exactly match LEP `section_header`.

**Examples:**
- HCA: `"Balmain East Heritage Conservation Area"`
- LEP: `"Schedule 5, Item 45 - Balmain East HCA"`

### Solution: Fuzzy matching
```python
def find_lep_for_hca(hca_name, conn):
    # Try exact match first
    result = query(f"section_header = '{hca_name}'")
    if result:
        return result

    # Try ILIKE match
    result = query(f"section_header ILIKE '%{hca_name}%'")
    if result:
        return result

    # Try provision_text match
    result = query(f"provision_text ILIKE '%{hca_name}%'")
    if result:
        return result

    # Fall back to manual mapping table
    return manual_mapping.get(hca_name)
```

---

## Success Criteria

### Extraction Quality:
- ✅ Extract 50-100 heritage items (all Schedule 5)
- ✅ 100% have `ref_number` (Schedule 5, Item X)
- ✅ 100% have `section_header` (HCA/item name)
- ✅ >80% have significance text >100 chars
- ✅ All categorized (Conservation Area vs Heritage Item)

### Matching Quality:
- ✅ >80% HCA names match LEP provisions
- ✅ <20% require fuzzy matching
- ✅ <5% require manual mapping

### API Performance:
- ✅ Response time <500ms (P95)
- ✅ Cache hit rate >70% after 1 week
- ✅ Error rate <1%

---

## Implementation Checklist

### Phase 1: Extraction (4-6 hours)
- [ ] Extract Schedule 5 from LEP PDF using MinerU
- [ ] Parse into structured JSON with fields above
- [ ] Verify extraction quality (>80% complete text)
- [ ] Import to `regulatory_provisions` table
- [ ] Verify import (SELECT COUNT should show 50-100)

### Phase 2: Matching (2-3 hours)
- [ ] Test HCA name matching with sample properties
- [ ] Implement fuzzy matching logic
- [ ] Create manual mapping table for edge cases
- [ ] Verify >80% match rate

### Phase 3: API (4-6 hours)
- [ ] Implement `/api/heritage/enrich` endpoint
- [ ] Add caching (Redis or in-memory)
- [ ] Test with sample addresses
- [ ] Verify performance (<500ms)

### Phase 4: UI (2-3 hours)
- [ ] Create `HeritageEnrichmentCard` component
- [ ] Integrate with `GeneralDCPSection`
- [ ] Test with Ashfield/Leichhardt addresses
- [ ] Verify enrichment displays correctly

**Total: 12-18 hours**

---

## Ready to Execute

All implementation plans are prepared:
1. ✅ **This document** - Field requirements
2. ✅ `LEP_ENRICHMENT_OPTION_C_IMPLEMENTATION.md` - Full implementation guide
3. ✅ `LEP_ENRICHMENT_FEASIBILITY_FINAL_ANSWER.md` - Feasibility assessment
4. ✅ `COUNCIL_PROFILES_INTEGRATION_STRATEGY.md` - UI integration plan

**Next step:** Create `extract_lep_schedule5.py` and begin Phase 1.
