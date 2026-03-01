# DCP General Provisions Extraction Standard
## Universal Best Practices for All LGAs

**Version:** 1.0
**Date:** 2025-10-31
**Status:** Production Standard

---

## Purpose

This document defines the proven, professional-practice-aligned methodology for extracting DCP general provisions across ALL LGAs. Based on successful extractions of Marrickville, Leichhardt, and Ashfield DCPs.

---

## Core Principles

### 1. Professional Practice Alignment
**How planners actually use DCPs:**
- ✅ Filter by **former council area** (in amalgamated LGAs)
- ✅ Filter by **development type** (dwelling house, RFB, multi-dwelling)
- ❌ **DO NOT filter general provisions by zone** (zones determine permitted uses via LEP, not which DCP provisions apply)

### 2. Data Hierarchy
```
Former Council Area (mandatory filter)
    ↓
Development Type (optional filter - some councils apply to ALL)
    ↓
General Provisions (apply broadly within council area)
    ↓
Precinct/Neighbourhood Provisions (geographic - add to or override general)
```

### 3. CLAUDE.md Compliance
- ✅ Batch processing (50 provisions per batch)
- ✅ Progress reporting (after every batch)
- ✅ Output validation (success rate tracking)
- ✅ No truncation (full text processing)
- ✅ Failure detection (stop after 2 consecutive batch failures)

---

## Database Schema Requirements

### dcp_general_requirements Table

**Core Fields:**
```sql
-- Identification
id                          SERIAL PRIMARY KEY
lga                         TEXT NOT NULL            -- 'Inner West'
former_council              TEXT NOT NULL            -- 'Ashfield' | 'Marrickville' | 'Leichhardt'

-- Filtering (Professional Practice)
development_types           TEXT[]                   -- ['dwelling_house'] | ['ALL']
applicable_zones            TEXT[]                   -- NULL (not used for general provisions)

-- Content
requirement_text            TEXT NOT NULL            -- Extracted actionable requirement
category                    TEXT                     -- 'setbacks' | 'parking' | 'landscaping' | etc.
subcategory                 TEXT                     -- Optional sub-categorization

-- Metadata (Part/Section Info)
part_number                 TEXT                     -- 'Part 1' | 'Section 2.10'
part_name                   TEXT                     -- 'Dwelling Houses' | 'Parking'
dcp_chapter                 TEXT                     -- 'F' | '2' | 'C'

-- Source Traceability
source_provision_ids        INTEGER[]                -- Links to regulatory_provisions
primary_source_provision_id INTEGER                  -- Primary source provision

-- PDF References (MANDATORY)
pdf_page                    INTEGER                  -- Page number in PDF
pdf_page_image_url          TEXT                     -- URL to page image
pdf_path                    TEXT                     -- Path to source PDF file

-- Quality Metadata
confidence                  TEXT                     -- 'high' | 'medium' | 'low'
processing_version          TEXT                     -- Extraction version
created_at                  TIMESTAMP DEFAULT NOW()
updated_at                  TIMESTAMP DEFAULT NOW()
```

**Key Changes from Original Approach:**
- ❌ **REMOVED:** `applicable_zones` filtering for general provisions
- ✅ **ADDED:** `development_types` array (only field that filters)
- ✅ **MANDATORY:** PDF metadata (page, image URL, path)
- ✅ **MANDATORY:** Source provision linking

---

## Council-Specific Tagging

### Ashfield DCP 2016 - Chapter F (Development Categories)

**Structure:** Development-type specific parts

| Part | Name | Development Types | Zones | Apply To |
|------|------|-------------------|-------|----------|
| Part 1 | Dwelling Houses | `['dwelling_house']` | NULL | All Ashfield dwelling houses |
| Part 2 | Secondary Dwellings | `['secondary_dwelling']` | NULL | All Ashfield secondary dwellings |
| Part 3 | Neighbourhood Shops | `['shop', 'neighbourhood_shop']` | NULL | All Ashfield neighbourhood shops |
| Part 4 | Multi Dwelling Housing | `['multi_dwelling_housing', 'dual_occupancy', 'townhouse', 'manor_house', 'attached_dwelling']` | NULL | All Ashfield multi-dwelling |
| Part 5 | Residential Flat Buildings | `['residential_flat_building', 'shop_top_housing']` | NULL | All Ashfield RFBs |
| Part 6 | Boarding Houses | `['boarding_house', 'student_accommodation']` | NULL | All Ashfield boarding houses |
| Part 7 | Residential Care | `['residential_care_facility', 'seniors_housing']` | NULL | All Ashfield care facilities |
| Part 8 | Child Care Centres | `['child_care_centre']` | NULL | All Ashfield child care |
| Part 9 | Drive-In Take-Away | `['food_and_drink_premises', 'take_away_food']` | NULL | All Ashfield take-away |
| Part 10 | Sex Industry | `['sex_services_premises']` | NULL | All Ashfield sex services |

