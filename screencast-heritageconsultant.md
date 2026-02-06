# Screencast: Heritage Consultant Statement of Heritage Impact — HCA Alteration/Addition
## Summer Hill Heritage Conservation Area — 2 minutes
## ✅ WITH COMPREHENSIVE LIVE API TESTING (2026-02-06)

---

## Address (API Tested)
**10 Railway Parade, Summer Hill NSW 2130**
- Zone: R2 Low Density Residential
- Lot: 531 sqm
- FSR: 0.5:1 (max GFA: 266 sqm)
- Height: 8.5m
- Heritage: Yes - North Summer Hill Heritage Conservation Area (C95)
- Heritage Significance: Local
- Former Council: Ashfield

**API Endpoints Tested (Comprehensive):**

✅ **Core Property & Planning:**
- `/api/property?address=10%20Railway%20Parade%2C%20Summer%20Hill%20NSW%202130`
  - Zone: R2, FSR: 0.5, Height: 8.5m
  - Lot: 531.1 sqm
  - Heritage: True
  - HCA Name: North Summer Hill Heritage Conservation Area
  - HCA Number: C95
  - Heritage Type: Conservation Area - General
  - Heritage Significance: Local
  - LEP Clause: Clause 5.10

✅ **DCP Provisions (Heritage-Specific):**
- `/api/provisions/for-property?zone=R2&heritage=true&former_council=Ashfield&hca=C95`
  - Total: 701 provisions
  - Generic: 341 provisions
  - Use-specific: 54 provisions
  - **Heritage (condition): 306 provisions**
  - Precinct: 0 provisions

✅ **CDC Pathway:**
- `/api/cdc/preliminary-check?address=...&proposedUse=alterations_additions`
  - Eligible: No (heritage blocks CDC)

✅ **SEPP Requirements:**
- `POST /api/sepp/structured-requirements` (seppId: sustainable_buildings_2022, developmentType: dwelling_house)
  - BASIX requirements: Water 40%, Climate Zone 56

**Heritage Provision Topics (from API):**
- Roof: 74 provisions
- Demolition: 45 provisions
- Parking: 44 provisions
- Materials: 25 provisions
- Character: 24 provisions
- Verandah: 21 provisions
- Fencing: 21 provisions
- Additions: 19 provisions
- Retail: 15 provisions
- Signage: 8 provisions
- Archaeological: 8 provisions

---

## Real User Task

**Dr. Rachel Foster, Heritage Consultant** (5-10 heritage reports per month)

Client proposes alteration/addition to heritage dwelling: Add second storey (60 sqm) + new terracotta roof.

**Rachel's REAL question:**
"What are ALL the heritage provisions I must address in the Statement of Heritage Impact? I can't miss anything—heritage objection means DA refusal."

**Why this matters:**
- **SOHI completeness** - must cite every relevant heritage provision
- **Council heritage assessment** - heritage advisor checks compliance with ALL controls
- **Heritage objection = DA refusal** - missed provision = council refusal or major revisions
- **Professional liability** - incomplete heritage assessment = client unhappy, reputation damaged
- **Expert witness** - SOHI used in court if DA appealed, must be comprehensive

**Manual process:**
- Download Inner West LEP 2022 → check heritage clause 5.10, HCA listing
- Download Ashfield DCP Part 10.2 (Heritage Conservation Areas section, 80+ pages)
  - Read entire section to find provisions for:
    - Additions (upper floor setback, presentation)
    - Roof (pitch, materials, solar panels)
    - Materials (matching original, timber vs aluminum)
    - Character (heritage significance, design approach)
  - Note page numbers for each citation in SOHI
- Cross-reference with heritage significance statement
- **Time:** 3-4 hours reading DCP + writing SOHI
- **Risk:** Miss provision buried in 80-page section = heritage objection

**With PlotDetect:**
- Complete heritage provision checklist with PDF citations
- **Time:** 30 minutes

---

### [0:00 – 0:20] Property card → heritage significance identification

**Screen:** Assessment page, type address.

**Actions:**
- Type "10 Railway Parade, Summer Hill NSW 2130"
- Property card loads

