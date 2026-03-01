# NSW Planning Compliance Engine
## Route Architecture & Feature Documentation
### Stakeholder Education & Training Guide

---

## 🎯 Executive Overview

The NSW Planning Compliance Engine is a professional-grade web application that provides **real-time planning compliance assessment** for properties in NSW, Australia. It integrates with the **NSW Planning Portal API** and a comprehensive **regulatory provisions database** to deliver accurate, actionable compliance information.

### Core Value Proposition
- **Real-time data**: Live integration with NSW Planning Portal
- **Comprehensive coverage**: SEPP (State) + LEP (Council) + DCP (Local) regulations
- **Professional accuracy**: 100% reliable structured requirements, no AI interpretation
- **Instant assessment**: Property analysis in under 5 seconds
- **Development-aware**: Customized results based on proposed development type

---

## 📍 Application Routes

The application has **two primary routes**, each serving distinct use cases:

| Route | Purpose | Primary Users | Key Features |
|-------|---------|--------------|--------------|
| `/assessment` | Full property compliance assessment | Certifiers, Planners, Architects | 2-column layout, complete compliance dashboard |
| `/assessment/search` | Provision search & research | Legal professionals, Researchers | Full-text search, intelligent ranking |

---

# Route 1: `/assessment` - Primary Assessment Page

## 🏗️ Layout Architecture

### Two-Column Professional Layout

```
┌────────────────────────────────────────────────────────────────┐
│                   NSW Planning Assessment                       │
│  Professional compliance assessment using real-time data        │
├───────────────┬────────────────────────────────────────────────┤
│               │                                                 │
│   LEFT (25%)  │           RIGHT (75%)                          │
│               │                                                 │
│  Property     │       Compliance Dashboard                     │
│  Information  │                                                 │
│               │  - SEPP Special Provisions (State)             │
│  - Address    │  - ADG Building Separation (Apartments)        │
│  - Zone (R2)  │  - Heritage Conservation Areas                 │
│  - LGA        │  - LEP Building Envelope (Height/FSR)          │
│  - Area       │  - DCP Design Controls                         │
│  - Heritage   │  - Parking Requirements                        │
│               │                                                 │
│  Dev Type ⬇   │  [Expandable cards with full legal text]       │
│               │                                                 │
│  NSW Planning │                                                 │
│  API Layers   │                                                 │
│  (20+ layers) │                                                 │
│               │                                                 │
└───────────────┴────────────────────────────────────────────────┘
```

---

## 🎨 User Interface Components

### 1. Property Search Bar
**Location**: Top of page, full-width
**Function**: Address lookup with autocomplete

**Features**:
- Autocomplete suggestions as you type
- Searches NSW Planning Portal address database
- Validates property exists in system
- Shows loading state during fetch

**User Interaction**:
```
User types: "180 Addison"
↓
System shows: "180 Addison Road, Marrickville NSW 2204"
↓
User clicks address
↓
System fetches property data (2-3 seconds)
↓
Dashboard populates with compliance data
```

---

### 2. Property Information Panel (Left)

#### 2.1 Basic Property Details
Displays:
- **Full Address**: 180 Addison Road, Marrickville NSW 2204
- **Zone**: R2 Low Density Residential
- **LGA**: Inner West Council
- **Property Area**: 607 sq m
- **Heritage Status**: Yes/No

**Data Source**: NSW Planning Portal API (real-time)

---

#### 2.2 Development Type Selector
**Critical Feature**: Determines which DCP controls apply

**Available Options**:
1. **Dwelling House** (default) - Single family homes
2. **Secondary Dwelling** - Granny flats
3. **Multi Dwelling Housing** - Townhouses, terraces
4. **Residential Flat Building** - Apartments
5. **Shop Top Housing** - Mixed use commercial/residential
6. **Boarding House** - Shared accommodation
7. **Child Care Centre** - Educational facilities
8. **Commercial Premises** - Retail, offices

**Logic Flow**:
```
Development Type: Dwelling House
↓
DCP Provisions API filters to:
  - Part 2: General Controls (all developments)
  - Part 4.1: Low Density Residential (dwelling house specific)
↓
Returns 241 provisions
```

**Why This Matters**:
- Different development types have different setback requirements
- Different parking requirements
- Different design controls
- Different SEPP standards

---

#### 2.3 Building Height Input
**Appears Only For**: Multi dwelling, Residential flat, Shop top housing

**Purpose**: Required for ADG Building Separation standards

**Validation**:
- Numeric input only
- Range: 0-100 meters
- Decimal precision (e.g., 10.5m)

**Usage**:
```
User selects: "Multi Dwelling Housing"
↓
Building height field appears
↓
User enters: "12" (meters)
↓
ADG Building Separation table calculates:
  - Side/Rear: 6m (up to 12m height)
  - Between buildings: 12m (habitable/habitable)
```

---

#### 2.4 NSW Planning API Layers
**Component**: `PropertyDetailsComprehensive`

**Displays All 20+ Planning Layers**:
1. Zoning Map
2. Height of Buildings Map
3. Floor Space Ratio Map
4. Lot Size Map
5. Heritage Map
6. Special Provisions (BASIX, Water Use, Climate Zones)
7. Flood Planning Map
8. Foreshore Building Line
9. Acid Sulfate Soils
10. Earthworks
11. Biodiversity
12. Riparian Land
13. Contaminated Land
14. ...and more

