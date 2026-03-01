# Professional User UX Design: Multi-Page Provisions

## The Real Problem

**Scenario:**
- Certifier checking compliance for 10 Blairgowie Street, Dulwich Hill
- Gets extracted requirement: "Front setback: 2-4 meters"
- Source provision is 4,803 characters spanning pages 5-7
- User needs to verify this is correct and check for conditions/exceptions

**Current UX (Broken):**
- Shows: "View PDF Page 5"
- User clicks → sees page 5
- Page 5 has general precinct description
- Setback text is actually on page 7
- User frustrated, loses trust in system

**Professional User Goals:**
1. ✅ Quick answer: "What's the setback requirement?" (we extract this)
2. ❓ Verify extraction: "Did the LLM get this right?"
3. ❓ Check conditions: "Are there exceptions or special cases?"
4. ❓ See context: "What else is relevant for this site?"
5. ✅ Audit trail: "Where exactly did this come from?"

---

## Solution: Progressive Disclosure with Context Access

### Level 1: Extracted Requirements (Current)

```
┌─────────────────────────────────────────────────┐
│ 📏 Setback - Front                              │
│ High Confidence                                  │
│                                                  │
│ Front setbacks should generally be between      │
│ 2 to 4 meters.                                  │
│                                                  │
│ [View Source Context] [View PDF Page 7]         │
└─────────────────────────────────────────────────┘
```

**What's new:**
- Accurate page number (7, not 5)
- "View Source Context" button

---

### Level 2: Source Context (Click "View Source Context")

```
┌─────────────────────────────────────────────────┐
│ 📄 Source: Section 9.10.1 Existing Character    │
│ Pages 5-7 | Found on Page 7                     │
│                                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ ...variety of buildings styles. A setback   │ │
│ │ of 2 metres to 4 metres is the most common.│ │
│ │ Frequently this area is soft landscape      │ │
│ │ although hard paving is common in some      │ │
│ │ parts of the precinct. Front fences are...  │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ [View Full Section] [View PDF Pages 5-7]        │
└─────────────────────────────────────────────────┘
```

**What this shows:**
- ±200 characters of surrounding text
- User sees context around the extracted requirement
- Can verify LLM extracted correctly
- See if there are conditions nearby

---

### Level 3: Full Section View (Click "View Full Section")

```
┌─────────────────────────────────────────────────┐
│ 📑 Full Section: 9.10.1 Existing Character      │
│ Pages 5-7 (3 pages)                             │
│                                                  │
│ [Page 5] [Page 6] [Page 7 - Current]            │
│                                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ [Full provision text, scrollable]           │ │
│ │                                              │ │
│ │ 9.10.1 Existing character                   │ │
│ │                                              │ │
│ │ This precinct is located in the western... │ │
│ │                                              │ │
│ │ ...                                          │ │
│ │                                              │ │
│ │ Front setbacks are generally consistent     │ │
│ │ within each street despite the variety of   │ │
│ │ buildings styles. ► A setback of 2 metres   │ │
│ │ to 4 metres is the most common. ◄           │ │
│ │ Frequently this area is soft landscape...   │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ [Open in PDF Viewer]                             │
└─────────────────────────────────────────────────┘
```

**What this shows:**
- Full section text (all 4,803 characters)
- Highlighting of extracted requirement (► ◄ markers)
- Page tabs to navigate within section
- Easy to read without opening PDF

---

### Level 4: PDF Viewer with Navigation

```
┌─────────────────────────────────────────────────┐
│ 📖 PDF Viewer: Dulwich Hill North Precinct      │
│                                                  │
│ [◄ Page 6] Page 7 of 18 [Page 8 ►]             │
│                                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │                                              │ │
│ │         [PDF page image]                     │ │
│ │                                              │ │
│ │   Front setbacks are generally consistent   │ │
│ │   within each street despite the variety    │ │
│ │   of buildings styles. A setback of 2       │ │
│ │   metres to 4 metres is the most common.    │ │
│ │   [highlighted in yellow]                    │ │
│ │                                              │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ Context: This is part of Section 9.10.1         │
│ (Pages 5-7). Use arrows to view adjacent pages. │
└─────────────────────────────────────────────────┘
```

**What this shows:**
- Actual PDF page with text highlighted
- Easy navigation to adjacent pages
- Context indicator showing section boundaries

---

## Implementation Strategy

### Phase 1: Fix Page Numbers (2 hours) - CRITICAL
✅ Already planned in COMPLETE_INNER_WEST_PAGE_FIX_PLAN.md

**Result:**
- Page numbers accurate
- Page ranges stored in database
- Users click to correct page

---

### Phase 2: Add Context Preview (3 hours) - HIGH VALUE

**Database:**
```sql
-- Already have this from V2 extraction
verbatim_source_text TEXT  -- Exact text from provision
```

**API Change:**
```typescript
// In /api/compliance/precinct-requirements/route.ts
// Return additional context fields

return {
  requirement_text: "Front setbacks: 2-4m",  // Clean summary
  verbatim_source_text: "A setback of 2 metres...",  // Exact text
  context_preview: provision_text.substring(pos-200, pos+300),  // Surrounding text
  section_title: "9.10.1 Existing Character",
  page_range: [5, 6, 7],  // All pages in section
  page_number: 7  // Specific page with this text
}
```