**Tagging Logic:**
```python
development_types = PART_METADATA['dev_types']  # From Part structure
applicable_zones = None  # Not used for general provisions
```

---

### Marrickville DCP 2011 - Part 2 (General Development Controls)

**Structure:** General provisions apply to ALL development

| Section | Name | Development Types | Zones | Apply To |
|---------|------|-------------------|-------|----------|
| 2.1 | Urban Design | `['ALL']` | NULL | All Marrickville development |
| 2.3 | Site Context Analysis | `['ALL']` | NULL | All Marrickville development |
| 2.5 | Access & Mobility | `['ALL']` | NULL | All Marrickville development |
| 2.6 | Privacy | `['ALL']` | NULL | All Marrickville development |
| 2.7 | Solar Access | `['ALL']` | NULL | All Marrickville development |
| 2.10 | Parking | `['ALL']` | NULL | All Marrickville development |
| 2.11 | Fencing | `['ALL']` | NULL | All Marrickville development |
| 2.12 | Signage | `['ALL']` | NULL | All Marrickville development |
| 2.13 | Biodiversity | `['ALL']` | NULL | All Marrickville development |
| 2.16 | Energy Efficiency | `['ALL']` | NULL | All Marrickville development |
| 2.17 | Water Sensitive Design | `['ALL']` | NULL | All Marrickville development |
| 2.18 | Landscaping | `['ALL']` | NULL | All Marrickville development |
| 2.25 | Stormwater | `['ALL']` | NULL | All Marrickville development |

**Tagging Logic:**
```python
development_types = ['ALL']  # Applies to all development
applicable_zones = None  # Not used for general provisions
```

---

### Leichhardt DCP 2013 - Parts A-F (General Provisions)

**Structure:** General provisions apply to ALL development

| Part | Name | Development Types | Zones | Apply To |
|------|------|-------------------|-------|----------|
| Part A | Administration | `['ALL']` | NULL | All Leichhardt development |
| Part B | Heritage | `['ALL']` | NULL | All Leichhardt development |
| Part C.1 | General Controls | `['ALL']` | NULL | All Leichhardt development |
| Part D | Development Types | `['ALL']` | NULL | All Leichhardt development |
| Part E | Environmental | `['ALL']` | NULL | All Leichhardt development |
| Part F | Food/Waste | `['ALL']` | NULL | All Leichhardt development |

**Tagging Logic:**
```python
development_types = ['ALL']  # Applies to all development
applicable_zones = None  # Not used for general provisions
```

---

## Extraction Process (Standard Workflow)

### Step 1: Source Data Verification

**Check regulatory_provisions table:**
```sql
SELECT id, document_id, section_header, page_number,
       pdf_page, pdf_page_image_url, pdf_source_file
FROM regulatory_provisions
WHERE document_id ILIKE '%[council_name]%'
  AND document_id NOT LIKE '%precinct%'
  AND document_id NOT LIKE '%neighbourhood%'
ORDER BY id;
```

**Verify:**
- ✅ Provisions exist for all Parts/Sections
- ✅ PDF metadata is populated (page_number, pdf_page, pdf_page_image_url)
- ✅ Provision text is complete (not truncated)

---

### Step 2: LLM Prompt (Standard Template)

```python
prompt = f"""Extract planning requirements from {council_name} DCP {part_name}.

REQUIREMENTS:
- Extract ALL actionable development controls from the text below
- Include ONLY specific rules/standards (not objectives, definitions, or explanatory text)
- Each requirement must be a complete, standalone control

Return valid JSON array:
[
  {{"requirement_text": "exact text of requirement", "category": "setbacks|parking|landscaping|building_design|building_height|heritage|accessibility|sustainability|privacy|solar_access|fencing|signage|waste_management|energy|water|biodiversity|other"}},
  ...
]

CRITICAL: Return ONLY the JSON array. No markdown, no explanation.

Text to process:
{batch_text}
"""
```

**LLM Configuration:**
```python
model = "gpt-4o-mini"
temperature = 0  # Deterministic
messages = [
    {"role": "system", "content": "You extract planning requirements and return ONLY valid JSON arrays. No markdown, no explanation."},
    {"role": "user", "content": prompt}
]
```

---

### Step 3: Batch Processing (CLAUDE.md Compliant)