**Feature**: Each layer shows:
- Layer name
- All attributes returned by API
- **Clickable "View on Planning Portal" links**
- Legislative clauses where applicable
- Version information

**Professional Value**:
- Complete transparency of data sources
- Audit trail for reports
- Direct verification via Planning Portal

---

### 3. Compliance Dashboard (Right Panel)

#### 3.1 Property Header
Displays:
- Property address
- LGA name
- Permission status badge (if applicable)

**Permission Status Types**:
- ✅ **Exempt Development**: No DA required
- 📋 **Complying Development**: CDC pathway available
- ⚠️ **Development Approval Required**: Full DA needed

---

#### 3.2 Regulatory Currency Banner
**Critical Notice**: Appears at top of page

```
⚠️ REGULATORY CURRENCY NOTICE
The regulations displayed below may not reflect the most current versions.
NSW planning regulations are updated frequently, and councils may have
adopted new amendments since our last extraction.

PROFESSIONAL VERIFICATION REQUIRED
Before relying on this data for development applications or advice,
verify current versions at legislation.nsw.gov.au
```

**Purpose**: Legal protection, professional accountability

---

## 📊 Compliance Sections (Hierarchical Display)

### Section 1: SEPP Special Provisions (State Level) 🟥
**Authority**: Highest legal precedence
**Color Code**: Orange/Red cards
**Data Source**: NSW Planning Portal API

#### Features:
1. **Structured Requirements** (100% Reliable)
   - Manually curated, no AI interpretation
   - Collapsible categories
   - Bullet point checklists
   - Legal citations

2. **Action Required vs Informational**
   - Filters out irrelevant controls (BASIX for alterations, etc.)
   - Shows count: "(3 require action, 2 informational)"
   - Dimmed display for informational items

#### Example Data Displayed:
```
SEPP (Sustainable Buildings) 2022 - Schedule 1 & 2

📋 Actionable Requirements [100% Reliable]

▼ BASIX Energy Requirements
   Reference: Schedule 1, Part 1

   ✓ Heating and Cooling: 50% reduction target
      📎 Clause 2.1.1 - BASIX heating/cooling requirements

   ✓ Hot Water System: Solar, heat pump, or gas instantaneous
      📎 Clause 2.1.2 - BASIX hot water requirements

   ✓ Lighting: Minimum 25% LED lighting
      📎 Clause 2.1.3 - BASIX lighting requirements

▼ BASIX Water Requirements
   Reference: Schedule 1, Part 2

   ✓ Water Efficiency: 40% reduction target
   ✓ Rainwater Tank: Minimum 2000L connected to toilet/laundry
```

#### User Interactions:
- Click category header to expand/collapse
- Click provision to view full legal text in slide-out panel
- Version badge shows amendment dates

---

### Section 2: ADG Building Separation (Apartments) 🟥
**Authority**: Statutory standards under SEPP (Housing) 2021
**Applies To**: Multi dwelling, Residential flat, Shop top housing
**Condition**: Only shows if building height entered

#### Features:
- **Dynamic calculation** based on building height
- **Three separation types**:
  - Between buildings on same site
  - Side/rear boundaries
  - Between windows

- **Room type matrix**:
  - Habitable ↔ Habitable: 12-24m
  - Habitable ↔ Non-habitable: 9-12m
  - Non-habitable ↔ Non-habitable: 6m

#### Example Display:
```
NSW Apartment Design Guide - Building Separation

Building Height: 12.0 meters (configured above)

Separation Requirements:

Between Buildings on Same Site:
┌─────────────────────────┬─────────┬──────────────┬─────────────────┐
│                         │ Habitable│ Non-Habitable│ Non-Habitable   │
│                         │ Rooms    │ Rooms        │ (Blank Wall)    │
├─────────────────────────┼─────────┼──────────────┼─────────────────┤
│ Habitable Rooms         │ 12 m    │ 9 m          │ 6 m             │
│ Non-Habitable Rooms     │ 9 m     │ 6 m          │ 3 m             │
│ Non-Habitable (Blank)   │ 6 m     │ 3 m          │ 0 m             │
└─────────────────────────┴─────────┴──────────────┴─────────────────┘

Side/Rear Boundaries:
• Up to 12m height: 6m minimum
• 12-25m height: 9m minimum
• Over 25m height: 12m minimum
```

**Professional Value**:
- Instant compliance check
- No manual ADG Part 3 lookup required
- Correct thresholds for building height

---

### Section 3: Heritage Conservation Areas (LEP Level) 🟦
**Authority**: Local Environmental Plan
**Color Code**: Blue
**Data Source**: Database (heritage_conservation_areas table)

#### Display Logic:
- **Shows only if** property within HCA boundary
- Uses **PostGIS spatial query** (ST_Within)
- Displays:
  - HCA name
  - Statement of significance
  - Heritage guidelines
  - Link to full Heritage DCP

#### Example:
```
🏛️ Heritage Conservation Area

Property is located within: Marrickville Heritage Conservation Area

Statement of Significance:
The Marrickville Heritage Conservation Area comprises predominantly
Federation and Inter-War residential buildings with some Victorian
examples. The area retains a high degree of architectural integrity...

Heritage Guidelines Apply:
• Maintain original building form and roof pitch
• Retain heritage facades and street presentation
• New development must be sympathetic to heritage character
• Colors must complement heritage palette

📄 View Full Heritage DCP: Marrickville DCP - Part 8: Heritage
```

