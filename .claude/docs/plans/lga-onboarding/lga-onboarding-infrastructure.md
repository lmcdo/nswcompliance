# LGA Onboarding Infrastructure: Scalable DCP Processing Framework

**Created:** 2026-02-13
**Status:** Strategic Framework
**Related Plans:**
- `ce-lga-onboarding-versioning-deployment.md` - Versioning infrastructure deployment
- `pd-multi-lga-expansion-plan.md` - User needs and product features

---

## Executive Summary

**Problem:** Current infrastructure has council-specific hardcoding (Part 8 references, HCA tagging, layer labels) that blocks automated onboarding of new LGAs beyond Inner West.

**Goal:** Enable **1-week onboarding** for new LGAs vs current manual/undefined process through:
1. Config-driven UI (no hardcoded council logic)
2. Automated DCP structure extraction
3. Universal spatial area architecture
4. LLM-based provision tagging with validation

**Key Insight from Inner West Experience:** Heritage dominates Inner West (merged 3 heritage-rich councils), but Parramatta might prioritize TOD/density near Metro, Randwick might prioritize coastal hazards. Infrastructure must adapt to each LGA's priorities, not force Inner West's heritage-first model.

---

## Current Infrastructure (What Works, What's Fragile)

### ✅ **Universal/Portable Components**

**1. Core v2 Taxonomy (DB Schema)**
```typescript
// These fields work across ANY LGA:
v2_marker: 'heritage' | 'flooding' | 'parking' | 'tree_canopy' | 'acoustic' | ...
v2_topic: specific subject within marker
v2_is_actionable: control vs informational
v2_display_priority: 'critical' for numeric provisions
v2_dcp_part: DCP section reference (flexible string)
```

**Why it works:** Marker system is authority-based (heritage trigger, flooding trigger), not council-specific. Every council has similar triggers.

**2. Layer-Based Filtering System**
```typescript
// Layer indices (0-4) map to authority sources:
0: use_specific (zone-based provisions)
1: height/fsr (numeric envelope)
2: condition (heritage, flooding, constraints)
3: precinct (character/spatial controls)
4: generic (council-wide)
```

**Why it works:** Layer architecture is **universal** - every council has these authority types. Only the labels differ (e.g., "Heritage" vs "Environmental Constraints").

**3. Provision Processing Pipeline**
```
PDF → text extraction → provision splitting → enrichment → tagging
```

**Why it works:** Pipeline is **LGA-agnostic** - works for any DCP structure.

---

### ⚠️ **Council-Specific/Hardcoded Components** (Need Abstraction)

**1. DCP Part Labels** (`TocSidebar.tsx`)
```typescript
// PROBLEM: Manually defined for each LGA's DCP structure
const DCP_PART_TITLES = {
  'Part 8': { label: 'Part 8', desc: 'Heritage' },      // Marrickville
  'Chapter E1': { label: 'Ch E1', desc: 'Heritage' },   // Ashfield
  'Part C Section 1': { label: 'Part C.1', desc: 'General' }  // Leichhardt
};
```

**Impact:** New LGA = manual TOC mapping work.

**Solution:** Auto-extract TOC structure from DCP, store in `council_config` table.

**2. Layer Label Overrides** (`PageGroupedProvisions.tsx`)
```typescript
// PROBLEM: Per-council customization, only for known councils
const COUNCIL_LAYER_LABELS = {
  marrickville: { condition: 'Heritage', precinct: 'Precinct Character' },
  leichhardt: { condition: 'Heritage', precinct: 'Distinct Neighbourhood' }
};
```

**Impact:** Hardcoded references like "Part 8: Heritage" fail for Leichhardt properties (should be "Part C Section 1: Heritage").

**Example Bug (Fixed 2026-02-13):** 20 Ferris St, Annandale (Leichhardt) showed "Part 8: Heritage" reference (Marrickville-specific).

**Solution:**
- Default layer labels for new LGAs
- Optional override via `council_config.layer_labels` JSON field
- Dynamic part reference: `councilLower === 'leichhardt' ? 'Part C Section 1' : 'Part 8'`

**3. HCA/Precinct-Specific Tagging**
```typescript
// PROBLEM: Marrickville-only HCA tagging with manual section mapping
v2_heritage_hca: 'hca_14'  // Section 8.2.16 → hca_14 Llewellyn Estate
```

**Manual Mapping Required:**
```javascript
const sectionToHCA = {
  16: 'hca_14',  // Section 8.2.16 = Llewellyn (NOT hca_16!)
  17: 'hca_15',  // Section 8.2.17 = hca_15
  // ... 36 more mappings
};
```

