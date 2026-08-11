# SEPP Extraction Scope Analysis

**Date:** 2026-02-20
**Purpose:** Objectively assess what's needed vs. what LLM extraction would provide

---

## Current State

### What EXISTS (Deterministic Extraction):
✅ **5,235 actionable SEPP provisions** in `regulatory_provisions`
✅ **Basic taxonomy:**
- v2_topic assigned to 60% (height, access, setbacks, landscaping, heritage, etc.)
- v2_is_actionable flagged
- Provision text extracted from PDFs

### What's MISSING:
❌ **v2_marker** = NULL for all 5,235 provisions (no categorization as exclusion/procedure/numeric)
❌ **No structured requirements** extracted
❌ **No numeric value** parsing (setbacks, heights, percentages)
❌ **No exclusion trigger** identification
❌ **No "applies_to"** pathway mapping (CDC vs DA vs Pattern Book)

---

## The Fundamental Question

**What is the actual use case?**

Based on the frontend code, the system checks:
1. **SEPP Exempt & Complying Development** - CDC pathway eligibility
2. **SEPP Housing** - Pattern Book pathway (referenced in code)
3. **Other SEPPs** - Heritage, Biodiversity, Resilience, etc.

**But do you ACTUALLY need all 5,235 provisions structurally extracted?**

---

## Scope Options

### Option 1: MINIMAL - Exclusion Triggers Only (est. 500-800 provisions)

**What:** Extract ONLY provisions that **exclude properties** from fast-track pathways

**Includes:**
- Heritage items/HCAs
- Flood planning areas
- Bushfire prone land
- Acid sulfate soils
- Threatened species habitat
- Coastal erosion zones
- Contaminated land
- Protected areas

**Why this might be enough:**
- Fast-track pathways (CDC, Pattern Book) are **permissive** by default
- Only need to know what **blocks** eligibility
- Numeric standards (setbacks, heights) come from DCP/LEP, not SEPP for most cases
- Procedural requirements don't affect pathway feasibility

**Time:**
- Deterministic: 15-20 hours (manual curation of exclusions from PDFs)
- LLM + review: 8-12 hours (LLM extracts, you review ~600 provisions)

---

### Option 2: TARGETED - Exclusions + Critical Numerics (est. 1,200 provisions)

**What:** Exclusions + provisions with numeric thresholds that override local controls

**Includes:**
- All exclusions (Option 1)
- BASIX requirements (already manually curated)
- SEPP Housing min/max standards (lot size, FSR, height overrides)
- TOD parking reductions
- Pattern Book dimensional requirements
- Affordable housing density bonuses

**Why this is probably optimal:**
- Covers pathway feasibility (exclusions)
- Covers numeric standards that **override** DCP/LEP
- Skips generic procedural text ("must submit form X")

**Time:**
- Deterministic: 35-45 hours (manual extraction)
- LLM + review: 15-22 hours (LLM extracts, you review ~1,000 provisions)

---

### Option 3: COMPREHENSIVE - All Actionable (5,235 provisions)

**What:** Extract structured requirements from every actionable SEPP provision

**Includes:** Everything