---

### Section 4: LEP Building Envelope Constraints 🟦
**Authority**: Local Environmental Plan
**Color Code**: Blue cards
**Data Source**: NSW Planning Portal API

#### Constraints Displayed:

##### 4.1 Maximum Building Height
```
┌─────────────────────────────────────┐
│ Maximum Building Height             │
│                                     │
│ 9.5 m                               │
│                                     │
│ Source: Clause 4.3                  │
│ Inner West LEP 2022                 │
│                                     │
│ 📋 View Full Legal Text →          │
│                                     │
│ [Version: Amendment 8, gazetted    │
│  13 October 2023]                  │
└─────────────────────────────────────┘
```

##### 4.2 Floor Space Ratio
```
┌─────────────────────────────────────┐
│ Floor Space Ratio                   │
│                                     │
│ 0.6:1 sq m                         │
│                                     │
│ Source: Clause 4.4                  │
│ Inner West LEP 2022                 │
│                                     │
│ 📋 View Full Legal Text →          │
│                                     │
│ [Version: Amendment 8, gazetted    │
│  13 October 2023]                  │
└─────────────────────────────────────┘
```

**User Interaction**:
- Click "View Full Legal Text" to open slide-out panel
- Panel shows complete Clause 4.3 or 4.4 text from LEP
- Includes objectives, requirements, exceptions

---

### Section 5: DCP Design Controls 🟢
**Authority**: Development Control Plan (Local)
**Color Code**: Green cards
**Data Source**: Database (regulatory_provisions table)

#### 5.1 Quick Reference Cards
Shows extracted numeric controls:
```
┌─────────────────────────────────────┐
│ Front Setback                       │
│                                     │
│ 5.5 m                              │
│                                     │
│ Source: Table in Section 4.1        │
│ Marrickville DCP 2011               │
│                                     │
│ 📋 View Full Table →               │
└─────────────────────────────────────┘
```

#### 5.2 Browse All DCP Provisions
**Critical Feature**: User-controlled provision browsing

##### Header Display:
```
📚 Browse All Dwelling House Provisions

Showing 241 provisions for Dwelling House:
• Part 2: General controls (parking, fencing, privacy, solar access)
• Part 4.1: Development-specific requirements for dwelling house

💡 Change "Development Type" dropdown above to see different provisions
```

##### Filter Interface:
```
🔍 Search: [Search provisions for dwelling house...]

Quick Filters:
[Setbacks] [Landscaping] [Privacy] [Solar Access] [Building Design] [Open Space]

[All Types] [Tables Only] [Controls Only] [Objectives Only]
```

##### Query Summary Panel:
```
┌────────────────────────────────────────────────────────────────┐
│ 🔍 QUERY SUMMARY - What You're Actually Seeing:                │
│                                                                 │
│ Development Type: DWELLING HOUSE                                │
│                                                                 │
│ Searching DCP Sections:                                         │
│ Part 2 (General) + Part 4.1 (Low Density)                     │
│                                                                 │
│ Active Filters:                                                 │
│ • Categories: setbacks, privacy                                 │
│                                                                 │
│ 💡 Why These Sections?                                          │
│ • Part 2: General controls apply to ALL developments           │
│ • Part 4.1: Specific controls for dwelling house               │
│                                                                 │
│ Result: 62 provisions match this query                         │
└────────────────────────────────────────────────────────────────┘
```

##### Provision Results:
```
[TABLE] 2.7.3 Solar access for surrounding buildings
Side and rear boundary setbacks in metres...
View Full Text ▼

[NUMERIC] 2.8.1 Landscaping requirements
Minimum 30% of site area to be landscaped...
View Full Text ▼

[CONTROL] 4.1.2 Front setback controls
Minimum front setback of 5.5m to maintain street character...
View Full Text ▼
```

**Filtering Logic**:

1. **Development Type** (dropdown above)
   - Controls which DCP sections are queried
   - Dwelling House → Part 2 + 4.1 (241 provisions)
   - Multi Dwelling → Part 2 + 4.2 (188 provisions)

2. **Quick Filters** (categories)
   - REFINE the existing provisions
   - Multiple selection (OR logic)
   - Example: Setbacks (62) + Privacy (34) = 81 provisions

3. **Provision Type**
   - EXPANDS to search ALL DCP sections
   - Overrides development type filtering
   - Use for browsing tables across entire DCP

4. **Search** (full-text)
   - PostgreSQL full-text search
   - Searches provision_text + section_header
   - Ranks by relevance

**Performance**:
- Query time: 84ms (optimized with MATERIALIZED CTEs)
- Debouncing: 150ms for filters, 300ms for search
- Pagination: 10 provisions per page, load more on demand

---

### Section 6: Parking Requirements 🅿️
**Source**: Marrickville DCP 2011 - Section 2.10
**Data**: Extracted parking table from DCP

#### Features:
- **Development type aware**: Shows requirements for selected dev type
- **Highlights relevant row** in full table
- **Displays description**: "Dwelling houses: 1 space per dwelling"

