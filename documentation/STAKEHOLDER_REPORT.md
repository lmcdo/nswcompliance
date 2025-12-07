# PlotDetect Compliance Engine
## Stakeholder Report — December 2025

---

## Executive Summary

PlotDetect is a professional planning compliance tool that provides instant access to NSW development controls for properties in the Inner West Council area. The system aggregates controls from:

- **State Environmental Planning Policies (SEPPs)**
- **Local Environmental Plans (LEPs)**
- **Development Control Plans (DCPs)**

Users enter a property address and receive filtered, relevant provisions based on the property's characteristics (zone, heritage status, precinct location).

**Current Coverage:** Inner West Council (Ashfield, Marrickville, Leichhardt former council areas)

---

## System Capabilities

### Address-Based Filtering

The system automatically filters provisions using the **4-Layer Model**:

| Layer | Description | Example |
|-------|-------------|---------|
| Generic | Applies to all development | Parking rates, setback principles |
| Zone-Specific | Filtered by property's zone | R2-specific dwelling controls |
| Condition | Filtered by site conditions | Heritage, flood, bushfire |
| Precinct | Filtered by location | Suburb-specific character controls |

### Data Sources

| Source | Provisions | Coverage |
|--------|------------|----------|
| Ashfield DCP | 1,420 | Full |
| Marrickville DCP | 812 | Full |
| Leichhardt DCP | 2,989 | Full |
| Inner West LEP 2022 | Integrated | Full |
| Relevant SEPPs | Integrated | Housing, Transport & Infrastructure |

### Key Features

1. **Property Lookup** — Integrates with NSW Planning Portal API for real-time property data
2. **Heritage Filtering** — Heritage Conservation Area (HCA) specific provisions
3. **PDF Source Links** — Direct links to source DCP pages for verification
4. **Topic Organisation** — Provisions grouped by professional topic (setbacks, parking, heritage, etc.)
5. **Dual Assessment Modes** — CDC (quantitative) and DA (full) provision sets

---

## Data Architecture

### Two-Table Design

The system uses complementary data sources:

| Table | Purpose | Quality |
|-------|---------|---------|
| `regulatory_provisions` | Complete DCP text from PDF extraction | Raw, comprehensive |
| `dcp_general_requirements` | LLM-distilled actionable requirements | Clean, structured |

**Rationale:** Raw provisions show full regulatory context; LLM-curated provisions power calculations (parking, setbacks) with cleaner data.

### Provision Classification

Each provision is tagged with:

- **Layer** — generic, zone_specific, condition, precinct
- **Topic** — 26 professional topics (setbacks, parking, heritage, etc.)
- **Type** — control, objective, definition, note
- **Markers** — DCP control markers (C1, O1, etc.)
- **Numeric values** — For quantitative compliance checking

---

## Current Status

### Data Quality Metrics

| Metric | Status |
|--------|--------|
| PDF page references | 100% coverage |
| Topic classification | 90%+ accuracy |
| Council separation | Verified correct |
| Heritage filtering | Working correctly |
| LaTeX/OCR artifacts | 91% cleaned |

### Resolved Issues (Past 30 Days)

| Issue | Resolution |
|-------|------------|
| Heritage topic fragmentation | Consolidated 364 provisions under single Heritage topic with subcategories |
| PDF page mismatches | Fixed page number display logic |
| Leichhardt false heritage inclusion | Excluded non-heritage "Connections" chapter |
| Stale data on address change | Added loading states and component refresh |

---

## Known Limitations

### 1. Provision Type Display

**Current:** All provisions shown in flat list without type distinction

**Impact:** Users see 400+ provisions per topic without knowing which are:
- Controls (must comply)
- Objectives (guiding principles)
- Character context (design guidance)

**Planned Enhancement:** Visual grouping and filtering by provision type (see Appendix A)

### 2. Provision Volume by Council

| Council | B2 Zone Provisions | Notes |
|---------|-------------------|-------|
| Marrickville | 412 | Baseline |
| Ashfield | 703 | Expected |
| Leichhardt | 1,021 | Includes context/character text |

Leichhardt's higher count reflects DCP structure (more contextual content), not data error.

### 3. Remaining Data Artifacts

- ~69 provisions with residual LaTeX formatting (from PDF math notation)
- Some OCR artifacts in historical text (spacing, special characters)

---

## Professional Workflow Support

### CDC Certifier Workflow

For Complying Development Certificate assessment:

- **Quantitative provisions** with numeric values
- Setbacks, heights, parking rates, landscaping percentages
- **Coverage:** 9-79 provisions per council (intentionally filtered)

### DA Planner Workflow

For Development Application merit assessment:

- **All provision types** including character and objectives
- Context for design decisions and merit arguments
- **Coverage:** 700-2,900 provisions per council (comprehensive)

---

## Roadmap

### Near-Term (Phase 1)

1. **Provision Type Filtering**
   - Add type counts to topic headers
   - Filter dropdown: All / Controls / Controls + Objectives

2. **Visual Hierarchy**
   - Badge controls (C markers) distinctly
   - Mute character/context text
   - Collapsible sections for dense topics

### Medium-Term (Phase 2)

1. **CDC Mode Enhancement**
   - Auto-filter to quantitative controls
   - Numeric value extraction display

2. **Additional Councils**
   - Expand beyond Inner West
   - Template-based DCP ingestion

---

## Appendix A: Proposed Provision Type UX

### Topic Header Enhancement

```
┌─────────────────────────────────────────────────────┐
│ Building Form                                   426 │
│ 89 controls • 12 objectives • 325 context          │
│ [Show: All | Controls ▼ | Controls + Objectives]    │
└─────────────────────────────────────────────────────┘
```

### Visual Treatment

| Type | Badge | Appearance |
|------|-------|------------|
| Control | `C12` teal | Normal weight, white background |
| Objective | `O1` blue | Normal weight, white background |
| Character | — | Muted gray text, light background |

### Density-Based Defaults

| Provision Count | Default View |
|-----------------|--------------|
| < 30 | Show all, grouped by type |
| 30-100 | Controls + objectives, context collapsed |
| > 100 | Controls only, expandable |

---

## Appendix B: Technical Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Address     │  │ Property    │  │ Provisions  │     │
│  │ Search      │  │ Details     │  │ Display     │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    API Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ /property   │  │ /provisions │  │ /capacity   │     │
│  │             │  │ /for-property│ │ /calculate  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                           │
│  ┌─────────────────────┐  ┌─────────────────────┐      │
│  │ regulatory_provisions│  │ dcp_general_       │      │
│  │ (raw PDF text)       │  │ requirements       │      │
│  │                      │  │ (LLM-curated)      │      │
│  └─────────────────────┘  └─────────────────────┘      │
│                                                         │
│  ┌─────────────────────┐  ┌─────────────────────┐      │
│  │ heritage_           │  │ precinct_           │      │
│  │ conservation_areas  │  │ boundaries          │      │
│  └─────────────────────┘  └─────────────────────┘      │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              External APIs                              │
│  ┌─────────────────────────────────────────────┐       │
│  │ NSW Planning Portal API                      │       │
│  │ (Property data, zoning, heritage status)     │       │
│  └─────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

---

## Demo Routes

| Route | Purpose |
|-------|---------|
| `/assessment` | Main application |
| `/assessment/mockup` | Proposed UX enhancement demo |

---

## Contact

**Product:** PlotDetect Compliance Engine
**Version:** 1.0-beta
**Environment:** Production (Vercel)
**Database:** Supabase (PostgreSQL)

---

*Report generated: December 2025*