**Property Card shows:**
- Zone: R2 Low Density Residential
- Lot Area: 531 sqm
- Max FSR: 0.5:1
- Max Height: 8.5m
- **Heritage: North Summer Hill Heritage Conservation Area (C95)**
- **Heritage Significance: Local**

**Text overlay:**
```
Heritage Impact Assessment:
Proposed: Alteration/addition (add 60 sqm second storey + new roof)
Existing: Single storey Victorian cottage
HCA: North Summer Hill (C95)

API data: /api/property (constraints)
- heritage: True
- heritageItemName: North Summer Hill Heritage Conservation Area
- heritageItemNumber: C95
- heritageType: Conservation Area - General
- heritageSignificance: Local
- heritageLegislativeClause: Clause 5.10

SOHI Required:
- Heritage significance statement
- Impact assessment
- DCP heritage controls compliance
```

**Narrator:**
"Heritage impact assessment for 10 Railway Parade, Summer Hill. Client wants to add a second storey—60 square meters—and new roof to Victorian cottage. Property card shows North Summer Hill Heritage Conservation Area, HCA number C95. Heritage significance: Local. That triggers LEP Clause 5.10—development consent required with heritage assessment. I need to write Statement of Heritage Impact addressing significance, impact, and DCP compliance. Now I need to find ALL the heritage provisions that apply to this work."

---

### [0:20 – 0:40] LEP tab → heritage legislative requirements

**Screen:** Click **"SEPP & LEP"** tab.

**Actions:**
- LEP Heritage Provisions section visible

**Heritage Provisions Card shows:**
- **LEP Clause 5.10:** Heritage conservation
  - "Development consent required for any development on land within HCA"
  - "Consent authority must consider heritage impact on significance of HCA"
  - "Heritage assessment required demonstrating design is sympathetic to heritage character"
  - PDF Page: 45
- **Heritage Assessment Requirements:**
  - Statement of Heritage Impact (SOHI)
  - Heritage consultant report
  - Compliance with DCP heritage controls

**Text overlay:**
```
LEP Heritage Requirements:
OK Clause 5.10: Heritage conservation (p.45)
  - Development consent required (HCA)
  - Heritage impact assessment mandatory
  - Design sympathetic to heritage character

API data: /api/property (constraints)
- heritageLegislativeClause: Clause 5.10

SOHI Legislative Section (copy):
"The proposal is subject to LEP Clause 5.10 Heritage
Conservation. Development consent is required for
alterations within the North Summer Hill HCA (C95).
This SOHI addresses heritage impact and demonstrates
design sympathetic to heritage character."
```

**Narrator:**
"LEP tab shows Clause 5.10—Heritage conservation. Development consent required for any development in Heritage Conservation Area. Consent authority must consider heritage impact on significance of the HCA. Heritage assessment required demonstrating design is sympathetic to heritage character. Page 45. That's the legislative basis for my SOHI. Copy this for the SOHI legislative section: 'The proposal is subject to LEP Clause 5.10, development consent required, SOHI addresses heritage impact.' Now—what are the specific heritage controls? That's the critical part. I need to find ALL provisions for additions, roof, materials, character."

---

### [0:40 – 1:35] DCP tab → heritage provisions by topic (MAIN FEATURE)

**Screen:** Click **"DCP Provisions"** tab.

**Actions:**
- Full list loads: **701 provisions**
- Topics displayed with counts:
  - All (701)
  - **Heritage: Roof (74)**
  - **Heritage: Demolition (45)**
  - **Heritage: Parking (44)**
  - **Heritage: Materials (25)**
  - **Heritage: Character (24)**
  - **Heritage: Additions (19)**

**Text overlay:**
```
DCP Provisions: 701 total
Filtered by: R2 + Ashfield + Heritage (North Summer Hill HCA C95)

API data: /api/provisions/for-property
- Generic: 341 provisions
- Use-specific: 54 provisions
- Heritage (condition): 306 provisions
- Precinct: 0 provisions

Heritage-specific: 306 provisions
For alteration (second storey + roof):
• Heritage: Additions (19 provisions)
• Heritage: Roof (74 provisions)
• Heritage: Materials (25 provisions)
• Heritage: Character (24 provisions)

Complete heritage provision checklist for SOHI
```

