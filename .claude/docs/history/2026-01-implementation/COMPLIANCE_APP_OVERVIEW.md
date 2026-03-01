#  PlotDetect - Inner West DCP Compliance Navigator
## Functional Overview & Workflow

---

## 1. Entry Point: Address Search

use given logo.png

User enters any Inner West address (e.g., "70 Norton St, Leichhardt")

**System automatically determines:**
- Which DCP applies (Leichhardt DCP 2013)
- Property coordinates for precinct detection
- Zoning and planning data from NSW Planning Portal

---

## 2. Output Sections

### A. Property Intelligence Panel (Left Column)

Data sourced from **NSW Planning Portal API** in real-time:

| Field | Example Value | Source |
|-------|---------------|--------|
| Address | 70 Norton St, Leichhardt NSW 2040 | Planning Portal |
| Lot/DP | Lot 1 DP 123456 | Cadastre |
| Zone | R2 Low Density Residential | LEP |
| FSR | 0.6:1 | LEP |
| Height Limit | 9.5m | LEP |
| Heritage | Within Heritage Conservation Area | LEP |
| Minimum Lot Size | 450 sqm | LEP |
| Land Value | $1,250,000 (July 2024) | Valuer General |
| Bushfire | Not bushfire prone | RFS |
| Flood | Not flood affected | Planning Portal |

### B. State-Level Controls (SEPP & LEP Tab)

**Automatic display based on property attributes:**

**SEPP Requirements**
- Sustainable Buildings SEPP requirements
- Displayed based on development type applicability

**LEP Controls**
- Zone permissibility (from LEP spatial layers)
- Minimum lot size requirements
- Direct links to legislation

**Apartment Design Guide (ADG)**
- Appears automatically for apartment-permitting zones (R3, R4, B1-B6, MU1, E1-E2)
- Key design criteria: apartment sizes, ceiling heights, ventilation
- Building separation table (6m/9m/12m by building height)
- Section references with page numbers
- Warning displayed if zone typically prohibits apartments (R2, RU*, IN*)

**TOD Parking Reductions**
- Appears automatically when property is near qualifying transport:
  - Heavy rail station within 800m
  - Light rail stop within 600m
  - Frequent bus service within 400m
- Shows nearby transport with distances
- Parking reduction rates table (10-30% depending on transport type and distance)
- Designated TOD precinct detection from NSW Planning Portal

### C. DCP Provisions Panel (Right Column)

**Organised by Topic** - User selects from dropdown:

- Heritage
- Building Form & Character
- Parking
- Landscaping
- Access
- Privacy
- Solar Access
- Waste
- Water/Stormwater
- Energy & BASIX
- Trees
- Signage
- Fencing
- Open Space
- Precinct-Specific Controls

---

## 3. Provision Display Format

Each provision shows:

```
┌─────────────────────────────────────────────────────────────┐
│ Part C Section 1 · Page 7                    [View DCP Page]│
├─────────────────────────────────────────────────────────────┤
│ C2 A development application for the demolition of a       │
│ Heritage Item or building in a Heritage Conservation Area  │
│ that contributes to the significance of that Area must     │
│ include:                                                   │
│                                                            │
│ a. statement of significance of the item                   │
│ b. heritage impact statement                               │
│ c. structural engineer's report                            │
└─────────────────────────────────────────────────────────────┘
```

**Key elements:**
- **DCP Part/Section** - e.g., "Part C Section 1" (Heritage), "Part D" (Energy)
- **Page Number** - PDF page reference
- **View DCP Page** - Direct link opens PDF at exact page
- **Provision Text** - Full requirement text

---

## 4. Granular Compliance Example

### Scenario: Heritage alterations at 70 Norton St, Leichhardt

**User selects:** Heritage topic

**System returns:** 101 heritage provisions from Leichhardt DCP, filtered to those applicable to the address

**Sample provisions displayed:**

---

**Part C Section 1 · Page 4**
> Council seeks to maximise opportunities for good urban design to make a positive contribution to the public domain and local character of the area.

