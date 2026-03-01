# Professional UI/UX Design Strategy
**Optimal Page Layout + Navigation for Compliance Professionals**

**Date:** 2025-01-14
**Focus:** Professional users (certifiers, planners, architects)
**Question:** Same page vs. separate pages? What's missing in existing tools?

---

## PART 1: GAPS IN EXISTING COMPLIANCE TOOLS

### **Current Tool Landscape**

| Tool | Target User | Strengths | Critical Gaps |
|------|------------|-----------|---------------|
| **NSW Planning Portal** | General public | Official data, map layers | Slow, manual cross-referencing, no provision text |
| **Council PDFs** | All | Comprehensive | Can't search across docs, version confusion, no relationships |
| **PlanningAlerts.org.au** | Public | DA notifications | No compliance data |
| **Cordell/Rawlinson's** | Professionals | Cost estimates | Outdated, not provision-level, expensive |
| **Council websites** | All | Free | Fragmented, hard to navigate, no search |

---

### **Professional Pain Points (Ranked by Frequency)**

#### **1. Manual Cross-Referencing (Universal Complaint)**

**The Problem:**
```
Step 1: Open Planning Portal → get zone, height, FSR
Step 2: Open LEP PDF → search for clause 4.3 → read height provisions
Step 3: Open DCP PDF → search for section 4.2 → read setbacks
Step 4: Open SEPP PDF → search for overrides
Step 5: Switch between all 4 → take notes → hope nothing missed
```

**Time:** 15-30 minutes per property
**Error Rate:** High (easy to miss provisions)
**Professional Quote:** *"I have 6 PDFs open at once and I'm constantly switching between them"*

**What They Want:**
- Single screen showing SEPP + LEP + DCP together
- Automatic cross-referencing ("This SEPP overrides this DCP")
- No manual searching

---

#### **2. "Did I Miss Anything?" Anxiety (Liability Risk)**

**The Problem:**
- Certifiers legally liable if they miss a provision
- No way to verify completeness
- Manual process = easy to skip sections

**Example:**
```
Certifier checks: Zone ✓, Height ✓, FSR ✓, Setbacks ✓
Missed: Parking requirements (different PDF)
Missed: Heritage HCA (separate layer)
Missed: SEPP override (wouldn't know to look)
→ Certification voided, professional indemnity claim
```

**What They Want:**
- Checklist: "You have reviewed 12/15 applicable provisions"
- Confidence: "No SEPP overrides detected"
- Audit trail: "Citation: Marrickville DCP 2011, Section 4.2.4.3, verified 2025-01-14"

---

#### **3. Version Control Nightmare (Critical Issue)**

**The Problem:**
```
Council website shows: "Marrickville DCP 2011"
But which version?
- Original 2011?
- Amendment No. 1 (2015)?
- Amendment No. 2 (2018)?
- IWLEP 2022 Amendment (2023)? ← Current

Certifier cites wrong version → DA rejected
```

**Professional Quote:** *"I've had DAs knocked back because I cited a provision that was superseded 2 years ago"*

**What They Want:**
- Clear version displayed: "IWLEP 2022 Amendment (March 2023)"
- Amendment history: "This provision changed in 2023"
- Confidence: "This is the current version as of [today's date]"

---

#### **4. No Provision Relationships (Context Missing)**

**The Problem:**
```
DCP says: "Front setback: 6m, except where Section 2.7 applies"
User thinks: "What's Section 2.7? Where is it?"
→ Opens PDF, searches, finds it's about solar access
→ Reads Section 2.7, finds it references Section 4.1
→ Opens Section 4.1... (endless loop)
```

**What They Want:**
- Hyperlinked provisions: Click "Section 2.7" → instant jump
- Related provisions shown: "Also see: Privacy requirements (2.6)"
- Dependency tree: "This provision depends on these 3 conditions"

---

#### **5. Can't Search Across Documents (Fundamental Limitation)**

**The Problem:**
```
Question: "Where are parking requirements for boarding houses?"
Current solution:
- Open DCP PDF → Ctrl+F "boarding house" → 47 results
- Manual scan through all 47 results
- Maybe find it in Section 2.10, maybe Section 4.3, maybe both
- Time: 10 minutes
```