**Impact:** Every council with spatial divisions (precincts/HCAs/character areas) needs manual section-to-area mapping.

**Solution:** Generic `v2_spatial_area_id` field linking to `spatial_areas` table with automated matching.

---

## Scalable Onboarding Framework

### **Phase 1: DCP Discovery & Analysis** (Automated)

**Goal:** Understand the DCP structure without manual reading.

#### **1.1 TOC Extraction**
```python
def extract_dcp_structure(pdf_path):
    """Extract hierarchical structure from PDF bookmarks/headings."""
    return {
        'parts': [
            {'id': 'Part 4', 'title': 'Development Controls', 'depth': 1},
            {'id': '4.1', 'title': 'Residential', 'depth': 2},
            {'id': '4.1.1', 'title': 'Building Height', 'depth': 3}
        ],
        'naming_pattern': 'numeric',  # vs 'chapter', 'section'
        'max_depth': 4
    }
```

**Output:**
- Auto-populate `DCP_PART_TITLES` for TocSidebar
- Detect naming convention (Part/Chapter/Section)
- Identify hierarchy depth (2-level vs 4-level)

**Storage:**
```sql
-- Store in council_config table
UPDATE council_config
SET part_titles = '[{"id": "Part 4", "title": "Development Controls", ...}]'
WHERE council_slug = 'parramatta';
```

#### **1.2 Provision Density Analysis**
```sql
-- What does this council care about?
SELECT
  v2_marker,
  COUNT(*) as provision_count,
  COUNT(*) FILTER (WHERE v2_display_priority = 'critical') as numeric_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as percentage
FROM regulatory_provisions
WHERE document_id ILIKE '%Parramatta%'
  AND v2_is_actionable = true
GROUP BY v2_marker
ORDER BY provision_count DESC;
```

**Expected Output:**
```
v2_marker       | provision_count | numeric_count | percentage
----------------|-----------------|---------------|------------
height          | 450             | 380           | 28.5%
heritage        | 320             | 45            | 20.3%
tod_precinct    | 280             | 200           | 17.7%
parking         | 220             | 180           | 13.9%
flooding        | 150             | 90            | 9.5%
tree_canopy     | 160             | 20            | 10.1%
```

**Insights:**
- **Top 3 markers** = council priorities (show in UI prominently)
- **Numeric density** (84% of height provisions are numeric) = prescriptive council
- **Heritage vs TOD ratio** (Parramatta: TOD > Heritage, opposite of Inner West)

**UI Impact:**
- Filter chips ordered by provision density
- Layer 2 ("Condition") might be "TOD Controls" not "Heritage" for Parramatta
- Default expanded sections = top 3 markers

#### **1.3 Spatial Division Detection**
```python
def detect_spatial_areas(provisions):
    """Scan for precinct/character area/HCA patterns."""
    patterns = {
        'heritage_areas': r'Heritage Conservation Area \d+|HCA [A-Z]?\d+|C\d+',
        'precincts': r'Precinct [A-Z\d]+|Village [A-Z]|Area \d+',
        'character_areas': r'Character Area \d+|Neighbourhood \d+|Locality [A-Z]',
        'tod_precincts': r'TOD Precinct [A-Z]|Station Precinct \d+'
    }

    areas = []
    for area_type, pattern in patterns.items():
        matches = set()
        for prov in provisions:
            found = re.findall(pattern, prov.provision_text, re.IGNORECASE)
            matches.update(found)

        for match in matches:
            areas.append({
                'area_type': area_type,
                'display_name': match,
                'db_slug': slugify(match),  # 'hca_14', 'precinct_a'
                'dcp_section_pattern': infer_section_pattern(match, provisions)
            })

    return areas
```

**Output:**
```python
[
    {'area_type': 'heritage_areas', 'display_name': 'HCA 14 Llewellyn Estate',
     'db_slug': 'hca_14', 'dcp_section_pattern': '8.2.16'},
    {'area_type': 'precincts', 'display_name': 'Precinct A Norton Street',
     'db_slug': 'precinct_a', 'dcp_section_pattern': 'G.1'},
]
```

**Storage:**
```sql
-- Populate spatial_areas table
INSERT INTO spatial_areas (council_slug, area_type, db_slug, display_name, dcp_section_pattern)
VALUES ('marrickville', 'heritage_areas', 'hca_14', 'Llewellyn Estate HCA', '8.2.16');
```

---

### **Phase 2: Priority Identification** (Semi-Automated + Human Review)

**Goal:** Understand what matters for compliance in this LGA.

#### **2.1 Topic Prioritization Matrix**

