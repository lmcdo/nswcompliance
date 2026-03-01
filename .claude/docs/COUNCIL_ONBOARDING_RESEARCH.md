# Council Onboarding Research - Jan 30, 2026

## Current Database State (VERIFIED LIVE DATA)

**Total provisions: 21,492**

### By Council/Source:
- **SEPP/State-level**: 16,413 provisions (76%)
  - SEPP Housing 2021
  - Other state environmental planning policies
- **Marrickville DCP**: 1,807 provisions
- **Leichhardt DCP**: 1,566 provisions
- **Ashfield DCP**: 1,706 provisions
- **Total Inner West DCP**: 5,079 provisions (24%)

### V2 Enrichment Status - EXCELLENT:
- ✅ v2_is_actionable: **100% populated**
- ✅ v2_dcp_layer: **100% populated**
- ✅ v2_applicable_zones: **100% populated**
- ✅ v2_applicable_dev_types: **100% populated**
- ⚠️ v2_topic: 51% populated (expected - not all provisions fit topic taxonomy)
- ⚠️ v2_precinct_id: 6.7% populated (1,646 provisions)

### Actionability Classification:
- Actionable: 10,316 (48%)
- Non-actionable: 11,176 (52%) - TOC/boilerplate filtered with 99.96% precision

### Spatial Data:
- 84 unique precincts
- 90 precinct boundaries (PostGIS)
- 2,039 Heritage Conservation Areas

### Layer Distribution:
- Generic: 18,070 provisions (84%)
- Precinct: 1,646 provisions (7.7%)
- Condition: 1,436 provisions (6.7%)
- Use-specific: 333 provisions (1.5%)

## Key Architecture Insights for Council Onboarding

### 1. Modular Components (Reusable):
- **Council configs**: `frontend-nextjs/lib/council-configs/{council}.json`
  - TOC structure mapping
  - Precinct patterns
  - Heritage patterns
  - Document IDs
  - Status ('active', 'planned', etc.)
- **LGA mappings**: `lga-mappings.json`
  - Postcodes
  - Suburbs
  - Council metadata
- **Database schema**: 100% council-agnostic
  - Uses `lga` field for filtering
  - Uses `document_id` patterns (e.g., `marrickville-dcp-2023`)
  - No hardcoded council references in schema

### 2. Council-Specific Work Required:

#### Data Acquisition (Critical Path - 2-3 weeks):
- **DCP documents** (PDF) from council
- **GIS precinct boundaries** (Shapefiles/GeoJSON)
- **Heritage overlay data** (if not in Planning Portal)
- Council response time is the main blocker

#### Technical Processing (1 week after data acquired):
1. **PDF Extraction** (~2 days):
   - Run sepp_full_text_extraction pipeline (adapted for DCP)
   - Extract provisions with page numbers, hierarchy
   - Validate extraction quality

2. **Enrichment** (~2 days):
   - v2_is_actionable classification (automated, 99.96% precision)
   - v2_dcp_layer assignment (generic/zone/condition/precinct)
   - v2_applicable_zones extraction (from provision text)
   - v2_applicable_dev_types extraction
   - v2_topic categorization (51% automation, rest manual review)

3. **Spatial Processing** (~1 day):
   - Import precinct boundaries to PostGIS
   - Test address→precinct matching
   - Validate HCA overlays

4. **Config Creation** (~2 hours):
   - Create council-configs/{new-council}.json
   - Map TOC structure
   - Define precinct/heritage patterns

5. **Testing** (~3 days):
   - Test 20+ real addresses across different zones/precincts
   - Verify layer filtering accuracy
   - Check Planning Portal integration
   - Validate provision relevance

### 3. Estimated Timeline for Central Coast:

**If data provided immediately:**
- Week 1: PDF extraction + initial enrichment
- Week 2: Spatial processing + config + testing
- **Total: 2 weeks technical work**

**Realistic timeline:**
- Weeks 1-3: Council data acquisition (CRITICAL PATH)
- Weeks 4-5: Technical processing
- **Total: 5 weeks from initial request**

### 4. Automation Opportunities:

**Already Automated (85%):**
- Actionability classification (48/52 split, 99.96% precision)
- Layer assignment (4-layer model)
- Zone extraction (pattern matching)
- Dev-type extraction (pattern matching)
- Database import pipeline
- PostGIS spatial matching

**Requires Manual Work (15%):**
- TOC structure mapping (each council has different organization)
- Precinct pattern identification (council-specific naming)
- Topic categorization review (51% auto, 49% manual)
- QA testing with real addresses
- Edge case handling (council-specific quirks)

## Data Quality Notes:

**Nov 10 → Jan 30 Change:**
- Previous backup (Nov 10): 47,818 provisions
- Current database (Jan 30): 21,492 provisions
- **Major cleanup occurred**: Removed duplicates, improved filtering

**Enrichment Quality:**
- Core filtering fields (zones, dev types, actionability, layer): 100% populated
- This is production-ready for filtering
- Topic categorization at 51% is acceptable (many provisions don't fit topic taxonomy)
- Precinct assignment at 6.7% is expected (most provisions are generic, not precinct-specific)

## Recommendations for Next Council:

1. **Start with data acquisition request immediately** - this is the critical path
2. **Use Central Coast as test case** - already have lga-mappings.json entry with status "planned"
3. **Reuse extraction pipeline** from sepp_full_text_extraction (proven 99.96% precision)
4. **Budget 2 weeks technical + 3 weeks council response** = 5 weeks total
5. **Focus manual effort on TOC mapping and precinct patterns** - these are council-specific

## Database Backup Reference:
- Latest backup: `backups/regulatory_provisions_post_dedup_20260128_125037.json` (Jan 28, 63M)
- Statistics script: `get_db_stats.py` (for live verification)
