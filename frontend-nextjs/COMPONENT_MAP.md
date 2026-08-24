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
    ↓ ⚠ pdf_printed_page was null on 100% of 2,623 provisions when measured
    ↓   2026-08-24 (Ashfield) — see "What the three tabs ACTUALLY serve" below
  ProvisionsByTocStructure.tsx
    ↓ passes provisions array
  PageGroupedProvisions.tsx
    ↓ groups by page via groupProvisionsByPage()
    ↓ displays page numbers via group.displayPageNumber
  ```

**LEP Tab:**
- `LepControls.tsx`
- API: **none of its own.** Every value arrives as props from `app/assessment/page.tsx`,
  which gets them from `usePropertyAssessment` → **`GET /api/property?address=…`**
  (NOT `/api/property/profile` — that is a different, flatter endpoint that returns no
  `constraints` and no `planningLayers`, and nothing on this tab reads it).

**SEPP Tab:**
- `StateLevelControls.tsx`
- APIs: `/api/adg/requirements`, `/api/sepp/structured-requirements`,
  `/api/tod/transport-autocomplete`, plus the same `/api/property` props.

---

## What the three tabs ACTUALLY serve — measured, not declared

> Captured 2026-08-24 from a running dev server for **100 Ramsay Street, Haberfield NSW
> 2045** (E1, Inner West / former **Ashfield** — one of the three deepest councils), by
> calling the endpoints and counting fields in the responses. Re-run rather than quote.
> A TypeScript interface listing a field is NOT evidence the field is populated: three of
> the ones below are declared and always null.

### LEP tab — `GET /api/property` → `data.constraints` + `data.heightSource` / `fsrSource`

Every numeric arrives with a clause and a live legislation URL:

| Shown | Value | Clause | Source |
|---|---|---|---|
| Max height | `10` | `Clause 4.3` | `legislation.nsw.gov.au/…/epi-2022-0457` |
| Max FSR | `1` | `Clause 4.4` | same |
| Heritage | `C54`, Haberfield HCA | `Clause 5.10` | `heritageLegislationUrl` |
| Instrument | Inner West LEP 2022 | — | `landApplicationInstruments` |

`planningLayers` returned **12** layers (Land Zoning, Height of Buildings, FSR, Heritage,
Acid Sulfate, Additional Permitted Uses, Special Provisions, …).

**This is Planning Portal data.** It is properly clause-cited, and it is also the part any
competitor can obtain from the same public API. It is not the differentiator.

### DCP tab — `GET /api/provisions/for-property?groupBy=toc&former_council=…&zone=…&heritage=…&hca=…&precinct_id=…`

**2,623 provisions** served for this property, across 17 TOC parts. Field coverage:

| Field | Populated |
|---|---|
| `pdf_page` | **100%** |
| `v2_topic` | **100%** |
| `ref_number` / `section_header` / `pdf_source_file` | **51.7%** |
| `pdf_page_image_url` | **48.3%** |
| `v2_marker` | 42.0% |
| `v2_precinct_id` | 7.6% |
| `v2_has_numeric_value` = **true** | **3.8%** (100 of 2,623) |
| `clause_label` | **0%** — declared in the interface, never populated |
| `pdf_printed_page` | **0%** |
| `relevance_level` / `relevance_reason` | **0%** (computed client-side) |

So the DCP tab is a **text corpus**: about half the provisions carry a clause reference
(via `ref_number` / `section_header`, NOT `clause_label`), just under half carry a page
image, and only 3.8% carry a numeric value. `PageGroupedProvisions.tsx` derives the
displayed page from `pdf_printed_page` first — which is null on every row here — so it
always falls through to the `pdf_page` + offset path.

### The numeric DCP controls are a SEPARATE surface

`DcpStructuredControls.tsx` → **`GET /api/dcp/structured-controls?council=…&dev_type=…`**
→ table `dcp_setback_controls` (967 live rows). For `ashfield` / `dwelling_house` it
returned **8 controls** in 5 categories (Setbacks 3, Parking 1, Site Coverage 1,
Landscaping & Canopy 2, Open Space 1), each carrying:

`control_type` · `value_min` / `value_max` · `unit` · `direction` · `condition` ·
`source_text` (verbatim quote from the DCP) · `section_ref` · `dcp_name` ·
`as_at` (`2017-01-10`, `basis: stated_in_document`)

`pdf_page` was present on 1 of 8 and `pdf_url` on 0 of 8.

**This is the differentiator** — deterministic numeric controls with the council's own
wording and an in-force date — and it is a different component and endpoint from the DCP
provisions tab. Do not conflate the two when describing coverage.

### ⚠ `setback_rules` is EMPTY (0 rows) and six surfaces read it

`GET /api/setbacks/reference?zone=…&lga=…` queries **`setback_rules`**, not
`dcp_setback_controls`. That table has **0 rows in production**, so the endpoint returns
`{"data": null}` for every zone and council — verified for R2 and E1 across Ashfield,
Waverley, Marrickville, Leichhardt and Ku-ring-gai. The inline setback reference chips on
the DCP tab therefore never render, silently.

Other readers of the same empty table: `/api/capacity/calculate`,
`/api/compliance/constraints`, `/api/setbacks/adg`, `lib/database/client.ts`,
`ComplianceDashboard.tsx`, `StateLevelControls.tsx`. Whether each degrades safely is NOT
established here — only that the table they read is empty.

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

### `/duplex-check` — Ads landing page (duplex verdict + builder referral)

**Page Component:** `app/duplex-check/page.tsx` (client) + `layout.tsx` (metadata, noindex)

Same engine + `/api/upzoning` proxy as the tool page, conversion-optimised shell:
no SiteNav/SiteFooter (1:1 attention ratio), verdict banner as the hero,
`BuilderReferralCard` directly under an eligible verdict, planning detail in a
`<details>` accordion, one-line disclaimer. Shared types/labels in `lib/upzoning.ts`
(also imported by the tool page). `tool_run` posthog event carries `source: 'ads_landing'`.
SEO traffic keeps landing on `/tools/upzoning-check`; this route is noindexed.

### `/embed/upzoning` + `/widget-demo/[slug]` — White-label duplex checker (builder partners)

**Components:** `app/embed/upzoning/page.tsx` (embed route, server) →
`components/tools/DuplexCheckWidget.tsx` (client) · `app/widget-demo/[slug]/page.tsx`
(per-builder demo shell, server) · config in `lib/widget-partners.ts` (20 partners).

Third surface over the same engine + `/api/upzoning` proxy: compact, iframe-embeddable,
carries the PARTNER's name, and on an eligible verdict the CTA links to the partner's
own contact page (no `BuilderReferralCard` — the enquiry belongs to the partner). Embed
branding resolves by `?ref=<slug>` from the registry; free-form `?partner=`/`?cta=`
params pass through `sanitizePartnerName`/`sanitizeCtaUrl` and are ignored when `ref`
is registered. Demo pages are noindexed, reached only from outreach emails; posthog:
`tool_run` with `source: 'widget'` + `partner`, and `widget_cta_click`. Verdict is
never conditioned on partner presence (neutrality rule).

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
      ├─ BriefIntentBar (flag-gated: intent chips shown during the stream wait)
      ├─ BriefOverlayCard (flag-gated: fetches /api/brief-overlay after complete + intent picked)
      ├─ ProgressBar (progress during streaming)
      ├─ SectionCard × N (progressive section rendering)
      └─ CompleteSummary (confidence, constraints, gaps)
```

**LLM overlay (dark by default):** `components/reports/BriefIntentOverlay.tsx` +
`app/api/brief-overlay/route.ts` → Railway `/pipeline/brief-overlay`
(`services/brief_overlay_api.py` → `brief_narration.generate_overlay`). Needs BOTH
`NEXT_PUBLIC_BRIEF_LLM_OVERLAY_ENABLED=true` (Vercel build env) and
`BRIEF_LLM_OVERLAY_ENABLED=true` (Railway) before anything shows.

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
