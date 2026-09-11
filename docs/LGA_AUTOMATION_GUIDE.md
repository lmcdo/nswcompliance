# LGA Implementation Automation Guide

This guide documents the complete process for adding a new LGA (Local Government Area) to the compliance engine, derived from reverse-engineering the Inner West (Leichhardt, Ashfield, Marrickville) implementation.

## System Overview

```
PDF Documents → Extraction → Database → Enrichment → API → Frontend
```

### Data Flow Summary

1. **Extraction**: PDF → raw provisions in `regulatory_provisions` table
2. **Enrichment**: Tag provisions with layer, topic, type, conditions
3. **Precinct Setup**: Define precinct boundaries for location-based filtering
4. **API Layer**: Serve filtered provisions based on property attributes
5. **Frontend**: Display provisions organized by TOC structure with filtering

---

## Phase 1: Document Analysis (Manual - 2-4 hours)

### 1.1 Obtain DCP Document

```bash
# Store in data/pdfs/{council}/
mkdir -p data/pdfs/{council_name}
# Download or copy DCP PDF to this location
```

### 1.2 Analyze DCP Structure

Create a structure map identifying:

| Part | Content Type | Layer | Applicability |
|------|--------------|-------|---------------|
| Part A | Administrative | generic | ALL |
| Part 2.x | General controls | generic | ALL |
| Part 4.x | Dev-type specific | use_specific | Zone-filtered |
| Part 8 | Heritage | condition | Heritage sites only |
| Part 9.x | Precincts | precinct | Location-filtered |

**Layer Types:**
- `generic`: Applies to ALL development (parking, landscaping, etc.)
- `use_specific`: Filtered by zone/development type
- `condition`: Filtered by site condition (heritage, flood, bushfire)
- `precinct`: Filtered by geographic location

### 1.3 Identify Topic Markers

Look for structural patterns in the DCP that indicate topics:

**Pattern Type 1: Section Numbers (Marrickville)**
```
2.6 Privacy → topic: privacy
2.7 Solar Access → topic: solar
2.10 Parking → topic: parking
```

**Pattern Type 2: Control Markers (Leichhardt)**
```
C3 → parking
C29 → privacy
C30 → solar
C37 → heritage
```

**Pattern Type 3: Chapter Headers (Ashfield)**
```
Chapter E1 Heritage → topic: heritage
Chapter F Part 1 Dwelling Houses → topic: residential
```

Document these mappings for use in configuration.

---

## Phase 2: Configuration (1-2 hours)

### 2.1 Create Council Config

Create `enrichment/config/{council}_config.py`:

```python
"""
{Council} DCP {Year} Configuration

Structure:
- Part A: Introduction - administrative, applies to ALL
- Part B: General Controls - applies to ALL
- Part C: Development Types - zone/dev-type specific
- Part D: Heritage - heritage sites only
- Part E: Precincts - location-filtered
"""

# Standard NSW zone codes
RESIDENTIAL_ZONES = ['R1', 'R2', 'R3', 'R4', 'R5']
BUSINESS_ZONES = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8']
INDUSTRIAL_ZONES = ['IN1', 'IN2', 'IN3', 'IN4']

ALL_ZONES = ['ALL']
ALL_DEV_TYPES = ['ALL']

{COUNCIL}_CONFIG = {
    "council": "{council}",
    "dcp_name": "{Council} DCP {Year}",

    "parts": {
        # Generic parts (apply to ALL)
        "Part A": {
            "description": "Introduction",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Use-specific parts (zone/dev-type filtered)
        "Part C": {
            "description": "Residential Development",
            "applicable_zones": RESIDENTIAL_ZONES,
            "applicable_dev_types": ["dwelling_house", "dual_occupancy"],
            "site_conditions": None,
        },

        # Condition parts (site condition filtered)
        "Part D": {
            "description": "Heritage",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": ["heritage"],
        },

        # Precinct parts (location filtered)
        "Part E": {
            "description": "Precincts",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
            "is_precinct_specific": True,
        },
    },

    # Topic mappings (if using section numbers or markers)
    "topic_markers": {
        # Section number → topic
        "2.6": "privacy",
        "2.7": "solar",
        "2.10": "parking",
        # OR control markers
        "C3": "parking",
        "C29": "privacy",
    },

    # Precinct definitions
    "precincts": {
        "E_1": {"name": "Town Centre", "precinct_number": 1},
        "E_2": {"name": "Industrial Area", "precinct_number": 2},
    },
}
```