| Council Type | Priority 1 | Priority 2 | Priority 3 | Layer 2 Label |
|--------------|-----------|-----------|-----------|---------------|
| Heritage-rich (Inner West, Woollahra) | Heritage | Tree Canopy | Flooding | "Heritage" |
| TOD-focused (Parramatta, Ryde) | Height/Density | TOD Controls | Parking | "Development Envelope" |
| Coastal (Randwick, Waverley) | Coastal Hazards | Flooding | Heritage | "Environmental Constraints" |
| Growth Area (Blacktown, Liverpool) | Affordable Housing | Infrastructure | TOD | "Growth Controls" |

**Decision Process:**
1. Run provision density analysis (Phase 1.2)
2. Review council's strategic plans:
   - DA rejection statistics (what gets knocked back?)
   - Urban strategy documents (growth priorities)
   - Council complaints (GIPA requests show resident concerns)
3. **Ask user via CLI prompt:**
   ```
   Parramatta DCP Analysis:
   - 450 height provisions (28.5%, 84% numeric)
   - 320 heritage provisions (20.3%, 14% numeric)
   - 280 TOD provisions (17.7%, 71% numeric)

   Recommended priority: Height > TOD > Heritage

   Accept? [Y/n]
   Or specify custom order: _____
   ```

**Output:**
```sql
UPDATE council_config
SET priority_markers = ARRAY['height', 'tod_precinct', 'heritage'],
    layer_labels = '{"condition": "Development Envelope"}'
WHERE council_slug = 'parramatta';
```

#### **2.2 Critical Provision Detection**

Auto-tag numeric/measurable provisions:
```python
NUMERIC_PATTERNS = {
    'dimension': r'\d+\.?\d*\s*(m|metres|meters)',  # "6m", "3.5 metres"
    'percentage': r'\d+\.?\d*\s*%',                   # "40%", "0.5%"
    'ratio': r'\d+\.?\d*\s*:\s*\d+',                  # "2.5:1", "1:100"
    'area': r'\d+\.?\d*\s*(m2|m²|sqm|ha)',           # "450m2", "1.2ha"
}

MANDATORY_PATTERNS = {
    'must': r'\bmust\b|\brequired\b|\bshall\b',
    'prohibited': r'\bnot permitted\b|\bprohibited\b|\bmaximum\b',
}

def detect_critical_provisions(provision_text):
    has_numeric = any(re.search(pattern, provision_text, re.IGNORECASE)
                      for pattern in NUMERIC_PATTERNS.values())
    has_mandatory = any(re.search(pattern, provision_text, re.IGNORECASE)
                        for pattern in MANDATORY_PATTERNS.values())

    return 'critical' if (has_numeric or has_mandatory) else 'standard'
```

**Example:**
```
Input: "Building height must not exceed 12m measured from ground level."
Output: v2_display_priority = 'critical' (has numeric "12m" + mandatory "must")

Input: "Council encourages green roofs and living walls."
Output: v2_display_priority = 'standard' (no numeric, no mandatory language)
```

---

### **Phase 3: Schema Configuration** (Database + Code)

**Goal:** Extend system for new LGA without breaking existing councils.

#### **3.1 Council Configuration Table**
```sql
CREATE TABLE council_config (
  id SERIAL PRIMARY KEY,
  council_slug TEXT UNIQUE,         -- 'parramatta', 'inner_west'
  display_name TEXT,                -- 'City of Parramatta'

  -- DCP structure metadata
  dcp_naming_convention TEXT,       -- 'part', 'chapter', 'section'
  part_titles JSONB,                -- Auto-generated from TOC extraction
  max_hierarchy_depth INTEGER,      -- 2-4 levels

  -- UI customization
  layer_labels JSONB,               -- Override default layer names
  priority_markers TEXT[],          -- Top 3 markers for this council
  filter_chip_order TEXT[],         -- Custom topic filter order

  -- Spatial configuration
  has_precincts BOOLEAN DEFAULT false,
  has_hcas BOOLEAN DEFAULT false,
  has_character_areas BOOLEAN DEFAULT false,
  precinct_id_pattern TEXT,         -- Regex for section → precinct mapping

  -- Branding (optional)
  brand_color_primary TEXT,         -- #FF6B35 for council branding
  brand_color_secondary TEXT,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Example row
INSERT INTO council_config VALUES (
  1, 'parramatta', 'City of Parramatta',
  'part',  -- naming convention
  '[{"id": "Part 4", "title": "Development Controls", "depth": 1}, ...]',  -- TOC
  4,  -- max depth
  '{"condition": "Development Envelope", "precinct": "TOD Precincts"}',  -- layer overrides
  ARRAY['height', 'tod_precinct', 'heritage'],  -- priority markers
  ARRAY['height', 'parking', 'tod_precinct', 'heritage', 'flooding'],  -- filter order
  true, false, false,  -- has_precincts, no HCAs, no character areas
  'Part 5\\.\\d+',  -- precinct pattern
  '#003DA5', '#00AEEF'  -- Parramatta brand colors
);
```

