# LLM Extraction vs Professional Workflow Analysis

## How LLM Extraction Currently Works

### 1. Categories Are Pre-Defined (By Us)

**Line 35 in `categorize_marrickville_provisions_v2.py`:**
```python
category: One of: setback_front, setback_side, setback_rear, parking,
landscaping, building_height, site_coverage, character, privacy,
fencing, biodiversity, solar_access, other
```

**Who decides categories:**
- ✅ We (developers) define the list
- ❌ LLM doesn't invent categories
- ✅ LLM chooses from our list

**Categories chosen based on:**
- Common planning regulations (setbacks, parking, height)
- Typical certifier checklist items
- What matters for development applications

---

### 2. LLM Decides What To Extract (Intelligent Selection)

**Process:**
1. Script sends precinct provisions to GPT-4o-mini
2. LLM reads all text (up to 15,000 chars)
3. LLM identifies specific requirements/rules
4. LLM categorizes each into one of our predefined categories
5. LLM extracts verbatim text + creates clean summary

**What LLM extracts:**
- ✅ Specific measurable requirements ("2-4 meter setback")
- ✅ Clear rules with conditions
- ✅ Numerical values (heights, percentages, areas)
- ❌ General guidance without specifics
- ❌ Background/context paragraphs
- ❌ Definitions

**Example: Precinct 10_ (Dulwich Hill North)**
- Source provisions: Multiple sections spanning pages
- LLM extracted: **5 requirements**
  - 1 setback_front
  - 1 biodiversity
  - 2 character
  - 1 other
- LLM ignored: General precinct description, history, objectives

---

### 3. Coverage Limitations

**Input Limit (Line 67):**
```python
provisions_with_ids[:15000]  # Only first 15,000 characters
```

**What this means:**
- If precinct provisions are 20,000 chars → only first 15,000 analyzed
- If precinct has 201-page provision → massive truncation
- Requirements at end of long provisions may be missed

**Marrickville Precinct 10_ Example:**
- Extracted: 5 requirements
- Categories: 4 out of 13 possible
- Coverage: Unknown % of actual compliance items

**Question: Is this enough?**

---

## How Professionals Actually Work

### Certifier Workflow (Current Practice)

**Step 1: Identify Applicable Controls**
```
1. Check address → find precinct
2. Check LEP zone + development type
3. Identify ALL applicable documents:
   - LEP (height, FSR, objectives)
   - DCP (design, setbacks, parking)
   - SEPPs (if applicable)
   - Development standards
```

**Step 2: Extract Relevant Requirements**
```
For each document, check:
- Building height controls
- Setback requirements (front, side, rear)
- Parking requirements
- Landscaping requirements
- Heritage considerations
- Character requirements
- Environmental protections
- Any special precinct rules
```

**Step 3: Checklist Completion**
```
Create compliance checklist with:
- Requirement name
- Source (document + clause)
- Required value
- Proposed value
- Complies Y/N
- Comments/justification if non-compliant
```

**Step 4: Report Generation**
```
Write certifier report citing:
- Specific clause numbers
- Exact page references
- How design complies (or seeks variation)
```

---

## Gap Analysis: LLM vs Professional Needs

### What LLM Does Well

✅ **Extract Numerical Requirements**
- "Setback: 2-4 meters" → clear, measurable
- "Height: 3.6m max" → specific limit
- "Parking: 1 space per dwelling" → quantifiable

✅ **Identify Common Categories**
- Setbacks → always relevant
- Height → always relevant
- Parking → always relevant

✅ **Provide Citations**
- Links to source provision
- Page numbers (when fixed)
- Verbatim text for verification

---

### What LLM Might Miss

❌ **Qualitative Requirements**
```
Example: "Development should be sympathetic to existing character"
- Not measurable
- LLM might categorize as "character"
- But professional needs to interpret
```

❌ **Conditional Requirements**
```
Example: "Front setback 4m, except where adjoining heritage item then 6m"
- LLM extracts main rule
- May miss condition
- Professional needs to check if condition applies
```

❌ **Cross-References**
```
Example: "Comply with Table 5.2 in Part 2"
- LLM extracts reference
- Doesn't resolve what Table 5.2 says
- Professional needs to look it up
```

❌ **Implicit Requirements**
```
Example: Section header "Building must be setback from street"
           Body text: "To maintain streetscape character..."
- Setback requirement implied but not stated with number
- LLM might miss if no specific measurement
```

❌ **Requirements Beyond 15,000 Chars**
```
If provision is 20,000 chars:
- First 15,000 chars analyzed
- Last 5,000 chars ignored
- Could miss important requirements at end
```

---

## Category Determination: System vs Professional

### Our System (Current)

**Pre-defined categories (13 total):**
```
1. setback_front
2. setback_side
3. setback_rear
4. parking
5. landscaping
6. building_height
7. site_coverage
8. character
9. privacy
10. fencing
11. biodiversity
12. solar_access
13. other
```

**LLM task:** "Which category does this requirement fit?"

---

### Professional Mental Model

**Certifier thinks in terms of:**

**1. Statutory Controls (Must Comply)**
```
- LEP height limits
- LEP FSR limits
- SEPP provisions (e.g., ADG)
- Minimum standards
```

**2. Design Guidelines (Must Consider)**
```
- DCP character guidelines
- Streetscape objectives
- Heritage compatibility
- Environmental objectives
```

**3. Numerical Requirements (Easy to Check)**
```
- Setbacks (meters)
- Height (meters/storeys)
- Parking (number of spaces)
- Landscaping (% of site)
- Site coverage (%)
```

