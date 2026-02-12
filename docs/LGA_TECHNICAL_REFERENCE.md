# LGA Technical Reference

Quick reference for database schema, key queries, and data patterns.

## Database Schema (Key Columns)

### regulatory_provisions

```sql
-- Core identification
id                  SERIAL PRIMARY KEY
document_id         TEXT          -- Unique identifier pattern: "{Council}_{DCP}_{Year}_{Part}_{Section}"
ref_number          TEXT          -- Original reference (e.g., "C3", "2.6.1")
section_header      TEXT          -- Section/subsection heading

-- Content
provision_text      TEXT          -- Full provision text
provision_type      TEXT          -- 'control', 'objective', 'definition', 'note', 'procedural'

-- Location
pdf_page            INTEGER       -- Page number in source PDF
pdf_page_image_url  TEXT          -- URL to page image (optional)

-- v2_ Enrichment columns (populated by pipeline)
v2_dcp_layer              TEXT    -- 'generic', 'use_specific', 'condition', 'precinct'
v2_dcp_part               TEXT    -- 'Part 2', 'Part C Section 1', 'Chapter F', etc.
v2_topic                  TEXT    -- 'parking', 'heritage', 'setbacks', etc.
v2_precinct_id            INTEGER -- FK to precincts table (for precinct layer)
v2_site_condition_required TEXT   -- 'heritage', 'flood', 'bushfire', 'none'
v2_provision_type         TEXT    -- 'control', 'objective', 'definition', etc.
v2_has_numeric_value      BOOLEAN -- Has extractable numeric values
v2_extracted_values       JSONB   -- Extracted numeric values
v2_applicable_zones       TEXT[]  -- Zone codes this applies to
v2_applicable_dev_types   TEXT[]  -- Development types this applies to
v2_is_actionable          BOOLEAN -- Is actionable (not boilerplate)

-- Metadata
is_current          BOOLEAN       -- Current version (vs superseded)
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

### precincts

```sql
id          SERIAL PRIMARY KEY
name        TEXT          -- Precinct name (e.g., "Town Centre")
lga         TEXT          -- LGA name
dcp_reference TEXT        -- DCP part reference (e.g., "Part E Section 1")
geometry    GEOMETRY      -- PostGIS polygon boundary
is_active   BOOLEAN       -- Currently active
```

---

## Layer Model

| Layer | Description | Filtering Method |
|-------|-------------|------------------|
| `generic` | Applies to ALL development | No filtering |
| `use_specific` | Zone/dev-type specific | Filter by zone + dev_type |
| `condition` | Site condition required | Filter by heritage/flood/bushfire status |
| `precinct` | Location-specific | Filter by precinct boundary match |

### Layer Assignment Logic

```
IF document is heritage-specific (Part 8, Chapter E1, etc.)
  → layer = 'condition'
ELSE IF document is precinct-specific (Part 9, Part G, etc.)
  → layer = 'precinct'
ELSE IF document is zone-specific (Part 4.x, Part 5, Part 6, etc.)
  → layer = 'use_specific'
ELSE
  → layer = 'generic'
```

---

## Topic Keywords Reference

Used for topic assignment when no structural markers exist:

```python
TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard',
    'height': r'\bheight|storey|floor\s+level|building\s+height|FSR',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space|bicycle',
    'solar': r'\bsolar|overshadow|sunlight|daylight',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation',
    'landscaping': r'\blandscap|garden|planting|vegetation|deep\s+soil',
    'heritage': r'\bheritage|conservation|historic|contributory',
    'trees': r'\btree|canopy|arborist',
    'fencing': r'\bfenc|fence',
    'access': r'\baccess|entry|driveway|pedestrian|mobility',
    'stormwater': r'\bstormwater|drainage|runoff|OSD',
    'waste': r'\bwaste|garbage|recycling|bin',
    'signage': r'\bsign\b|signage|advertising',
    'building_form': r'\bbulk|scale|massing|streetscape',
    'building_design': r'\bfacade|articulation|materials|architectural',
    'open_space': r'\bopen\s+space|courtyard|private\s+open',
    'flooding': r'\bflood|inundation',
    'contamination': r'\bcontaminat|remediat',
    'safety': r'\bsafety|crime|cpted|surveillance',
    'residential': r'\bresidential|dwelling|apartment|house',
    'commercial': r'\bcommercial|retail|shop\b',
    'industrial': r'\bindustrial|warehouse',
    'energy': r'\benergy|renewable|thermal|insulation',
    'environmental': r'\benvironmental|ecology|habitat|biodiversity',
    'water': r'\bwater\s+management|rainwater|WSUD',
}
```

---

## Key SQL Queries

### Count provisions by council

```sql
SELECT
    CASE
        WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
        WHEN document_id ILIKE '%Leichhardt%' THEN 'Leichhardt'
        WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
        ELSE 'Other'
    END as council,
    COUNT(*) as count
FROM regulatory_provisions
WHERE is_current = TRUE
GROUP BY 1
ORDER BY 2 DESC;
```

### Layer distribution for a council

```sql
SELECT v2_dcp_layer, COUNT(*) as count
FROM regulatory_provisions
WHERE document_id ILIKE '%{Council}%'
  AND is_current = TRUE
GROUP BY 1
ORDER BY 2 DESC;
```

### Topic distribution for a council

```sql
SELECT v2_topic, COUNT(*) as count
FROM regulatory_provisions
WHERE document_id ILIKE '%{Council}%'
  AND is_current = TRUE
  AND v2_topic IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC;