#### **3.2 Universal Spatial Areas Table**
```sql
-- REPLACE heritage_conservation_areas with generic spatial_areas
DROP TABLE IF EXISTS heritage_conservation_areas CASCADE;

CREATE TABLE spatial_areas (
  id SERIAL PRIMARY KEY,
  council_slug TEXT NOT NULL,
  area_type TEXT NOT NULL,          -- 'hca', 'precinct', 'character_area', 'tod_precinct'
  db_slug TEXT NOT NULL,            -- 'hca_14', 'precinct_a', 'tod_parramatta'
  display_name TEXT NOT NULL,       -- 'Llewellyn Estate HCA', 'Norton Street Precinct'
  boundary GEOMETRY(Polygon),       -- Spatial boundary for property matching
  dcp_section_pattern TEXT,         -- '8.2.16', 'G.1', 'Part 5.3' for auto-tagging
  council_url TEXT,                 -- Link to council page about this area

  -- Metadata
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(council_slug, db_slug)
);

CREATE INDEX idx_spatial_areas_council ON spatial_areas(council_slug);
CREATE INDEX idx_spatial_areas_boundary ON spatial_areas USING GIST(boundary);

-- Example rows
INSERT INTO spatial_areas VALUES
  (1, 'marrickville', 'hca', 'hca_14', 'Llewellyn Estate Heritage Conservation Area',
   ST_GeomFromText('POLYGON((...))', 4326), '8.2.16',
   'https://www.innerwest.nsw.gov.au/ArticleDocuments/1244/Llewellyn_Estate_HCA.pdf'),

  (2, 'parramatta', 'tod_precinct', 'tod_parramatta', 'Parramatta TOD Precinct',
   ST_GeomFromText('POLYGON((...))', 4326), 'Part 5.2',
   'https://parramatta.nsw.gov.au/tod-parramatta'),

  (3, 'leichhardt', 'precinct', 'precinct_norton', 'Norton Street Village Precinct',
   ST_GeomFromText('POLYGON((...))', 4326), 'G.1',
   'https://www.innerwest.nsw.gov.au/live/my-neighbourhood/norton-street');
```

#### **3.3 Provision Schema Extension**
```sql
-- RENAME v2_heritage_hca → v2_spatial_area_id (universal spatial tagging)
ALTER TABLE regulatory_provisions
  RENAME COLUMN v2_heritage_hca TO v2_spatial_area_id;

-- Add council_slug for multi-LGA queries
ALTER TABLE regulatory_provisions
  ADD COLUMN council_slug TEXT;

-- Backfill council_slug from document_id
UPDATE regulatory_provisions
SET council_slug = CASE
  WHEN document_id ILIKE '%Marrickville%' THEN 'marrickville'
  WHEN document_id ILIKE '%Leichhardt%' THEN 'leichhardt'
  WHEN document_id ILIKE '%Ashfield%' THEN 'ashfield'
  WHEN document_id ILIKE '%Parramatta%' THEN 'parramatta'
  ELSE 'unknown'
END;

-- Add foreign key to spatial_areas
ALTER TABLE regulatory_provisions
  ADD CONSTRAINT fk_spatial_area
  FOREIGN KEY (v2_spatial_area_id)
  REFERENCES spatial_areas(db_slug);

-- Index for fast filtering
CREATE INDEX idx_council_marker ON regulatory_provisions(council_slug, v2_marker);
CREATE INDEX idx_council_spatial ON regulatory_provisions(council_slug, v2_spatial_area_id);
```

---

### **Phase 4: Automated Tagging Pipeline**

**Goal:** Tag provisions correctly without manual review.

#### **4.1 Marker Classification** (LLM-based, Dual-Pass Validation)

