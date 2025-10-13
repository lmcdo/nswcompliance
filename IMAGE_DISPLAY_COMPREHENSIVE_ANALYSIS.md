# Image Display: Comprehensive Analysis & Solution Design

**Date:** 2025-10-13
**Issue:** 1,129 extracted images not displaying in UI
**Root Cause:** Format mismatch + insufficient metadata for association

---

## 🔍 CURRENT STATE ANALYSIS

### Data Structure

**Image Provisions:** 1,129 provisions
```sql
ref_number: "img_2_219"
document_id: "Inner_West_Ashfield_DCP_2016___Chapter_A..."
provision_text: "Image: images/a660c46...jpg | Page: 49 | Context: None"
pdf_page: NULL  ← Not populated!
is_canonical: true
```

**Non-Image Provisions:** 20,702 provisions
```sql
ref_number: "4.1.6.2"
document_id: "Inner_West_Ashfield_DCP_2016___Chapter_A..."
provision_text: "Building setbacks must comply..."
pdf_page: 48  ← Only 26% have this!
is_canonical: true
```

**Image Files:** 2,077 JPG files
- Location: `frontend-nextjs/public/images/[64-char-hash].jpg`
- Size: 245 MB total
- Accessible at: `/images/[hash].jpg`

###metadata Coverage

| Category | Total | With pdf_page | Coverage |
|----------|-------|---------------|----------|
| **Image provisions** | 1,129 | 0 (0%) | ❌ **0%** |
| **DCP provisions** | 14,955 | 5,404 (36.1%) | 🟡 **36%** |
| **LEP provisions** | 967 | 0 (0%) | ❌ **0%** |
| **SEPP provisions** | 4,780 | 0 (0%) | ❌ **0%** |

**Critical Finding:** Images have page numbers in text (`"Page: 49"`) but not in `pdf_page` column!

---

## 🚫 WHY IMAGES DON'T DISPLAY

### Problem 1: Format Mismatch

**Frontend Expects:**
```typescript
// ReactMarkdown in TruncatedFormattedText component
// Line 147-157 in LegalTextPanel.tsx
components={{
  img: ({ node, ...props }) => (
    <img src={props.src} className="..." />
  )
}}
// Expects: ![alt](path) markdown syntax
```

**Database Has:**
```
Plain text: "Image: images/a660c46...jpg | Page: 49 | Context: None"
```

**Result:** ReactMarkdown ignores plain text, no images render.

### Problem 2: Separate Provisions

**Current API Behavior:**
```javascript
// /api/provisions?q=setback returns:
[
  { id: 1000, ref: "4.1.6", text: "Building setbacks..." },
  { id: 1001, ref: "img_2_219", text: "Image: images/..." },  // Separate card!
  { id: 1002, ref: "4.1.7", text: "Front setbacks..." }
]
```

**Frontend Renders:**
```
[Card 1] 4.1.6: Building setbacks...
[Card 2] img_2_219: [broken image text]  ← User sees this!
[Card 3] 4.1.7: Front setbacks...
```

**User Experience:** Confusing image "provisions" with ref numbers like `img_2_219` show up as separate results.

### Problem 3: Insufficient Metadata for Association

**Cannot reliably match images to parents because:**

1. **Page numbers incomplete:**
   - Images: 0% have pdf_page column populated
   - Provisions: Only 36% (in DCPs only) have pdf_page
   - **Result:** Can't use spatial proximity (page N vs page N+1)

2. **No explicit parent_id:**
   - No foreign key linking image → parent provision
   - No `parent_provision_id` column
   - **Result:** Must infer relationship

3. **Text reference missing:**
   - Parent provisions don't contain "See Figure 4.1.6" references
   - Can't search provision text for image mentions
   - **Result:** Can't use content-based matching

---

## 💡 SOLUTION OPTIONS: DETAILED ANALYSIS

### Option 1: Database Embedding (Direct Approach)

**What it does:**
1. Extract page number from image provision_text
2. Find parent provision (same document, closest preceding page)
3. Append markdown image to parent provision_text
4. Delete image provision