#### Example Display:
```
┌────────────────────────────────────────────────────────────────┐
│ 🅿️ Parking Requirements                                        │
│                                                                 │
│ Marrickville DCP 2011 - Section 2.10                          │
│                                                                 │
│ Development Type: Dwelling House                                │
│                                                                 │
│ Requirement: 1 covered space per dwelling house                │
│                                                                 │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ Land Use             │ Rate                              │  │
│ ├──────────────────────────────────────────────────────────┤  │
│ │ Dwelling house       │ 1 space per dwelling             │  │ ← Highlighted
│ └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│ [View Full Parking Table]                                      │
└────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Interactive Features

### 1. Slide-Out Legal Text Panel
**Triggered By**: Clicking any constraint card "View Full Legal Text" button

**Panel Features**:
- **Slides in from right** (60% screen width)
- **Left content compresses** (40% width)
- Smooth animation (300ms transition)

**Panel Contents**:
```
┌────────────────────────────────────────────────────────────────┐
│ [ × Close ]                                                     │
│                                                                 │
│ Clause 4.3 - Maximum Building Height                           │
│ Inner West Local Environmental Plan 2022                       │
│                                                                 │
│ [Version Badge: Amendment 8, 13 Oct 2023]                     │
│                                                                 │
│ ────────────────────────────────────────────────────────────── │
│                                                                 │
│ Objectives:                                                     │
│ (a) to ensure the height of buildings is appropriate to the    │
│     existing and desired future character of the area          │
│ (b) to minimise overshadowing of neighbouring properties and   │
│     public spaces                                               │
│ (c) to maintain solar access to private and public open space  │
│                                                                 │
│ Requirements:                                                   │
│ 1. The height of a building on any land is not to exceed the   │
│    maximum height shown for the land on the Height of          │
│    Buildings Map.                                               │
│                                                                 │
│ 2. Despite subclause (1), development consent may be granted   │
│    to a building that exceeds the height shown on the Height   │
│    of Buildings Map if:                                         │
│    (a) the consent authority is satisfied that the additional  │
│        height will result in better design outcomes...          │
│                                                                 │
│ [Full legal text continues...]                                 │
└────────────────────────────────────────────────────────────────┘
```

**HTML Rendering**:
- Tables styled with borders
- Lists formatted with bullets
- Markdown headings converted to HTML
- Preserves legal formatting

---

### 2. PDF Page Image Viewer
**Feature**: View actual PDF page of DCP provision

**Triggered By**: Clicking "📄 View PDF Page" button in expanded provision

**Display**:
- Full-screen modal overlay
- High-resolution page image
- Extracted from DCP PDF
- Shows provision in original context

**Professional Value**:
- Verify provision accuracy
- See surrounding context
- Check diagrams/figures
- Audit trail

---

## 🔢 Data Flow & Logic

### Property Lookup Flow
```
1. User types address
   ↓
2. AutocompleteAPI queries NSW Planning Portal
   ↓
3. User selects address
   ↓
4. /api/property?address=... called
   ↓
5. Backend fetches from Planning Portal:
   - Basic property data
   - All 20+ planning layers
   - Zone, LGA, lot details
   ↓
6. Backend queries database:
   - Heritage conservation areas (PostGIS spatial query)
   - Property geometry
   ↓
7. Response returned to frontend (JSON)
   ↓
8. Frontend populates:
   - Property info panel
   - NSW Planning layers list
   ↓
9. Frontend calls /api/compliance/constraints
   ↓
10. Backend queries:
    - regulatory_provisions (SEPP/LEP/DCP)
    - development_controls (numeric constraints)
    - zone_setback_rules (setbacks)
    - structured_sepp_requirements (BASIX)
   ↓
11. Frontend renders Compliance Dashboard
```

**Timing**:
- Address autocomplete: <500ms
- Property fetch: 2-3 seconds
- Compliance constraints: 1-2 seconds
- **Total**: 3-5 seconds from search to full display

---

### DCP Provision Filtering Logic

**Scenario**: User selects "Dwelling House", zone "R2"

```
Step 1: Document ID Pattern Generation
─────────────────────────────────────────────
Development Type: dwelling_house
↓
API maps to DCP sections:
- Pattern 1: Marrickville.*_2_  (Part 2: General)
- Pattern 2: Marrickville.*4\.1 (Part 4.1: Low Density)

Step 2: Database Query (Optimized)
─────────────────────────────────────────────
WITH document_filtered AS MATERIALIZED (
  -- Filter by document_id first (uses index)
  SELECT * FROM regulatory_provisions
  WHERE document_id LIKE 'Marrickville%'
    AND (document_id ~ 'Marrickville.*_2_'
      OR document_id ~ 'Marrickville.*4\.1')
)
SELECT * FROM document_filtered
WHERE provision_text ILIKE '%setback%'  -- If filter applied
ORDER BY
  CASE provision_text LIKE '%<table%' THEN 1 ELSE 4 END,  -- Tables first
  pdf_page ASC
LIMIT 10

Step 3: Result Ranking
─────────────────────────────────────────────
Type Ranks (1 = highest priority):
1. Tables (structured data)
2. Numeric provisions (5.5m, 30%, etc.)
3. Controls ("Control: Front setback must...")
4. Objectives
5. Other text

