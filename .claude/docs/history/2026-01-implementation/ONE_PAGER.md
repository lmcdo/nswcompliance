# NSW Development Compliance Engine

**Intelligent DCP filtering for building certifiers and town planners**

---

## The Problem

NSW Inner West Council has 3 former council DCPs containing **48,000+ provisions** across 500+ pages.

For any given property, only ~50-90 provisions actually apply.

**Current workflow:**
- Read entire DCP documents (hours)
- Manually determine which Parts apply to your zone
- Hunt for which Heritage Conservation Area you're in
- Cross-reference 3 separate DCPs
- Miss precinct-specific controls buried in Part 9
- Re-do this for every new address

---

## The Solution

Enter an address → See only provisions that apply to that property.

```
User enters: 15 Smith St, Marrickville

System queries NSW Planning Portal API:
  → Zone: R2
  → Heritage: Yes (HCA C26 - Marrickville South)
  → Flood: No
  → Precinct: 12

4-Layer Filter applies automatically:

  Layer 1 (Generic):   Base controls everyone needs      → 200 provisions
  Layer 2 (Zone):      R2-specific only                  → +80 provisions
  Layer 3 (Condition): Heritage HCA C26 only             → +60 provisions
  Layer 4 (Precinct):  Precinct 12 only                  → +30 provisions
                                                         ─────────────────
                                                           370 provisions

User selects: "Rear Addition" + "CDC"                    → 52 provisions
```

**48,000 → 52 relevant provisions in seconds**

---

## PDF vs App

| Manual PDF Approach | Compliance Engine |
|---------------------|-------------------|
| Read entire 500-page DCP | See only relevant provisions |
| Manually check "does Part 4.1 apply to R2?" | Auto-filtered by zone |
| Hunt for which HCA you're in | Auto-detected from address |
| Miss precinct-specific controls | Auto-included by location |
| Cross-reference 3 separate DCPs | All merged in one view |
| Hours per property | Seconds per property |

---

## What You See

### State-Level Controls (Automatic)

**Apartment Design Guide (ADG)** — appears automatically for R3, R4, B1-B6 zones
- Design criteria: apartment sizes, ceiling heights, ventilation minimums
- Building separation tables by height
- Zone restriction warnings

**TOD Parking Reductions** — appears when near qualifying transport
- Heavy rail ≤800m, light rail ≤600m, frequent bus ≤400m
- Automatic parking reduction rates (10-30%)
- Designated TOD precinct detection

### DCP Provisions

**Original regulatory text** — not AI summaries. Exact wording for professional reports.

**DCP structure preserved** — provisions organized by Part and Section as they appear in the document.

**PDF page links** — click to view the original DCP page for verification.

**Professional citations** — section markers (C1, C2, etc.) for compliance reports.

---

## How It Works

**Data pipeline (one-time):**
1. Extract provisions from DCP PDFs (MinerU)
2. Classify by layer, zone, condition, precinct (LLM enrichment)
3. Link to document TOC by page ranges
4. Store in database with all metadata

**Runtime (per address):**
1. Query NSW Planning Portal for property attributes
2. Detect precinct from coordinates
3. Filter provisions by 4-layer model
4. Display with document structure

---

## Coverage

**Inner West Council (3 former councils):**
- Marrickville DCP 2011 — 12 Parts, 26,000+ provisions
- Leichhardt DCP 2013 — Parts A-G, 15,000+ provisions
- Ashfield DCP 2016 — Chapters A-F, 7,000+ provisions

**Data quality:**
- 48,374 total provisions extracted
- 97% have layer classification
- 100% have PDF page references
- TOC linking for section-level display

---

## Competitive Landscape

**NSW Government AI Solutions Panel** ($5.6M investment):

**DAISY** (ADAPTOVATE/EnterpriseAI)
- Focus: DA validation, document checking
- Gap: No structured DCP provisions, no precinct filtering

**PropCode CDC**
- Focus: CDC eligibility checking
- Gap: Treats councils separately, no merged council logic

**Our Differentiation:**
- **Precinct-level filtering** — PropCode doesn't handle Inner West's 3 unconsolidated DCPs
- **Provision data layer** — The structured regulatory content these tools need but don't have
- **Merged council complexity** — Built specifically for councils with multiple active DCPs

---

## Integration Opportunities

**Council Direct (Pilot Model):**
- Pre-lodgement self-assessment for applicants
- Staff lookup tool across 3 DCPs
- Reduces incomplete submissions (30% of DAs require additional info, adding 42 days average)
- Bridges gap until DCP consolidation (2+ years away)

**Platform Partners:**
- Provision API for PropCode/DAISY integration
- White-label for council portals
- Data layer for planning software vendors

**Expansion Path:**
- Northern Beaches (3 unconsolidated DCPs)
- Cumberland (3 unconsolidated DCPs)
- Any merged council pre-consolidation

---

## Broader Platform: PlotDetect

The compliance engine is one component of a property intelligence platform:

**Map Viewer** (charts.plotdetect.com.au)
- Interactive property search across all 127 NSW councils
- Planning controls: zoning, FSR, height, heritage
- DA/CDC volumes, approval rates, timelines
- Environmental overlays: bushfire, flood, acid sulfate

**Compliance Engine** (this product)
- DCP provision filtering by property attributes
- Professional-grade regulatory lookup
- Original text with PDF source links

**Combined Value:**
- Property intelligence (map) + Regulatory provisions (engine)
- Complete picture for any NSW address

---

## Target Users

**Building Certifiers** — CDC assessments, numeric controls, quick compliance checks

**Town Planners** — DA assessments, merit considerations, full provision review

**Architects** — Early design guidance, site constraint understanding

**Council Staff** — Pre-lodgement support, provision lookup across multiple DCPs

**Planning Software Vendors** — Provision data API for integration

---

*Provisions filtered by property. Original text preserved. Professional-grade citations.*