**What They Want:**
- Cross-document search: "boarding house parking" → instant results from ALL docs
- Ranked by relevance
- Preview: "Section 2.10 - Parking: 1 space per 4 residents + 1 visitor per 10 residents"

---

#### **6. Tables in PDFs Are Unusable (Data Extraction Problem)**

**The Problem:**
```
DCP has parking rate table with 50 rows
Professional needs: Rate for "multi-dwelling, 2 bedroom, visitor parking"
→ PDF table: Can't filter, can't sort, can't extract
→ Must read entire table, find row manually
→ Copy/paste doesn't work (formatting lost)
```

**What They Want:**
- Interactive tables: Filter, sort, search
- CSV export: Copy into reports
- Smart lookup: "Show me parking for multi-dwelling" → filtered table

---

#### **7. No Side-by-Side Comparison (Design Optimization)**

**The Problem:**
```
Architect: "Should I do dual occupancy or multi-dwelling?"
Current process:
- Look up dual occupancy controls → write down
- Look up multi-dwelling controls → write down
- Make spreadsheet → compare manually
- Time: 30-60 minutes
```

**What They Want:**
- Instant comparison table
- Feasibility check: "Lot too small for multi-dwelling"
- Tradeoffs highlighted: "Dual occ = easier approval, multi-dwelling = higher yield"

---

#### **8. Precinct/Heritage Provisions Buried (Hidden Requirements)**

**The Problem:**
```
Property in Heritage Conservation Area
DCP Section 8 (Heritage) has 40 pages of additional requirements
Easy to miss: "Fencing in HCA: max 1.2m open style"
→ DA submitted with 1.8m solid fence
→ DA rejected
```

**What They Want:**
- Automatic detection: "Property in HCA C86"
- Highlighted additional requirements
- Can't miss them

---

#### **9. No Mobile Access (Field Work)**

**The Problem:**
```
Certifier at site inspection
Needs to check: "Is this setback compliant?"
→ Can't access DCP PDF on phone (too large, unreadable)
→ Takes photos, checks later at office
→ Might need to return to site
```

**What They Want:**
- Mobile-optimized
- Offline access
- Photo annotation: "This wall is 4.2m from boundary - complies with DCP 4.2.4.3"

---

#### **10. Citation Formatting (Report Writing)**

**The Problem:**
```
Writing compliance report:
Must cite: "Marrickville Development Control Plan 2011 (as amended by Inner West Local Environmental Plan 2022 Amendment No. 3 dated March 2023), Part 4 - Residential Development, Section 4.2 - Multi-Dwelling Housing and Residential Flat Buildings, Clause 4.2.4.3 - Building Setbacks, Control C17"

Time to type this: 2 minutes
Risk of typo: High
```

**What They Want:**
- Copy citation button
- Format options: APA, MLA, Council style
- Include in export

---

## PART 2: OPTIMAL UI/UX DESIGN

### **Design Philosophy: Professional IDE Model**

**Inspiration:** VSCode, Figma, CAD software
**Why:** Professionals need:
- Multiple views of same data
- Persistent context
- Quick mode switching
- Power user shortcuts
- Not simplified (feature-rich is OK)

---

### **RECOMMENDATION: Sidebar + Dynamic Main Content (Single Page Application)**

**NOT separate pages** - because:
- ❌ Loses context when switching (property deselected)
- ❌ Slower (full page reload)
- ❌ Can't have side-by-side views

**NOT tabs** - because:
- ❌ Tabs get cluttered (4+ tabs = confusing)
- ❌ Can't see multiple tabs simultaneously
- ❌ Tab metaphor = separate documents (wrong mental model)

**YES: Sidebar navigation** - because:
- ✅ Persistent context (property stays selected)
- ✅ Quick mode switching (one click)
- ✅ Can split screen (assessment + browse)
- ✅ Professional feel (like IDE)
- ✅ Keyboard shortcuts (Alt+1, Alt+2, etc.)

---