**UI Component:**
```tsx
// CategorizedRequirementsCard.tsx
<RequirementCard>
  <h3>Front setback: 2-4m</h3>
  <p>{requirement.requirement_text}</p>

  {/* NEW: Collapsible context */}
  <Collapsible trigger="View Source Context">
    <SourceContext>
      <p className="text-sm text-gray-600">
        Section {requirement.section_title} (Pages {requirement.page_range.join('-')})
      </p>
      <blockquote className="border-l-4 pl-4 my-2">
        {requirement.context_preview}
      </blockquote>
    </SourceContext>
  </Collapsible>

  <div className="flex gap-2">
    <Button onClick={() => viewFullSection(requirement.provision_id)}>
      View Full Section
    </Button>
    <Button onClick={() => openPDF(requirement.page_number)}>
      View PDF Page {requirement.page_number}
    </Button>
  </div>
</RequirementCard>
```

**Effort:** 3 hours
- API changes: 1 hour
- UI component: 1.5 hours
- Testing: 30 mins

---

### Phase 3: Full Section Viewer (4 hours) - MEDIUM VALUE

**API Endpoint:**
```typescript
// /api/provisions/[id]/full-text
GET /api/provisions/78829/full-text

Returns:
{
  provision_id: 78829,
  section_number: "9.10.1",
  section_title: "Existing Character",
  full_text: "...",  // All 4,803 characters
  page_range: [5, 6, 7],
  requirements: [
    {text: "Front setback: 2-4m", position: 4049}  // Highlight position
  ]
}
```

**UI Component:**
```tsx
<FullSectionModal>
  <PageTabs>
    <Tab>Page 5</Tab>
    <Tab>Page 6</Tab>
    <Tab active>Page 7</Tab>
  </PageTabs>

  <SectionText>
    {highlightRequirements(fullText, requirements)}
  </SectionText>
</FullSectionModal>
```

**Effort:** 4 hours
- API endpoint: 1 hour
- Modal component: 2 hours
- Highlighting logic: 1 hour

---

### Phase 4: PDF Viewer with Navigation (6 hours) - NICE TO HAVE

**Features:**
- Previous/Next page buttons
- Section boundary indicators
- Text highlighting on PDF images
- Jump to page functionality

**Effort:** 6 hours
- PDF navigation: 2 hours
- Highlighting: 3 hours (complex - need coordinate mapping)
- Polish: 1 hour

---

## Professional User Flow Example

**User:** Certifier checking 10 Blairgowie Street

**Step 1: Quick Check**
```
Sees: "Front setback: 2-4m" ✓
```
→ Most users stop here if it matches their design

**Step 2: Verify (if needed)**
```
Clicks: "View Source Context"
Reads: "...A setback of 2 metres to 4 metres is the most common..."
```
→ Confirms LLM extracted correctly

**Step 3: Check Conditions**
```
Reads context: "...although hard paving is common in some parts..."
```
→ Sees there might be flexibility for hard vs soft landscaping

**Step 4: Deep Dive (if needed)**
```
Clicks: "View Full Section"
Reads all of 9.10.1 (pages 5-7)
```
→ Discovers additional guidance about corner sites

**Step 5: Cite in Report**
```
Uses: "Section 9.10.1, Page 7, Marrickville DCP 2011"
```
→ Has accurate citation for certifier report

---

## Recommended Implementation Order

**Week 1 (CRITICAL):**
- ✅ Phase 1: Fix page numbers (2 hours)
- Result: Basic trust restored

**Week 2 (HIGH VALUE):**
- ✅ Phase 2: Add context preview (3 hours)
- Result: Professionals can verify extractions

**Week 3 (MEDIUM VALUE):**
- ✅ Phase 3: Full section viewer (4 hours)
- Result: Deep dive without leaving app

**Future (NICE TO HAVE):**
- Phase 4: Advanced PDF viewer (6 hours)

---

## Why This Works for Professionals

**1. Respects Their Expertise**
- Gives them control to verify
- Doesn't hide the source material
- Provides audit trail

**2. Saves Time**
- Quick answer first (Level 1)
- Context on demand (Level 2)
- Deep dive optional (Level 3-4)

**3. Builds Trust**
- Accurate page numbers
- Show your work (verbatim text)
- Easy to verify LLM didn't hallucinate

**4. Supports Workflow**
- Extract numbers for quick checks
- Context for verification
- Citations for reports
- PDF access for colleagues who want traditional view

---

## Data Already Available

**We have (from V2 extraction):**
- ✅ verbatim_source_text (exact text)
- ✅ primary_source_provision_id (links to provision)
- ✅ requirement_text (clean summary)

**We need (from page fix):**
- ⚠️ page_range (array of pages) - Phase 1
- ⚠️ accurate page_number - Phase 1

**We can derive (with queries):**
- ✅ context_preview (substring around verbatim)
- ✅ full_section_text (from regulatory_provisions)

**Minimal additional storage needed!**

---

## Quick Wins vs Long-term

**Quick Win (2 hours):**
- Fix page numbers
- Show page range in UI
- Result: "Section 9.10.1 (Pages 5-7) - View PDF Page 7"

**Medium Win (+3 hours = 5 hours total):**
- Add context preview
- Result: Users can verify without opening PDF

**Full Solution (+4 hours = 9 hours total):**
- Add full section viewer
- Result: Professional-grade UX

**Your Call:**
Do Phase 1+2 now (5 hours)?
Or just Phase 1 (2 hours) and see if users need more?

---

**Created:** 2025-10-29
**Focus:** Real professional user needs, not technical perfectionism