**4. Qualitative Requirements (Judgment Required)**
```
- "Compatible with character"
- "Sympathetic design"
- "Minimise visual impact"
- "Appropriate scale"
```

**5. Conditional Requirements (If-Then)**
```
- "If corner site, then..."
- "Where adjoining heritage, then..."
- "Unless approved by Council..."
```

---

## The Fundamental Question

### What Should We Extract?

**Option A: Comprehensive (All Requirements)**
```
Pro: Complete picture
Con: Overwhelms user with 50+ items per site
Con: Includes qualitative/subjective items
Con: Hard to verify compliance
```

**Option B: Focused (Key Numerical Only)**
```
Pro: Clear, measurable items
Pro: Easy compliance checking
Con: Might miss important qualitative requirements
Con: User doesn't see full picture
```

**Option C: Tiered (Critical + Context)**
```
Pro: Quick numerical checks + access to full text
Pro: User can drill down if needed
Con: Need to define what's "critical"
```

---

## Real World Example: Precinct 10_

### What LLM Extracted (5 items)

```
1. setback_front: "Front setbacks: 2-4 meters"
2. biodiversity: "3m vegetation buffer from GreenWay"
3. other: "Access from Edward Lane for Old Canterbury Rd sites"
4. character: "Retain single storey form on specific streets"
5. other: "Avoid tunnel effect along GreenWay"
```

### What Might Be In Full Provisions (Unknown)

```
Potentially also in text:
- Side setback requirements?
- Rear setback requirements?
- Maximum height?
- Parking requirements?
- Landscaping % requirements?
- Site coverage limits?
- Solar access requirements?
- Privacy requirements?
```

**Critical Question:** Did LLM extract everything, or just highlights?

---

## How Professionals Determine Categories

### Traditional Method

**1. Read entire provision**
- Note every requirement
- Identify type (numerical/qualitative)
- Note conditions/exceptions

**2. Create compliance matrix**
```
| Requirement | Source | Value | Proposed | Complies |
|-------------|--------|-------|----------|----------|
| Front setback | DCP 9.10 p7 | 2-4m | 3m | Yes |
| Side setback | DCP 9.10 p8 | 0.9m | 1.2m | Yes |
| Height | LEP | 9m | 8.5m | Yes |
| Parking | DCP 9.10 p9 | 1/dwell | 1/dwell | Yes |
```

**3. Categories emerge from:**
- Industry standard checklists
- Council DA requirements
- Professional experience
- Building Code requirements
- What matters for approval

---

## Recommendations

### Short Term (Current System)

**1. Acknowledge Limitations**
```
UI text: "Key extracted requirements. View full provisions for complete picture."
```

**2. Provide Full Text Access**
```
"View Full Section" → shows all text, not just extracted items
User can verify nothing was missed
```

**3. Show Extraction Coverage**
```
"Analyzed 15,000 of 18,500 characters (81%)"
Warns user if truncation occurred
```

---

### Medium Term (Improvements)

**1. Increase Input Limit**
```
Current: 15,000 chars
Proposed: 32,000 chars (GPT-4o-mini max with output)
Benefit: Cover more provisions
```

**2. Add Missing Categories**
```
Current: 13 categories
Add:
- floor_space_ratio
- heritage
- tree_protection
- stormwater
- accessibility
- energy_efficiency
```

**3. Multi-Pass Extraction**
```
Pass 1: Extract numerical requirements
Pass 2: Extract qualitative requirements
Pass 3: Extract cross-references
Combine results
```

---

### Long Term (Comprehensive)

**1. Semantic Chunking**
```
Instead of truncating at 15,000 chars:
- Split provisions into semantic chunks
- Extract from each chunk
- Combine results
Result: Nothing missed due to length
```

**2. Validation Layer**
```
After LLM extraction:
- Compare against regulatory checklist
- Flag if expected categories missing
- Prompt user to verify
```

**3. Professional Review Mode**
```
Allow certifiers to:
- Mark extractions as verified/incorrect
- Add missing requirements manually
- Build training data for better LLM prompts
```

---

## Answer to Your Question

### "What is the nature of the LLM extraction?"

**Current State:**
1. **Categories = Pre-defined by us** (13 categories based on common planning requirements)
2. **Extraction = Intelligent selection by LLM** (reads text, identifies specific requirements)
3. **Coverage = Partial** (first 15,000 chars, LLM judgment on what's "important")
4. **Goal = Highlight key measurable requirements**, not comprehensive extraction

**Professional Workflow:**
1. **Categories = Emerge from requirements** (what council needs, what matters for approval)
2. **Extraction = Comprehensive manual review** (read everything, note everything)
3. **Coverage = Complete** (nothing missed)
4. **Goal = Full compliance checklist** with every applicable requirement

### Gap

Our system provides **intelligent highlights** of key requirements.
Professionals need **comprehensive checklist** of all requirements.

We're at **80% of the way there** for common cases.
The 20% gap is:
- Items beyond 15,000 char limit
- Qualitative requirements LLM skips
- Cross-references to other sections
- Conditional requirements
- Implicit requirements

### Solution

Implement **Progressive Disclosure** (from PROFESSIONAL_USER_UX_DESIGN.md):
- Level 1: Show extracted requirements (quick answer)
- Level 2: Show source context (verify extraction)
- Level 3: Show full section (check nothing missed)
- Level 4: Show PDF (traditional workflow)

This gives professionals the **speed of LLM extraction** with the **confidence of manual review**.

---

**Created:** 2025-10-29
**Status:** Identifies gap between current system and professional needs
**Next Step:** Decide on coverage vs usability tradeoff
