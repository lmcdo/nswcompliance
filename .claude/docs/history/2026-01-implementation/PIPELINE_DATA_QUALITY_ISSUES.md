# Pipeline Data Quality Issues

**Purpose:** Track data extraction and processing errors that need cleanup in future pipeline optimization branches.

**Status:** Active tracking - fix in dedicated data-quality branch when ready

---

## Critical Issues

### Issue #001: PDF Page Number Artifacts in Clause Titles

**Discovered:** 2025-08-30 
**Severity:** High - affects all DCP clause references 
**Status:** Identified, not fixed 

**Problem:**
MinerU PDF extraction is appending page numbers to clause titles, corrupting regulatory references throughout the system.

**Examples:**
```
 Current: "4.2.4.2 Building heights . 5"
 Should be: "4.2.4.2 Building heights"

 Current: "4.2.4.3 Building setbacks.. 5" 
 Should be: "4.2.4.3 Building setbacks"

 Current: "4.2.4.1 Floor space ratio and site coverage . /4"
 Should be: "4.2.4.1 Floor space ratio and site coverage"

 Current: "Parking and access .... .. 10"
 Should be: "Parking and access"
```

**Root Cause:**
- **File:** `prp_complete_missing_extractions.py`
- **Function:** `extract_with_mineru()` (line 110-149)
- **Command:** `mineru -p '{wsl_pdf_path}' -o {wsl_output_path} -m auto`
- **Issue:** Page numbers (5, 10, 13, etc.) are being extracted as part of clause text

**Impact Scope:**
- **Identified in:** AutoSchemaKG knowledge graph data
- **Identified in:** Triple CSV exports 
- **Identified in:** Frontend API responses
- **Identified in:** LightRAG processed content
- **Potentially affects:** All regulatory clause references across system

**Affected Files:**
```
autoschemakg_data_ollama_final/nsw_planning_docs_014.json
autoschemakg_output/triples_csv/triple_nodes_nsw_planning_docs_from_json_without_emb.csv
.claude/NSW Planning Compliance Engine output.txt
[and many others across processing pipeline]
```

**Fix Strategy:**
```python
# Regex pattern to clean page number artifacts
import re
cleaned_text = re.sub(r'\s*\.+\s*/?\d+$', '', original_text)
```

**Proposed Fix Locations:**
1. **Option A:** Post-MinerU cleanup in `prp_complete_missing_extractions.py` after line 132
2. **Option B:** Pre-processing cleanup in RagAnything pipeline before clause parsing
3. **Option C:** AutoSchemaKG input sanitization before knowledge graph creation

**Priority:** High - needs dedicated branch for systematic cleanup

---

## Moderate Issues

### Issue #002: [Reserved for next data quality issue]

**Template for new issues:**
```markdown
### Issue #XXX: [Brief description]

**Discovered:** YYYY-MM-DD 
**Severity:** [Critical|High|Moderate|Low] 
**Status:** [ Identified| In Progress| Fixed| Deferred]

**Problem:**
[Detailed description]

**Examples:**
[Specific examples with before/after]

**Root Cause:**
[File, function, line numbers where issue originates]

**Impact Scope:**
[What parts of system are affected]

**Fix Strategy:**
[Code snippets or approach for fix]

**Priority:** [High|Medium|Low]
```

---

## Issue Summary

| ID | Description | Severity | Status | Priority |
|----|-------------|----------|---------|----------|
| 001 | PDF page number artifacts in clause titles | High | Identified | High |

---

## Cleanup Branch Strategy

**Recommended approach:**
1. Create dedicated `data-quality-fixes` branch
2. Implement fixes in order of priority
3. Run full regression testing on knowledge graph outputs 
4. Verify council setback calculator accuracy after cleanup
5. Update data validation procedures to catch similar issues

**Testing Requirements:**
- [ ] Verify clause references are clean in API responses
- [ ] Check knowledge graph data integrity
- [ ] Validate setback calculator regulatory citations
- [ ] Ensure no functional regressions in existing features

---

**Last Updated:** 2025-08-30 
**Next Review:** When ready for data quality sprint