### 2.2 Update Layer Topic Tagger

Add council-specific tagging logic to `enrichment/extractors/layer_topic_tagger.py`:

```python
def _tag_{council}(self, document_id: str, provision_text: str) -> Tuple[str, str, Optional[str]]:
    """Tag {Council} provision."""
    doc = document_id or ''

    # Part D - Heritage (condition)
    if 'Part D' in doc or 'Part_D' in doc:
        return ('condition', 'Part D', 'heritage')

    # Part E - Precincts (location-filtered)
    if 'Part E' in doc or 'Precinct' in doc:
        topic = self._extract_topic_from_text(provision_text)
        return ('precinct', 'Part E', topic)

    # Part C - Residential (use-specific)
    if 'Part C' in doc:
        topic = self._extract_topic_from_text(provision_text)
        return ('use_specific', 'Part C', topic)

    # Default to generic
    topic = self._extract_topic_from_text(provision_text)
    return ('generic', 'Part A', topic)
```

---

## Phase 3: PDF Extraction (2-4 hours)

### 3.1 Extraction Script Template

Create `scripts/extract_{council}_dcp.py`:

```python
#!/usr/bin/env python3
"""
Extract {Council} DCP provisions from PDF.

Usage:
    python scripts/extract_{council}_dcp.py --pdf data/pdfs/{council}/{dcp}.pdf
"""

import os
import sys
import argparse
import pdfplumber
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def extract_provisions(pdf_path: str, dry_run: bool = False):
    """Extract provisions from PDF and insert into database."""

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    with pdfplumber.open(pdf_path) as pdf:
        current_section = None
        provisions = []

        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue

            # Parse page content
            # This is council-specific - adapt based on DCP structure
            lines = text.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Detect section headers (adapt pattern)
                if is_section_header(line):
                    current_section = line
                    continue

                # Skip non-provision content
                if is_boilerplate(line):
                    continue

                # Create provision record
                provision = {
                    'document_id': generate_document_id(current_section),
                    'section_header': current_section,
                    'provision_text': line,
                    'pdf_page': page_num,
                    'is_current': True,
                }
                provisions.append(provision)

        print(f"Extracted {len(provisions)} provisions")

        if not dry_run:
            # Insert provisions
            for prov in provisions:
                cur.execute("""
                    INSERT INTO regulatory_provisions
                    (document_id, section_header, provision_text, pdf_page, is_current)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    prov['document_id'],
                    prov['section_header'],
                    prov['provision_text'],
                    prov['pdf_page'],
                    prov['is_current'],
                ))

            conn.commit()
            print(f"Inserted {len(provisions)} provisions")

    cur.close()
    conn.close()

def is_section_header(line: str) -> bool:
    """Detect section headers. Adapt for council-specific patterns."""
    import re
    # Example: "2.6 Privacy" or "Part C Section 1"
    return bool(re.match(r'^(\d+\.?\d*\s+[A-Z]|Part\s+[A-Z])', line))

def is_boilerplate(line: str) -> bool:
    """Detect boilerplate content to skip."""
    boilerplate_patterns = [
        r'^Page\s+\d+',
        r'^\d+$',  # Page numbers
        r'^{Council}\s+DCP',  # Header/footer
    ]
    import re
    return any(re.match(p, line) for p in boilerplate_patterns)

def generate_document_id(section: str) -> str:
    """Generate document_id from section header."""
    # Example: "2.6 Privacy" → "{Council}_DCP_{Year}_2_6_Privacy"
    import re
    if not section:
        return "{Council}_DCP_{Year}_Unknown"

    clean = re.sub(r'[^a-zA-Z0-9\s]', '_', section)
    clean = re.sub(r'\s+', '_', clean)
    return f"{{Council}}_DCP_{{Year}}_{clean}"

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', required=True, help='Path to DCP PDF')
    parser.add_argument('--dry-run', action='store_true', help='Preview without inserting')
    args = parser.parse_args()

    extract_provisions(args.pdf, args.dry_run)
```

