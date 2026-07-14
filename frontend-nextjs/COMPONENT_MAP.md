# Component Map - UI Routes to Components

**PURPOSE:** Map user-visible UI to actual components rendering them.
**USAGE:** When debugging UI bugs, look up route/view here to find exact component to fix.

**Related Docs:**
- [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) - Complete CSS/color scheme reference
- [HERITAGE_UI_DESIGN.md](./HERITAGE_UI_DESIGN.md) - Heritage-specific UI patterns

---

## Main Routes

### `/assessment?address=X` - Property Assessment Page

**Page Component:** `app/assessment/page.tsx`

**Left Panel (property context):**
- Aerial tile with lot boundary: shared `components/reports/AerialTile.tsx` (SIX Maps imagery);
  polygon fetched from `/api/property/profile` (same source as brief + /property pages);
  `maplibre-gl.css` imported in `app/assessment/layout.tsx`

**Provisions Display:**
- **DCP Tab (Table of Contents view):**
  - `ProvisionsByTocStructure.tsx` (lines 1-100)
    - Calls API: `/api/provisions/for-property?groupBy=toc`
    - Renders: Left sidebar (TOC) + Right panel (provisions)
    - Delegates to: `PageGroupedProvisions.tsx`

- **Component Tree:**
  ```
  app/assessment/page.tsx
    └─ ProvisionsByTocStructure.tsx
        ├─ TocSidebar.tsx (left panel)
        └─ PageGroupedProvisions.tsx (right panel - RENDERS PROVISIONS)
            └─ Individual provision cards with PDF page buttons
  ```

- **UI Text Patterns to search for:**
  - "Part 8 · Page X" → rendered by `PageGroupedProvisions.tsx` line 544
  - "Page X (N provisions)" → rendered by `PageGroupedProvisions.tsx` line 544
  - PDF button title → `PageGroupedProvisions.tsx` line 562

- **Data Flow:**
  ```
  API: /api/provisions/for-property?groupBy=toc
    ↓ returns by_toc structure with pdf_page, pdf_printed_page
  ProvisionsByTocStructure.tsx
    ↓ passes provisions array
  PageGroupedProvisions.tsx
    ↓ groups by page via groupProvisionsByPage()
    ↓ displays page numbers via group.displayPageNumber
  ```

**LEP Tab:**
- `LepControls.tsx`
- API: Different endpoint

**SEPP Tab:**
- `StateLevelControls.tsx`
- API: Different endpoint

---

## Heritage Provisions Display

**ACTIVE COMPONENT:** `PageGroupedProvisions.tsx` (when viewing via DCP Tab → Part 8)

**DEAD COMPONENTS (NOT USED):**
- ❌ `HeritageProvisions.tsx` - Not imported anywhere, legacy code
- ❌ `HeritageProvisionsCard.tsx` - Old pattern, check imports before editing

**How to verify which component is used:**
```bash
# Search for imports of suspected component
grep -r "from.*HeritageProvisions" app/ components/
```

---

## Page Number Display

**All places that display PDF page numbers:**

1. **PageGroupedProvisions.tsx** ← MAIN ONE FOR DCP TAB ✅ FIXED 2026-02-13
   - Line 544: `<span>Page {group.displayPageNumber}</span>`
   - Line 562: `title="Page ${group.displayPageNumber}"`
   - Line 68: `getDcpPageNumber()` function - uses `pdf_printed_page` FIRST, then falls back to `pdf_page`
   - **Fix:** Function now correctly prioritizes `pdf_printed_page` over extraction `pdf_page`
   - **Tested:** Provision ID 78649 now shows "Page 6" (correct) instead of "Page 20" (extraction number)

2. **ProvisionsByTopic.tsx** ← USED FOR TOPIC VIEW (not TOC view)
   - Line 1301: `title="Page ${displayPage}"`
   - Line 1555: `title="Page ${displayPage}"`
   - Uses: `provision.pdf_printed_page || provision.pdf_page || 1`

3. **GeneralDCPSection.tsx** ← LEGACY/OLD
   - Check if still imported before editing

---

## API Endpoints

### `/api/provisions/for-property`

