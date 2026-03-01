# LightRAG Processing Scope - FINAL
**Date:** 2025-10-23
**Purpose:** Actual scope based on complete database analysis

---

## Complete Scope Breakdown

### 1. Base DCP Sections (15 batches)

| LGA | Part 2 | Part 4.1 | Part 4.2 | Part 4.3 | Part 5 | Total |
|-----|--------|----------|----------|----------|--------|-------|
| Marrickville | ✅ | ✅ | ✅ | ✅ | ✅ | 5 |
| Ashfield | ✅ | ✅ | ✅ | ✅ | ✅ | 5 |
| Leichhardt | ✅ | ✅ | ✅ | ✅ | ✅ | 5 |
| **TOTAL** | **3** | **3** | **3** | **3** | **3** | **15** |

**Cost:** 15 batches × $0.05 = **$0.75**

---

### 2. Precinct Sections (By LGA)

#### Marrickville Precincts
**Status:** ✅ Already extracted to `dcp_precinct_provisions` table

```
Precinct count: 43 precincts
Documents: 102 Part 9 documents
Provisions: 299 provisions already extracted
Status: READY TO PROCESS WITH LIGHTRAG
```

**Cost:** 43 batches × $0.01 = **$0.43**

#### Ashfield Precincts
**Status:** ⚠️ NOT YET extracted to `dcp_precinct_provisions`

```
Precinct chapter: Chapter D - Precinct Guidelines
Documents: 2 documents in database
Status: NEED TO EXTRACT to dcp_precinct_provisions first
```

**Action needed:** Extract Ashfield Chapter D provisions before LightRAG processing

#### Leichhardt Precincts
**Status:** ⚠️ NOT YET extracted to `dcp_precinct_provisions`

```
Precinct chapter: Part G - Precinct Controls (Sections 1-13)
Documents: 10 documents in database
Status: NEED TO EXTRACT to dcp_precinct_provisions first
```

**Action needed:** Extract Leichhardt Part G provisions before LightRAG processing

---

## Processing Options

### Option A: Marrickville Only (Fastest)

**Scope:**
- 5 base sections (Marrickville Part 2, 4.1, 4.2, 4.3, 5)
- 43 precincts (Marrickville Part 9)
- **Total: 48 batches**

**Cost:** $0.25 (base) + $0.43 (precincts) = **$0.68**

**Timeline:** 1 week

**Coverage:** Inner West addresses in former Marrickville area

---

### Option B: All Base Sections + Marrickville Precincts

**Scope:**
- 15 base sections (all 3 LGAs × 5 sections)
- 43 precincts (Marrickville only)
- **Total: 58 batches**

**Cost:** $0.75 (base) + $0.43 (precincts) = **$1.18**

**Timeline:** 1.5 weeks

**Coverage:** All Inner West addresses, but only Marrickville gets precinct supplements

---

### Option C: Complete (Base + All Precincts)

**Scope:**
- 15 base sections (all 3 LGAs × 5 sections)
- 43 Marrickville precincts (ready)
- TBD Ashfield precincts (need extraction)
- TBD Leichhardt precincts (need extraction)

**Cost:** $0.75 (base) + ~$0.60 (all precincts) = **~$1.35**

**Timeline:** 2-3 weeks (includes extracting Ashfield/Leichhardt precincts)

**Coverage:** Complete coverage for all Inner West addresses

---

## Recommended Approach: **Option B**

### Why Option B?

1. **Fastest to value** (1.5 weeks vs 2-3 weeks)
2. **Covers all development types** (base sections for all LGAs)
3. **Most precincts covered** (Marrickville has 43 of the ~60 total precincts)
4. **Low cost** ($1.18 total)
5. **Can add Ashfield/Leichhardt precincts later** (incremental)

### What You Get:

✅ **Any address in Inner West:**
- Categorized base requirements (setbacks, parking, landscaping, etc.)
- From appropriate DCP sections (Part 2 + dev-type-specific)

✅ **Addresses in Marrickville precincts:**
- PLUS precinct-specific requirements
- Character controls, heritage, special provisions

⏳ **Addresses in Ashfield/Leichhardt precincts:**
- Base requirements only (for now)
- Precinct supplements added later

---

## Implementation Timeline (Option B)

### Week 1: Database + Processing

**Day 1-2:**
```sql
CREATE TABLE dcp_categorized_requirements (
  -- schema as per LIGHTRAG_IMPLEMENTATION_STREAMLINED.md
);
```

**Day 3-4:**
```python
# Process base sections
# 15 batches: Marrickville, Ashfield, Leichhardt (Part 2, 4.1, 4.2, 4.3, 5)
python process_dcp_with_lightrag.py
```

**Day 5-7:**
```python
# Process Marrickville precincts
# 43 batches from dcp_precinct_provisions table
python process_marrickville_precincts.py
```

### Week 2: API + UI

**Day 8-9:** Build API endpoint
**Day 10-11:** Build UI component
**Day 12:** Integration
**Day 13-14:** Testing

---

## Future: Add Ashfield/Leichhardt Precincts

**When ready:**

1. Extract Ashfield Chapter D to `dcp_precinct_provisions`
2. Extract Leichhardt Part G to `dcp_precinct_provisions`
3. Run LightRAG processing on new precincts (~20 batches, $0.20)
4. No API/UI changes needed - automatic

**Incremental cost:** ~$0.20
**Incremental time:** ~2 days

---

## Summary Table

| Option | Batches | Cost | Timeline | Coverage |
|--------|---------|------|----------|----------|
| **A: Marrickville** | 48 | $0.68 | 1 week | Marrickville only |
| **B: Base + Marr Precincts** | 58 | $1.18 | 1.5 weeks | All LGAs base + Marr precincts |
| **C: Complete** | ~75 | $1.35 | 2-3 weeks | Full coverage |

**Recommendation:** Start with Option B, add Ashfield/Leichhardt precincts incrementally later.

---

## Next Steps

**Ready to implement Option B?**

1. Create `dcp_categorized_requirements` table
2. Process 15 base sections (all LGAs)
3. Process 43 Marrickville precincts
4. Build API + UI
5. Ship in 1.5 weeks

**Or prefer different option?**
- Option A (faster, Marrickville only)
- Option C (complete, longer timeline)