**Implementation:**
```sql
-- Step 1: Extract page numbers into pdf_page column
UPDATE regulatory_provisions
SET pdf_page = (regexp_match(provision_text, 'Page: (\d+)'))[1]::int
WHERE ref_number LIKE 'img_%';

-- Step 2: For each parent provision, append child images
UPDATE regulatory_provisions parent
SET provision_text = provision_text || E'\n\n' || (
  SELECT string_agg(
    '![Diagram](/images/' ||
    regexp_replace(img.provision_text, '.*images/([a-f0-9]{64}\.jpg).*', '\1') ||
    ')',
    E'\n\n'
  )
  FROM regulatory_provisions img
  WHERE img.document_id = parent.document_id
    AND img.ref_number LIKE 'img_%'
    AND img.pdf_page >= parent.pdf_page
    AND img.pdf_page < COALESCE(
      (SELECT p2.pdf_page FROM regulatory_provisions p2
       WHERE p2.document_id = parent.document_id
         AND p2.pdf_page > parent.pdf_page
         AND p2.ref_number NOT LIKE 'img_%'
       ORDER BY p2.pdf_page ASC LIMIT 1),
      999999
    )
)
WHERE parent.ref_number NOT LIKE 'img_%'
  AND parent.pdf_page IS NOT NULL
  AND EXISTS (
    SELECT 1 FROM regulatory_provisions img
    WHERE img.document_id = parent.document_id
      AND img.ref_number LIKE 'img_%'
      AND img.pdf_page >= parent.pdf_page
  );

-- Step 3: Delete image provisions
DELETE FROM regulatory_provisions WHERE ref_number LIKE 'img_%';
```

**Pros:**
- ✅ Works with search/filter/sort (images travel with text)
- ✅ No code changes needed (ReactMarkdown already handles markdown)
- ✅ Single API call, no extra joins
- ✅ Clickable zoom already implemented (line 155 in LegalTextPanel.tsx)