Step 4: Frontend Display
─────────────────────────────────────────────
Results shown with:
- Type badge (TABLE, NUMERIC, CONTROL)
- Section header
- Text preview (150 chars)
- Expandable full text
- PDF page image link
```

**Performance Optimization**:
- Step 1 (Document filter): 241 rows (from 42,005 total)
- Step 2 (Text filter): 62 rows (from 241)
- Query time: 84ms (with MATERIALIZED CTE + LIKE prefix)

---

### SEPP Override Matching

**Problem**: SEPP can override LEP/DCP provisions

**Solution**: Planning API clauses matched to database provisions

```
Step 1: Extract Planning API Clauses
─────────────────────────────────────────────
NSW Planning Portal returns:
- Height of Buildings Map → "Clause 4.3"
- Floor Space Ratio Map → "Clause 4.4"
- Special Provisions → "Clause 5.10"

Step 2: Query SEPP Override Database
─────────────────────────────────────────────
SELECT * FROM sepp_overrides
WHERE clause_number IN ('4.3', '4.4', '5.10')
  AND applies_to_zone(zone, 'R2')

Step 3: Display SEPP Override If Found
─────────────────────────────────────────────
┌────────────────────────────────────────┐
│ ⚠️ SEPP Override Applies               │
│                                        │
│ SEPP (Affordable Rental Housing) 2009  │
│ Clause 19 - Height Incentive           │
│                                        │
│ LEP height may be exceeded by 3.5m if: │
│ • Development provides affordable units│
│ • Minimum 10% affordable housing       │
│ • Design excellence demonstrated       │
│                                        │
│ This overrides: Clause 4.3 LEP height │
└────────────────────────────────────────┘
```

**Professional Value**:
- Catches SEPP incentives
- Identifies override opportunities
- Prevents LEP-only assessment errors

---

## 📱 Use Cases

### Use Case 1: Certifier Pre-Assessment
**User**: Private Certifier
**Scenario**: Client wants to build 2-storey dwelling house at 180 Addison Road

**Workflow**:
1. Search "180 Addison Road" → Property loads
2. Confirm Zone: R2 Low Density Residential
3. Select Development Type: "Dwelling House"
4. View SEPP requirements: BASIX 50% energy, 40% water
5. View LEP constraints: 9.5m height, 0.6:1 FSR
6. Browse DCP provisions:
   - Filter "Setbacks" → Front: 5.5m, Side: 0.9m, Rear: 6m
   - Filter "Building Design" → Max site coverage 40%
   - Filter "Landscaping" → Min 30% landscaped area
7. Check Parking: 1 covered space required
8. View Heritage: Not in HCA, no heritage controls

**Output**: Complete compliance checklist in 2 minutes

---

### Use Case 2: Architect Feasibility Study
**User**: Architect
**Scenario**: Feasibility for 4-storey apartment building (multi dwelling)

**Workflow**:
1. Search property address
2. Select Development Type: "Multi Dwelling Housing"
3. Enter Building Height: "12" meters
4. Review SEPP ADG Building Separation:
   - Side/rear boundary: 6m (up to 12m height)
   - Between buildings: 12m (hab-hab), 9m (hab-nonhab)
5. Review LEP Height: 12m allowed (12m proposed = compliant)
6. Review DCP Part 4.2 provisions:
   - Filter "Tables Only" to see all control tables
   - Check setbacks for multi-dwelling
   - Check private open space requirements
7. Calculate feasible yield based on constraints

**Output**: Preliminary yield analysis with regulatory constraints

---

### Use Case 3: Town Planner DA Preparation
**User**: Town Planner
**Scenario**: Preparing Development Application documentation

**Workflow**:
1. Search property → Load compliance data
2. Export constraint summary for DA report
3. Click "View Full Legal Text" for each constraint
4. Copy exact legal wording for DA compliance tables
5. Use version badges to cite current LEP amendment
6. Download PDF page images for report appendix
7. Use Heritage DCP for heritage statement (if applicable)

**Output**: Accurate DA compliance section with verifiable sources

---

### Use Case 4: Solicitor Due Diligence
**User**: Property Solicitor
**Scenario**: Due diligence for property purchase

**Workflow**:
1. Search property address
2. Check Planning API layers:
   - Flood planning: Check flood level/category
   - Acid sulfate soils: Check ASSLevel
   - Contaminated land: Check restrictions
   - Heritage: Check HCA status
3. Review LEP constraints:
   - Height/FSR limits for redevelopment potential
4. Check SEPP special provisions:
   - BASIX requirements for extensions
   - Any prohibitions or restrictions
5. Click "View on Planning Portal" links to verify
6. Document findings in due diligence report

**Output**: Comprehensive planning constraints report

---

# Route 2: `/assessment/search` - Provision Search

## 🔍 Purpose & Audience

**Primary Users**:
- Legal researchers
- Council planners
- Policy analysts
- Academic researchers
- Certifiers doing provision lookups

**Use Cases**:
- Finding specific provision text
- Researching clause interpretation
- Cross-referencing SEPP/LEP/DCP
- Citation verification

---

## 🏗️ Layout Architecture

### Two-Column Research Layout

```
┌────────────────────────────────────────────────────────────────┐
│                   Provision Search                              │
│  Search across all SEPP, LEP, DCP with intelligent ranking     │
├───────────────────────────────────────────────────────────────┤
│  Property Context (Optional): [Address Search]                 │
│  Zone: R2 Low Density Residential                              │
├────────────────────────────┬───────────────────────────────────┤
│                            │                                    │
│   LEFT (66%)               │      RIGHT (33%)                  │
│                            │                                    │
│   Search Interface         │   Provision Details Panel         │
│                            │                                    │
│   🔍 [Search: setback]     │   ┌──────────────────────────┐   │
│                            │   │ Clause 4.1.2             │   │
│   Filters:                 │   │ SEPP / LEP / DCP        │   │
│   ☑ SEPP  ☐ LEP  ☑ DCP    │   │                          │   │
│   ☑ Tables Only            │   │ Setback Requirements     │   │
│                            │   │                          │   │
│   Results (24 found):      │   │ [Full legal text]        │   │
│                            │   │                          │   │
│   ┌─ Result 1 ──────────┐ │   │ Ranking: 85.3            │   │
│   │ SEPP                 │ │   │ Text: 72.1               │   │
│   │ Clause 4.3           │ │   │ Zone: 1.2x               │   │
│   │ Front setback: 5.5m  │ │   │ Quant: 1.0x              │   │
│   │ Rank: 85.3           │ │   └──────────────────────────┘   │
│   └──────────────────────┘ │                                   │
│                            │                                    │
│   ┌─ Result 2 ──────────┐ │                                   │
│   │ DCP                  │ │                                   │
│   │ Table 4.1            │ │                                   │
│   │ Residential setbacks │ │                                   │
│   │ Rank: 68.7           │ │                                   │
│   └──────────────────────┘ │                                   │
│                            │                                    │
└────────────────────────────┴───────────────────────────────────┘
```

---

## 🎯 Key Features

### 1. Optional Property Context
**Purpose**: Enables Tier 1 intelligent ranking

**With Property Context**:
```
Property: 180 Addison Road
Zone: R2 Low Density Residential
↓
Search: "setback"
↓
Tier 1 Ranking Applied:
- R2-specific provisions ranked higher (1.2x boost)
- Numeric provisions ranked higher (1.0x boost)
- Text match relevance (base score)
↓
Results ordered by relevance to property
```

**Without Property Context**:
```
Search: "setback"
↓
Text Ranking Only:
- Full-text search relevance
- No zone-specific boosting
- No quantitative boost
↓
Results ordered by text match score
```

---

### 2. Full-Text Search Engine
**Backend**: PostgreSQL full-text search with `tsvector` indexes

**Features**:
- Stemming: "setback" matches "setbacks", "setback"
- Stop word removal: "the", "and", "of" ignored
- Phrase matching: "front setback" as phrase
- Ranking by relevance

**Query Processing**:
```
User Input: "front setback dwelling"
↓
PostgreSQL Processing:
to_tsvector('english', provision_text)
@@ plainto_tsquery('english', 'front setback dwelling')
↓
Matches:
- "Front setbacks for dwelling houses" (100% relevance)
- "Setback requirements for residential dwellings" (85%)
- "Side and front boundary setbacks" (72%)
↓
Ranked results returned
```

---

### 3. Intelligent Ranking (Tier 1)

**Ranking Formula** (when zone context available):
```
final_rank = text_rank × zone_boost × quant_boost