### **FULL UI MOCKUP: Professional Layout**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ NSW PLANNING COMPLIANCE ENGINE                   [Help] [Settings] [Account] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  🔍 Property Search: [180 Addison Rd, Marrickville        ] [Search]        │
│                                                                               │
├──────┬──────────────────────────────────────────────────────────────────────┤
│      │                                                                        │
│  📍  │  ┌─ PROPERTY CONTEXT (Always Visible) ──────────────────────────┐   │
│ Prop │  │ 180 Addison Road, Marrickville                                │   │
│ erty │  │ Zone: R2  |  LGA: Inner West  |  Lot: 405m²                   │   │
│      │  │ Dev Type: [Dwelling House ▼]  |  Heritage: No  |  HCA: No    │   │
│ ──── │  │ [Change Property] [View Map] [Export Summary]                 │   │
│      │  └────────────────────────────────────────────────────────────────┘   │
│  📋  │                                                                        │
│ Ass- │  ┌─ VIEW MODE: ASSESSMENT ───────────────────────────────────────┐   │
│ ess  │  │                                                                 │   │
│ ment │  │ ┌─ SEPP Controls (State) ──────────────────────────┐          │   │
│      │  │ │ 🟥 Highest Priority                               │          │   │
│ ──── │  │ │ Complying Development: NOT AVAILABLE             │          │   │
│      │  │ │ BASIX Water: 40% target                          │          │   │
│  📚  │  │ └──────────────────────────────────────────────────┘          │   │
│ Brow │  │                                                                 │   │
│  se  │  │ ┌─ LEP Requirements (Statutory) ───────────────────┐          │   │
│      │  │ │ 🔴 Must Comply                                    │          │   │
│ ──── │  │ │ Height: 9m | FSR: 0.6:1 | Lot Min: 360m²        │          │   │
│      │  │ └──────────────────────────────────────────────────┘          │   │
│  🔬  │  │                                                                 │   │
│ Res- │  │ ┌─ PRIMARY DCP (Dwelling House) ───────────────────┐          │   │
│ earch│  │ │ 🟡 Guidelines (May Vary)                          │          │   │
│      │  │ │ Section 4.1 - Low Density Residential             │          │   │
│ ──── │  │ │ • Front: Match street (4-6m typical)             │          │   │
│      │  │ │ • Side: 900mm / 1.5m / 2.5m (by storey)          │          │   │
│  ⚖️  │  │ │ • Rear: Merit-based (solar access)               │          │   │
│ Comp │  │ │ [View Full Section 4.1] [View in Browse Mode]    │          │   │
│ are  │  │ └──────────────────────────────────────────────────┘          │   │
│      │  │                                                                 │   │
│ ──── │  │ ┌─ GENERAL DCP (All Dev Types) ────────────────────┐          │   │
│      │  │ │ 🟡 Apply to all development                       │          │   │
│  ⚙️  │  │ │ • Parking (2.10): 1-2 spaces [View Table]        │          │   │
│ Sett │  │ │ • Landscaping (2.18): Min 30% [View Standards]   │          │   │
│ ings │  │ │ • Fencing (2.11): Max 1.2m front [View Details]  │          │   │
│      │  │ └──────────────────────────────────────────────────┘          │   │
│      │  └─────────────────────────────────────────────────────────────────┘   │
│      │                                                                        │
└──────┴──────────────────────────────────────────────────────────────────────┘
```

---

### **SIDEBAR NAVIGATION ITEMS**

#### **📍 Property Mode (Default)**
- Property-centric view
- Shows SEPP > LEP > DCP hierarchy
- Primary + General + Conditional sections
- Quick export, citation

**Keyboard:** `Alt+1` or `Cmd+1`

---

#### **📋 Assessment Mode (Enhanced Property)**
- Same as property but with:
- Detailed provision text panels
- Slide-out legal text
- Compliance checklist
- Annotation tools

**Keyboard:** `Alt+2`

---

#### **📚 Browse Mode (Document Navigation)**

**Sidebar changes to:**
```
┌─ BROWSE MODE ────────────────────┐
│ LGA: [Inner West - Marrickville] │
│                                   │
│ 📁 Marrickville DCP 2011          │
│   📂 Part 2: General Controls     │
│     📄 2.10 Parking (15)          │
│     📄 2.11 Fencing (8)           │
│     📄 2.18 Landscaping (12)      │
│   📂 Part 4: Residential          │
│     📂 4.1 Low Density (45)       │
│       📄 4.1.6.2 Setbacks (12) ←  │
│       📄 4.1.6.3 Coverage (5)     │
│     📂 4.2 Multi-Dwelling (67)    │
│   📂 Part 9: Precincts (40+)      │
│                                   │
│ 📁 Inner West LEP 2022            │
│   📄 Part 4: Principal Dev Stds   │
│   📄 Part 5: Miscellaneous        │
│                                   │
│ 📁 SEPPs                          │
│   📄 Housing 2021                 │
│   📄 Exempt & Complying 2008      │
└───────────────────────────────────┘
```

**Main content shows:**
- Full section with all provisions
- No dev type filtering
- Filter controls: "Numeric only" "Tables only"
- Provision detail view

**Keyboard:** `Alt+3`

---

#### **🔬 Research Mode (Zone + Dev Type Explorer)**

**Sidebar changes to:**
```
┌─ RESEARCH MODE ──────────────────┐
│ No property selected              │
│                                   │
│ LGA: [Inner West ▼]              │
│ Zone: [R2 ▼]                      │
│ Dev Type: [Multi-Dwelling ▼]     │
│                                   │
│ [Research]                        │
│                                   │
│ ─────────────────────────────    │
│ Recent Searches:                  │
│ • R2 + Dwelling House             │
│ • R3 + Multi-Dwelling             │
│ • B4 + Shop Top Housing           │
│                                   │
│ ─────────────────────────────    │
│ Saved Scenarios:                  │
│ • Scenario A: R2 DH               │
│ • Scenario B: R2 Dual Occ         │
│ [+ New Scenario]                  │
└───────────────────────────────────┘
```

**Main content shows:**
- General applicability (not property-specific)
- Ranges: "Height: typically 9m-12m"
- All controls for zone + dev type combo
- Link: "Apply to specific property"

**Keyboard:** `Alt+4`

---

#### **⚖️ Compare Mode (Scenario Comparison)**

**Sidebar changes to:**
```
┌─ COMPARE MODE ───────────────────┐
│ Property: 180 Addison Rd          │
│ Comparing 3 scenarios:            │
│                                   │
│ ✓ Scenario A: Dwelling House      │
│ ✓ Scenario B: Dual Occupancy      │
│ ✓ Scenario C: Multi-Dwelling      │
│                                   │
│ [+ Add Scenario]                  │
│                                   │
│ Show:                             │
│ ☑ Permissibility                  │
│ ☑ Setbacks                        │
│ ☑ Parking                         │
│ ☑ FSR/Height                      │
│ ☐ Detailed provisions             │
│                                   │
│ Format:                           │
│ ⦿ Table                           │
│ ○ Cards                           │
│                                   │
│ [Export to Excel]                 │
└───────────────────────────────────┘
```

**Main content shows:**
- Side-by-side comparison table
- Feasibility indicators
- Tradeoff analysis

**Keyboard:** `Alt+5`

---

### **ADVANCED FEATURES: Power User Tools**

#### **1. Split Screen View**

```
┌──────────────────────────────┬──────────────────────────────┐
│ LEFT: Assessment View        │ RIGHT: Browse View           │
│ (Property 180 Addison Rd)    │ (Section 4.1.6.2 full text)  │
│                              │                              │
│ DCP Setback: 900mm (Side)    │ TABLE: Side Setback Reqs     │
│ [View in Browse] ────────────┼──> ┌─────┬─────┬──────┐     │
│                              │    │1 st │900mm│1.5m  │     │
│                              │    │2 st │1.5m │2.1m  │     │
│                              │    └─────┴─────┴──────┘     │
└──────────────────────────────┴──────────────────────────────┘