**Why you probably DON'T need this:**
- Many provisions are procedural boilerplate
- Definitions already extracted separately
- Context/intro text marked as actionable (but isn't for pathways)
- Extracting "procedure" requirements doesn't help feasibility checks

**Time:**
- Deterministic: 150-200 hours (unrealistic)
- LLM + review: 52 hours (per my earlier estimate)

---

## Reality Check: What Does Frontend Actually Query?

Looking at `CDCPathway.tsx` and related components:

**Current queries:**
1. SEPP Exempt & Complying provisions by **work type** (Deck, Garage, Pool, Fence)
2. Checks for **numeric thresholds** (area, height limits)
3. Checks for **exclusions** (heritage, flood, etc.)

**Does NOT query:**
- Procedural requirements ("submit BASIX certificate")
- General context provisions
- Definitions (separate table)

**Conclusion:** Frontend needs **Option 2** (Exclusions + Critical Numerics), not Option 3 (all 5,235)

---

## Official Pathway Names (Research Needed)

**Question:** What is the official name of the new pathway?

**Possibilities:**
1. **Low Rise Housing Diversity Code** (Housing SEPP 2021)
2. **Medium Density Housing Code** (Housing SEPP 2021 Part 4)
3. **NSW Housing Code** (generic term)
4. **Pattern Book Pathway** (informal, refers to design templates)
5. **10-Day CDC** (processing time, not official name)

**Where to find official name:**
- Housing SEPP 2021 Part 4 title
- NSW Planning Portal CDC documentation
- Planning.nsw.gov.au policy pages

**Action:** Confirm official terminology before proceeding

---

## Recommended Approach

### Phase 1: Manual Curation of Exclusions (~500 provisions)

**Why manual:**
- ✅ 100% accuracy required for exclusions (legal liability)
- ✅ Defensible in court ("we manually verified")
- ✅ Fast (15-20 hours vs 52 hours for LLM review of all 5,235)
- ✅ No hallucination risk

**Method:**
1. Filter `regulatory_provisions` WHERE v2_topic IN ('heritage', 'flooding', 'bushfire', 'biodiversity', 'coastal')
2. You manually read each provision's PDF page
3. Hand-enter exclusion records into `sepp_curated_requirements` table:
   ```sql
   INSERT INTO sepp_curated_requirements
   (provision_id, requirement_type, exclusion_type, applies_to, confidence)
   VALUES
   (34963, 'exclusion', 'heritage', 'all', 1.0);
   ```

**Deliverable:** ~500 exclusion triggers, 100% accurate, fully defensible

---

### Phase 2: Regex Patterns for Numeric Standards (~200 provisions)

**Why regex:**
- ✅ Deterministic
- ✅ Auditable (pattern = documentation)
- ✅ Fast execution

**Method:**
```python
def extract_height_limit(provision_text):
    """Extract height limits from SEPP Housing provisions."""
    patterns = [
        r'maximum.*?height.*?(\d+(?:\.\d+)?)\s*m',
        r'not.*?exceed.*?(\d+(?:\.\d+)?)\s*metres?',
        r'height.*?limited.*?(\d+(?:\.\d+)?)\s*m'
    ]
    for pattern in patterns:
        match = re.search(pattern, provision_text, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None
```

**Deliverable:** ~200 numeric standards, deterministic extraction

---

### Phase 3: LLM for Discovery (Optional)

**Use LLM to find provisions you might have missed:**
- Run LLM extraction on remaining 4,500 provisions
- **Don't save to production database**
- Use output to discover edge cases you didn't manually code
- Add those patterns to regex extractors
- LLM = research tool, not production extractor

---

## Cost-Benefit Analysis

| Approach | Time | Coverage | Accuracy | Defensible | Cost |
|----------|------|----------|----------|------------|------|
| **Option 2 Manual** | 35-45h | 1,200 critical | 100% | ✅ Yes | $0 |
| **Option 3 LLM + Review** | 52h | 5,235 all | 85-95% | ⚠️ Maybe | $75 API |
| **Hybrid (recommended)** | 25h | 700 critical | 100% | ✅ Yes | $20 API |

**Hybrid = Manual for exclusions/numerics + LLM for discovery**

---

## Decision Needed

**Question 1:** What's the actual use case?
- [ ] CDC pathway eligibility only (Option 1)
- [ ] CDC + Pattern Book pathways (Option 2) ← **Recommended**
- [ ] Complete SEPP coverage (Option 3)

**Question 2:** What's the official pathway name?
- Need to confirm terminology for user-facing docs

**Question 3:** Extraction method?
- [ ] Manual curation (like BASIX) ← **Recommended for exclusions**
- [ ] Regex patterns ← **Recommended for numerics**
- [ ] LLM + human review ← **Optional for discovery**
- [ ] Pure LLM (not recommended)

**Question 4:** Acceptable timeline?
- 15-20 hours over 2-3 weeks? (Manual exclusions)
- 35-45 hours over 4-6 weeks? (Manual exclusions + numerics)
- 52 hours over 6-8 weeks? (LLM + review all 5,235)

---

## Next Step

**Before writing ANY code, answer:**
1. Do you actually need all 5,235 provisions extracted?
2. Or just the ~700-1,200 that affect pathway feasibility?
3. What's the official name of the pathway (for documentation)?

**My recommendation:** Option 2 with hybrid approach (manual + regex + LLM discovery)
