# Phase 4: Improve PDF Section Number Extraction

## Current State Analysis

**Problem:** Only 2.4% of provisions have `pdf_section` populated (534 out of 22,648)

**Current Coverage:**
```sql
-- From backfill results:
Total provisions:     22,648
Has pdf_page:          5,407 (23.9%)
Has pdf_section:         534 (2.4%)  ← LOW!
Has pdf_source_file:   5,407 (23.9%)
Has pdf_extra:         5,407 (23.9%)
```

**Why Low?**
Current extraction only catches:
- Simple numbered sections: `4.1.6.2`
- Control codes: `C8`, `D12`
- Schedule references: `Schedule 1`

**Missing:**
- Table of contents entries
- Heading hierarchies (H1, H2, H3 in extraction)
- Parent section inference (if we see 4.1.6.2, we know it's under 4.1.6 and 4.1)
- Descriptive sections without numbers (e.g., "Historical development patterns")

---

## Phase 4 Goals

### **Primary Goal:**
Increase section coverage from 2.4% to **>60%** (13,589+ provisions)

### **Success Metrics:**
1. ✅ 60%+ provisions have `pdf_section` populated
2. ✅ Section numbers are accurate (verified against PDF TOC)
3. ✅ Hierarchy relationships captured in `pdf_extra`
4. ✅ Zero false positives (wrong section numbers)

---

## Strategy Overview

### **Approach 1: Multi-Pass Section Extraction** ⭐ **RECOMMENDED**

**Pass 1: Direct Extraction (Current)**
- Already implemented in `backfill_pdf_metadata.py`
- Extracts from text elements with `text_level == 1`
- Coverage: ~2.4%

**Pass 2: Table of Contents Mining**
- Parse TOC entries from JSON (identified by patterns like "4.1.6.2 Building setbacks ... 12")
- Build section → page mapping
- Match provisions by page ranges
- Expected coverage: +20-30%

**Pass 3: Heading Hierarchy Inference**
- Track `text_level` sequences (1 = H1, 2 = H2, etc.)
- When we see heading at level 2, it belongs to most recent level 1
- Build parent-child relationships
- Expected coverage: +15-25%

**Pass 4: Reference Number Mapping**
- Use existing `ref_number` field as fallback
- If `ref_number` matches section pattern, copy to `pdf_section`
- Clean up: "table in 4.1.6.2" → "4.1.6.2"
- Expected coverage: +20-30%

**Pass 5: LLM-Assisted Extraction (Optional)**
- For remaining provisions without sections
- Use Claude/GPT-4 to parse complex document structures
- Expected coverage: +10-15%

**Total Expected Coverage: 60-95%**

---

## Implementation Plan

### **Step 1: Analyze Current Data**

**Task:** Understand what we're working with

```python
# Check text_level distribution in JSON
# Count provisions per document
# Identify documents with TOC vs without
# Sample provisions with/without sections
```

**Output:**
- Document type taxonomy (DCP vs LEP vs SEPP structure)
- Text level usage patterns
- TOC detection patterns

**Estimated Time:** 30 minutes

---

### **Step 2: Implement Pass 2 - TOC Mining**

**Task:** Extract section numbers from table of contents

**Algorithm:**
```python
def extract_toc_mapping(json_data):
    """
    Find TOC entries like:
    "4.1.6 Building envelope ..................... 12"
    "4.1.6.1 Building height ..................... 12"
    "4.1.6.2 Building setbacks ................... 12"
    """
    toc_pattern = r'^(\d+(?:\.\d+)+[A-Z]?)\s+(.+?)\s+\.+\s+(\d+)$'

    section_map = {}  # {section: (title, page)}

    for item in json_data:
        if item['type'] == 'text':
            text = item['text'].strip()
            match = re.match(toc_pattern, text)
            if match:
                section, title, page = match.groups()
                section_map[section] = (title, int(page))

    return section_map

def match_provisions_to_sections(provisions, section_map):
    """
    Match provisions to sections by page range
    Section 4.1.6 on page 12 covers provisions on pages 12-13
    (until next section starts)
    """
    # Sort sections by page
    # For each provision, find section that covers its page
    # Update pdf_section
```

**Output:**
- `section_map.json` for each document
- Updated `pdf_section` for ~20-30% more provisions

**Estimated Time:** 2 hours

---

### **Step 3: Implement Pass 3 - Heading Hierarchy**

**Task:** Infer sections from heading levels

**Algorithm:**
```python
def build_heading_hierarchy(json_data):
    """
    Track heading context as we traverse document:

    text_level=1: "4.1 Low Density Residential"  → current_h1 = "4.1"
    text_level=2: "4.1.6 Building envelope"      → current_h2 = "4.1.6" (parent: 4.1)
    text_level=3: "4.1.6.2 Building setbacks"    → current_h3 = "4.1.6.2" (parent: 4.1.6)
    text_level=4: (content)                      → belongs to 4.1.6.2
    """
    heading_stack = {}  # {level: section_number}

    for item in json_data:
        level = item.get('text_level')
        text = item.get('text', '')

        if level in [1, 2, 3]:  # Heading levels
            section = extract_section_number(text)
            if section:
                heading_stack[level] = section
                # Clear lower levels
                for l in range(level + 1, 10):
                    heading_stack.pop(l, None)

        # Current context for this item
        current_section = heading_stack.get(min(heading_stack.keys()))

    return hierarchy
```

**Output:**
- Hierarchical section relationships
- `pdf_extra.hierarchy` = ["4.1", "4.1.6", "4.1.6.2"]
- Updated `pdf_section` for ~15-25% more provisions

**Estimated Time:** 2 hours

---

### **Step 4: Implement Pass 4 - Reference Number Mapping**

**Task:** Mine existing `ref_number` field for section numbers

**Algorithm:**
```python
def extract_section_from_ref_number(ref_number):
    """
    Clean patterns:
    - "4.1.6.2" → "4.1.6.2" ✓
    - "C8" → "C8" ✓
    - "table in 4.1.6.2 Building setbacks" → "4.1.6.2" ✓
    - "Schedule 1 Part 2" → "Schedule 1" ✓
    - "Design solutions for additions" → None (descriptive, not a section)
    """
    # Pattern 1: Extract from "table in X.X.X"
    match = re.search(r'table in (\\d+(?:\\.\\d+)+)', ref_number, re.I)
    if match:
        return match.group(1)

    # Pattern 2: Direct section number
    match = re.match(r'^(\\d+(?:\\.\\d+)+[A-Z]?)\\s', ref_number)
    if match:
        return match.group(1)

    # Pattern 3: Control code
    match = re.match(r'^([A-Z]\\d+[A-Z]?)$', ref_number.strip())
    if match:
        return match.group(1)

    return None
```

**Output:**
- Updated `pdf_section` for ~20-30% more provisions
- No database structure changes needed

**Estimated Time:** 1 hour

---

### **Step 5: Validate & Commit**

**Task:** Verify accuracy and commit results

**Validation:**
```sql
-- Check coverage increase
SELECT COUNT(*) FILTER (WHERE pdf_section IS NOT NULL) * 100.0 / COUNT(*)
FROM regulatory_provisions;

-- Sample random provisions per document
SELECT document_id, pdf_section, ref_number, pdf_page
FROM regulatory_provisions
WHERE pdf_section IS NOT NULL
ORDER BY RANDOM()
LIMIT 50;

-- Check for suspicious patterns (likely errors)
SELECT pdf_section, COUNT(*)
FROM regulatory_provisions
WHERE pdf_section ~ '^[^0-9A-Z]'  -- Starts with invalid character
GROUP BY pdf_section;
```

**Output:**
- Validation report showing before/after coverage
- Sample verification dataset
- Error rate analysis

**Estimated Time:** 1 hour

---

## Success Criteria

### **Must Have:**
- ✅ 60%+ provisions have `pdf_section` (13,589+)
- ✅ Zero false positives in sample of 100
- ✅ All 4 passes implemented and tested
- ✅ Database indexes perform well

### **Nice to Have:**
- ✅ 80%+ coverage (18,118+)
- ✅ `pdf_extra.hierarchy` populated
- ✅ Section → parent relationships queryable
- ✅ Confidence scores for extracted sections

---

## Alternative Approaches (Not Recommended)

### **Alternative 1: Full Re-extraction with Better Parser**
- Re-run MinerU with better section detection
- **Pros:** Clean slate, can use latest tools
- **Cons:** Very expensive (~$100-500), time consuming, may not improve much

### **Alternative 2: Manual Tagging**
- Hire annotators to tag sections
- **Pros:** 100% accurate
- **Cons:** Expensive, slow, not scalable

### **Alternative 3: Regex-Only Approach**
- Just use regex on `ref_number` and `provision_text`
- **Pros:** Fast, simple
- **Cons:** Lower coverage (~30%), misses context

---

## Technical Specifications

### **New Script:** `migrations/enhance_pdf_sections.py`

```python
#!/usr/bin/env python3
"""
Phase 4: Enhance PDF Section Number Extraction
==============================================
Multi-pass approach to increase section coverage from 2.4% to 60%+

Passes:
1. TOC mining (section → page mapping)
2. Heading hierarchy inference (text_level tracking)
3. Reference number mapping (clean ref_number)
4. Parent-child relationships (pdf_extra.hierarchy)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_safety_wrapper import get_safe_connection

class SectionEnhancer:
    def __init__(self):
        self.conn = get_safe_connection()
        self.cursor = self.conn.cursor()

    def pass_1_analyze(self):
        """Analyze current state"""
        pass

    def pass_2_toc_mining(self):
        """Extract from table of contents"""
        pass

    def pass_3_heading_hierarchy(self):
        """Infer from heading levels"""
        pass

    def pass_4_ref_number_mapping(self):
        """Mine existing ref_numbers"""
        pass

    def validate(self):
        """Validate accuracy"""
        pass

    def run(self):
        """Execute all passes"""
        print("Phase 4: PDF Section Enhancement")
        print("="*80)

        self.pass_1_analyze()
        self.pass_2_toc_mining()
        self.pass_3_heading_hierarchy()
        self.pass_4_ref_number_mapping()
        self.validate()

if __name__ == "__main__":
    enhancer = SectionEnhancer()
    enhancer.run()
```

---

## Timeline Estimate

| Task | Time | Cumulative |
|------|------|------------|
| Analyze current data | 30 min | 30 min |
| Implement TOC mining | 2 hrs | 2.5 hrs |
| Implement hierarchy inference | 2 hrs | 4.5 hrs |
| Implement ref_number mapping | 1 hr | 5.5 hrs |
| Validation & testing | 1 hr | 6.5 hrs |
| **Total** | **~7 hours** | - |

**Recommended Approach:** Implement incrementally, commit after each pass

---

## Next Steps

1. **Create analysis script** to understand current data
2. **Implement Pass 2 (TOC mining)** - highest ROI
3. **Test on 1 document** before running on all 112
4. **Validate results** with manual spot checks
5. **Commit and push** after each successful pass
6. **Update frontend** to display pdf_section (Phase 3)

---

## Questions to Resolve

1. **Should we store hierarchy in `pdf_extra` or separate table?**
   - Recommendation: `pdf_extra` (simpler, already indexed)

2. **What to do with ambiguous sections?**
   - Store confidence score in `pdf_extra.section_confidence`

3. **How to handle multi-document provisions?**
   - Rare case, pick primary document's section

4. **Should we backfill or run forward-only?**
   - Backfill (update existing rows, don't create new)

---

**Ready to proceed with Phase 4 implementation?**