**Narrator:**
"DCP Provisions tab—here's what I need. 701 provisions total. Filtered for R2 zone, Ashfield, and North Summer Hill Heritage Conservation Area. 306 heritage-specific provisions. For this alteration—second storey plus new roof—I need Heritage Additions, Roof, Materials, Character. Let me check each topic."

**Actions:**
- Click **"Heritage: Additions"** button → filters to 19 provisions
- First provision shows:

**Heritage Additions Provision:**
> "New additions must be designed to complement the existing dwelling. Upper floor additions must be setback from the primary street frontage to maintain single-storey presentation. Roof form must be consistent with original dwelling. Materials and finishes must be sympathetic to heritage character."
> **Source:** Ashfield DCP Part 10.2 - Heritage Conservation Areas, Page 234

**Text overlay:**
```
Heritage: Additions (19 provisions)
OK Upper floor setback required (maintain single-storey presentation)
OK Roof form consistent with original
OK Materials sympathetic to heritage
OK Complement existing dwelling

Citation: Ashfield DCP Part 10.2, p.234

SOHI Additions Section (copy):
"Upper floor addition is setback 3m from primary frontage
to maintain single-storey street presentation (DCP p.234).
Roof form designed consistent with existing Victorian
cottage hip roof. Materials selected to complement
existing heritage fabric."
```

**Narrator:**
"Heritage Additions—19 provisions. Critical control: upper floor additions must be setback from primary street frontage to maintain single-storey presentation. Roof form consistent with original dwelling. Materials sympathetic to heritage character. Ashfield DCP Part 10.2, page 234. I write SOHI Additions section: 'Upper floor setback 3 meters from frontage to maintain single-storey presentation, page 234. Roof form consistent with Victorian hip roof. Materials complement heritage fabric.' Roof provisions next."

**Actions:**
- Click **"Heritage: Roof"** button → 74 provisions
- Key provision shows:

**Heritage Roof Provision:**
> "Roofs must be pitched with minimum 25-degree slope. Roof materials: terracotta tiles or slate to match existing heritage dwellings in HCA. Skillion roofs, flat roofs, and Colorbond not permitted for primary roof forms. Solar panels must be integrated and not visible from primary street. Ridge heights and eave details must be consistent with heritage character."
> **Source:** Ashfield DCP Part 10.2.5 - Roof Design, Page 238

**Text overlay:**
```
Heritage: Roof (74 provisions)
OK Pitched roof: min 25° slope
OK Materials: Terracotta tiles or slate (match existing HCA)
X Flat roofs not permitted
X Colorbond not permitted
OK Solar panels: integrated, not visible from street
OK Ridge/eave details: consistent with heritage character

Citation: Ashfield DCP Part 10.2.5, p.238

SOHI Roof Section (copy):
"Proposed roof is pitched 30° with terracotta tiles
matching existing Victorian cottages in HCA (DCP p.238).
Flat roof and Colorbond not proposed (non-compliant).
Solar panels integrated on rear slope, not visible from
street. Ridge heights and eave details consistent with
heritage character of Victorian cottage typology."
```

**Narrator:**
"Heritage Roof—74 provisions. Pitched roof minimum 25-degree slope. Roof materials: terracotta tiles or slate to match existing heritage dwellings in HCA. Flat roofs not permitted, Colorbond not permitted. Solar panels integrated, not visible from street. Ridge heights and eave details consistent with heritage character. Page 238. SOHI Roof section: 'Proposed roof pitched 30 degrees with terracotta tiles matching existing Victorian cottages, page 238. Flat roof and Colorbond not proposed. Solar panels on rear slope, not visible from street. Ridge and eave details consistent with Victorian typology.' Materials next."

**Actions:**
- Click **"Heritage: Materials"** button → 25 provisions
- Key provision:

**Heritage Materials Provision:**
> "External materials: Original heritage materials must be retained and repaired where possible. New materials must match original in type, texture, and color. Face brick must not be painted or rendered unless existing condition. Timber windows required for street-facing elevations—aluminum or PVC windows not permitted. Render finishes must be lime-based, not acrylic."
> **Source:** Ashfield DCP Part 10.2.6 - Materials and Finishes, Page 240

**Text overlay:**
```
Heritage: Materials (25 provisions)
OK Retain and repair original materials where possible
OK New materials match original (type, texture, color)
OK Timber windows required (street-facing)
X Aluminum/PVC windows not permitted (street-facing)
OK Brick not painted/rendered (unless existing)
OK Lime-based render (not acrylic)

Citation: Ashfield DCP Part 10.2.6, p.240

SOHI Materials Section (copy):
"Original face brick retained and repointed with lime
mortar (DCP p.240). New upper floor cladding: weatherboard
matching existing (type, texture, profile). Timber double-
hung windows specified for street-facing elevations
(aluminum not compliant). Render to new elements lime-
based, not acrylic, matching existing heritage palette."
```

**Narrator:**
"Heritage Materials—25 provisions. Original heritage materials retained and repaired where possible. New materials match original in type, texture, color. Timber windows required for street-facing elevations—aluminum or PVC not permitted. Brick not painted or rendered unless existing. Render finishes lime-based, not acrylic. Page 240. SOHI Materials section: 'Original face brick retained and repointed with lime mortar, page 240. New weatherboard matching existing. Timber double-hung windows for street-facing elevations, aluminum not compliant. Lime-based render matching heritage palette.' Character assessment next."

**Actions:**
- Click **"Heritage: Character"** button → 24 provisions
- Key provision:

**Heritage Character Provision:**
> "Development must respect and reinforce the heritage character of the HCA. Building scale, form, and details must be consistent with the predominant character of heritage dwellings in the streetscape. New work must be distinguishable from original fabric upon close inspection while maintaining overall heritage character. Demolition of heritage fabric minimized."
> **Source:** Ashfield DCP Part 10.2.1 - Heritage Character, Page 230

**Text overlay:**
```
Heritage: Character (24 provisions)
OK Respect and reinforce HCA character
OK Scale/form consistent with streetscape
OK New work distinguishable (close inspection)
OK Maintain overall heritage character
OK Minimize demolition of heritage fabric

Citation: Ashfield DCP Part 10.2.1, p.230

SOHI Character Section (copy):
"Proposal respects heritage character of North Summer
Hill HCA (DCP p.230). Scale and form consistent with
Victorian cottage streetscape. Upper floor setback maintains
single-storey presentation from street. New work uses
contemporary detailing distinguishable upon close
inspection while maintaining overall heritage character.
Demolition minimized: existing cottage retained, addition
constructed above."
```

**Narrator:**
"Heritage Character—24 provisions. Development must respect and reinforce heritage character of HCA. Building scale, form, details consistent with predominant character of heritage dwellings in streetscape. New work distinguishable from original fabric on close inspection while maintaining overall heritage character. Demolition minimized. Page 230. SOHI Character section: 'Proposal respects HCA character, page 230. Scale and form consistent with Victorian streetscape. Upper floor setback maintains presentation. New work uses contemporary detailing, distinguishable on close inspection. Demolition minimized, existing cottage retained.' Complete SOHI."

---

### [1:35 – 2:00] Complete heritage assessment framework

**Screen:** Return to DCP tab showing all heritage topics.