### 3.2 Extraction Quality Checks

After extraction, run these validation queries:

```sql
-- Count provisions by part
SELECT
    SUBSTRING(document_id FROM '{Council}_DCP_\d+_(.+?)_') as part,
    COUNT(*) as count
FROM regulatory_provisions
WHERE document_id ILIKE '%{Council}%'
GROUP BY 1
ORDER BY 2 DESC;

-- Check for empty provisions
SELECT COUNT(*)
FROM regulatory_provisions
WHERE document_id ILIKE '%{Council}%'
  AND (provision_text IS NULL OR provision_text = '');

-- Check page distribution
SELECT pdf_page, COUNT(*) as count
FROM regulatory_provisions
WHERE document_id ILIKE '%{Council}%'
GROUP BY 1
ORDER BY 1;
```

---

## Phase 4: Enrichment (1-2 hours)

### 4.1 Run Enrichment Pipeline

```bash
# 1. Layer + Topic tagging
python enrichment/pipeline.py --phase layer --limit 1000

# 2. Site condition tagging (heritage/flood/bushfire)
python enrichment/pipeline.py --phase site_condition

# 3. Type classification (control/objective/definition/note)
python enrichment/pipeline.py --phase type

# 4. Numeric rule extraction (heights, setbacks, percentages)
#    `--phase numeric` was DELETED 2026-09-11: it targeted v2_enriched_at /
#    v2_extracted_values, columns that exist on no table. The live path writes
#    v2_extracted_rules and is a separate pipeline:
python -m enrichment.rule_extraction_pipeline --phase deterministic --council <council>

# 5. Check status
python enrichment/pipeline.py --phase status
```

### 4.2 Validate Enrichment Quality

Create `scripts/validate_{council}_enrichment.py`:

```python
#!/usr/bin/env python3
"""Validate enrichment quality for {Council}."""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

def validate():
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    with conn.cursor() as cur:
        # Layer distribution
        cur.execute("""
            SELECT v2_dcp_layer, COUNT(*) as count
            FROM regulatory_provisions
            WHERE document_id ILIKE '%{Council}%' AND is_current = TRUE
            GROUP BY 1
        """)
        print("Layer Distribution:")
        for row in cur.fetchall():
            print(f"  {row['v2_dcp_layer']}: {row['count']}")

        # Topic distribution
        cur.execute("""
            SELECT v2_topic, COUNT(*) as count
            FROM regulatory_provisions
            WHERE document_id ILIKE '%{Council}%' AND is_current = TRUE
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 20
        """)
        print("\nTop 20 Topics:")
        for row in cur.fetchall():
            print(f"  {row['v2_topic']}: {row['count']}")

        # Check for NULL topics
        cur.execute("""
            SELECT COUNT(*) as count
            FROM regulatory_provisions
            WHERE document_id ILIKE '%{Council}%'
              AND is_current = TRUE
              AND v2_topic IS NULL
        """)
        null_count = cur.fetchone()['count']
        print(f"\nProvisions with NULL topic: {null_count}")

        # Part distribution
        cur.execute("""
            SELECT v2_dcp_part, COUNT(*) as count
            FROM regulatory_provisions
            WHERE document_id ILIKE '%{Council}%' AND is_current = TRUE
            GROUP BY 1
            ORDER BY 2 DESC
        """)
        print("\nPart Distribution:")
        for row in cur.fetchall():
            print(f"  {row['v2_dcp_part']}: {row['count']}")

    conn.close()

if __name__ == '__main__':
    validate()
```

### 4.3 Topic Accuracy Check

Use keyword matching to estimate topic accuracy:

```python
#!/usr/bin/env python3
"""Check topic accuracy using keyword matching."""

import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard',
    'height': r'\bheight|storey|floor\s+level|building\s+height',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space',
    'solar': r'\bsolar|overshadow|sunlight|daylight',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation',
    'landscaping': r'\blandscap|garden|planting|vegetation',
    'heritage': r'\bheritage|conservation|historic|contributory',
    'trees': r'\btree|canopy|arborist',
    'fencing': r'\bfenc|fence',
    # Add more as needed
}

def get_keyword_scores(text):
    if not text:
        return {}
    scores = {}
    text_lower = text.lower()
    for topic, pattern in TOPIC_KEYWORDS.items():
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            scores[topic] = len(matches)
    return scores

def check_accuracy():
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    keyword_match = 0
    no_keywords = 0
    wrong_topic = 0

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic
            FROM regulatory_provisions
            WHERE document_id ILIKE '%{Council}%'
              AND v2_topic IS NOT NULL
              AND is_current = TRUE
        """)

        for p in cur.fetchall():
            text = p['provision_text'] or ''
            assigned = p['v2_topic']

            scores = get_keyword_scores(text)

            if assigned in scores:
                keyword_match += 1
            elif not scores:
                no_keywords += 1
            else:
                wrong_topic += 1

    total = keyword_match + no_keywords + wrong_topic

    print(f"Topic Accuracy Analysis:")
    print(f"  Keyword match (100% accurate): {keyword_match} ({keyword_match/total*100:.1f}%)")
    print(f"  No keywords (~90% accurate): {no_keywords} ({no_keywords/total*100:.1f}%)")
    print(f"  Wrong topic (~70% accurate): {wrong_topic} ({wrong_topic/total*100:.1f}%)")

    # Estimate overall accuracy
    estimated_accurate = keyword_match * 1.0 + no_keywords * 0.90 + wrong_topic * 0.70
    print(f"\nEstimated overall accuracy: {estimated_accurate/total*100:.1f}%")

    conn.close()

if __name__ == '__main__':
    check_accuracy()
```

---

## Phase 5: Precinct Setup (2-4 hours)

### 5.1 Precinct Boundary Data

Precincts require GeoJSON boundaries for location-based filtering.

**Option A: NSW Planning Portal API**
```python
# Use NSW Planning Portal to get precinct boundaries
import requests

def get_precinct_boundaries(lga_code: str):
    url = f"https://api.planning.nsw.gov.au/precincts?lga={lga_code}"
    response = requests.get(url)
    return response.json()
```

**Option B: Manual GeoJSON**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "precinct_id": 1,
        "name": "Town Centre",
        "dcp_reference": "Part E Section 1"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[...]]
      }
    }
  ]
}
```

### 5.2 Insert Precincts

```python
#!/usr/bin/env python3
"""Insert precinct boundaries for {Council}."""

import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def insert_precincts(geojson_path: str):
    with open(geojson_path) as f:
        data = json.load(f)

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    for feature in data['features']:
        props = feature['properties']
        geom = json.dumps(feature['geometry'])

        cur.execute("""
            INSERT INTO precincts (
                name, lga, dcp_reference, geometry, is_active
            ) VALUES (%s, %s, %s, ST_GeomFromGeoJSON(%s), TRUE)
        """, (
            props['name'],
            '{Council}',
            props['dcp_reference'],
            geom
        ))

    conn.commit()
    print(f"Inserted {len(data['features'])} precincts")

    cur.close()
    conn.close()

if __name__ == '__main__':
    import sys
    insert_precincts(sys.argv[1])
```

### 5.3 Link Provisions to Precincts

```python
#!/usr/bin/env python3
"""Enrich provisions with precinct IDs."""

import os
import re
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Map document_id patterns to precinct IDs
PRECINCT_PATTERNS = {
    r'Town_Centre': 1,
    r'Industrial_Area': 2,
    r'Residential_North': 3,
    # Add patterns from document_id analysis
}

def enrich_precinct_ids():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    # Get precinct provisions
    cur.execute("""
        SELECT id, document_id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%{Council}%'
          AND v2_dcp_layer = 'precinct'
          AND v2_precinct_id IS NULL
    """)

    updates = []
    for row in cur.fetchall():
        prov_id, doc_id = row
        for pattern, precinct_id in PRECINCT_PATTERNS.items():
            if re.search(pattern, doc_id, re.IGNORECASE):
                updates.append((precinct_id, prov_id))
                break

    for precinct_id, prov_id in updates:
        cur.execute("""
            UPDATE regulatory_provisions
            SET v2_precinct_id = %s
            WHERE id = %s
        """, (precinct_id, prov_id))

    conn.commit()
    print(f"Updated {len(updates)} provisions with precinct IDs")

    cur.close()
    conn.close()

