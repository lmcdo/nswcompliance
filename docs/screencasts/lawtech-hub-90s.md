# Screencast: LawTech Hub by Lander & Rogers — Application Demo
## 10 Cove Street, Haberfield — Heritage DA (R2, HCA) — 90 seconds
## Format: Text overlays only, no narration
## ✅ API-VERIFIED (2026-04-01)

---

### Verified API Data (run before recording)

**Address used:** 10 Cove Street, Haberfield NSW 2045
*(Note: entered as "10 Norman Street, Haberfield" — resolved by Planning Portal to Cove St)*

**Property:**
- Zone: R2 Low Density Residential
- Heritage: Yes — Conservation Area (General)
- Area: 500m²
- FSR: 0.5:1 — Inner West LEP 2022, Clause 4.4
- Height: 7m — Inner West LEP 2022, Clause 4.3

**SEPP Housing 2021 (dual occupancy):**
- Eligible: Yes (500m² ≥ 450m² min, 15m ≥ 12m min)
- FSR standard: 0.65:1 — Clause 168(2)(d), SEPP Housing 2021 page 72
- Height standard: 9.5m — Clause 168(2)(e), SEPP Housing 2021 page 72
- Pathway: DA (heritage conservation area — CDC excluded)

**DCP Provisions (Ashfield DCP 2016, R2, heritage, dual_occupancy):**
- Total: 2,362 provisions
- Layer 1 (Generic): 883
- Layer 2 (Zone-specific): 252
- Layer 3 (Heritage/condition): 1,096
- Layer 4 (Precinct): 131
- Heritage provisions: 251

**SEE Document sections (6 pages):**
1. Cover — DRAFT Statement of Environmental Effects, site summary, prepared by, date
2. Site Context — zone, LEP standards, FSR, height, heritage, constraints
3. Approval Pathway — DA determination, legislative basis, required specialist reports
4. DCP Assessment (Schedule A) — section-by-section compliance table
5. Environmental Impact — BASIX, TOD parking, noise
6. Conclusion + Schedule B — non-applicable DCP chapters dismissed with reasons

---

### [0:00–0:12] Property lookup

**Screen:** Assessment page at verify.plotdetect.com.au. Enter address.

**Actions:**
- Type "10 Norman Street, Haberfield NSW 2045"
- Property card appears

**Text overlay:**
```
Development Application
Dual occupancy — Haberfield Heritage Conservation Area

Applicable controls:
Inner West LEP 2022 · Ashfield DCP 2016
SEPP Housing 2021 · SEPP Sustainable Buildings 2022
```

---

### [0:12–0:28] SEPP tab — pathway and state controls

**Screen:** Click SEPP tab.

**Actions:**
- Show pathway triage: Exempt & Complying — Ineligible (heritage). DA required.
- Show SEPP Housing 2021 dual occupancy standards with page citations

**Text overlay:**
```
Pathway: Development Application (DA)
Heritage Conservation Area — CDC excluded
LEP Clause 5.10 · SEPP (Exempt & Complying) 2008 cl.1.17

SEPP Housing 2021 — Dual Occupancy standards:
  Max FSR: 0.65:1     Clause 168(2)(d) · page 72
  Max height: 9.5m    Clause 168(2)(e) · page 72
  Min lot: 450m²      Clause 168(2)(a) · page 72
  Min width: 12m      Clause 168(2)(b) · page 72

Source instrument · clause · PDF page
for every standard
```

---

### [0:28–0:45] LEP tab — site-specific controls

**Screen:** Click LEP / Planning Controls tab.

**Actions:**
- Show LEP development standards: FSR 0.5:1 (Cl.4.4), Height 7m (Cl.4.3)
- Show heritage provisions: Cl.5.10 Conservation of Heritage Items, Schedule 5

**Text overlay:**
```
Inner West LEP 2022
  Cl.4.3  Height of Buildings: 7m
  Cl.4.4  Floor Space Ratio: 0.5:1
  Cl.5.10 Heritage Conservation (mandatory)
  Schedule 5: Heritage Conservation Area — Haberfield

Every standard traceable to:
  Instrument name · clause number · legislation.nsw.gov.au
```