```python
BATCH_SIZE = 50  # Per CLAUDE.md rules

for i in range(0, input_count, BATCH_SIZE):
    batch = provisions[i:i+BATCH_SIZE]
    batch_num = i // BATCH_SIZE + 1
    batch_start = i + 1
    batch_end = min(i + BATCH_SIZE, input_count)

    # MANDATORY: Progress reporting
    print(f"Processing batch {batch_num}/{total_batches} (items {batch_start}-{batch_end} of {input_count})")

    # Build batch text - NO TRUNCATION
    batch_text = "\n\n".join([
        f"[Section: {p.section_header}]\n{p.provision_text}"
        for p in batch
    ])

    # LLM extraction
    batch_requirements = process_batch_with_llm(batch, part_name, batch_num, total_batches)

    # MANDATORY: Failure detection
    if not batch_requirements:
        failed_batches += 1
        if failed_batches > 2:
            print(f"❌ CRITICAL FAILURE: {failed_batches} consecutive batches failed")
            break
    else:
        print(f"✅ Batch results: {len(batch_requirements)} requirements")
        all_requirements.extend(batch_requirements)
        failed_batches = 0

    time.sleep(1)  # Rate limiting
```

---

### Step 4: Metadata Enrichment

**For each extracted requirement, add:**

```python
for req in batch_requirements:
    # From LLM
    req_text = req.get('requirement_text', '')
    category = req.get('category', 'other')

    # From Part/Section metadata (predefined)
    req['development_types'] = part_metadata['dev_types']
    req['applicable_zones'] = None  # Not used for general provisions
    req['part_number'] = part_metadata['part']
    req['part_name'] = part_metadata['name']

    # From source provision (matched by text)
    source_prov = match_source_provision(req_text, batch_provisions)
    req['source_prov_id'] = source_prov.id
    req['pdf_page'] = source_prov.pdf_page or source_prov.page_number
    req['pdf_page_image_url'] = source_prov.pdf_page_image_url
    req['pdf_source_file'] = source_prov.pdf_source_file
```

**Source Provision Matching:**
```python
def match_source_provision(req_text, provisions):
    """Match requirement to source provision by text overlap"""
    req_start = req_text[:100]  # First 100 chars

    for prov in provisions:
        if req_start in prov.provision_text:
            return prov

    # Default to first provision if no match
    return provisions[0]
```

---

### Step 5: Database Import

```python
for req in all_requirements:
    cur.execute('''
        INSERT INTO dcp_general_requirements
            (requirement_text, category, part_number, part_name,
             lga, former_council,
             development_types, applicable_zones,
             source_provision_ids, primary_source_provision_id,
             pdf_page, pdf_page_image_url, pdf_path,
             confidence, processing_version)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        req['requirement_text'][:1000],
        req['category'],
        req['part_number'],
        req['part_name'],
        lga,
        former_council,
        req['development_types'],     # TEXT[] - e.g., ['dwelling_house'] or ['ALL']
        None,                          # applicable_zones - NULL for general provisions
        [req['source_prov_id']],      # INTEGER[]
        req['source_prov_id'],
        req['pdf_page'],
        req['pdf_page_image_url'],
        req['pdf_source_file'],
        'high',                        # confidence
        'v1.0'                         # processing_version
    ))

conn.commit()
```

---

### Step 6: Validation (MANDATORY)

**Per-Part Validation:**
```python
output_count = len(all_requirements)
success_rate = (output_count / input_count * 100) if input_count > 0 else 0

print(f"VALIDATION: {part_name}")
print(f"  Input: {input_count} provisions")
print(f"  Output: {output_count} requirements")
print(f"  Success rate: {success_rate:.1f}%")

if success_rate < 50:
    print(f"  ❌ CRITICAL FAILURE: Success rate below 50%")
elif success_rate < 80:
    print(f"  ⚠️  WARNING: Success rate below 80%")
else:
    print(f"  ✅ Success rate acceptable")
```

**Final Database Verification:**
```python
cur.execute('''
    SELECT
        COUNT(*) as total,
        COUNT(CASE WHEN development_types IS NOT NULL
                   AND array_length(development_types, 1) > 0 THEN 1 END) as has_devtypes,
        COUNT(pdf_page) as has_pdf_page,
        COUNT(pdf_page_image_url) as has_pdf_url,
        COUNT(source_provision_ids) as has_source_ids
    FROM dcp_general_requirements
    WHERE former_council = %s
''', (former_council,))

row = cur.fetchone()
total, has_devtypes, has_pdf, has_url, has_source = row

print(f"Database verification:")
print(f"  Total requirements: {total}")
print(f"  Has development_types: {has_devtypes}/{total} ({has_devtypes/total*100:.1f}%)")
print(f"  Has pdf_page: {has_pdf}/{total} ({has_pdf/total*100:.1f}%)")
print(f"  Has pdf_page_image_url: {has_url}/{total} ({has_url/total*100:.1f}%)")
print(f"  Has source_provision_ids: {has_source}/{total} ({has_source/total*100:.1f}%)")

# PASS criteria
if has_devtypes == total and has_pdf == total and has_url == total and has_source == total:
    print(f"✅ SUCCESS: All requirements have complete metadata")
else:
    print(f"❌ FAILURE: Missing metadata")
```

