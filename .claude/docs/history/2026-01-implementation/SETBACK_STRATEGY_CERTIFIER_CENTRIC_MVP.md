# Setback Strategy: Certifier-Centric MVP & Future Roadmap
**Date**: 2025-10-11
**Context**: Comprehensive audit + extraction analysis complete

---

## Executive Summary

**Current State**: Only R2 zone has curated setback data because that's what was manually validated and linked during initial development. The database contains 1,498 provisions mentioning setbacks across multiple zones, but only 18 are production-ready (12 ADG + 6 R2 DCP).

**Why Only R2?**: Time constraints + manual validation burden + Inner West pilot focus

**Strategic Question**: Given setbacks are nuanced and contextual, what's the right certifier-centric strategy for MVP and future expansion?

---

## Part 1: Why Only R2 is Done

### Technical History

**Timeline**:
1. **RAG-Anything PDF Import** (Initial Phase)
   - Extracted 803 provisions mentioning "setback" from DCPs
   - Extracted 695 zone-linked canonical provisions
   - BUT: Did NOT parse tables into structured data
   - Result: Qualitative text exists, no structured rules

2. **Manual Curation Phase** (R2 Focus)
   - Ashfield DCP: 6 provisions manually extracted and linked
   - Leichhardt DCP: 3 numeric values added to `zone_setback_rules` (unlinked)
   - Marrickville DCP: Skipped entirely
   - Result: Only R2/Ashfield production-ready

3. **ADG Standards** (Oct 10, 2025)
   - 12 ADG rules manually curated from PDF tables
   - SEPP-level, applies state-wide
   - Result: Multi-dwelling fully covered

4. **Automated Extraction Attempt** (Oct 10, 2025)
   - `extract_complete_inner_west_setbacks.py` created
   - Used GPT-4-turbo + Instructor to parse provisions
   - Extracted only 6 rules from Inner West
   - **NOT imported to database** (still in JSON file)
   - Result: Proof of concept, not production

### Why R2 Specifically?

**Ashfield DCP Structure**:
```
Chapter E2: Haberfield Neighbourhood Area
  Table 1: Development Standards
    - Front setback: 6m
    - Side setback: 0.9m
    - (Clear numeric table format)
```

**Leichhardt/Marrickville Structure**:
```
Part G: Residential Character
  "Front setbacks vary from 1m to 4m"
  "Most common: 2m to 4m"
  (Descriptive guidance, no tables)
```

**Winner**: Ashfield had extractable tables → easiest to validate → became pilot → R2 only zone done

---

## Part 2: Available Data for Extraction

### 2.1 Already Extracted (In Database)

**Quantitative** (Ready for parsing):
- ✅ `development_controls` table: 198 setback entries
  - R2: 116 controls
  - B1: 16 controls
  - Others: 66 scattered
  - **Status**: Automated extraction, 0.60-0.85 confidence
  - **Action**: Needs validation before production use

- ✅ `regulatory_provisions_canonical`: 199 provisions with embedded numeric values
  - R2: ~100 provisions
  - R1/R3/R5/B1: ~50 provisions
  - Others: ~49 provisions
  - **Status**: Raw text with extractable measurements
  - **Action**: Run extraction pipeline

**Qualitative** (Fallback display):
- ✅ 695 canonical provisions mentioning setbacks
- ✅ Currently used for Leichhardt/Marrickville fallback
- ✅ Legally accurate DCP text

### 2.2 Available PDFs (Not Yet Processed)

**Confirmed PDFs in Project**:
```
docs/apartment-design-guide-part-3.pdf ✅ (ADG already done)
docs/apartment-design-guide-part-4.pdf ⚠️ (Part 4 - not setbacks)
```

**Missing**:
- ❌ Inner West LEP 2022 (full PDF)
- ❌ Ashfield DCP 2016 (full PDF)
- ❌ Leichhardt DCP 2013 (full PDF)
- ❌ Marrickville DCP 2011 (full PDF)
- ❌ Other LGA DCPs (Parramatta, Canterbury-Bankstown, etc.)

**Note**: The provisions in database came from RAG-Anything extraction, meaning PDFs were processed but the structured output (tables) was not imported - only descriptive text.

### 2.3 Extraction Outputs (Not Imported)

**Files Found**:
```
extraction_outputs/inner_west_complete_setbacks_20251010_161244.json
  - 6 rules extracted using GPT-4-turbo
  - Confidence: 0.9-1.0
  - Status: NOT imported to database
  - Missing: Zone mapping (all show zone: null)
```

**Why Not Imported?**:
- Lacks zone assignment (critical for queries)
- Missing LGA sub-area (Ashfield/Leichhardt/Marrickville)
- Needs manual review/validation
- Only 6 rules (not comprehensive enough)