```python
def classify_provision_marker(provision_text: str) -> dict:
    """
    Classify provision's regulatory trigger using LLM dual-pass validation.
    Returns marker, confidence, and mismatch flag.
    """

    prompt = """
Classify this DCP provision's primary regulatory trigger.

MARKERS (choose ONE):
- heritage: Heritage items, conservation areas, archaeology, contributory buildings
- flooding: Flood risk, stormwater, drainage, overland flow
- tree_canopy: Tree preservation, landscaping, canopy targets, green cover
- parking: Parking rates, vehicle access, loading zones, bicycle parking
- acoustic: Noise, sound attenuation, acoustic privacy
- height: Building height limits, storey limits, skyplane controls
- fsr: Floor space ratio, GFA calculations, plot ratio
- setback: Building setbacks, boundary clearances, spatial separation
- open_space: Private open space, deep soil, communal open space
- tod_precinct: Transport-oriented development, station proximity, walkability
- coastal_hazard: Coastal erosion, sea level rise, beach access
- character: Streetscape character, built form, neighbourhood identity
- affordable_housing: Affordable housing requirements, inclusionary zoning
- subdivision: Lot size, subdivision controls, battle-axe access

Provision: "{provision_text}"

Output JSON only:
{{"marker": "heritage", "confidence": 0.95}}
"""

    # Pass 1
    response1 = llm.complete(prompt.format(provision_text=provision_text))
    result1 = json.loads(response1)

    # Pass 2 (independent)
    response2 = llm.complete(prompt.format(provision_text=provision_text))
    result2 = json.loads(response2)

    # Validation
    if result1['marker'] != result2['marker']:
        return {
            'marker': result1['marker'],  # Use Pass 1 as default
            'confidence': min(result1['confidence'], result2['confidence']),
            'mismatch': True,
            'pass1': result1,
            'pass2': result2,
            'requires_review': True
        }

    avg_confidence = (result1['confidence'] + result2['confidence']) / 2
    if avg_confidence < 0.9:
        return {
            'marker': result1['marker'],
            'confidence': avg_confidence,
            'mismatch': False,
            'requires_review': True  # Low confidence
        }

    return {
        'marker': result1['marker'],
        'confidence': avg_confidence,
        'mismatch': False,
        'requires_review': False  # High confidence, no mismatch
    }

# Process provisions in batches
def tag_all_provisions(council_slug: str, batch_size: int = 50):
    provisions = fetch_provisions(council_slug, v2_marker__isnull=True)

    auto_tagged = 0
    flagged_for_review = 0

    for batch in chunk(provisions, batch_size):
        for prov in batch:
            result = classify_provision_marker(prov.provision_text)

            if result['requires_review']:
                # Save to review queue
                save_to_review_queue(prov.id, result)
                flagged_for_review += 1
            else:
                # Auto-tag with high confidence
                update_provision(prov.id, v2_marker=result['marker'])
                auto_tagged += 1

        time.sleep(2)  # Rate limiting

    print(f"✓ Auto-tagged: {auto_tagged} provisions")
    print(f"⚠ Flagged for review: {flagged_for_review} provisions")
    print(f"Review rate: {flagged_for_review / len(provisions) * 100:.1f}%")
```

**Expected Performance (based on Inner West heritage enrichment):**
- **Auto-accept rate:** ~53% (confidence ≥ 0.9, no mismatch)
- **Review rate:** ~47% (low confidence or mismatch)
- **After user review:** ~90% accept, ~10% override

#### **4.2 Spatial Area Linking**

```python
def link_provision_to_spatial_area(provision, spatial_areas):
    """
    Link provision to spatial area using 3 methods:
    1. DCP section pattern matching
    2. Text analysis (area name mentioned)
    3. Boundary matching (if property coords available)
    """

    # Method 1: Section pattern matching
    if provision.v2_dcp_part:
        for area in spatial_areas:
            if area.dcp_section_pattern and re.match(
                area.dcp_section_pattern,
                provision.v2_dcp_part
            ):
                return area.db_slug

    # Method 2: Text analysis
    for area in spatial_areas:
        if area.display_name.lower() in provision.provision_text.lower():
            return area.db_slug

    # Method 3: Boundary matching (requires property context)
    # Skip for general provision tagging

    return None  # General provision (no spatial constraint)

# Example usage
spatial_areas = fetch_spatial_areas('marrickville')

for prov in provisions:
    spatial_area_id = link_provision_to_spatial_area(prov, spatial_areas)
    if spatial_area_id:
        update_provision(prov.id, v2_spatial_area_id=spatial_area_id)
```

**Results for Marrickville (2026-02-13):**
- 84 HCA-tagged provisions across 35 HCAs
- Section pattern matching: 40 provisions (8.2.X.6 → hca_X)
- Text analysis: 44 provisions (area name in text)

#### **4.3 Critical Provision Detection**