**Cons:**
- ❌ Only works for 36% of provisions (those with pdf_page)
- ❌ Irreversible (destroys separation of concerns)
- ❌ Increases provision_text size (could hit limits)
- ❌ Loses ability to update/replace images independently
- ❌ What if matching logic is wrong? Can't easily fix
- ❌ Images tied to single parent (can't reuse across provisions)

**Risk Assessment:**
- **Data Loss Risk:** HIGH - Cannot undo, original structure destroyed
- **Matching Accuracy:** MEDIUM - Only 36% matchable, 64% unmatchable
- **Maintenance:** LOW - Simple structure, but brittle

---

### Option 2: Relational Approach (Junction Table)

**What it does:**
Create `provision_images` junction table to maintain many-to-many relationships.

**Schema:**
```sql
CREATE TABLE provision_images (
  id SERIAL PRIMARY KEY,
  provision_id INTEGER REFERENCES regulatory_provisions(id),
  image_id INTEGER REFERENCES regulatory_provisions(id),
  display_order INTEGER DEFAULT 0,
  position TEXT CHECK (position IN ('inline', 'after', 'before', 'reference')),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_provision_images_provision ON provision_images(provision_id);
CREATE INDEX idx_provision_images_image ON provision_images(image_id);
```

**API Changes:**
```typescript
// New endpoint: /api/provisions/[id]/images
async function getProvisionImages(provisionId: number) {
  const result = await client.query(`
    SELECT
      rp.provision_text,
      (regexp_match(rp.provision_text, 'images/([a-f0-9]{64}\.jpg)'))[1] as image_hash,
      pi.display_order,
      pi.position
    FROM provision_images pi
    JOIN regulatory_provisions rp ON pi.image_id = rp.id
    WHERE pi.provision_id = $1
    ORDER BY pi.display_order
  `, [provisionId]);

  return result.rows;
}
```

**Frontend Changes:**
```typescript
// In LegalTextPanel.tsx
const [provisionImages, setProvisionImages] = useState<Map<number, ImageData[]>>(new Map());

useEffect(() => {
  // Fetch images for all provisions
  Promise.all(
    provisions.map(p =>
      fetch(`/api/provisions/${p.id}/images`).then(r => r.json())
    )
  ).then(results => {
    const imageMap = new Map();
    provisions.forEach((p, i) => {
      imageMap.set(p.id, results[i]);
    });
    setProvisionImages(imageMap);
  });
}, [provisions]);

// Render
{provisions.map(provision => (
  <div>
    <TruncatedFormattedText text={provision.provision_text} />
    {provisionImages.get(provision.id)?.map(img => (
      <img src={`/images/${img.image_hash}`} />
    ))}
  </div>
))}
```

**Pros:**
- ✅ Maintains data integrity (normalized structure)
- ✅ One image can belong to multiple provisions
- ✅ Easy to update/reorder images
- ✅ Reversible (can drop table, no data loss)
- ✅ Explicit relationships (no inference needed)
- ✅ Can track position metadata (inline vs after)

**Cons:**
- ❌ Requires schema migration
- ❌ Need to populate 1,129+ junction table rows
- ❌ Extra API call per provision (N+1 query problem)
- ❌ Frontend complexity (state management for images)
- ❌ Slightly slower (additional JOIN)
- ❌ Still need matching algorithm to populate initially

**Risk Assessment:**
- **Data Loss Risk:** LOW - Additive, doesn't modify existing data
- **Matching Accuracy:** MEDIUM - Still relies on page number matching
- **Maintenance:** MEDIUM - More complex queries, but flexible

---

### Option 3: JSONB Metadata Column

**What it does:**
Add `related_image_ids` JSON column to provisions, fetch images client-side.

**Schema:**
```sql
ALTER TABLE regulatory_provisions
ADD COLUMN related_image_ids INTEGER[] DEFAULT '{}';

-- Populate using page-based matching
UPDATE regulatory_provisions parent
SET related_image_ids = ARRAY(
  SELECT img.id
  FROM regulatory_provisions img
  WHERE img.document_id = parent.document_id
    AND img.ref_number LIKE 'img_%'
    AND (regexp_match(img.provision_text, 'Page: (\d+)'))[1]::int >= parent.pdf_page
    AND (regexp_match(img.provision_text, 'Page: (\d+)'))[1]::int < COALESCE(
      (SELECT p2.pdf_page FROM regulatory_provisions p2
       WHERE p2.document_id = parent.document_id AND p2.pdf_page > parent.pdf_page
       ORDER BY p2.pdf_page ASC LIMIT 1),
      999999
    )
  ORDER BY (regexp_match(img.provision_text, 'Page: (\d+)'))[1]::int
)
WHERE parent.pdf_page IS NOT NULL
  AND parent.ref_number NOT LIKE 'img_%';

CREATE INDEX idx_provisions_related_images ON regulatory_provisions USING GIN(related_image_ids);
```

**API Query:**
```sql
SELECT
  p.id,
  p.ref_number,
  p.provision_text,
  p.related_image_ids,
  ARRAY(
    SELECT json_build_object(
      'image_hash', regexp_replace(rp.provision_text, '.*images/([a-f0-9]{64}\.jpg).*', '\1'),
      'page', regexp_replace(rp.provision_text, '.*Page: (\d+).*', '\1')::int
    )
    FROM regulatory_provisions rp
    WHERE rp.id = ANY(p.related_image_ids)
  ) as images
FROM regulatory_provisions p
WHERE ...;
```

**Pros:**
- ✅ Simple schema change (single column)
- ✅ PostgreSQL array queries are fast with GIN index
- ✅ Single query (no joins, no N+1)
- ✅ Reversible (can drop column)
- ✅ Works with existing search/filter

**Cons:**
- ❌ Denormalized (image IDs duplicated in many provisions)
- ❌ Array maintenance (need to update if images change)
- ❌ Still only works for 36% of provisions
- ❌ Frontend needs to parse image metadata

**Risk Assessment:**
- **Data Loss Risk:** LOW - Additive column
- **Matching Accuracy:** MEDIUM - Same 36% limitation
- **Maintenance:** MEDIUM - Need to keep arrays in sync

---

### Option 4: Smart Frontend Grouping (No DB Changes)

**What it does:**
Group image provisions with preceding non-image provision client-side.

**Implementation:**
```typescript
interface EnrichedProvision {
  provision: Provision;
  images: Provision[];
}

function groupProvisionsWithImages(provisions: Provision[]): EnrichedProvision[] {
  const groups: EnrichedProvision[] = [];
  let currentGroup: EnrichedProvision | null = null;

  provisions.forEach(p => {
    if (p.ref_number.startsWith('img_')) {
      // Add to current group's images
      if (currentGroup) {
        currentGroup.images.push(p);
      }
    } else {
      // Start new group
      currentGroup = { provision: p, images: [] };
      groups.push(currentGroup);
    }
  });

  return groups;
}

// Render
{groupProvisionsWithImages(provisions).map(group => (
  <div key={group.provision.id}>
    <TruncatedFormattedText text={group.provision.provision_text} />
    {group.images.map(img => {
      const hash = img.provision_text.match(/images\/([a-f0-9]{64}\.jpg)/)?.[1];
      return hash ? (
        <img
          src={`/images/${hash}`}
          onClick={() => setZoomedImage(`/images/${hash}`)}
        />
      ) : null;
    })}
  </div>
))}
```

**Pros:**
- ✅ No database changes whatsoever
- ✅ Instant implementation (< 30 minutes)
- ✅ Fully reversible
- ✅ Works for all provisions (100% coverage)
- ✅ Simple logic

**Cons:**
- ❌ **BREAKS WITH SEARCH** - images lost when filtering
- ❌ **BREAKS WITH SORT** - images attached to wrong parent
- ❌ **BREAKS WITH PAGINATION** - images split across pages
- ❌ Assumes provisions fetched in document order
- ❌ Fragile (depends on API query order)

**Failure Scenarios:**
```javascript
// Scenario 1: User searches "setback"
// API returns provisions sorted by relevance, images filtered out
provisions = [
  { id: 1003, ref: "4.1.7", score: 0.95 },  // Page 50
  { id: 1000, ref: "4.1.6", score: 0.80 },  // Page 48
  // img_2_219 (page 49) excluded - doesn't match "setback"
]
// Result: No images displayed

// Scenario 2: User sorts by clause number
provisions = [
  { id: 1000, ref: "4.1.6" },  // Text provision
  { id: 1003, ref: "4.1.7" },  // Text provision
  { id: 1001, ref: "img_2_219" },  // Image sorts to end (alphabetically)
]
// Result: Image attached to wrong parent (4.1.7 instead of 4.1.6)
```

**Risk Assessment:**
- **Data Loss Risk:** NONE - No DB changes
- **Matching Accuracy:** HIGH - If provisions in document order
- **Maintenance:** HIGH - Breaks easily with any API changes

---

## 📊 COMPARISON MATRIX

| Criteria | Embedding | Junction Table | JSONB Array | Frontend Grouping |
|----------|-----------|----------------|-------------|-------------------|
| **Implementation Time** | 2 hours | 6 hours | 3 hours | 30 minutes |
| **Works with Search** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Works with Filter** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Works with Sort** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Works with Pagination** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Coverage** | 🟡 36% | 🟡 36% | 🟡 36% | ✅ 100% |
| **Reversible** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Performance** | ✅ Fast | 🟡 Medium | ✅ Fast | ✅ Fast |
| **Maintenance** | ✅ Simple | 🟡 Medium | 🟡 Medium | ❌ Fragile |
| **Data Integrity** | ❌ Lost | ✅ Maintained | 🟡 Denormalized | ✅ Maintained |
| **Code Changes** | None | Medium | Small | Small |

---

## 🎯 RECOMMENDED SOLUTION: Hybrid Approach

### Phase 1: Quick Fix (Frontend Grouping) - Deploy Tomorrow

**For immediate user value:**
- Implement frontend grouping
- **Only apply when:** API returns provisions in document+page order
- **Disable when:** User applies search/filter/sort

```typescript
const canGroupImages = !hasSearchQuery && !hasFilters && !hasSorting;

{canGroupImages ? (
  // Grouped view
  groupProvisionsWithImages(provisions).map(renderGroup)
) : (
  // Ungrouped view (current behavior)
  provisions.filter(p => !p.ref_number.startsWith('img_')).map(renderProvision)
)}
```

**User Experience:**
- ✅ Images show immediately for document browsing
- ⚠️ Warning shown when search/filter active: "Images hidden when filtering"
- 🔍 Search still works (just no images during search)

**Timeline:** 2-3 hours implementation + testing

---

### Phase 2: Permanent Fix (JSONB + Backfill) - Next Sprint

**Step 1: Fix Missing pdf_page for Images**
```sql
-- Populate pdf_page for images from text
UPDATE regulatory_provisions
SET pdf_page = (regexp_match(provision_text, 'Page: (\d+)'))[1]::int
WHERE ref_number LIKE 'img_%' AND pdf_page IS NULL;
```

**Step 2: Add Metadata Column**
```sql
ALTER TABLE regulatory_provisions
ADD COLUMN related_image_ids INTEGER[] DEFAULT '{}';
```

**Step 3: Intelligent Matching**
```sql
-- Match images to provisions by:
-- 1. Same document
-- 2. Image page between this provision and next
-- 3. Within reasonable distance (< 5 pages)
UPDATE regulatory_provisions parent
SET related_image_ids = ARRAY(
  SELECT img.id
  FROM regulatory_provisions img
  WHERE img.document_id = parent.document_id
    AND img.ref_number LIKE 'img_%'
    AND img.pdf_page >= parent.pdf_page
    AND img.pdf_page < COALESCE(
      (SELECT MIN(p2.pdf_page) FROM regulatory_provisions p2
       WHERE p2.document_id = parent.document_id
         AND p2.pdf_page > parent.pdf_page
         AND p2.ref_number NOT LIKE 'img_%'),
      parent.pdf_page + 5  -- Fallback: within 5 pages
    )
  ORDER BY img.pdf_page
)
WHERE parent.ref_number NOT LIKE 'img_%'
  AND parent.pdf_page IS NOT NULL;
```

**Step 4: Update API**
```typescript
const result = await client.query(`
  SELECT
    p.*,
    COALESCE(
      json_agg(
        json_build_object(
          'hash', regexp_replace(img.provision_text, '.*images/([a-f0-9]{64}\.jpg).*', '\1'),
          'page', img.pdf_page
        ) ORDER BY img.pdf_page
      ) FILTER (WHERE img.id IS NOT NULL),
      '[]'
    ) as images
  FROM regulatory_provisions p
  LEFT JOIN regulatory_provisions img ON img.id = ANY(p.related_image_ids)
  WHERE ...
  GROUP BY p.id
`);
```

**Step 5: Update Frontend**
```typescript
{provisions.map(provision => (
  <div>
    <TruncatedFormattedText text={provision.provision_text} />
    {provision.images?.map((img: any) => (
      <img
        src={`/images/${img.hash}`}
        onClick={() => setZoomedImage(`/images/${img.hash}`)}
      />
    ))}
  </div>
))}
```

**Coverage:** 36% now, but foundation for future 100%

**Timeline:** 1 week (3 days dev + 2 days testing + 2 days buffer)

---

### Phase 3: Complete Coverage (Extract Remaining Documents) - Future

**Extract SEPPs & LEPs with MinerU:**
- Run MinerU on 109 SEPPs → +4,237 provisions with pdf_page
- Run MinerU on 7 LEPs → +967 provisions with pdf_page
- Re-run backfill script

**Result:** 83% coverage (up from 36%)

**Timeline:** 2-3 weeks (extraction time + validation)

---

## ⚠️ CRITICAL CONSTRAINTS

### The 36% Problem

**Reality Check:**
- Only DCPs have pdf_page (36% of provisions)
- SEPPs/LEPs have ZERO pdf_page
- Cannot match images without page numbers

**Options:**
1. **Accept 36% coverage** - Acknowledge limitation, focus on DCPs
2. **Extract more documents** - MinerU on SEPPs/LEPs (3 weeks)
3. **Alternative matching** - Use ref_number proximity, document structure
4. **Manual curation** - Associate images via admin UI (labor-intensive)

**Recommendation:** Accept 36% for now, plan extraction sprint for 83%.

---

## 🚀 IMPLEMENTATION PLAN

### Week 1: Quick Win
- [ ] Day 1: Implement frontend grouping with conditional logic
- [ ] Day 2: Add user warning for filtered views
- [ ] Day 3: Test with real data, deploy to staging
- [ ] Day 4-5: User testing, bug fixes

**Deliverable:** Images visible when browsing documents

### Week 2-3: Permanent Solution
- [ ] Day 1: Populate pdf_page for images
- [ ] Day 2: Add related_image_ids column
- [ ] Day 3: Implement matching algorithm
- [ ] Day 4: Update API with image joins
- [ ] Day 5: Update frontend to use API images
- [ ] Week 3: Testing, rollout, documentation

**Deliverable:** Images work with search/filter/sort

### Month 2: Complete Coverage (Optional)
- [ ] Week 1: MinerU extraction planning
- [ ] Week 2-3: Extract SEPPs/LEPs
- [ ] Week 4: Backfill, testing, validation

**Deliverable:** 83% coverage

---

## 📝 DECISION MATRIX

**Choose Frontend Grouping if:**
- ✅ Need immediate results (< 1 day)
- ✅ Users primarily browse documents (not search)
- ✅ Okay with temporary solution

**Choose JSONB Array if:**
- ✅ Need production-ready solution (1-2 weeks)
- ✅ Users heavily use search/filter
- ✅ Want flexibility for future changes
- ✅ Accept 36% initial coverage

**Choose Junction Table if:**
- ✅ Need maximum flexibility
- ✅ Have 2+ weeks for implementation
- ✅ Want to support multiple parents per image
- ✅ Plan to build admin UI for image management

**Choose Embedding if:**
- ❌ Never - Too risky, irreversible, low coverage

---

## 🎯 FINAL RECOMMENDATION

**Implement Hybrid Approach:**

1. **This Week:** Frontend grouping (conditional)
   - Fast user value
   - No risk
   - Foundation for Phase 2

2. **Next Sprint:** JSONB + intelligent matching
   - Production-ready
   - Works with search/filter
   - 36% coverage (acceptable MVP)

3. **Future:** Extract remaining documents
   - 83% coverage
   - Complete solution

**Total Timeline:** 1 week MVP → 3 weeks production → 2 months complete

**User Experience:**
- Week 1: Images visible when browsing ✓
- Week 3: Images visible with search ✓
- Month 2: 83% of provisions have images ✓

---

**Status:** Ready for implementation decision
**Next Step:** Choose approach and proceed with Phase 1