[View DCP Page] → Opens PDF at page 4

---

**Part C Section 1 · Page 7**
> O1 To enhance the environmental performance, cultural significance and character of Heritage Items and Heritage Conservation Areas.

[View DCP Page] → Opens PDF at page 7

---

**Part C Section 1 · Page 7**
> C2 A development application for the demolition of a Heritage Item or building in a Heritage Conservation Area that contributes to the significance of that Area must include:
> - a. statement of significance of the item
> - b. heritage impact statement
> - c. structural engineer's report

[View DCP Page] → Opens PDF at page 7

---

**Part C Section 2 · Page 131**
> Development in the Leichhardt Heritage Conservation Area should maintain the existing scale, form and character of the streetscape.

[View DCP Page] → Opens PDF at page 131

---

## 5. Precinct-Specific Filtering

### How it works:

1. System detects property coordinates
2. PostGIS spatial query checks which precinct polygon contains the point
3. Only provisions for that precinct are shown in Part G results

### Example:

**Address:** 70 Norton St, Leichhardt
**Precinct Detected:** Norton Street Neighbourhood Centre

**Part G provisions shown:** Only Norton Street-specific controls
**Part G provisions hidden:** Old Ampol Land, Robert St Balmain, Marion St, etc.

---

## 6. Navigation Flow

```
┌──────────────────┐
│  Enter Address   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│ Planning Portal  │────▶│ Property Panel   │
│ API Lookup       │     │ (Zoning, FSR,    │
└──────────────────┘     │  Heritage, etc.) │
         │               └──────────────────┘
         ▼
┌──────────────────┐
│ Determine DCP    │
│ (Leichhardt/     │
│  Marrickville/   │
│  Ashfield)       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Precinct         │
│ Detection        │
│ (PostGIS query)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│ Select Topic     │────▶│ Provisions Panel │
│ (Heritage,       │     │ - Part/Section   │
│  Parking, etc.)  │     │ - Page number    │
└──────────────────┘     │ - Full text      │
                         │ - PDF link       │
                         └──────────────────┘
```

---

## 7. DA/Assessment Relevance

### For Applicants (Pre-Lodgement)

1. Enter site address
2. Review property constraints (heritage status, zoning)
3. Select relevant topics (Heritage, Parking, Building Form)
4. Read each provision
5. Ensure DA submission addresses all requirements
6. Use PDF links to reference exact DCP pages in Statement of Environmental Effects

### For Assessment Officers

1. Enter DA site address
2. System confirms which DCP applies
3. Review provisions by topic
4. Check submitted documents against provision requirements
5. Identify any provisions not addressed in submission

### For Duty Planners

1. Caller asks: "What are the heritage requirements for my site?"
2. Enter address
3. Select Heritage topic
4. Read out applicable provisions
5. Provide PDF page references for caller to review

---

## 8. Data Coverage

### Leichhardt DCP 2013
- **1,221 actionable provisions** extracted
- **31 topics** classified
- **Part G precincts** mapped with boundaries
- PDF page offsets calibrated for direct linking

### Topics with provision counts:
- Building Design: 151
- Heritage: 101
- Access: 90
- Landscaping: 83
- Parking: 82
- Trees: 63
- Building Form: 62
- Water: 52
- Waste: 47
- + 22 more topics

---

## 9. Technical Integration

| Component | Technology |
|-----------|------------|
| Address Lookup | NSW Planning Portal API |
| Property Data | NSW ePlanning API |
| Zoning/FSR/Height | LEP spatial layers |
| Precinct Detection | PostGIS spatial queries |
| Provision Storage | Supabase (PostgreSQL) |
| Frontend | Next.js / React |
| Hosting | Vercel |

---

## Summary

**Input:** Address
**Output:** All applicable DCP provisions, organised by topic, with direct PDF links

**Value:** Eliminates manual DCP hunting across 3 separate documents, ensures no provisions are missed, speeds up both pre-lodgement self-assessment and DA processing.