```

### Part distribution for a council

```sql
SELECT v2_dcp_part, COUNT(*) as count
FROM regulatory_provisions
WHERE document_id ILIKE '%{Council}%'
  AND is_current = TRUE
GROUP BY 1
ORDER BY 2 DESC;
```

### Find provisions without topics

```sql
SELECT id, document_id, LEFT(provision_text, 100) as preview
FROM regulatory_provisions
WHERE document_id ILIKE '%{Council}%'
  AND is_current = TRUE
  AND v2_topic IS NULL
LIMIT 50;
```

### Find provisions with wrong topic (by keyword)

```sql
-- Example: Find provisions tagged 'parking' but mentioning 'heritage'
SELECT id, v2_topic, LEFT(provision_text, 200) as preview
FROM regulatory_provisions
WHERE document_id ILIKE '%{Council}%'
  AND is_current = TRUE
  AND v2_topic = 'parking'
  AND provision_text ~* 'heritage|conservation|historic'
LIMIT 20;
```

### Check precinct linking

```sql
SELECT
    v2_precinct_id,
    p.name as precinct_name,
    COUNT(*) as provision_count
FROM regulatory_provisions rp
LEFT JOIN precincts p ON rp.v2_precinct_id = p.id
WHERE rp.document_id ILIKE '%{Council}%'
  AND rp.v2_dcp_layer = 'precinct'
  AND rp.is_current = TRUE
GROUP BY 1, 2
ORDER BY 3 DESC;
```

### Provisions by page (extraction check)

```sql
SELECT pdf_page, COUNT(*) as count
FROM regulatory_provisions
WHERE document_id ILIKE '%{Council}%'
  AND is_current = TRUE
GROUP BY 1
ORDER BY 1;
```

### Document_id patterns (for debugging)

```sql
SELECT DISTINCT
    SUBSTRING(document_id FROM '^[^_]+_[^_]+_[^_]+_[^_]+') as pattern_prefix,
    COUNT(*) as count
FROM regulatory_provisions
WHERE document_id ILIKE '%{Council}%'
GROUP BY 1
ORDER BY 2 DESC;
```

---

## Backup & Restore

### Create backup before changes

```sql
CREATE TABLE regulatory_provisions_backup_{date} AS
SELECT id, v2_topic, v2_dcp_part, v2_dcp_layer, v2_precinct_id
FROM regulatory_provisions
WHERE document_id ILIKE '%{Council}%';
```

### Restore from backup

```sql
UPDATE regulatory_provisions rp
SET
    v2_topic = b.v2_topic,
    v2_dcp_part = b.v2_dcp_part,
    v2_dcp_layer = b.v2_dcp_layer,
    v2_precinct_id = b.v2_precinct_id
FROM regulatory_provisions_backup_{date} b
WHERE rp.id = b.id;
```

### Delete backup after verification

```sql
DROP TABLE regulatory_provisions_backup_{date};
```

---

## Common document_id Patterns

### Marrickville

```
Marrickville_DCP_2011_-_2_6_Privacy
Marrickville__DCP__2011__-__4__1__Low_Density_Residential
Marrickville_DCP_2011_-_8_0_Heritage
Marrickville_DCP_2011_-_9_12_Marrickville_Park
```

### Leichhardt

```
Leichhardt_DCP_2013_Part_C_Section_1_Place
Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_Young_Street
Leichhardt_DCP_2013_Part_D_Energy
Leichhardt_DCP_2013_Part_G_Norton_Street
```

### Ashfield

```
Inner_West_Ashfield_DCP_2016___Chapter_F_Part_1
Inner_West_Ashfield_DCP_2016___Chapter_E1_Heritage
Inner_West_Ashfield_DCP_2016___Chapter_D_Precinct_1
```

---

## API Endpoints Reference

| Endpoint | Purpose |
|----------|---------|
| `POST /api/dcp/provisions` | Get DCP provisions for property |
| `GET /api/browse/toc` | Get TOC structure for browsing |
| `GET /api/browse/section` | Get provisions for a section |
| `POST /api/precinct/match` | Match address to precinct |
| `GET /api/property/[address]` | Get property details |

### DCP Provisions Request

```json
{
  "address": "123 Main St, Suburb",
  "lga": "Inner West",
  "zone": "R3",
  "developmentType": "multi_dwelling",
  "search": "setback",
  "categories": ["setbacks", "height"],
  "provisionType": "control",
  "limit": 20,
  "offset": 0
}
```

---

## File Locations

```
compliance-engine/
├── data/
│   └── pdfs/{council}/          # Source PDFs
├── enrichment/
│   ├── config/
│   │   └── {council}_config.py  # Council configuration
│   ├── extractors/
│   │   └── layer_topic_tagger.py # Layer/topic assignment
│   └── pipeline.py              # Enrichment orchestration
├── scripts/
│   ├── extract_{council}_dcp.py # Extraction script
│   └── validate_{council}*.py   # Validation scripts
├── frontend-nextjs/
│   ├── lib/
│   │   ├── inner-west-mapping-v2.ts # Suburb→council mapping
│   │   └── dcp-section-service.ts   # DCP section logic
│   └── app/api/dcp/
│       └── provisions/route.ts  # Main provisions API
└── docs/
    ├── LGA_AUTOMATION_GUIDE.md
    ├── LGA_IMPLEMENTATION_CHECKLIST.md
    └── LGA_TECHNICAL_REFERENCE.md
```