---

## Part 3: The Setback Problem - Nuance & Context

### 3.1 Why Setbacks Are Complex

**Context Dependencies**:
```
Front Setback Example:
  - Heritage area: 6m (maintain character)
  - Corner lot: 3m (visibility splay)
  - Battleaxe lot: No front setback (laneway access)
  - Dual occupancy: 6m (primary), 3m (secondary)
  - Adjoining council property: Match existing (1-8m range)
  - Flood affected: 3m PLUS flood planning level
```

**Table vs Reality**:
| What Table Says | What Certifier Needs to Know |
|-----------------|------------------------------|
| Front: 6m | Unless heritage (check HCA map) |
| Side: 0.9m | Unless dwelling>8m high (then 1.2m) |
| Rear: 1.1m | Unless upper floor (then 3m) |
| - | Unless balcony (then 4m) |
| - | Unless swimming pool (then 1m) |
| - | Unless garage (then 0m allowed) |

**The Certifier's Dilemma**:
- Tables give a starting point (6m front)
- But 8-12 exceptions may apply
- Descriptive text captures nuance better
- BUT can't be auto-calculated

---

### 3.2 Current Approaches in Industry

**Approach 1: Simple Tables Only** (Competitors)
```
Front: 6m
Side: 0.9m
Rear: 1.1m
```
**Pros**: Fast, clear, calculable
**Cons**: Often wrong, doesn't show exceptions, certifier still checks DCP manually

**Approach 2: Full DCP Text** (Your Current System)
```
"Front setbacks in Haberfield are to be 6m to maintain the established character
of the neighbourhood. However, on corner lots, a reduced setback of 3m may be
considered where it does not compromise sightlines. For heritage items..."
```
**Pros**: Legally accurate, shows context, defensible
**Cons**: Not calculable, requires reading, slower

**Approach 3: Hybrid** (What certifiers actually want)
```
Quick Reference:
  Front: 6m (typical)
  Side: 0.9m (typical)
  Rear: 1.1m (typical)

+ View Full Requirements →
  [Shows full DCP text with all exceptions]
```
**Pros**: Speed + accuracy, calculable starting point + full context
**Cons**: Requires both table data AND text data

---

## Part 4: Certifier-Centric MVP Strategy

### 4.1 What Certifiers Actually Need

**Interviewed Use Case** (Typical certifier workflow):

1. **Property Lookup** (10 seconds)
   - Address → Zone → LGA
   - "Okay, it's R2 Inner West"

2. **Quick Scan** (30 seconds)
   - Height limit? → 9m
   - FSR? → 0.6:1
   - Setbacks? → ???
   - Heritage? → Check map

3. **Deep Dive** (5-10 minutes if needed)
   - View full LEP clause
   - View full DCP section
   - Check exceptions
   - Check heritage controls
   - Check SEPP overrides

**Pain Point**: Step 2 → Setbacks often missing or wrong in other tools

**Certifier's Hierarchy of Needs**:
```
Tier 1 (MUST HAVE):
  ✅ "Does data exist?" - Show SOMETHING rather than nothing
  ✅ "Where does it come from?" - Source citation (DCP section)
  ✅ "Is it reliable?" - Confidence level / human verified

Tier 2 (NICE TO HAVE):
  ⚠️ "What's the typical value?" - Quick reference number
  ⚠️ "Can I calculate?" - Numeric value for geometry overlay

Tier 3 (LUXURY):
  ❌ "Auto-check my plans" - Geometry validation (future)
  ❌ "Show on map" - Setback visualization (future)
```

### 4.2 MVP Strategy (Next 2 Weeks)

**Goal**: Ship reliable setback data for R2 + make expansion scalable

**Phase 1: Quality over Quantity** (Week 1)

**Task 1.1**: Validate Existing R2 Data ✅
- Review 6 Ashfield provisions (already done, production-ready)
- Test API responses (already done, working)
- Document source PDFs (needed)

**Task 1.2**: Import ADG Standards to Main API ⚠️
- Currently separate endpoint (`/api/setbacks/adg`)
- Should appear in main constraints response
- Add to `building_envelope` section
- **Priority**: HIGH (affects all multi-dwelling)

**Task 1.3**: Improve Fallback Display 🔄
- Current: Shows descriptive text for Leichhardt/Marrickville
- Improve: Add "Character Guidance" label
- Add: Confidence indicator (0.6 = descriptive, 0.9+ = specific)
- Add: Visual distinction (icon, color)

**Task 1.4**: Validate 198 Extracted Controls ⚠️
- Query `development_controls` for setbacks
- Filter by confidence > 0.75
- Manual spot-check 20 random samples
- Flag low-confidence for review
- **Outcome**: Decide which to promote to production