```python
def tag_critical_provisions(provision_text: str) -> str:
    """Auto-flag numeric/mandatory provisions as critical."""

    # Numeric patterns
    has_numeric = bool(re.search(
        r'\d+\.?\d*\s*(m|metres|meters|%|m2|m²|sqm|ha|:)',
        provision_text,
        re.IGNORECASE
    ))

    # Mandatory language
    has_mandatory = bool(re.search(
        r'\b(must|shall|required|mandatory|not permitted|prohibited|maximum|minimum)\b',
        provision_text,
        re.IGNORECASE
    ))

    if has_numeric or has_mandatory:
        return 'critical'

    return 'standard'

# Batch tag
UPDATE regulatory_provisions
SET v2_display_priority = CASE
  WHEN provision_text ~* '\d+\.?\d*\s*(m|metres|%|m2|ha|:)' THEN 'critical'
  WHEN provision_text ~* '\b(must|shall|required|not permitted|prohibited|maximum|minimum)\b' THEN 'critical'
  ELSE 'standard'
END
WHERE council_slug = 'parramatta';
```

---

### **Phase 5: UI Route Generation** (Config-Driven, Dynamic)

**Goal:** No hardcoded routes for new LGAs.

#### **Problem: Current Hardcoded Logic**

```typescript
// BEFORE (hardcoded)
if (['leichhardt', 'ashfield', 'marrickville'].includes(councilLower)) {
  return (
    <div>
      <p>→ See <strong>Part 8: Heritage</strong> below</p>
      {/* WRONG for Leichhardt! */}
    </div>
  );
}
```

**Bug Example (Fixed 2026-02-13):**
- 20 Ferris St, Annandale (Leichhardt) showed "Part 8: Heritage" (Marrickville reference)
- Should show "Part C Section 1: Heritage"

#### **Solution: Config-Driven Rendering**

```typescript
// AFTER (config-driven)
const councilConfig = await fetchCouncilConfig(councilSlug);

// Dynamic heritage part reference
const heritagePartRef = councilConfig.part_titles
  .find(p => p.title.toLowerCase().includes('heritage'))?.id
  || 'Part 8';  // Fallback

return (
  <div>
    <p>→ See <strong>{heritagePartRef}: Heritage</strong> below</p>
  </div>
);
```

**Spatial Area Rendering:**
```typescript
// Config-driven spatial summary
if (councilConfig.has_hcas) {
  return <HCASection hcaData={hcaData} councilConfig={councilConfig} />;
} else if (councilConfig.has_precincts) {
  return <PrecinctSection precinctData={precinctData} councilConfig={councilConfig} />;
} else if (councilConfig.has_character_areas) {
  return <CharacterAreaSection areaData={areaData} councilConfig={councilConfig} />;
}
```

**Layer Label Rendering:**
```typescript
// Use council-specific labels or fallback to defaults
const layerLabel = councilConfig.layer_labels?.[layer]
  || DEFAULT_LAYER_LABELS[layer];

return <Badge>{layerLabel}</Badge>;
```

**Auto-Generated API Routes:**
```typescript
// /api/provisions/for-property?address=X&council=parramatta
// → Filters by council_slug, applies council-specific config

const councilConfig = await fetchCouncilConfig(councilSlug);
const provisions = await db.query(`
  SELECT * FROM regulatory_provisions
  WHERE council_slug = $1
    AND v2_is_actionable = true
  ORDER BY
    CASE v2_marker
      ${councilConfig.priority_markers.map((m, i) => `WHEN '${m}' THEN ${i}`).join('\n')}
      ELSE 999
    END
`, [councilSlug]);
```

---

## Onboarding Checklist for New LGA

### **Automated Steps** (Run scripts, ~4 hours)

- [ ] **Extract DCP structure** (`python scripts/extract_toc_structure.py parramatta_dcp.pdf`)
  - Output: `council_config.part_titles` populated
  - Verify: TOC depth, naming convention detected correctly

- [ ] **Run provision density analysis** (`python scripts/analyze_provision_density.py parramatta`)
  - Output: Priority markers identified (top 3 by count)
  - Verify: Makes sense for this LGA's development profile

- [ ] **Extract spatial areas** (`python scripts/extract_spatial_areas.py parramatta`)
  - Output: `spatial_areas` table populated (precincts/HCAs/etc.)
  - Verify: Section-to-area patterns detected correctly

- [ ] **Auto-tag provisions with v2_marker** (`python scripts/tag_provisions_llm.py parramatta --dual-pass`)
  - Output: ~50% auto-tagged, ~50% flagged for review
  - Verify: Review queue populated with low-confidence/mismatch provisions

- [ ] **Link provisions to spatial areas** (`python scripts/link_spatial_areas.py parramatta`)
  - Output: `v2_spatial_area_id` populated for area-specific provisions
  - Verify: Sample provisions correctly linked to precincts/HCAs

### **Manual Review Steps** (Human decisions, ~1-2 days)

- [ ] **Review LLM-flagged provisions** (~47% need review based on Inner West experience)
  - Use review interface: `npm run review-provisions --council=parramatta`
  - Accept/override marker classifications
  - Target: >90% accept rate (if <90%, retrain prompt)