---

## API Query Logic (Standard)

### Frontend Request
```typescript
interface DCPRequest {
  address: string;
  coordinates: { lat: number; lon: number };
  developmentType: string;  // e.g., 'dual_occupancy'
  lga: string;               // e.g., 'Inner West'
}
```

### Backend Query
```typescript
// Step 1: Determine former council from address
const formerCouncil = determineFormerCouncilArea(address, lga);
// Returns: 'Ashfield' | 'Marrickville' | 'Leichhardt'

// Step 2: Get general requirements
const generalRequirements = await query(`
    SELECT
        requirement_text, category, subcategory,
        part_number, part_name,
        pdf_page, pdf_page_image_url, pdf_path
    FROM dcp_general_requirements
    WHERE former_council = $1
    AND (
        'ALL' = ANY(development_types)        -- Matches Marrickville/Leichhardt
        OR $2 = ANY(development_types)        -- Matches Ashfield specific types
    )
    ORDER BY category, part_number
`, [formerCouncil, developmentType]);

// Step 3: Get precinct requirements (if property in precinct)
const precinctId = await getPrecinctId(coordinates);
if (precinctId) {
    const precinctRequirements = await query(`
        SELECT ...
        FROM dcp_precinct_requirements
        WHERE precinct_id = $1
    `, [precinctId]);
}

// Step 4: Return combined
return {
    general: generalRequirements,    // Base requirements
    precinct: precinctRequirements,  // Add/override general
    combined: [...general, ...precinct]
};
```

---

## Expected Success Rates

**Normal rates by DCP structure:**

| Council | DCP Style | Expected Rate | Reason |
|---------|-----------|---------------|--------|
| Ashfield Chapter F | Performance-based with objectives | 10-30% | Lots of explanatory text, objectives |
| Marrickville Part 2.X | Mix of controls and context | 20-40% | Controls + objectives + explanatory |
| Leichhardt Parts A-F | General provisions | 20-40% | Similar to Marrickville |

**These rates are CORRECT behavior** - we filter OUT:
- ❌ Table of Contents
- ❌ "Objective O1: To ensure..."
- ❌ "Purpose: This guideline aims to..."
- ❌ "Application: This part applies to..."
- ✅ KEEP: "Minimum side setback of 900mm required"
- ✅ KEEP: "Site coverage must not exceed 50%"

---

## Common Pitfalls & Solutions

### Pitfall 1: Over-filtering by zone
**Problem:** Trying to tag general provisions with specific zones
**Solution:** Set `applicable_zones = NULL` for all general provisions

### Pitfall 2: Missing PDF metadata
**Problem:** Requirements imported without page numbers/URLs
**Solution:** Always fetch PDF metadata from regulatory_provisions and link

### Pitfall 3: Truncating batch text
**Problem:** LLM only sees partial provision text
**Solution:** Process full text, NO truncation (CLAUDE.md rule)

### Pitfall 4: Not validating output
**Problem:** Silent failures where 0 requirements extracted
**Solution:** Track success rate, fail loudly if < 50%

### Pitfall 5: Losing source traceability
**Problem:** Can't link requirement back to source provision
**Solution:** Match by text overlap, store in `source_provision_ids`

---

## File Naming Convention

**Extraction Scripts:**
```
extract_{council}_{section}_COMPLIANT.py
```
Examples:
- `extract_ashfield_chapter_f_COMPLIANT.py`
- `extract_marrickville_general_COMPLIANT.py`
- `extract_leichhardt_general_COMPLIANT.py`

**Output JSON (if needed):**
```
{council}_{section}_requirements_{date}.json
```
Examples:
- `ashfield_chapter_f_requirements_20251031.json`
- `marrickville_part2_requirements_20251031.json`

---

## Quality Checklist

Before declaring extraction complete, verify:

- [ ] All Parts/Sections processed (none skipped)
- [ ] Success rate ≥ 50% overall (80% excellent)
- [ ] 100% have `development_types` populated
- [ ] 100% have `pdf_page` populated
- [ ] 100% have `pdf_page_image_url` populated
- [ ] 100% have `source_provision_ids` populated
- [ ] Sample manual check: 10 random requirements are accurate
- [ ] API query returns results for test addresses
- [ ] Frontend displays requirements with PDF links

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-31 | Initial standard based on Marrickville/Leichhardt/Ashfield extractions |

---

## References

- CLAUDE.md - Data processing rules
- Ashfield DCP 2016 - Chapter F structure
- Marrickville DCP 2011 - Part 2 structure
- Leichhardt DCP 2013 - Parts A-F structure
- Professional planning practice guidelines