Where:
- text_rank = PostgreSQL ts_rank (0-1.0)
- zone_boost = 1.2 if provision matches property zone, else 1.0
- quant_boost = 1.0 if provision has numeric values, else 0.8
```

**Example**:
```
Provision A: "Front setback for R2 zone: 5.5m"
- text_rank: 0.85 (high text relevance)
- zone_boost: 1.2 (matches R2)
- quant_boost: 1.0 (has numeric value)
- final_rank: 0.85 × 1.2 × 1.0 = 1.02

Provision B: "Setback guidelines and principles"
- text_rank: 0.72
- zone_boost: 1.0 (no zone specified)
- quant_boost: 0.8 (no numeric value)
- final_rank: 0.72 × 1.0 × 0.8 = 0.576

Result: Provision A ranked higher (more relevant)
```

---

### 4. Authority Level Filters
**Checkboxes**: SEPP / LEP / DCP

**Logic**: OR combination
```
Selected: SEPP + DCP
↓
Query: WHERE authority_level IN ('SEPP', 'DCP')
↓
Excludes: All LEP provisions
```

---

### 5. Provision Type Filters
**Checkboxes**: Tables Only / Controls Only / Objectives Only

**Detection Logic**:
```
Tables: provision_text LIKE '%<table%'
Controls: provision_text ~* '^(Control|Controls)'
Objectives: provision_text ~* '^(Objective|Objectives)'
```

---

### 6. Results Display

#### Result Card Format:
```
┌─────────────────────────────────────────────────────────────┐
│ [SEPP] Clause 4.3 - Building Height                        │
│                                                             │
│ "The maximum building height for residential development   │
│  in R2 zones is 9.5 metres..."                             │
│                                                             │
│ Document: SEPP (Affordable Rental Housing) 2009            │
│ Page: 47                                                    │
│ Rank: 85.3 (Text: 72.1, Zone: 1.2x, Quant: 1.0x)         │
│                                                             │
│ [Click to view details →]                                  │
└─────────────────────────────────────────────────────────────┘
```

**Color Coding**:
- SEPP: Orange badge
- LEP: Blue badge
- DCP: Green badge

---

### 7. Details Panel (Right)

**Displays On Click**:
- Authority level badge
- Clause/reference number
- Section header
- Page number
- Zone (if applicable)
- **Full provision text** (formatted HTML)
- Ranking breakdown (if ranking enabled)

**HTML Formatting**:
- Tables with borders
- Lists converted to bullets
- Headings styled
- Line breaks preserved

---

## 🔄 Search Workflow Examples

### Example 1: Finding Setback Requirements
```
1. User enters property address (optional)
   → Zone: R2 detected