**Phase 2: Controlled Expansion** (Week 2)

**Task 2.1**: Extract R1/R3/R5 Setbacks
- Focus on zones with existing text data
- Use GPT-4-turbo extraction pipeline
- Target: 10-15 provisions per zone
- Manual validation required

**Task 2.2**: Add Zone Coverage Dashboard
- Show users which zones have data
- "R2: Full coverage ✅"
- "R3: Descriptive only ⚠️"
- "R4: No data ❌"
- Set expectations clearly

**Task 2.3**: Create Validation Queue
- UI for reviewing extracted setbacks
- Show: Provision text + extracted value
- Action: Approve / Edit / Reject
- Track: Who validated, when

---

### 4.3 Certifier-Centric Display Strategy

**UI Mockup**:

```
┌─────────────────────────────────────────────────────────────┐
│ SETBACK REQUIREMENTS (R2 Zone - Inner West)                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 🟢 Specific Minimums Available (Ashfield DCP 2016)         │
│                                                              │
│ ┌────────────────┬──────────┬──────────────────────────┐   │
│ │ Boundary       │ Minimum  │ Source                   │   │
│ ├────────────────┼──────────┼──────────────────────────┤   │
│ │ Front          │ 6.0m     │ Chapter E2 (High conf.)  │   │
│ │ Side           │ 0.9m     │ Chapter E2 (High conf.)  │   │
│ └────────────────┴──────────┴──────────────────────────┘   │
│                                                              │
│ ⚠️ Character Guidance (Leichhardt DCP 2013)                │
│                                                              │
│ "Front setbacks in this area vary from 1m to 4m, with      │
│  2m to 4m being most common. Maintain continuity with      │
│  adjoining properties."                                     │
│                                                              │
│ [View Full DCP Section →]  [Check Exceptions →]            │
│                                                              │
│ ℹ️ Note: Always verify exceptions for corner lots,          │
│   heritage items, and upper floors                          │
└─────────────────────────────────────────────────────────────┘
```

**Key Principles**:
1. **Honesty**: Show what we have vs don't have
2. **Confidence**: Visual indicators for data quality
3. **Depth**: Quick reference + full text access
4. **Source**: Always cite DCP section
5. **Caveats**: Remind users to check exceptions

---

### 4.4 Long-Term Strategy (Month 2+)

**Expansion Priorities** (Based on NSW property development volume):

**Tier 1 LGAs** (High volume, focus first):
- Inner West ← Current
- Canterbury-Bankstown
- Parramatta
- Blacktown
- Cumberland

**Tier 2 LGAs** (Medium volume):
- Northern Beaches
- Sutherland
- Liverpool
- The Hills

**Tier 3 LGAs** (Lower volume or simpler):
- Regional councils
- Lower density areas

**Expansion Approach**:
1. Partner with 1 certifier firm per LGA
2. They validate extracted data (domain expertise)
3. We provide tool + support
4. Win-win: We get validation, they get early access

---

## Part 5: Technical Implementation Path

### 5.1 Extraction Pipeline Refinement

**Current Tool**: `extractors/setback_extractor.py` using Instructor + GPT-4

**Improvements Needed**:

```python
# CURRENT (extract_complete_inner_west_setbacks.py)
result = extractor.extract_setbacks(
    provision_text=prov_text,
    ref_number=ref_num,
    provision_id=prov_id,
    document_type=doc_type,
    lga="Inner West"  # ← Generic, not specific
)

# IMPROVED (needed)
result = extractor.extract_setbacks(
    provision_text=prov_text,
    ref_number=ref_num,
    provision_id=prov_id,
    document_type=doc_type,
    lga="Inner West",
    council_area="Ashfield",  # ← Specific sub-area
    zone="R2",                 # ← Explicit zone assignment
    development_type="dwelling_house",  # ← If mentioned
    requires_validation=True   # ← Flag for manual review
)
```

**Schema Enhancement**:
```python
@dataclass
class SetbackRule:
    # Existing fields...
    boundary_type: str
    setback_meters: float

    # ADD THESE:
    zone_applicability: List[str]  # ["R1", "R2"]
    development_type_filter: Optional[str]  # "multi_dwelling"
    site_conditions: List[str]  # ["corner_lot", "heritage"]
    exceptions_summary: Optional[str]  # Brief list
    requires_site_check: bool  # True if exceptions complex

    # Validation metadata:
    validated_by: Optional[str]  # Certifier name/ID
    validated_date: Optional[datetime]
    validation_notes: Optional[str]
```

### 5.2 Database Schema for Validation Workflow