---

### [0:45–1:05] DA Mode — DCP section-by-section assessment

**Screen:** Click "Enable DA Mode". DCP tab shows section list.

**Actions:**
- Show section list: Heritage, Building Form, Setbacks, Landscaping, Parking
- Click into Heritage section — show provisions with compliance status fields
- Planner records "Complies" with note — section marked with green dot

**Text overlay:**
```
DA Mode — DCP Assessment
2,362 applicable provisions · 251 heritage
Ashfield DCP 2016

Planner works section by section:
  ✓ Heritage controls — Complies
  ✓ Building form — Complies
  ~ Setbacks — Varies (rear setback justification required)
  ✓ Landscaping — Complies
  N/A Signage — Not applicable (dismissed)

Every section: recorded compliance status + narrative
Schedule B: dismissed chapters logged with reason
```

---

### [1:05–1:25] Export SEE — the document that goes to council

**Screen:** Click "Export SEE" button. PDF downloads.

**Actions:**
- Show PDF cover page: DRAFT Statement of Environmental Effects, address, zone, heritage, prepared by, date
- Scroll to show sections: 1 Introduction · 2 Site Context · 3 Approval Pathway · 4 DCP Assessment (Schedule A) · 5 Environmental Impact · 6 Conclusion
- Show Schedule A compliance table — section rows with Complies/Varies/N/A
- Show Schedule B — non-applicable chapters with one-sentence reasons

**Text overlay:**
```
Statement of Environmental Effects — exported as PDF

Section 1  Introduction (EP&A Act 1979 basis)
Section 2  Site Context (zone · LEP standards · heritage · constraints)
Section 3  Approval Pathway (DA — legislative basis cited)
Section 4  DCP Assessment — Schedule A
           Every applicable section: status + narrative
Section 5  Environmental Impact (BASIX · TOD · noise)
Section 6  Conclusion
           Schedule B — dismissed chapters (with reasons)

Ready for DA lodgement.
Not AI-generated text. Planner's own words.
Structured evidence base. Every provision cited.
```

---

### [1:25–1:30] Final frame

**Text overlay (full screen):**
```
Preparing a DA compliance report without PlotDetect:

Download Inner West LEP 2022 (200 pages)
Download Ashfield DCP 2016 (400+ pages)
Find applicable provisions manually
Record compliance against each
Draft SEE document
Note every page citation

Half a day per DA.
Risk: miss a provision → council RFI → 2-week delay

PlotDetect:
2,362 applicable provisions identified automatically
Every control cited to source instrument, clause, page
SEE document structured for EP&A Act compliance
Pathway determination with legislative basis
Export PDF → lodge with DA

verify.plotdetect.com.au
```

---

### Production checklist

**✅ API-verified (2026-04-01):**
- `/api/property?address=10+Norman+Street+Haberfield+NSW+2045` → R2, Heritage, 500m², FSR 0.5:1 (Cl.4.4), Height 7m (Cl.4.3)
- `POST /api/housing-sepp/eligibility` → dual_occupancy eligible, FSR 0.65:1 page 72, Height 9.5m page 72
- `/api/provisions/for-property?lga=Inner+West&zone=R2&heritage=true&former_council=ashfield&dev_type=dual_occupancy` → 2,362 provisions (883 generic, 252 zone, 1096 heritage/condition, 131 precinct)
- SEE document structure confirmed: Page1Cover → Page2SiteContext → Page3Pathway → Page4Dcp (Schedule A + B) → Page5Environmental → Page6Conclusion

**NOT demonstrated (not applicable to lawtech pitch):**
- ❌ Corner lot detection (investor tool, wrong audience)
- ❌ TOD walking distance (spatial layer, wrong pitch framing)
- ❌ AI chat widget (must hide for lawtech audience — see DEMO_SETUP.md)

**Total duration:** 90 seconds at comfortable reading pace