**Query params affecting response structure:**
- `groupBy=topic` → returns `by_topic` structure
- `groupBy=toc` → returns `by_toc` structure
- `heritage=true` → filters to heritage provisions
- `former_council=marrickville` → filters to specific council

**Response fields:**
- `pdf_page`: Extraction page number (sequential from extraction process)
- `pdf_printed_page`: Human-readable page number from actual PDF document
- `pdf_page_image_url`: R2 storage URL for page image

---

## Maintenance Instructions

**When adding new UI:**
1. Document the route
2. Document the component tree
3. Document the API calls
4. Document searchable UI text patterns

**When debugging:**
1. User describes bug with route + UI text
2. Look up route in this doc → find component
3. Search for UI text pattern to verify component
4. Fix the EXACT component listed here

**Auto-update hook (add to .claude/hooks.json):**
```json
{
  "postEdit": [
    {
      "pattern": "app/.*\\.tsx",
      "command": "echo 'REMINDER: Update COMPONENT_MAP.md if route structure changed'"
    }
  ]
}
```

---

## Quick Lookup Table

| User sees | Route | Component | Line |
|-----------|-------|-----------|------|
| "Part 8 · Page X" | `/assessment` DCP tab | PageGroupedProvisions.tsx | 544 |
| "Page X (N provisions)" | `/assessment` DCP tab | PageGroupedProvisions.tsx | 544 |
| PDF button tooltip | `/assessment` DCP tab | PageGroupedProvisions.tsx | 562 |
| Topic filter chips | `/assessment` DCP tab | ProvisionsByTocStructure.tsx | TBD |
| Heritage layer toggle | `/assessment` filters | TBD | TBD |
| DCP currency status bar (dot + verified date + staleness/amendment badges + disclaimer) | `/assessment` DCP tab | ProvisionsByTocStructure.tsx | ~1825 |

---

## Free Tools — /tools/*

### `/tools/upzoning-check` — Upzoning Check (2025 LMR/TOD reforms)

**Page Component:** `app/tools/upzoning-check/page.tsx` (client; mirrors `zoning-check` structure)

**Data Flow:**
```
PropertySearch → POST /api/upzoning (proxy, rate-limited)
  → Python POST /pipeline/upzoning (services/upzoning_check.py)
    → resolve_address + parse_controls (conveyancing pipeline helpers)
    → lot_dimensions (area + battleaxe-aware width from Portal geometry;
      flag lots use the developable head width, not the access handle)
    → housing_sepp_eligibility.evaluate_eligibility (live 776/752/759/452 gates,
      heritage suppression, fail-closed) — ALL eligibility logic lives here
  ← { status: ok|not_residential|unavailable, forms[], gates, heritage }
```

**Three-state rules:** engine `reason` strings render verbatim; `unconfirmed` → amber
"not determinable" (never green); `status=unavailable` → visible outage box (an outage
must never render as "nothing possible").

---

## Reports - Intelligence Brief

### `/reports/intelligence-brief` - Intelligence Brief Page

**Page Component:** `app/reports/intelligence-brief/page.tsx`

**Component Tree:**
```
app/reports/intelligence-brief/page.tsx
  └─ IntelligenceBriefInner (client component)
      ├─ AddressAutocomplete (address input)
      ├─ useRealtimeStream(@trigger.dev/react-hooks) — subscribes to Trigger.dev stream
      ├─ ProgressBar (progress during streaming)
      ├─ SectionCard × N (progressive section rendering)
      └─ CompleteSummary (confidence, constraints, gaps)
```

**Data Flow:**
```
POST /api/intelligence-brief → { runId, publicAccessToken }
  ↓ triggers Trigger.dev task → calls Python SSE endpoint
useRealtimeStream(runId, 'intelligence-brief', { accessToken })
  ↓ receives BriefEvent[] progressively
SectionCard renders each section as it arrives
CompleteSummary renders after 'complete' event
```

**API Route:** `app/api/intelligence-brief/route.ts`

---

**Last updated:** 2026-05-30
**Update trigger:** Any time a new component is added to `/assessment`, provision rendering changes, or reports routes are added