- [ ] **Verify priority markers** (Heritage? TOD? Coastal?)
  - Review provision density output
  - Check council strategic plan
  - Confirm or override: `UPDATE council_config SET priority_markers = ARRAY[...]`

- [ ] **Define layer label overrides** (if council has specific branding)
  - Default labels: "Condition Layer", "Precinct Controls"
  - Override only if strong brand: "Heritage Controls", "TOD Precincts"
  - Update: `UPDATE council_config SET layer_labels = '{...}'`

- [ ] **Validate spatial area boundaries** (GIS check)
  - Import GIS files from council website
  - Verify boundaries match provision section patterns
  - Test property-to-area matching for 10 sample addresses

- [ ] **Configure UI branding** (optional)
  - Extract brand colors from council website
  - Update: `UPDATE council_config SET brand_color_primary = '#003DA5'`

### **Testing Protocol** (Validation, ~1 day)

- [ ] **Test 5 properties in different zones** (R1, R4, B4, RE1, E3)
  - Verify provision counts match manual DCP review
  - Check layer ordering reflects priority markers
  - Confirm spatial area filtering works (precincts show correct provisions)

- [ ] **Validate numeric provision flagging**
  - Critical badge appears on provisions with measurements
  - Non-numeric provisions not flagged
  - Spot-check 20 random provisions

- [ ] **Cross-check with sample DA**
  - Get recent approved DA from council
  - Run property through app
  - Verify provisions match DA assessment report

- [ ] **Performance testing**
  - Load 10 properties in parallel
  - Check API response times (target: <2s for provision query)
  - Verify caching works correctly

---

## Key Architectural Decisions

### **1. Universal vs Council-Specific Markers**

**Universal Markers** (add to all councils):
```python
UNIVERSAL_MARKERS = [
    'heritage',      # Every council has heritage provisions
    'flooding',      # Every council has stormwater/drainage
    'parking',       # Every council regulates parking
    'tree_canopy',   # Every council has landscaping requirements
    'acoustic',      # Every council has noise controls
    'height',        # Every council has height limits
    'fsr',           # Every council has density controls
    'setback',       # Every council has setback rules
    'open_space',    # Every council requires private open space
]
```

**Council-Specific Markers** (add only if truly unique):
```python
# Example: Coastal councils
COASTAL_MARKERS = ['coastal_hazard', 'beach_access', 'dune_protection']

# Example: Airport-adjacent councils
AIRPORT_MARKERS = ['airport_noise', 'anef_zone', 'overflight']

# Example: TOD-focused councils
TOD_MARKERS = ['tod_precinct', 'station_proximity', 'walkability']
```

**Storage:**
```sql
-- Store custom markers in council_config
UPDATE council_config
SET custom_markers = ARRAY['coastal_hazard', 'beach_access']
WHERE council_slug = 'randwick';
```

**Validation Rule:** Only add custom marker if:
1. >50 provisions would use it (not a one-off)
2. Can't be represented as a topic within existing marker
3. Represents a distinct authority/trigger (not just a subject area)

### **2. Layer System is Universal**

**Keep 5 layers across all councils:**
```typescript
const UNIVERSAL_LAYERS = {
  0: 'use_specific',  // Zone-based provisions (R1, R4, B4, etc.)
  1: 'height_fsr',    // Numeric envelope (height/FSR limits)
  2: 'condition',     // Constraint triggers (heritage, flooding, etc.)
  3: 'precinct',      // Spatial controls (precincts, character areas)
  4: 'generic'        // Council-wide provisions
};
```

**Only customize LABELS, not structure:**
```typescript
// Inner West: Heritage-focused
layer_labels: { condition: 'Heritage', precinct: 'Neighbourhood Character' }

// Parramatta: TOD-focused
layer_labels: { condition: 'Development Envelope', precinct: 'TOD Precincts' }

// Randwick: Coastal-focused
layer_labels: { condition: 'Environmental Constraints', precinct: 'Coastal Precincts' }
```

**Rationale:** Layer architecture represents **authority types**, not subject matter. Every council has these authority types, just with different priorities.

### **3. Spatial Areas Replace All Hardcoded Geography**

**Before (hardcoded):**
```sql
-- Separate table for each spatial type
heritage_conservation_areas
precincts
character_areas
tod_precincts
```

**After (unified):**
```sql
-- Single table, area_type field distinguishes
spatial_areas (area_type IN ('hca', 'precinct', 'character_area', 'tod_precinct'))
```

**Benefits:**
1. **Extensible:** New spatial division types don't require schema changes
2. **Query simplicity:** Single table for all spatial filtering
3. **Consistent tagging:** All provisions use `v2_spatial_area_id` (no separate heritage_hca vs precinct_id fields)