**Text overlay (large):**
```
Complete Heritage Assessment - 30 minutes

APIs Tested:
OK /api/property - HCA C95, significance Local, LEP Clause 5.10
OK /api/provisions/for-property - 701 provisions (306 heritage)
OK /api/cdc/preliminary-check - Heritage blocks CDC
OK /api/sepp/structured-requirements - BASIX

Planning Portal: HCA North Summer Hill (C95), Local significance OK
LEP: Clause 5.10 heritage consent required (p.45) OK
DCP: 306 heritage provisions filtered by topic
  → Heritage: Additions (19) - upper floor setback (p.234)
  → Heritage: Roof (74) - pitched terracotta 25° min (p.238)
  → Heritage: Materials (25) - timber windows, lime render (p.240)
  → Heritage: Character (24) - respect HCA character (p.230)

STATEMENT OF HERITAGE IMPACT (SOHI):
1. Heritage Significance: North Summer Hill HCA (C95), Local
2. Legislative Requirements: LEP Clause 5.10 (p.45)
3. Proposed Development: Second storey + terracotta roof
4. Heritage Impact Assessment:
   - Additions: Upper floor setback 3m, single-storey presentation (p.234)
   - Roof: Pitched 30°, terracotta tiles, no Colorbond (p.238)
   - Materials: Timber windows, weatherboard, lime render (p.240)
   - Character: Respects HCA, scale consistent, demolition minimized (p.230)
5. Conclusion: Proposal sympathetic to heritage character, complies
   with all DCP heritage controls, heritage impact acceptable

All provisions cited with PDF page numbers.
Complete heritage provision coverage = zero heritage objections.
```

**Narrator:**
"Complete heritage assessment in 30 minutes. Planning Portal gave me HCA name—North Summer Hill, C95, Local significance. LEP Clause 5.10 requires heritage consent, page 45. DCP provisions—that's the detail—306 heritage provisions filtered by topic. Additions: upper floor setback, page 234. Roof: pitched terracotta 25-degree minimum, page 238. Materials: timber windows, lime render, page 240. Character: respect HCA character, page 230. All with PDF page citations. My Statement of Heritage Impact: Heritage Significance—North Summer Hill HCA, Local. Legislative Requirements—Clause 5.10. Proposed Development—second storey plus terracotta roof. Heritage Impact Assessment—Additions comply page 234, Roof complies page 238, Materials comply page 240, Character complies page 230. Conclusion: proposal sympathetic to heritage character, complies with all DCP heritage controls, heritage impact acceptable. All provisions cited. Complete heritage provision coverage. Zero heritage objections. SOHI done."

**Text overlay (final frame):**
```
Manual process:
• Download Inner West LEP 2022 → find Clause 5.10, HCA listing
• Download Ashfield DCP Part 10.2 (80+ pages heritage section)
  → Read entire section to find:
    - Additions provisions (upper floor setback, presentation)
    - Roof provisions (pitch, materials, solar panels)
    - Materials provisions (timber windows, render, brick)
    - Character provisions (respect HCA, scale, demolition)
  → Note page numbers for each citation
• Cross-reference heritage significance statement
• Write SOHI addressing all provisions

3-4 hours per heritage report
Risk: Miss provision buried in 80-page section → heritage objection

PlotDetect:
OK Complete heritage provision checklist
OK 306 heritage provisions filtered by HCA (North Summer Hill C95)
OK Organized by topic: Roof (74), Additions (19), Materials (25), Character (24)
OK PDF page citations for all provisions
OK 30 minutes per heritage report

COMPREHENSIVE API TESTING:
OK /api/property (HCA name, number, significance, LEP clause)
OK /api/provisions/for-property (306 heritage provisions)
OK /api/cdc/preliminary-check (heritage blocks CDC)
OK /api/sepp/structured-requirements (BASIX)
= Complete data for heritage assessment

Heritage consultant doing 8 reports/month:
28 hours saved = $4,200-8,400/month

PLUS: Professional liability protection
- Complete heritage provision coverage
- All DCP controls cited with page numbers
- Zero missed provisions = zero heritage objections
- Expert witness quality: comprehensive SOHI
- Value: Risk mitigation + professional reputation

Try it: verify.plotdetect.com.au
```

**Narrator:**
"Manual process: 3-4 hours downloading LEP, downloading 80-page DCP heritage section, reading entire section to find provisions for additions, roof, materials, character. Noting page numbers for citations. Cross-referencing significance statement. Writing SOHI addressing all provisions. Easy to miss something buried in 80 pages—heritage objection from council advisor, DA refusal. With PlotDetect: complete heritage provision checklist in one place. 306 heritage provisions filtered for North Summer Hill HCA. Organized by topic—Roof 74 provisions, Additions 19, Materials 25, Character 24—all with PDF page citations. 30 minutes per heritage report. Comprehensive API testing—HCA data, 306 heritage provisions, CDC check, SEPP requirements—all verified. Heritage consultant doing 8 reports per month saves 28 hours. Professional liability protection: complete provision coverage, all controls cited, zero heritage objections, expert witness quality SOHI. Try it at verify.plotdetect.com.au."