if __name__ == '__main__':
    enrich_precinct_ids()
```

---

## Phase 6: API Configuration (30 min)

### 6.1 Update Inner West Mapping (if Inner West)

If the council is part of Inner West, update `frontend-nextjs/lib/inner-west-mapping-v2.ts`:

```typescript
const SUBURB_TO_COUNCIL: Record<string, string> = {
  // Existing mappings...

  // {Council} suburbs
  'suburb1': '{Council}',
  'suburb2': '{Council}',
};
```

### 6.2 Update DCP Section Service

Update `frontend-nextjs/lib/dcp-section-service.ts` if needed for dev type mappings.

---

## Phase 7: Frontend Verification (1-2 hours)

### 7.1 Test Address Lookup

1. Go to `/assessment`
2. Enter an address in the new LGA
3. Verify:
   - Property is found
   - Zone is correct
   - DCP provisions load
   - TOC structure displays correctly

### 7.2 Test Layer Filtering

For each layer type, verify filtering works:

- **Generic**: Should show for all addresses
- **Use-specific**: Should filter by zone/dev type
- **Condition**: Should only show for heritage/flood sites
- **Precinct**: Should filter by location

### 7.3 Test Topic Filtering

Click through topic pills in the sidebar and verify:
- Correct provisions are shown
- Provision count matches expected

### 7.4 Test PDF Page Links

Click "View in PDF" links and verify:
- Correct page opens
- Page images load (if configured)

---

## Phase 8: Quality Assurance Checklist

### Extraction Quality
- [ ] All DCP parts extracted
- [ ] No duplicate provisions
- [ ] PDF page numbers correct
- [ ] Section headers captured

### Enrichment Quality
- [ ] All provisions have v2_dcp_layer
- [ ] All provisions have v2_dcp_part
- [ ] >90% provisions have v2_topic
- [ ] Topic accuracy >95% (via keyword check)

### Precinct Quality
- [ ] All precinct boundaries imported
- [ ] Precinct provisions linked to precinct IDs
- [ ] Location-based filtering works

### Frontend Quality
- [ ] TOC structure displays correctly
- [ ] Layer filtering works
- [ ] Topic filtering works
- [ ] Search works
- [ ] PDF links work

---

## Automation Summary

### Scripts to Create
1. `scripts/extract_{council}_dcp.py` - PDF extraction
2. `enrichment/config/{council}_config.py` - Council configuration
3. `scripts/validate_{council}_enrichment.py` - Quality validation
4. `scripts/enrich_{council}_precincts.py` - Precinct linking

### Manual Steps Required
1. DCP structure analysis (cannot automate - needs human judgment)
2. Topic marker identification (council-specific patterns)
3. Precinct boundary sourcing (may need manual GeoJSON creation)
4. Final QA testing

### Estimated Total Time
| Phase | Effort | Automation Potential |
|-------|--------|---------------------|
| 1. Document Analysis | 2-4 hrs | 0% - requires human judgment |
| 2. Configuration | 1-2 hrs | 50% - templates help |
| 3. PDF Extraction | 2-4 hrs | 70% - scripts exist |
| 4. Enrichment | 1-2 hrs | 90% - pipeline automated |
| 5. Precinct Setup | 2-4 hrs | 40% - data sourcing varies |
| 6. API Config | 30 min | 80% - mostly pattern matching |
| 7. Frontend Verify | 1-2 hrs | 20% - manual testing needed |
| 8. QA | 1-2 hrs | 30% - validation scripts help |

**Total: 10-20 hours per LGA**

---

## Appendix: Common Issues

### Issue: Topics not assigning correctly
**Cause**: document_id patterns don't match config
**Fix**: Check `layer_topic_tagger.py` regex patterns

### Issue: Provisions showing in wrong layer
**Cause**: Part detection regex too broad/narrow
**Fix**: Adjust pattern specificity in tagger

### Issue: Precincts not filtering
**Cause**: v2_precinct_id not set
**Fix**: Run precinct enrichment script

### Issue: Empty topic pills
**Cause**: No provisions with that topic in current filter
**Fix**: Check layer + topic combination has data

### Issue: PDF pages off by one
**Cause**: PDF page numbering vs extraction offset
**Fix**: Adjust pdf_page in extraction script
