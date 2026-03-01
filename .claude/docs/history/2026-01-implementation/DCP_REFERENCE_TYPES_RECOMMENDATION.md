# DCP Reference Types - Extraction Recommendation

## Analysis Results (100 Marrickville provisions sample)

| Reference Type | Frequency | Example |
|----------------|-----------|---------|
| **Section cross-refs** | 50% | "refer Section 2.9 (Community Safety)" |
| **Figures** | 30% | "Figure 5 shows window placement" |
| **Tables** | 16% | "in accordance with the following table" ✓ Already captured |
| **Maps** | 13% | "Height of Buildings Map of MLEP 2011" |
| **"refer to"** | 13% | Generic pattern (not specific target) |
| **LEP references** | 11% | "MLEP 2011" |
| **"in accordance with"** | 11% | Generic pattern |
| Policy references | 8% | "Affordable Housing SEPP" |
| Appendices | 3% | "Appendix 1 - Heritage Conservation Areas Map" |
| SEPP references | 3% | "BASIX SEPP" |
| Schedules | 2% | "Schedule 1 - Victoria Road Precinct Noise Policy" |
| Clauses | 1% | "Clause 5.4 for controls relating to..." |

## Recommendation: Add 4 High-Value Reference Types

### 1. **Figures/Diagrams** (HIGH PRIORITY - 30% frequency)
**Why capture:**
- Visual aids that explain complex requirements
- User needs to view these to understand requirement
- Already extracted in MinerU JSON (but not linked to requirements)

**Schema addition:**
```json
{
  "references_figure": true,
  "figure_number": "5",
  "figure_description": "Window placement for secondary dwellings",
  "figure_page": 12
}
```

**Detection pattern:**
```
Figure \d+|Fig\. \d+
```

**Example:**
> "Only two front facing dormers will be considered (Figure 5)"

**UI display:**
```
Side setback per table (View Table) | View diagram (Figure 5)
```

---

### 2. **DCP Section Cross-References** (HIGH PRIORITY - 50% frequency)
**Why capture:**
- Links to other relevant DCP sections (e.g., heritage, parking)
- User may need to check multiple sections for complete requirements
- Enables "related requirements" navigation

**Schema addition:**
```json
{
  "references_section": true,
  "section_reference": "Section 2.9",
  "section_title": "Community Safety"
}
```

**Detection pattern:**
```
(Section|Part|Chapter) \d+\.\d*
```

**Example:**
> "For details refer Section 2.9 (Community Safety) of this DCP"

**UI display:**
```
See also: Section 2.9 (Community Safety)
```

**Future enhancement:** Clickable link to Section 2.9 requirements in database

---

### 3. **LEP/Map References** (MEDIUM PRIORITY - 11-13% frequency)
**Why capture:**
- LEP (Local Environment Plan) is the legal instrument (DCP interprets it)
- Maps (Height of Buildings, FSR) are regulatory controls
- User must check LEP/maps for legal compliance

**Schema addition:**
```json
{
  "references_lep": true,
  "lep_document": "MLEP 2011",
  "lep_map_type": "Height of Buildings Map"
}
```

**Detection pattern:**
```
(LEP|MLEP|ILEP) \d{4}|(Height of Buildings|HOB|FSR) Map
```

**Example:**
> "Maximum permissible FSR and height must be consistent with the Height of Buildings (HOB) and FSR Maps of MLEP 2011"

**UI display:**
```
⚠️ Refer to MLEP 2011 Height of Buildings Map for legal maximum
```

---

### 4. **SEPP References** (LOW-MEDIUM PRIORITY - 3% frequency)
**Why capture:**
- State Environmental Planning Policies override DCP
- Important for user to know when state policy applies

**Schema addition:**
```json
{
  "references_sepp": true,
  "sepp_name": "Affordable Rental Housing SEPP 2009"
}
```

**Detection pattern:**
```
SEPP|State Environmental Planning Policy
```

**Example:**
> "State Environmental Planning Policy (Affordable Rental Housing) 2009 (Affordable Housing SEPP) may override DCP controls"

**UI display:**
```
⚠️ SEPP may apply: Affordable Rental Housing SEPP 2009
```

---

## NOT Recommended to Capture

### Generic patterns (too vague to link):
- "refer to" without specific target
- "in accordance with" (without specific document)
- "as per" (too generic)

**Reason:** Cannot create actionable link/reference without specific target

---

## Implementation Priority