Toggle: [Split Screen] button or `Ctrl+\`
```

**Use case:**
- Check property assessment while reading full DCP text
- Cross-reference SEPP with DCP
- Compare two properties side-by-side

---

#### **2. Provision Detail Slide-Out (Current)**

```
┌──────────────────────────────────┐  ┌────────────────────────┐
│ Main Content                     │  │ PROVISION DETAIL       │
│                                  │  │                        │
│ Front Setback: 6m                │  │ Marrickville DCP 2011  │
│ [View Details] ──────────────────┼─>│ Section 4.2.4.3        │
│                                  │  │                        │
│                                  │  │ Control C17:           │
│                                  │  │ "The front setback     │
│                                  │  │  for multi-dwelling... │
│                                  │  │                        │
│                                  │  │ Version: IWLEP 2022 Amd│
│                                  │  │ Date: March 2023       │
│                                  │  │ Status: CURRENT ✓      │
│                                  │  │                        │
│                                  │  │ [Copy Citation]        │
│                                  │  │ [View PDF] [Export]    │
│                                  │  │ [X Close]              │
└──────────────────────────────────┘  └────────────────────────┘
```

**Already implemented** - keep this!

---

#### **3. Quick Search (Global)**

```
Press: / (forward slash) or Ctrl+K

┌──────────────────────────────────────────────────────┐
│ 🔍 Quick Search                                      │
│ [parking requirements dwelling house           ]     │
│                                                      │
│ Results:                                             │
│ 📄 DCP 2.10 - Parking: 1-2 spaces (dwelling house)  │
│ 📄 DCP 4.1.7 - Car Parking: Design standards        │
│ 📄 LEP 6.12 - Off-street parking: General provisions│
│                                                      │
│ [↑↓ Navigate] [Enter to open] [Esc to close]        │
└──────────────────────────────────────────────────────┘
```