2. User searches: "front setback"
3. System returns 24 results
4. Top result: "Table 4.1 - Residential Setbacks" (DCP)
   - Rank: 85.3
   - Contains: "Front: 5.5m"
5. User clicks result
6. Details panel shows full table with all setbacks
```

---

### Example 2: SEPP Research
```
1. User searches: "BASIX energy"
2. Filters: SEPP only
3. System returns:
   - Schedule 1, Part 1 - BASIX Energy
   - Clause 2.1.1 - Heating/cooling target
   - Clause 2.1.2 - Hot water requirements
4. User clicks each result to view full requirements
5. Uses for DA preparation
```

---

### Example 3: Cross-Reference Check
```
1. User has LEP clause reference: "Clause 4.3"
2. Searches: "4.3 height"
3. Filters: LEP + SEPP
4. Results show:
   - LEP Clause 4.3 (base requirement)
   - SEPP override Clause 19 (if applicable)
5. User compares both provisions
6. Identifies SEPP override applies
```

---

## 🆚 Route Comparison

| Feature | `/assessment` | `/assessment/search` |
|---------|---------------|---------------------|
| **Primary Purpose** | Property compliance assessment | Provision research & lookup |
| **Property Required** | Yes | Optional (for ranking) |
| **Layout** | 2-column (25/75) | 2-column (66/33) |
| **Data Display** | Structured cards by authority | Search results list |
| **Search Capability** | DCP provisions only (filtered) | All SEPP/LEP/DCP (full-text) |
| **Ranking** | Type-based (tables first) | Text + Zone + Quantitative |
| **Filters** | Category + Type | Authority + Type |
| **User Control** | Development type dropdown | Search bar + filters |
| **Output** | Compliance checklist | Provision details |
| **Use Case** | Pre-assessment, feasibility | Research, citation, verification |

---

## 📊 Technical Architecture

### Database Schema

#### Core Tables:
```sql
regulatory_provisions (42,005 rows)
├── id (primary key)
├── ref_number (clause reference)
├── section_header (provision title)
├── provision_text (full text, HTML)
├── document_id (identifies source)
├── document_type (SEPP/LEP/DCP)
├── authority_level (SEPP/LEP/DCP)
├── zone (R2, R3, B1, etc.)
├── development_type (dwelling_house, etc.)
├── pdf_page (source page number)
├── pdf_page_image_url (extracted page image)
└── provision_tsv (tsvector for full-text search)

development_controls (1,245 rows)
├── id
├── provision_id (FK to regulatory_provisions)
├── control_type (height, fsr, setback, etc.)
├── value_numeric (5.5, 0.6, etc.)
├── value_text ("5.5m", "0.6:1")
├── unit (m, %, :1, etc.)
└── applies_to_zone

heritage_conservation_areas (47 rows)
├── id
├── name (HCA name)
├── lga
├── geometry (PostGIS polygon)
├── statement_significance
└── heritage_guidelines

structured_sepp_requirements (24 rows)
├── id
├── sepp_id (sustainable_buildings_2022)
├── schedule (Schedule 1)
├── section (Part 1 - Energy)
├── development_type_category (dwelling_house)
├── requirement_data (JSON: structured requirements)
└── source_provision_id (FK to regulatory_provisions)
```

---

### API Endpoints

#### Property Assessment Route: `/assessment`

**API Calls Made**:
1. `/api/property?address={address}`
   - Returns: Property data + Planning Portal layers

2. `/api/compliance/constraints`
   - Body: `{ zone, lga, developmentType, address }`
   - Returns: Building envelope, environmental, special provisions

3. `/api/sepp/structured-requirements`
   - Body: `{ seppId, developmentType }`
   - Returns: Structured BASIX requirements

4. `/api/dcp/parking`
   - Body: `{ developmentType, zone, lga }`
   - Returns: Parking table + relevant row

5. `/api/dcp/provisions`
   - Body: `{ lga, zone, developmentType, search, categories, provisionType, limit, offset }`
   - Returns: Filtered DCP provisions with pagination

6. `/api/sepp/full-text`, `/api/lep/full-text`, `/api/dcp/full-text`
   - Body: `{ various identifiers }`
   - Returns: Full provision text for slide-out panel

---

#### Provision Search Route: `/assessment/search`

**API Calls Made**:
1. `/api/property?address={address}` (optional)
   - For zone context

2. `/api/provisions/search`
   - Body: `{ query, authorityLevels, provisionTypes, zone (optional), limit, offset }`
   - Returns: Ranked provision results

**Query Logic**:
```sql
-- Tier 1 Ranking with zone context
SELECT
  id,
  ref_number,
  section_header,
  provision_text,
  document_id,
  authority_level,
  zone,
  page_number,
  -- Text ranking
  ts_rank(provision_tsv, plainto_tsquery('english', $query)) as text_rank,
  -- Zone boost
  CASE WHEN zone = $user_zone THEN 1.2 ELSE 1.0 END as zone_boost,
  -- Quantitative boost
  CASE WHEN provision_text ~ '[0-9]+\.?[0-9]*\s*(m|metre|%|sqm)'
    THEN 1.0 ELSE 0.8 END as quant_boost,
  -- Final rank
  (ts_rank(provision_tsv, plainto_tsquery('english', $query)) *
   CASE WHEN zone = $user_zone THEN 1.2 ELSE 1.0 END *
   CASE WHEN provision_text ~ '[0-9]+\.?[0-9]*\s*(m|metre|%|sqm)'
     THEN 1.0 ELSE 0.8 END
  ) as final_rank