**Provision Linking:**
```sql
-- BEFORE: Multiple nullable foreign keys
regulatory_provisions (
  v2_heritage_hca TEXT,       -- Marrickville only
  v2_precinct_id TEXT,        -- Leichhardt only
  v2_character_area TEXT      -- Future councils?
)

-- AFTER: Single universal foreign key
regulatory_provisions (
  v2_spatial_area_id TEXT REFERENCES spatial_areas(db_slug)
)
```

### **4. Config-Driven UI > Hardcoded Logic**

**Eliminate all `if (council === 'X')` checks:**

```typescript
// ❌ BEFORE (hardcoded)
if (council === 'marrickville') {
  showHCASummary = true;
  heritagePart = 'Part 8';
} else if (council === 'leichhardt') {
  showHCASummary = true;
  heritagePart = 'Part C Section 1';
} else if (council === 'ashfield') {
  showHCASummary = true;
  heritagePart = 'Chapter E1';
}

// ✅ AFTER (config-driven)
const config = await fetchCouncilConfig(council);

if (config.has_hcas || config.has_precincts) {
  const spatialAreas = await fetchSpatialAreas(council);
  return <SpatialAreaSummary areas={spatialAreas} config={config} />;
}

const heritagePart = config.part_titles.find(p =>
  p.title.toLowerCase().includes('heritage')
)?.id || 'Heritage';
```

**New LGAs work automatically once config exists:**
- No code changes required
- Just populate `council_config` and `spatial_areas` tables
- UI renders based on flags and data

---

## Expected Onboarding Timeline

### **Week 1: Automated Processing**
- **Day 1-2:** Run extraction scripts (TOC, density, spatial areas)
- **Day 3-4:** LLM tagging pipeline (dual-pass, generate review queue)
- **Day 5:** Spatial area linking, critical provision detection

### **Week 2: Manual Review & Validation**
- **Day 1-2:** Review LLM-flagged provisions (~47% of total)
- **Day 3:** Validate priority markers, layer labels, spatial boundaries
- **Day 4:** Test 20-30 sample properties across zones
- **Day 5:** Production deployment, monitoring

**Total Effort:** ~10 days vs current **undefined/manual** process

**Comparison to Inner West (Manual):**
- Ashfield + Leichhardt + Marrickville = ~3 months of manual work
- Marrickville HCA tagging alone = 2 sessions (40 provisions, manual section mapping)

**Scalability Target:**
- After 5 LGAs onboarded: <5 days per new LGA (refined prompts, validated patterns)
- After 10 LGAs: <3 days per new LGA (mature automation)

---

## Success Metrics

### **Technical Metrics**
- [ ] Auto-tagging accept rate: >85% (currently ~53% for heritage elements)
- [ ] Spatial area linking accuracy: >90% (currently 100% for Marrickville)
- [ ] Critical provision detection precision: >95% (no false positives)
- [ ] API response time: <2s for provision query (any council)

### **Process Metrics**
- [ ] Onboarding time: <2 weeks (target: 1 week after 5th LGA)
- [ ] Manual review time: <2 days per LGA
- [ ] Code changes required: 0 (config-only changes)

### **Data Quality Metrics**
- [ ] Provision coverage: 100% (all provisions tagged)
- [ ] Missing markers: <1% (provisions with v2_marker = NULL)
- [ ] Orphaned spatial areas: 0 (all areas have linked provisions)

---

## Related Documentation

- `ce-lga-onboarding-versioning-deployment.md` - Provision versioning infrastructure (for tracking DCP updates)
- `pd-multi-lga-expansion-plan.md` - User personas, product features, exception handling
- `DB_SCHEMA.md` - Current database schema reference
- `.claude/prp/INDEX.md` - Architecture overview

---

## Open Questions for Next LGA (Parramatta)

1. **TOD vs Heritage Priority:** Parramatta has more TOD provisions than heritage. Should Layer 2 be "TOD Controls" not "Heritage Controls"?

2. **Precinct Structure:** Parramatta has 15+ TOD precincts. Do these map to DCP Part 5 sections cleanly, or need manual GIS boundary import?

3. **Custom Markers Needed?** Does Parramatta need `tod_precinct` as a distinct marker, or can it be a topic under `precinct`?

4. **Brand Colors:** Should UI adopt Parramatta brand colors (#003DA5, #00AEEF) or stay neutral?

5. **Auto-Tagging Threshold:** Start with 0.9 confidence threshold, or lower to 0.85 given larger dataset?

---

**Document Status:** ACTIVE - Use as reference for next LGA onboarding (Parramatta, Randwick, Woollahra candidates).