**Features:**
- Search across ALL documents
- Fuzzy matching
- Recent searches
- Keyboard navigation

---

#### **4. Citation Manager**

```
Right-click any provision → "Add to Citations"

┌─ CITATIONS (Bottom Bar) ──────────────────────────┐
│ 3 provisions added                                 │
│ • DCP 4.1.6.2 - Front setbacks                     │
│ • DCP 2.10 - Parking rates                         │
│ • LEP 4.3 - Height of buildings                    │
│                                                    │
│ [Export All] [Clear] [Generate Report]             │
└────────────────────────────────────────────────────┘

Export formats:
- Word document (with full text)
- Excel table (summary)
- PDF report (formatted)
- Plain text (copy/paste)
```

---

#### **5. Compliance Checklist (Assessment Mode)**

```
┌─ COMPLIANCE CHECKLIST ────────────────────────────┐
│ Dwelling House in R2 Zone                          │
│                                                    │
│ ✅ Permissibility: Permitted with consent          │
│ ✅ Height: 7.5m < 9m limit (complies)              │
│ ✅ FSR: 0.55:1 < 0.6:1 limit (complies)            │
│ ⚠️ Front Setback: 5.0m - verify matches street     │
│ ✅ Side Setback: 1.5m > 900mm minimum (complies)   │
│ ⚠️ Rear Setback: 3.5m - check solar access         │
│ ⏸️ Parking: Not assessed (enter space count)       │
│ ✅ Landscaping: 35% > 30% minimum (complies)       │
│ ❌ Heritage: NOT CHECKED - verify HCA status       │
│                                                    │
│ Progress: 6/9 complete                             │
│ Status: REQUIRES ATTENTION (3 items)               │
│                                                    │
│ [Export Checklist] [Mark Complete] [Save]         │
└────────────────────────────────────────────────────┘
```

**Addresses:** "Did I miss anything?" anxiety

---

#### **6. Version History Panel**

```
Hover over any provision → "🕐 Version History"

┌─ VERSION HISTORY: Section 4.2.4.3 ────────────────┐
│                                                    │
│ ● Current: March 2023 (IWLEP 2022 Amendment)      │
│   Changed: Side setback increased from 3m to 4m   │
│   Status: IN FORCE                                 │
│                                                    │
│ ○ Previous: September 2018 (Amendment No. 5)      │
│   Changed: Added driveway exemption (7m)          │
│   Status: Superseded                               │
│                                                    │
│ ○ Original: October 2011 (Adopted)                │
│   Original text: "Side setback: 3m minimum"       │
│   Status: Superseded                               │
│                                                    │
│ [View Full Amendment History] [Compare Versions]  │
└────────────────────────────────────────────────────┘
```

**Addresses:** Version control nightmare

---

#### **7. Related Provisions Auto-Linking**

