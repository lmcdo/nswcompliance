# Product Demo — 2 Minutes
## verify.plotdetect.com.au — Current Feature State
## Target: Architects / Town Planners / Developers

---

### Scenario
**Emma Chen, Town Planner**
New DA instruction: dual occupancy, heritage site, Ashfield.
Task: scope the compliance work, start the SEE, quote the fee.

Manual process: download Inner West LEP (200 pages), find Part 6 Clause 6.20, download Ashfield DCP (300+ pages), manually identify applicable topics. **3–4 hours.**

With PlotDetect: **15 minutes.**

---

### [0:00 – 0:10] Address entry → property card

**Screen:** Assessment page, blank.

**Actions:**
- Type "35 Albert Street, Ashfield NSW 2049"
- Property card loads instantly:
  - Zone: R2 Low Density Residential
  - Lot area: 736 sqm | Frontage: 9.8m
  - Heritage Conservation Area badge
  - Lot dimensions visible

**Text overlay:**
```
35 Albert Street, Ashfield
R2 Low Density | 736 sqm
Heritage Conservation Area
```

---

### [0:10 – 0:25] SEPP tab — approval pathway

**Screen:** Click SEPP & LEP tab.

**Actions:**
- CDC eligibility screener loads
- Result: ❌ Not eligible — heritage area
- Approval pathway: Development Application (DA)
- BASIX section: Water 40%, Climate Zone 56, thermal requirements shown
- TOD parking: not applicable (not near TOD precinct)

**Text overlay:**
```
CDC eligibility: ✗ Not available
(Heritage Conservation Area)

Approval pathway: DA required

BASIX targets:
Water 40% | Climate Zone 56
```

**Narrator / title card:**
"Heritage area means no fast-track CDC. DA is the path. BASIX targets locked in for the brief — confirmed in under 30 seconds."

---

### [0:25 – 0:45] LEP tab — standards and constraints

**Screen:** Scroll down to LEP section.

**Actions:**
- Height: 9m card visible
- FSR: 0.55:1 card visible
- Environmental constraints: no flood, no acid sulfate
- Heritage card expands: "Ashfield HCA — LEP Schedule 5 Clause 5.10 (page 50)"
- Local Provisions card: red "Site-Specific Controls" badge
  - "Clause 6.20: Development on land in Haberfield HCA (page 77)"
  - This clause controls: street alignment, visibility from street, materials compatibility

**Text overlay:**
```
LEP Development Standards:
Height 9m | FSR 0.55:1

Heritage:
✓ Schedule 5 — Clause 5.10 (page 50)
✓ Clause 6.20 — Site-specific (page 77)
  "New work not visible from street"
```

**Narrator / title card:**
"Clause 6.20 is the critical one. It's not in the general standards — it's a Part 6 site-specific clause. Miss it and council will RFI you. PlotDetect surfaces it automatically."

---

### [0:45 – 1:15] DCP tab — DA mode, scope intake, triage

**Screen:** Click DCP Provisions tab. DA Mode panel is visible.

**Actions:**
- Set dev type: "Dual Occupancy"
- Ancillary works: tick "Retaining wall", tick "Demolition"
- Scope auto-sets: 197 provisions across 8 topics
- Excluded topics section shows:
  - 6 topics with 0 provisions for this dev type
  - "Demolition — selected — none for this dev type" (labelled)
  - Retaining wall is in the active topics list (has provisions)
- Active topics visible: Access 40, Environmental 28, General 21, Landscaping 20...

**Text overlay:**
```
Dev type: Dual Occupancy
Ancillary: Retaining wall + Demolition

Scope: 197 provisions / 8 topics

Demolition: selected but no provisions
for this dev type — noted automatically
```

**Narrator / title card:**
"Scope is set from your selection. 197 provisions instead of 400+. Topics with nothing to assess are flagged — including ones you explicitly selected so you know the system registered them."

**Actions (continue):**
- Topics list shows with provision counts
- Hover "Access" topic → × appears → click
- Type: "No new vehicle access — existing crossover retained"
- Confirm → topic removed
- Count drops: now 157 provisions / 7 topics

**Text overlay:**
```
Excluding irrelevant topics:
hover → × → state basis

"No new vehicle access proposed"

Reason recorded in SEE automatically
This is the correct professional method
for handling non-applicable topics
```

---

### [1:15 – 1:35] Working through provisions

**Screen:** Provisions list open, first topic expanded.

**Actions:**
- First provision visible: a Building Form clause
- Click "Complies" → green tick, provision moves to Complies bucket
- Click next provision → read → click "Varies" → amber
  - Reason field appears: type "FSR calculation pending survey"
- Scroll through — show a few more marked

**Text overlay:**
```
Marking provisions:
✓ Complies — confirmed
△ Varies — justification required
— N/A — not applicable to proposal

Assessment recorded as you work
```

---

### [1:35 – 1:50] Export SEE

**Screen:** Click "Export SEE Draft" button.

**Actions:**
- PDF downloads: "Draft-SEE-Inner-West-2026-03-10.pdf"
- Show PDF opening:
  - Cover page: address, dev type, date, prepared by
  - Section 2: Site context
  - Section 5: LEP Standards (height, FSR, heritage clause citations with page numbers)
  - Section 6: DCP schedule — 6.1 Varies (1), 6.2 Complies (X), 6.3 N/A planner, 6.4 N/A intake
  - Schedule B: "Access — No new vehicle access proposed"

**Text overlay:**
```
Draft SEE exported:
✓ Site context auto-populated
✓ LEP clauses cited with page numbers
✓ DCP schedule: Varies / Complies / N/A
✓ Schedule B: excluded topics with basis

Ready to complete and lodge
```

---

### [1:50 – 2:00] Final frame

**Text overlay (full screen):**
```
Manual: 3–4 hours
• Download LEP (200 pages)
• Find Clause 6.20 (or miss it)
• Download DCP (300+ pages)
• Manually identify applicable topics
• Draft SEE from scratch

PlotDetect: 15 minutes
• LEP constraints surfaced automatically
• DCP scoped to your development type
• SEE drafted as you assess

Know what applies. Before you start.

verify.plotdetect.com.au
```

---

### Production notes

**Address:** 35 Albert Street, Ashfield NSW 2049 (R2, Heritage, verified working)

**Preparation before recording:**
- Session already in DA mode with some provisions marked (don't start from zero — looks slow)
- Have dev type and ancillary works pre-selected, then reset to show the selection for camera
- Triage click: practise hover → × → reason → confirm until smooth (~2 seconds)
- PDF: pre-mark 5–8 provisions (2 Complies, 1 Varies, 1 N/A) so exported PDF looks meaningful

**Key moments to nail:**
- Clause 6.20 red badge on LEP tab (0:35 mark) — pause on it
- "Demolition — selected — none for this dev type" label in excluded topics (0:55 mark) — pause on it
- PDF cover page loading (1:38 mark) — must look clean

**Do NOT show:**
- Loading spinners or slow API responses — re-record if this happens
- Empty provision lists
- The Browse tab (not relevant to DA workflow)

**Total: 2:00**