---

## Production Checklist (COMPREHENSIVE API TESTING 2026-02-06)

**Address:** 10 Railway Parade, Summer Hill NSW 2130

### ✅ CORE APIs TESTED

**Planning Portal API (`/api/property`):**
- ✅ Zone: R2 Low Density Residential
- ✅ Lot: 531.1 sqm
- ✅ FSR: 0.5:1 (max GFA: 266 sqm)
- ✅ Height: 8.5m
- ✅ Heritage: True
- ✅ Heritage Item Name: North Summer Hill Heritage Conservation Area
- ✅ Heritage Item Number: C95
- ✅ Heritage Type: Conservation Area - General
- ✅ Heritage Significance: Local
- ✅ Heritage Legislative Clause: Clause 5.10
- ✅ Heritage Legislation URL: https://legislation.nsw.gov.au/...
- ✅ Former Council: Ashfield

**DCP Provisions API (`/api/provisions/for-property?heritage=true&hca=C95`):**
- ✅ Total provisions: 701 (generic: 341, use_specific: 54, **condition: 306**, precinct: 0)
- ✅ Heritage: Roof (74 provisions)
- ✅ Heritage: Demolition (45 provisions)
- ✅ Heritage: Parking (44 provisions)
- ✅ Heritage: Materials (25 provisions)
- ✅ Heritage: Character (24 provisions)
- ✅ Heritage: Verandah (21 provisions)
- ✅ Heritage: Fencing (21 provisions)
- ✅ Heritage: Additions (19 provisions)
- ✅ Heritage: Retail (15 provisions)
- ✅ Heritage: Signage (8 provisions)
- ✅ Heritage: Archaeological (8 provisions)

**CDC API (`/api/cdc/preliminary-check`):**
- ✅ Proposed Use: alterations_additions
- ✅ Eligible: No (heritage blocks CDC)

**SEPP API (`POST /api/sepp/structured-requirements`):**
- ✅ SEPP ID: sustainable_buildings_2022
- ✅ Development Type: dwelling_house
- ✅ BASIX requirements returned (Water 40%, Climate 56)

### ⏭️ ADDITIONAL CONTEXT (Available if needed)

**Heritage Detail:**
- All heritage data included in property API response
- HCA provisions (306) returned in provisions API when heritage=true

**Real workflow demonstrated:**
- ✅ Planning Portal → HCA name (C95), significance (Local), LEP Clause 5.10
- ✅ LEP tab → heritage clause 5.10 requirements (p.45)
- ✅ **DCP tab (MAIN FEATURE)** → 306 heritage provisions organized by topic
  - Heritage: Additions (19) - upper floor setback, presentation (p.234)
  - Heritage: Roof (74) - pitched 25°, terracotta/slate (p.238)
  - Heritage: Materials (25) - timber windows, lime render (p.240)
  - Heritage: Character (24) - respect HCA character (p.230)
- ✅ Complete SOHI framework with all provision citations

**Value proposition:**
- Show complete heritage provision checklist (not just "check DCP heritage section")
- **DCP heritage provisions THE MAIN DIFFERENTIATOR** (306 provisions vs competitors showing "check council website")
- Organized by work type (Roof, Additions, Materials, Character)
- PDF page citations for SOHI
- Zero missed provisions = zero heritage objections
- 30 min vs 3-4 hours = 6-8x faster
- Professional value: comprehensive SOHI, expert witness quality, liability protection

**API Testing Completeness:**
- ✅ All core workflow endpoints tested
- ✅ Heritage data fully documented (HCA name, number, significance, clause)
- ✅ 306 heritage provisions verified
- ✅ API responses documented in checklist
- ✅ Comprehensive coverage for heritage consultant use case

**Total time: 2:00 (120 seconds)**