```
Provision text with hyperlinks:

"Front setback should match existing street pattern
 (refer to [Section 2.3 - Site Context Analysis]) and
 maintain solar access to neighbouring properties
 (refer to [Section 2.7 - Solar Access])."

Click [Section 2.3] → Jump to that provision (split screen or replace)

Also shows:
┌─ RELATED PROVISIONS ───────────────────────────────┐
│ This provision references:                          │
│ • Section 2.3 - Site Context Analysis              │
│ • Section 2.7 - Solar Access                       │
│                                                    │
│ This provision is referenced by:                   │
│ • Section 4.1.8 - Building Design                  │
│ • Section 8.2 - Heritage Areas                     │
│                                                    │
│ SEPP overrides: None detected ✓                    │
└────────────────────────────────────────────────────┘
```

**Addresses:** No provision relationships

---

### **MOBILE DESIGN (Responsive)**

**On tablet/phone:**
- Sidebar collapses to hamburger menu
- Single column layout
- Swipe between modes
- Offline mode (cache provisions)
- Camera integration: "Measure setback"

---

## PART 3: IMPLEMENTATION PRIORITY

### **Phase 1: Core Layout (Week 1-2)**

**Build:**
1. Sidebar navigation component
2. Mode switching (Property, Browse, Research)
3. Persistent context (property stays selected)
4. Keyboard shortcuts

**Skip for now:**
- Compare mode (future)
- Split screen (future)
- Citation manager (future)

---

### **Phase 2: Enhance Assessment Mode (Week 3-4)**

**Build:**
1. Hybrid display (Primary/General/Conditional)
2. Version badges on provisions
3. Quick search (global)
4. Slide-out detail panel (already exists, enhance)

---

### **Phase 3: Build Browse Mode (Week 5-6)**

**Build:**
1. DCP table of contents
2. Section hierarchy navigation
3. Full provision view
4. Cross-references

---

### **Phase 4: Add Research Mode (Week 7-8)**

**Build:**
1. No-property zone explorer
2. Range displays
3. Saved scenarios
4. Link to assessment

---

### **Phase 5: Power User Features (Future)**

**Build:**
1. Split screen
2. Citation manager
3. Compliance checklist
4. Version history panel
5. Compare mode

---

## SUMMARY: ANSWER TO YOUR QUESTIONS

### **"Different routes or same page - how does best UI/UX look?"**

**Answer: SINGLE PAGE with sidebar navigation**

**Why:**
- ✅ Persistent context (property doesn't reset)
- ✅ Quick mode switching (one click)
- ✅ Professional feel (like IDE)
- ✅ Can do split screen later
- ✅ Keyboard shortcuts
- ✅ Deep linking still works (URL updates)

**NOT separate pages** because:
- ❌ Loses context
- ❌ Slower
- ❌ Can't split screen

**NOT tabs** because:
- ❌ Gets cluttered
- ❌ Wrong mental model

---

### **"Think of likely gaps/weaknesses in existing compliance apps"**

**Top 10 Gaps (All Addressed by Our Design):**

1. ✅ **Manual cross-referencing** → Single screen, automatic SEPP/LEP/DCP linking
2. ✅ **"Did I miss anything?"** → Compliance checklist, completeness verification
3. ✅ **Version control nightmare** → Version badges, history panel, currency dates
4. ✅ **No provision relationships** → Auto-linked text, related provisions panel
5. ✅ **Can't search across docs** → Global search, cross-document results
6. ✅ **Tables unusable in PDFs** → Interactive tables, filter/sort/export
7. ✅ **No comparison tool** → Compare mode, side-by-side scenarios
8. ✅ **Hidden requirements (HCA)** → Automatic detection, highlighted sections
9. ✅ **No mobile access** → Responsive design, offline mode
10. ✅ **Citation formatting** → Copy citation button, multiple formats

---

### **"We could always create simplified UX for novices, laypeople"**

**Agree** - Focus on professionals first because:
1. Professionals = paying customers
2. Professionals = high-value features
3. Novice UX = subset of professional UX (hide features, not rebuild)
4. Get professional UX right first, then simplify

**Later: "Novice Mode" toggle:**
- Hide Browse/Research/Compare modes
- Show only Assessment mode
- Add wizard: "Answer questions → get answer"
- Plain language explanations
- Visual examples

---

## NEXT STEP

**Start with Phase 1:** Build sidebar navigation + mode switching?

Or do you want to refine the design first?