### **Phase 1 (Immediate - add to current extraction):**
1. **Figures** - Add to `OPTIMAL_MARRICKVILLE_EXTRACTION_PROMPT.md`
2. **Section cross-references** - Add to prompt

### **Phase 2 (After Phase 1 extraction completes):**
3. **LEP/Map references** - Add to prompt
4. **SEPP references** - Add to prompt

### **Phase 3 (Future enhancement):**
- Parse section references to create clickable links
- Link figure numbers to actual extracted figures in database
- Fetch LEP map data from NSW Planning Portal

---

## Schema Changes Required

### Add to `dcp_general_requirements` table:

```sql
-- Figure references
ALTER TABLE dcp_general_requirements
ADD COLUMN references_figure BOOLEAN DEFAULT FALSE,
ADD COLUMN figure_number TEXT,
ADD COLUMN figure_description TEXT,
ADD COLUMN figure_page INTEGER;

-- Section cross-references
ALTER TABLE dcp_general_requirements
ADD COLUMN references_section BOOLEAN DEFAULT FALSE,
ADD COLUMN section_reference TEXT,
ADD COLUMN section_title TEXT;

-- LEP references
ALTER TABLE dcp_general_requirements
ADD COLUMN references_lep BOOLEAN DEFAULT FALSE,
ADD COLUMN lep_document TEXT,
ADD COLUMN lep_map_type TEXT;

-- SEPP references
ALTER TABLE dcp_general_requirements
ADD COLUMN references_sepp BOOLEAN DEFAULT FALSE,
ADD COLUMN sepp_name TEXT;
```

---

## Updated Prompt Section (Figure References)

Add to `OPTIMAL_MARRICKVILLE_EXTRACTION_PROMPT.md`:

```markdown
### 7. Figure/Diagram References (HIGH VALUE)
When a requirement references a figure or diagram, extract these fields:

**Detection patterns:**
- "Figure X"
- "Fig. X"
- "(Figure X)"
- "as shown in Figure X"
- "see diagram"

**Output fields:**
```json
{
  "references_figure": true,
  "figure_number": "5",
  "figure_description": "Window placement for secondary dwellings",
  "figure_page": 12  // Same as pdf_page unless explicit page given
}
```

**Examples:**
```
Text: "Only two front facing dormers will be considered (Figure 5)"
Output:
{
  "requirement_text": "Maximum two front facing dormers",
  "references_figure": true,
  "figure_number": "5",
  "figure_page": 11
}
```

### 8. Section Cross-References (HIGH VALUE)
When a requirement refers to another DCP section:

**Detection patterns:**
- "Section X.X"
- "Part X"
- "Chapter X"
- "refer Section X.X"

**Output fields:**
```json
{
  "references_section": true,
  "section_reference": "Section 2.9",
  "section_title": "Community Safety"  // If mentioned in text
}
```

**Examples:**
```
Text: "For details refer Section 2.9 (Community Safety) of this DCP"
Output:
{
  "requirement_text": "Refer to Community Safety requirements",
  "references_section": true,
  "section_reference": "Section 2.9",
  "section_title": "Community Safety"
}
```
```

---

## Cost/Benefit Analysis

### Implementation cost:
- Schema changes: 5 minutes
- Prompt updates: 10 minutes
- Testing: 5 minutes
- **Total: 20 minutes**

### Extraction cost impact:
- Adds ~2 fields per requirement (10% of current extraction)
- Estimated cost increase: +10% ($72.40 → $79.64 total)
- **Additional cost: $7.24**

### User value:
- **Figures:** Essential for understanding visual requirements (e.g., "dormer placement per Figure 5")
- **Section cross-refs:** Enables discovery of related requirements (50% of provisions have cross-refs!)
- **LEP/Map refs:** Legal compliance awareness (user must check maps)
- **SEPP refs:** State policy override awareness

**ROI:** HIGH - $7.24 additional cost for 4 high-value reference types

---

## Recommendation Summary

**Add to extraction NOW (before running Phase 1):**
1. ✅ Tables (already included)
2. ✅ Figures (30% frequency - high value)
3. ✅ Section cross-references (50% frequency - very high value)
4. ✅ LEP/Map references (13% frequency - legal compliance)
5. ✅ SEPP references (3% frequency - state policy override)

**Schema changes required:** 4 new field groups (12 columns total)

**Estimated implementation time:** 20 minutes

**Additional extraction cost:** $7.24 (+10%)

**User value:** Very high - enables visual reference, related requirement discovery, and legal compliance awareness