**New Table**: `setback_extraction_queue`
```sql
CREATE TABLE setback_extraction_queue (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER REFERENCES regulatory_provisions(id),
    extracted_rule JSONB,  -- Raw extracted data
    extraction_method TEXT,
    extraction_date TIMESTAMP DEFAULT NOW(),
    confidence_score NUMERIC(3,2),

    -- Validation fields
    validation_status TEXT CHECK (status IN ('pending', 'approved', 'rejected', 'needs_revision')),
    validated_by TEXT,
    validated_date TIMESTAMP,
    validation_notes TEXT,

    -- If approved, link to production
    zone_setback_rule_id INTEGER REFERENCES zone_setback_rules(id)
);
```

**Workflow**:
1. Extraction script → Insert to `setback_extraction_queue`
2. Admin UI → Review queue items
3. Approve → Copy to `zone_setback_rules`, update status
4. Reject → Mark rejected, add notes
5. Needs revision → Flag for re-extraction with hints

### 5.3 API Integration Strategy

**Current State**:
- `/api/setbacks/adg` → Separate endpoint (ADG standards)
- `/api/compliance/constraints` → Main endpoint (DCP/LEP)
- NOT integrated

**MVP Integration** (Option A - Quick):
```typescript
// In /api/compliance/constraints
const constraints = {
  building_envelope: [
    ...lepConstraints,
    ...dcpSetbacks,
    ...adgStandards  // ← Call ADG API internally, merge results
  ]
}
```

**Better Integration** (Option B - Proper):
```typescript
// Unified setback resolution
const setbacks = await resolveSetbacks({
  zone: 'R2',
  lga: 'Inner West',
  developmentType: 'multi_dwelling',
  buildingHeight: 15,
  address: '180 Addison Rd'
});

// Returns hierarchy:
// 1. SEPP (ADG) - if applicable
// 2. LEP - if specified
// 3. DCP - zone-specific
// 4. DCP - character guidance (fallback)
```

---

## Part 6: Recommendations

### For MVP (Ship in 2 weeks):

**DO THIS**:
1. ✅ **Keep R2/Ashfield as gold standard** - It works, it's validated, show it off
2. ✅ **Improve descriptive text display** - Make Leichhardt/Marrickville fallback look intentional
3. ✅ **Add ADG to main constraints API** - Currently separate, should be integrated
4. ✅ **Add confidence indicators** - Show users what's reliable vs guidance
5. ✅ **Create zone coverage dashboard** - Set expectations ("R2: Full, R3: Partial, R4: None")

**DON'T DO THIS YET**:
- ❌ Auto-extract all zones (too risky without validation)
- ❌ Import unvalidated controls (198 extracted rules need review)
- ❌ Promise comprehensive coverage (manage expectations)
- ❌ Build geometry validation (Tier 3, not MVP)

### For Post-MVP (Months 2-3):

**Prioritize**:
1. **Validation workflow** - Build UI for reviewing extractions
2. **Controlled expansion** - R1, R3, R5 (zones with existing text)
3. **Certifier partnerships** - Get domain experts to validate
4. **LGA expansion** - Canterbury-Bankstown, Parramatta (high volume)

### For Long-Term (Months 4-6):

**Invest In**:
1. **Automated table extraction** - ML model trained on NSW DCP tables
2. **Exception modeling** - Capture conditional setbacks properly
3. **Geometry validation** - Auto-check plans against setbacks
4. **Multi-LGA coverage** - Expand beyond Sydney

---

## Part 7: The Honest Answer

**Why only R2?**
- Limited time
- Manual validation required
- Ashfield had clean tables
- Inner West was pilot LGA
- Other zones are in database but not curated

**Should you extract all zones now?**
- **No** - Risk of incorrect data
- **Yes** - But with validation workflow
- **Hybrid** - Extract to queue, validate before production

**What's the right strategy?**
```
MVP: Quality (R2 gold standard) + Transparency (show what's missing)
  ↓
Phase 2: Controlled expansion with validation
  ↓
Phase 3: Scale with certifier partnerships
  ↓
Long-term: Automated extraction + ML validation
```

**Certifier-centric = Honest + Reliable + Defensible**
- Show what you have
- Show confidence level
- Always link to source
- Make full DCP text accessible
- Never guess or generate

---

## Conclusion

**For MVP**:
- Ship R2/Ashfield as proof of concept
- Show descriptive text for other zones (better than nothing)
- Add clear labeling (confidence, source, coverage)
- Integrate ADG standards
- Build validation workflow for future expansion

**After MVP**:
- Extract R1/R3/R5 to validation queue
- Partner with certifiers to validate
- Expand incrementally with quality control
- Never sacrifice accuracy for coverage

**The certifier doesn't need every zone perfect - they need to trust that what you show is correct.**

---

**End of Report**
