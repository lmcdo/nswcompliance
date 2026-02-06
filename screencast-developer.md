# Screencast: Developer Feasibility — Dual Occupancy DA Requirements
## Ashfield R2 Large Lot — 2 minutes
## ✅ WITH LIVE API DATA (2026-02-06)

---

## Address (API Tested)
**35 Albert Street, Ashfield NSW 2131**
- Zone: R2 Low Density Residential
- Lot: 736 sqm
- FSR: 0.7:1 (max GFA: 515 sqm)
- Height: 8.5m
- Heritage: No
- Former Council: Ashfield

**API Endpoints Tested:**
- `/api/property?address=35%20Albert%20Street%2C%20Ashfield%20NSW%202131`
- `/api/provisions/for-property?zone=R2&former_council=Ashfield`
- DCP Provisions: 395 total (parking: 32, landscaping: 11, setbacks: 4, building_form: 20)

---

## Real User Task

**Michael Chen, Small-Scale Developer** (2-3 projects per year)

Evaluating dual occupancy feasibility on 736 sqm Ashfield lot.

**Michael's REAL question:**
"What are the DA requirements I need to meet? What will this cost to deliver?"

**Why this matters:**
- **DA pathway required** (Inner West doesn't allow CDC for dual occupancy)
- **DCP compliance** determines construction cost
- **Parking, setbacks, landscaping** = hard costs developer must factor in
- **Missing a requirement** = council RFI = 2-4 week delay + rework costs

**Manual process:**
- Download Inner West LEP 2022 (200 pages) - check zone, FSR, height
- Download SEPP Sustainable Buildings - check BASIX requirements
- Download Ashfield DCP (multiple parts, 200+ pages) - find parking, setbacks, landscaping rules
- Cross-reference everything
- **Time:** 3-4 hours
- **Risk:** Miss a provision = RFI during assessment

**With PlotDetect:**
- Complete regulatory cascade in one interface
- **Time:** 15 minutes

---

### [0:00 – 0:20] Property card → max GFA calculation

**Screen:** Assessment page, type address.

**Actions:**
- Type "35 Albert Street, Ashfield NSW 2131"
- Property card loads

**Property Card shows:**
- Zone: R2 Low Density Residential
- Lot Area: 736 sqm
- Max FSR: 0.7:1
- Max Height: 8.5m
- **Max GFA: 515 sqm** (FSR × lot area)

**Text overlay:**
```
Site evaluation: R2 zone, 736 sqm lot
Max GFA: 736 sqm × 0.7:1 = 515 sqm
Dual occupancy target: 2 × 120 sqm = 240 sqm
Well within FSR limit ✓
```

**Narrator:**
"736 square meter lot in Ashfield, R2 zone. FSR is 0.7 to 1—that gives me 515 square meters max GFA. Dual occupancy needs about 240 square meters total, so FSR is fine. Height limit 8.5 meters. Now I need to check the DA requirements."

---

### [0:20 – 0:40] SEPP tab → BASIX cost impact

**Screen:** Click **"SEPP & LEP"** tab.

**Actions:**
- SEPP Requirements section visible

**SEPP section shows:**
- **BASIX Targets:**
  - Water: 40% reduction
  - Climate Zone: 56
  - BASIX Area: 5 (Inner West)
- **DA Pathway:** Inner West requires DA for dual occupancy (CDC not available per council policy)

**Text overlay:**
```
SEPP Requirements:
✓ BASIX triggered (dual occ > $50k threshold)
  - Water 40%: Efficient fixtures ($1,500)
  - Climate Zone 56: Enhanced insulation ($2,000)
  - BASIX cost: ~$3,500

✓ DA pathway required (Inner West policy)
  - CDC not available for dual occupancy
  - Must comply with DCP provisions
```

**Narrator:**
"SEPP tab shows BASIX requirements. Water target 40%, Climate Zone 56. That's about $3,500 in efficient fixtures and insulation I need to budget. Inner West requires DA for dual occupancy—CDC isn't available here. So I need to meet all DCP provisions."

---

### [0:40 – 1:00] LEP tab → zone controls

**Screen:** Scroll down to LEP section (same tab).

**Actions:**
- LEP section shows:

**Land Use Zoning Card:**
- R2 Low Density Residential
- Permitted uses table:
  - ✓ Dwelling houses (permitted)
  - ✓ **Dual occupancies (permitted with consent)**
  - ✓ Secondary dwellings (permitted with consent)
- Zone objectives: Provide housing choice while maintaining low-density character

**No Local Provisions card** (no Part 6 site-specific clauses)
**No Heritage Provisions card** (property not in HCA)

**Text overlay:**
```
LEP Controls:
✓ Zone R2: Dual occupancy permitted with consent
✓ No Part 6 blockers
✓ No heritage constraints
✓ Clean DA pathway
```

**Narrator:**
"LEP tab confirms: R2 zone, dual occupancy permitted with development consent. No Part 6 local provisions, no heritage constraints. Clean DA pathway. Now I need to see the actual DCP requirements—parking, setbacks, landscaping. That's where the cost is."

---

### [1:00 – 1:40] DCP tab → compliance requirements (MAIN FEATURE)

**Screen:** Click **"DCP Provisions"** tab.

**Actions:**
- Full list loads: **395 provisions**
- Topics displayed with counts:
  - All (395)
  - Parking (32)
  - Building Form (20)
  - Landscaping (11)
  - Height (10)
  - Open Space (9)
  - Setbacks (4)
  - Privacy (3)

**Text overlay:**
```
DCP Provisions: 395 total
Filtered by zone (R2) + council (Ashfield)

Key topics for dual occupancy:
• Parking: 32 provisions
• Building Form: 20 provisions
• Landscaping: 11 provisions
• Setbacks: 4 provisions
```

**Narrator:**
"DCP Provisions tab—here's the detail I need. 395 provisions total, already filtered for R2 zone in Ashfield. Let me check the critical topics for dual occupancy."

**Actions:**
- Click **"Parking"** button → filters to 32 provisions
- First provision shows:

**Parking Provision (example):**
> "Dual occupancy: 2 car spaces per dwelling (total 4 spaces). Covered carport or garage required. Driveway width minimum 2.5m for single access, 5.5m for dual access."

**Text overlay:**
```
Parking requirements:
✓ 4 spaces total (2 per dwelling)
✓ Covered (carport/garage)
✓ Driveway: 2.5m min width

Cost impact: 4 spaces @ $8k = $32k
```

**Narrator:**
"Parking: 4 spaces required, 2 per dwelling. Must be covered—carport or garage. Driveway minimum 2.5 meters wide. At $8,000 per space including driveway, that's $32,000."

**Actions:**
- Click **"Landscaping"** button → 11 provisions
- Key provision shows:

**Landscaping Provision:**
> "Minimum landscaped area: 30% of site area. Deep soil zone: minimum 6m dimension. Canopy trees required: 1 per 100 sqm site area."

**Text overlay:**
```
Landscaping requirements:
✓ 30% min landscaped: 221 sqm (736 × 30%)
✓ Deep soil zone: 6m min dimension
✓ Canopy trees: 7 required (736/100)

Cost impact: ~$15k landscaping
```

**Narrator:**
"Landscaping: minimum 30% of site—that's 221 square meters. Deep soil zone with 6-meter dimension. Seven canopy trees required. About $15,000 in landscaping cost."

**Actions:**
- Click **"Building Form"** button → 20 provisions
- Key provision:

**Building Form Provision:**
> "Maximum site coverage: 50% of site area. Building separation: minimum 6m between dwellings for dual occupancy."

**Text overlay:**
```
Building form requirements:
✓ Max site coverage: 50% (368 sqm)
✓ Building separation: 6m between dwellings

Confirms: 240 sqm dual occ footprint OK
```

**Narrator:**
"Building form: maximum 50% site coverage, that's 368 square meters. My dual occupancy is 240 square meters total footprint—well within limit. Six-meter separation between dwellings required."

---

### [1:40 – 2:00] Feasibility outcome

**Screen:** Return to DCP tab showing all topics.

**Text overlay (large):**
```
DA Requirements identified in 15 minutes

Planning Portal: Zone R2, FSR 0.7:1, 515 sqm max GFA ✓
SEPP: BASIX $3,500 ✓
LEP: Dual occ permitted, no blockers ✓
DCP: 395 provisions filtered by topic
  → Parking: 4 spaces ($32k)
  → Landscaping: 30% min ($15k)
  → Building form: 50% max coverage ✓
  → Setbacks: Front/side/rear (read provisions)

FEASIBILITY:
Construction: 240 sqm @ $3,500/sqm = $840k
Hard costs: Parking $32k + Landscaping $15k + BASIX $3.5k = $50k
DA approval: $30k
Total: $920k
Revenue: 240 sqm @ $8,000/sqm = $1.92M
Return: ($1.92M - $920k) / $920k = 109%
= 52% return = PROCEED
```

**Narrator:**
"Complete DA requirements in 15 minutes. Planning Portal gave me FSR and height. SEPP showed BASIX cost $3,500. LEP confirmed dual occupancy permitted, no blockers. DCP provisions—that's the detail—parking 4 spaces, $32,000. Landscaping 30%, $15,000. Building form, setbacks, all the rules I need for DA. Total hard costs $50,000. Add that to construction, run feasibility: 52% return. Good project. Proceed."

**Text overlay (final frame):**
```
Manual process:
• Download LEP 2022 (200 pages) → find zone, FSR, height
• Download SEPP Sustainable Buildings → find BASIX targets
• Download Ashfield DCP Part 2, Part 4 (200+ pages)
  → Search for parking provisions
  → Search for landscaping provisions
  → Search for setbacks, building form
• Cross-reference everything
• Note page numbers for DA report citations

3-4 hours per site
Risk: Miss DCP provision → RFI → 2-4 week delay

PlotDetect:
✓ Complete regulatory cascade: PP → SEPP → LEP → DCP
✓ 395 DCP provisions filtered by zone + council
✓ Organized by topic: Parking (32), Landscaping (11), Setbacks (4)
✓ PDF page citations for DA report
✓ 15 minutes per site

Developer analyzing 20 sites/year:
60 hours saved = $9,000-18,000/year

PLUS: Avoid missed provisions
- Complete DCP compliance check upfront
- No council RFIs during assessment
- Value: $15k-30k in avoided delays per project

Try it: verify.plotdetect.com.au
```

**Narrator:**
"Manual process: 3-4 hours downloading LEPs, SEPPs, DCPs, searching for provisions. Easy to miss something—council RFI, 2-4 week delay. With PlotDetect: complete regulatory cascade in one place. 395 DCP provisions filtered and organized by topic. All with page citations for DA report. 15 minutes per site. Developer analyzing 20 sites per year saves 60 hours and avoids costly RFIs. Try it at verify.plotdetect.com.au."

---

## Production Checklist (API Verified 2026-02-06)

**Address:** 35 Albert Street, Ashfield NSW 2131

**Planning Portal API (`/api/property`):**
- ✅ Zone: R2 Low Density Residential
- ✅ Lot: 736 sqm
- ✅ FSR: 0.7:1 (max GFA: 515 sqm)
- ✅ Height: 8.5m
- ✅ Heritage: False
- ✅ Former Council: Ashfield
- ✅ BASIX: Water 40%, Climate Zone 56

**DCP Provisions API (`/api/provisions/for-property`):**
- ✅ Total provisions: 395 (generic: 341, use_specific: 54)
- ✅ Parking: 32 provisions
- ✅ Building form: 20 provisions
- ✅ Landscaping: 11 provisions
- ✅ Height: 10 provisions
- ✅ Open space: 9 provisions
- ✅ Setbacks: 4 provisions
- ✅ Privacy: 3 provisions

**Real workflow demonstrated:**
- ✅ Planning Portal → zone, FSR, height limits
- ✅ SEPP tab → BASIX requirements ($3,500 cost)
- ✅ LEP tab → dual occ permitted, no Part 6 blockers
- ✅ **DCP tab (MAIN FEATURE)** → 395 provisions filtered by topic
  - Parking requirements (4 spaces, $32k cost)
  - Landscaping requirements (30%, $15k cost)
  - Building form (50% max coverage)
  - Setbacks (front/side/rear)
- ✅ Feasibility outcome: $50k hard costs identified → 52% return → PROCEED

**Value proposition:**
- Show complete regulatory cascade (PP → SEPP → LEP → DCP)
- DCP provisions are THE MAIN FEATURE (395 provisions vs competitors showing "check DCP manually")
- Filtered by zone + council (not dumping 10,000 generic provisions)
- Organized by topic (parking, landscaping, setbacks)
- Real cost impact shown (parking $32k, landscaping $15k)
- 15 min vs 3-4 hours = 12x faster

**Total time: 2:00 (120 seconds)**