FROM regulatory_provisions
WHERE provision_tsv @@ plainto_tsquery('english', $query)
  AND authority_level = ANY($authority_levels)
ORDER BY final_rank DESC
LIMIT $limit OFFSET $offset
```

---

## 🎓 Training Recommendations

### For Certifiers:
1. **Start with `/assessment` route** - primary workflow
2. Practice entering different development types
3. Learn to interpret constraint cards
4. Use slide-out panel for full legal text
5. Verify with "View on Planning Portal" links
6. Export/document findings for certification reports

### For Planners:
1. **Use both routes** - assessment + research
2. `/assessment` for DA preparation
3. `/assessment/search` for clause verification
4. Learn DCP provision filtering
5. Understand development type impacts
6. Use version badges for citation accuracy

### For Solicitors:
1. **Focus on Planning API layers** - due diligence data
2. Check all environmental constraints
3. Verify heritage status
4. Review SEPP special provisions
5. Document sources for reports
6. Use search for clause cross-referencing

### For Architects:
1. **Feasibility workflow** - quick envelope checks
2. Use building height input for ADG
3. Browse DCP design controls
4. Filter by "Tables Only" for numeric limits
5. Calculate yield based on constraints
6. Iterate development types for options

---

## 🔐 Data Quality & Reliability

### Data Sources:
1. **NSW Planning Portal API** (Real-time)
   - Updated by NSW Government
   - Official legal data
   - High reliability

2. **Database Provisions** (Extracted)
   - Extracted from official PDFs
   - Verified against source documents
   - **Currency warning displayed** - may not reflect latest amendments

3. **Structured SEPP Requirements** (Manual Curation)
   - 100% reliable
   - Manually created by planning experts
   - No AI interpretation
   - Limited coverage (BASIX only currently)

### Version Tracking:
- **LEP provisions**: Show amendment date from Planning API
- **SEPP provisions**: Show gazetted date if available
- **DCP provisions**: Source PDF metadata stored
- **Currency banner**: Warns users to verify current versions

---

## 📈 Performance Metrics

### Page Load Times:
- `/assessment` initial load: 300ms
- Property fetch: 2-3 seconds
- Compliance constraints: 1-2 seconds
- DCP provisions query: 84ms (optimized)
- Total time to full display: 3-5 seconds

### Database Performance:
- Total provisions: 42,005
- Index size: ~500MB
- Query cache hit rate: 95%+
- Concurrent users supported: 100+

### Search Performance:
- Full-text search: 50-200ms
- Filtered search: 80-300ms
- Pagination: 10ms per page
- Debounce delay: 150-300ms

---

## 🚀 Future Enhancements

### Planned Features:
1. **Export to PDF** - Compliance reports
2. **Save assessments** - User accounts
3. **Compare properties** - Side-by-side view
4. **Bulk address import** - Developer portfolios
5. **More structured SEPP requirements** - Expand beyond BASIX
6. **Notification system** - LEP/DCP amendment alerts
7. **3D envelope visualization** - Building envelope preview
8. **Automated DA checklist** - Generate compliance tables

---

## 📞 Support & Documentation

### For Technical Issues:
- Check browser console for errors
- Verify internet connection (NSW Planning Portal required)
- Clear cache if data seems stale
- Contact: support@example.com

### For Data Accuracy Questions:
- Always verify with official sources:
  - legislation.nsw.gov.au (LEP/SEPP)
  - Council website (DCP)
  - planningportal.nsw.gov.au (spatial data)
- Regulatory currency banner includes verification guidance

### For Training:
- User manual: /docs/user-guide.pdf
- Video tutorials: /docs/videos
- Webinars: Monthly training sessions
- Contact: training@example.com

---

## ✅ Summary

The NSW Planning Compliance Engine provides:

✓ **Two specialized routes** for different workflows
✓ **Real-time NSW Planning Portal integration**
✓ **Comprehensive SEPP/LEP/DCP provision database**
✓ **Intelligent search and filtering**
✓ **Professional-grade compliance assessment**
✓ **Full legal text with version tracking**
✓ **Spatial heritage conservation analysis**
✓ **Development-type aware filtering**
✓ **Fast performance** (sub-second queries)
✓ **Transparent data sources** (audit trail)

**Primary Use Cases**:
1. Property compliance pre-assessment
2. DA preparation and documentation
3. Feasibility studies
4. Due diligence
5. Provision research
6. Legal citation verification

**Target Users**:
- Private certifiers
- Town planners
- Architects
- Property solicitors
- Council planners
- Researchers

---

*End of Stakeholder Presentation*

**Document Version**: 1.0
**Last Updated**: October 2024
**Next Review**: Quarterly
