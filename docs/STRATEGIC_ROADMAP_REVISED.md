# PlotDetect Strategic Roadmap - REVISED
**Date:** 2026-02-06
**Context:** Post-competitive analysis + assuming Opus 4.6/Codex 5.2 commoditize "easy" moats

---

## Critical Reality Check

### What I Got Wrong

**Original thesis:** "Build spatial compliance engine with 3D envelopes, solar analysis, provision database"

**Problem:** Archistar already does this ($22.7M funding, 130k users, since 2010):
- ✅ 3D compliance envelope visualization
- ✅ 90+ automated compliance checks in 90 seconds
- ✅ Shadow diagram generation
- ✅ Site finder and feasibility analysis
- ✅ Generative AI and ML
- ✅ Government partnerships (25+ municipalities)
- ✅ BIM/CAD format acceptance

**Additional problems:**
- PropCode: Complete NSW LEP/DCP digitization (3M properties)
- canibuild: Real-Time 3D, granny flat dominance
- Zoneomics + Autodesk Forma: AI-driven envelopes integrated into Revit
- Free government portals: NSW Planning Portal spatial viewer

**Opus 4.6/Codex 5.2 implications:**
- Data curation (47,818 provisions) → AI can parse PDFs and extract this automatically
- Spatial rule encoding → AI can convert "setback 6m" to PostGIS queries
- Provision filtering → AI can do semantic search/matching
- 3D visualization → AI can generate geometry from text descriptions

**What's left that's defensible?**

---

## The Only True Blue Ocean: Heritage

### Why Heritage Impact Assessment is White Space

**Current state:** Completely manual, NO automation found in market
- Heritage consultancies: Artefact Heritage, Trace Enterprises, Context, Curio Projects, GML Heritage
- Tools: GIS for mapping, laser scanning for 3D, but ZERO automated compliance
- Process: Manual site visits, archival research, DA outcome case studies, written reports (3-10 days, $3k-15k)

**Why NO ONE has automated this:**

1. **Subjective judgment required**:
   - "Compatible with heritage character" - what does this mean?
   - Requires understanding conservation management plans, curtilage, significance assessments
   - Case law interpretation (Land & Environment Court decisions)

2. **Multiple regulatory layers**:
   - State heritage items (NSW Heritage Act)
   - Local heritage items (LEP schedules)
   - Heritage Conservation Areas (DCP character statements)
   - Aboriginal heritage (AHIMS database, field surveys)
   - Archaeological potential (predictive modeling)

3. **Cultural/historical context**:
   - Federation cottage vs Victorian terrace vs Inter-War flat - different considerations
   - Contributory vs non-contributory items in HCAs
   - View corridors to heritage landmarks (e.g., church spires, civic buildings)
   - Cumulative impact (multiple developments over time)

4. **Field work required**:
   - Aboriginal heritage: Can't automate site surveys, LALC consultation
   - Archaeological potential: Requires physical investigation
   - Structural assessment of existing heritage fabric

**Why this resists AI commoditization:**

- Opus 4.6 can't do field surveys
- Opus 4.6 can't interpret "heritage character" without training data (no labeled dataset exists)
- Opus 4.6 can't understand cultural significance without Indigenous knowledge holders
- DA outcome prediction for heritage is sparse data problem (few heritage DAs compared to standard residential)

**Market size:**
- ~42,000 heritage items in NSW (state + local)
- ~800 Heritage Conservation Areas
- Every DA within/adjacent to heritage requires Heritage Impact Statement or SOHI
- Inner West councils: 30-40% of DAs have heritage component
- Current spend: $3k-15k per SOHI × thousands of DAs per year = $10M+ market just NSW

---

## Revised Strategic Thesis

**PlotDetect should become the "Heritage Compliance Intelligence Platform"**

### Core Insight

Heritage compliance is the ONLY planning domain where:
1. No automated solution exists (Archistar doesn't touch it)
2. Regulatory requirement (can't skip it)
3. High complexity (resists simple AI automation)
4. Requires hybrid AI + human expert model
5. Data moat buildable (no one has digitized heritage provisions, Area Character Statements, conservation management plans)

### What This Means

**DON'T build:**
- ❌ Generic 3D building envelopes (Archistar does this)
- ❌ General compliance checking (Archistar, PropCode, canibuild)
- ❌ Site finder (Archistar, Stash, PropHero)
- ❌ Solar/shadow analysis (Pylon, Shadowmap, Spacemaker)
- ❌ BIM plugins (Autodesk ecosystem too strong)

**DO build:**
- ✅ Heritage provision database (DCP heritage chapters, Area Character Statements, conservation plans)
- ✅ Heritage compliance checker (alignment with contributory elements, materials, scale, form)
- ✅ Heritage impact report generator (automated SOHI first draft with LLM + expert review)
- ✅ Aboriginal heritage proximity checker (AHIMS integration, LALC consultation workflows)
- ✅ Heritage DA outcome prediction (train on heritage-specific DA approvals/refusals)
- ✅ Council heritage planner co-pilot (assist with s4.15(1)(c) heritage assessment)

---

## Heritage Compliance Intelligence Platform: Detailed Spec

### Phase 1 (6-12 months): Heritage Data Foundation

#### 1.1 Heritage Provision Database
**What:** Digitize ALL heritage provisions across Inner West councils

**Data sources:**
- DCP heritage chapters (Part C controls for HCAs, heritage item controls)
- Area Character Statements (1-2 pages per HCA describing key features)
- Conservation Management Plans for significant items
- Heritage Inventory Sheets (description, significance, curtilage, key features)
- LEP heritage schedules (5.10 clauses)

**Structured extraction:**
```
heritage_provisions:
  - provision_id
  - hca_slug (C1, C2, C95, etc.)
  - heritage_item_number (I001, I002, etc.)
  - provision_type (character, materials, form, scale, additions, demolition)
  - provision_text (exact wording)
  - significance_level (state, local, contributory, non-contributory)
  - key_elements (["federation detailing", "hipped roof", "timber joinery"])
  - pdf_page
  - photo_reference_url
```

**Why this is defensible:**
- Requires domain expertise to parse (what's actionable vs background?)
- Area Character Statements are NARRATIVE text (hard to structure)
- Photos must be linked to specific provisions
- Opus 4.6 could help but still needs human heritage expert validation

**Volume estimate:**
- Inner West: ~800 heritage provisions (306 already extracted for general category, but need HCA-specific refinement)
- Add Area Character Statements: ~30 HCAs × 5 key features each = 150 structured elements
- Add Heritage Inventory Sheets: ~500 local items × 10 key features = 5,000 structured elements
- **Total: ~6,000 structured heritage data points**

#### 1.2 Aboriginal Heritage Integration
**What:** AHIMS database integration + LALC consultation workflow

**Data sources:**
- AHIMS (Aboriginal Heritage Information Management System) - NSW government API
- LALC boundaries (Metropolitan, Deerubbin, Gandangara LAs cover Inner West)
- Due diligence code of practice requirements

**Features:**
- Automated AHIMS search by address (check for registered sites within 200m)
- LALC notification workflow ("Your DA at 35 Albert St requires Deerubbin LALC consultation")
- Due diligence assessment checklist generator

**Why this is defensible:**
- AHIMS API integration requires government data agreement
- LALC consultation is relationship-based (software can't automate relationships)
- Due diligence process is legally prescribed (Opus 4.6 can't make up regulatory requirements)

#### 1.3 Heritage DA Outcome Dataset
**What:** Scrape and label 5,000+ heritage DAs across Inner West

**Data to collect:**
- DA number, address, description, heritage item/HCA reference
- Proposal type (addition, alteration, demolition, new building)
- Heritage provisions cited in assessment
- Heritage objections (if any)
- Outcome (approved/refused/modified)
- Refusal reasons (if heritage-related)
- Conditions of consent (heritage-specific)

**Labeling schema:**
```
heritage_da_outcomes:
  - da_number
  - address
  - heritage_item_number
  - hca_slug
  - proposal_type
  - heritage_compliance_score (0.0-1.0, calculated from provisions met)
  - outcome (approved/refused)
  - refusal_reasons_heritage (bool)
  - key_issues (["scale", "materials", "facade_retention"])
  - approval_probability_factors
```

**Why this is defensible:**
- Manual collection takes months (scraping council registers + manual review)
- Labeling requires heritage domain expertise ("was this refused for heritage or other reasons?")
- Network effect: More DAs collected → better prediction models
- Opus 4.6 can help scrape but can't label without ground truth training

**Target:** 5,000 heritage DAs across Ashfield, Leichhardt, Marrickville (2015-2025)

### Phase 2 (12-24 months): Heritage Compliance Checker

#### 2.1 Heritage Provision Matching
**What:** Given address + proposed works → match applicable heritage provisions

**Algorithm:**
1. Check if address is heritage item (I001) or within HCA (C95)
2. If heritage item: Load Heritage Inventory Sheet provisions
3. If HCA: Load Area Character Statement + general HCA provisions
4. If adjacent to heritage (within 50m): Load view corridor, curtilage, setting provisions
5. Return matched provisions with relevance scores

**Example output:**
```
Address: 10 Railway Parade, Summer Hill NSW 2130
Heritage context:
  - Within HCA C95 (Railway Parade Heritage Conservation Area)
  - Adjacent to Heritage Item I045 (Railway station, State significant)

Applicable provisions (18 matched):
  [HIGH RELEVANCE]
  - Roof: "Hipped or gabled roofs of 25-35 degree pitch typical"
  - Materials: "Face brick or rendered masonry with timber joinery"
  - Additions: "Setback upper storey additions 3m from primary facade"
  - Scale: "Maximum 2 storeys, consistent with streetscape rhythm"

  [MEDIUM RELEVANCE]
  - Fencing: "Timber picket or low masonry, max 1.2m height"
  - Landscaping: "Retain mature canopy trees where possible"

  [ADJACENT HERITAGE]
  - View corridor: "Avoid obstruction of sightlines to railway station clock tower from Railway Pde intersection"
  - Curtilage: "Minimize visual impact on setting of State heritage item"
```

**Why this is defensible:**
- Requires understanding of "applicable" (not just keyword matching)
- Curtilage and setting are spatial concepts (requires GIS + domain knowledge)
- Relevance scoring based on DA outcome analysis (learned from Phase 1 dataset)

#### 2.2 Heritage Design Upload & Assessment
**What:** Upload proposed design (DXF/photos/Revit) → heritage compliance report

**Workflow:**
1. User uploads:
   - Site plan (DXF/GeoJSON)
   - Elevations (PDF/images/DXF)
   - 3D model (optional, IFC/SketchUp)
   - Proposal description (text, e.g., "Two-storey rear addition, retain front facade")

2. PlotDetect extracts:
   - Building footprint (from site plan)
   - Materials (from description or BIM attributes)
   - Height/scale (from elevations or 3D model)
   - Facade changes (from elevations)

3. Test against heritage provisions:
   - **Roof form:** Extract roof type from model/elevations, compare to "hipped/gabled 25-35°"
   - **Materials:** Extract material list, compare to "face brick/rendered masonry with timber joinery"
   - **Scale:** Extract height, compare to "2 storey maximum"
   - **Setback additions:** Calculate setback of upper storey from primary facade, compare to "3m setback"
   - **View corridors:** Generate 3D viewshed from heritage item viewpoint, check if proposed building intrudes

4. Generate compliance matrix:
   ```
   Heritage Compliance Assessment:

   ✅ Roof form: Hipped roof at 30° pitch (COMPLIES with 25-35° requirement)
   ✅ Materials: Face brick with timber windows (COMPLIES with heritage character)
   ❌ Scale: Upper storey setback 1.8m (FAILS - min 3m required)
   ⚠️  View corridor: Proposed roofline partially obstructs view to railway station clock tower (POTENTIAL ISSUE)

   Recommendations:
   - Increase upper storey setback from 1.8m to 3m (move 1.2m further back)
   - Consider lowering roofline by 0.5m to reduce view corridor impact
   - Maintain face brick materiality (compliant with Area Character Statement)
   ```

5. Generate SOHI first draft (LLM-assisted):
   ```
   Statement of Heritage Impact - DRAFT

   1. Heritage Context
   The subject site at 10 Railway Parade, Summer Hill is located within Heritage
   Conservation Area C95 and is adjacent to Summer Hill Railway Station (I045), a State
   significant heritage item. The Area Character Statement identifies Federation-era
   detailing, hipped roofs, and face brick construction as key contributory elements.

   2. Proposed Works
   [Auto-generated from proposal description]

   3. Heritage Impact Assessment
   The proposed two-storey rear addition demonstrates heritage sensitivity through:
   - Retention of the primary Federation facade (POSITIVE)
   - Use of face brick and timber joinery consistent with character (POSITIVE)
   - Hipped roof form at 30° pitch (COMPLIANT)

   However, the following impacts require consideration:
   - Upper storey setback of 1.8m is below the 3m minimum recommended in DCP (NON-COMPLIANT)
   - Proposed roofline may partially obstruct views to the railway station clock tower
     from the Railway Parade/Station Street intersection (POTENTIAL IMPACT)

   4. Mitigation Measures
   - Increase upper storey setback to 3m to minimize visibility from street
   - Consider lowering roofline by 0.5m to reduce view corridor impact

   5. Conclusion
   Subject to the recommended modifications, the proposed development is considered
   compatible with the heritage significance of the Conservation Area and the setting
   of the adjacent State heritage item.

   [This is a draft assessment generated by PlotDetect Heritage Intelligence.
    Final SOHI must be prepared by qualified heritage consultant.]
   ```

**Why this is defensible:**
- Requires multi-modal analysis (site plan + elevations + 3D + text)
- "Compatibility with heritage character" is subjective judgment (AI can assist but needs expert validation)
- View corridor analysis requires GIS viewshed + understanding of "significant views"
- SOHI draft generation is value-add but explicitly requires human expert review (regulatory/liability constraint)

**Target users:**
- Heritage consultants: Use PlotDetect to generate first draft (3 hours → 30 minutes), then expert review/finalize
- Architects: Pre-check heritage compliance before engaging consultant
- Town planners: Quick feasibility assessment ("will this need major redesign?")

#### 2.3 Heritage Impact Visualization
**What:** 3D visualization of proposed design in heritage context

**Features:**
- Load heritage HCA boundary and heritage item locations
- Load existing 3D building context (from Planning Portal or infer from cadastre + typical heights)
- Overlay proposed design 3D mesh (from IFC/SketchUp/generated from elevations)
- Highlight heritage items in red, HCA boundary in yellow, proposed in blue (semi-transparent)
- Generate before/after comparison images
- Generate view corridor diagrams (viewshed from significant viewpoints)

**Technical stack:**
- CesiumJS for 3D web rendering
- PostGIS ST_3DDistance for view corridor analysis
- Heritage item photos overlaid as billboards in 3D scene

**Why this is defensible:**
- Heritage-specific 3D visualization (not generic building envelope like Archistar)
- View corridor analysis requires heritage domain knowledge (which viewpoints matter?)
- Before/after comparison tailored for SOHI inclusion

### Phase 3 (24-36 months): Heritage Intelligence & Prediction

#### 3.1 Heritage DA Approval Predictor
**What:** Predict approval probability for heritage DAs based on Phase 1 dataset

**Model:**
- Training data: 5,000 heritage DAs with outcomes
- Features:
  - heritage_compliance_score (provisions met %)
  - scale_ratio (proposed_height / typical_hca_height)
  - facade_retention (bool)
  - materials_match (bool)
  - setback_compliance (bool)
  - view_corridor_impact (bool)
  - objections_count
  - council (Ashfield vs Leichhardt vs Marrickville - different tolerance)
  - heritage_significance (state vs local vs contributory)
  - proposal_type (addition vs new building vs demolition)

- Target: approved (1) or refused (0)

**Output:**
```
Heritage DA Approval Probability: 68%

Risk factors:
- Upper storey setback non-compliance (-18% approval probability)
- View corridor impact to State heritage item (-12% probability)

Mitigation:
- Increase setback to 3m → probability increases to 82%
- Lower roofline 0.5m → probability increases to 79%
- Both changes → probability increases to 91%

Based on 287 similar Federation-era HCA addition DAs in Inner West (2015-2025)
```

**Why this is defensible:**
- Heritage-specific prediction model (not generic like Archistar might build)
- Training data is expensive to collect (5,000 DAs manually labeled)
- Network effect: More predictions made → more outcome data collected → better model
- Heritage context features are domain-specific (facade_retention, materials_match)

#### 3.2 Heritage Council Planner Co-Pilot
**What:** Assist council heritage planners with s4.15(1)(c) assessment

**Use case:**
- Council planner receives DA for heritage property
- Uploads DA docs to PlotDetect (or PlotDetect auto-scrapes from ePlanning)
- PlotDetect generates draft heritage assessment:
  - Applicable heritage provisions (auto-matched)
  - Compliance matrix (auto-checked)
  - Similar DA precedents ("Approved DA D123/2019 at 12 Railway Pde had similar upper storey setback")
  - Draft s4.15(1)(c) heritage impact section

**Why councils would pay for this:**
- Reduces planner time (30 min vs 2 hours per heritage DA)
- Standardizes heritage assessment (consistent provision application)
- Provides precedent case law/DA support (defensible decisions)
- Reduces refusal risk (identify issues before approval)

**Business model:**
- White-label for councils (like Archistar's Digital Twin Victoria partnership)
- Subscription: $5k-15k per month per council (based on DA volume)
- Revenue share: 20% of efficiency savings

**Why this is defensible:**
- Requires council partnership (relationship moat)
- Requires integration with council ePlanning systems (technical moat)
- Requires trust-building (councils won't adopt untested tools - first-mover advantage)

#### 3.3 Heritage Change Detection
**What:** Monitor heritage areas for unauthorized works using satellite/aerial imagery + AI

**Process:**
1. Baseline: Nearmap aerial imagery of all heritage items/HCAs (2024)
2. Monitor: Quarterly aerial imagery updates
3. Detect changes: SAMGeo (Segment Anything Model for Geospatial) detects:
   - New building footprints
   - Roof color/material changes
   - Tree removal
   - Facade alterations (if resolution sufficient)
4. Alert council: "Potential unauthorized works at 10 Railway Parade (HCA C95)"
5. Council investigates: Site visit or request DA docs

**Why councils would pay for this:**
- Enforcement cost reduction (proactive vs reactive)
- Heritage protection (detect unauthorized demolition before completion)
- Compliance culture (property owners know they're monitored)

**Business model:**
- Per-LGA subscription: $2k-5k per month
- Alert volume-based: $50 per verified alert

**Why this is defensible:**
- SAMGeo is open source but heritage-specific training is unique
- Requires Nearmap subscription ($10k+ per year) - cost barrier
- Requires council relationship (no other customer for this data)

---

## Defensibility Analysis (Post-Opus 4.6)

### What Opus 4.6 CAN'T Easily Replicate

#### 1. Heritage Training Data (⭐⭐⭐⭐⭐)
- 5,000 heritage DAs with labeled outcomes → months of manual collection
- Area Character Statements structured → requires domain expertise to parse narrative
- Heritage Inventory Sheets linked to provisions → manual photography + matching
- DA refusal reasons labeled → "was this heritage or other?" requires human judgment

**Why defensible:** Data doesn't exist in structured form; must be created/labeled by humans with heritage expertise

#### 2. Heritage DA Outcome Prediction (⭐⭐⭐⭐⭐)
- Model trained on PlotDetect's unique dataset
- Network effect: Every DA predicted → outcome collected → model improves
- First-mover advantage: If PlotDetect has 5,000 DAs and competitor has 0, 2-year head start

**Why defensible:** Network effects compound; ground truth validation requires real-world DAs

#### 3. Council Partnerships (⭐⭐⭐⭐⭐)
- White-label council co-pilot requires trust (relationship moat)
- Integration with ePlanning systems (technical + partnership moat)
- Certification/endorsement creates regulatory barrier

**Why defensible:** Councils won't adopt unproven tools; first-mover advantage huge

#### 4. Heritage Change Detection (⭐⭐⭐⭐)
- SAMGeo training on heritage-specific features (roof colors, facade styles)
- Nearmap subscription cost ($10k/year) + processing infrastructure
- Council partnership (no other customer for this data)

**Why defensible:** Infrastructure cost + niche application + council relationship

#### 5. Subjective Heritage Judgment (⭐⭐⭐⭐)
- "Compatible with heritage character" requires case law understanding
- Opus 4.6 can draft SOHI but can't sign off (liability requires human expert)
- Cultural significance (Indigenous heritage) requires knowledge holder consultation

**Why defensible:** Regulatory/liability constraint; AI can assist but can't replace expert

### What Opus 4.6 CAN Replicate

#### ❌ Heritage Provision Extraction
- Opus 4.6 could parse DCP heritage chapters automatically
- Area Character Statements could be extracted with LLM prompting
- No moat here unless PlotDetect structures/labels first

**Mitigation:** Extract and structure ALL Inner West heritage data immediately (6-month sprint)

#### ❌ Heritage Provision Matching
- Given structured provisions, Opus 4.6 can do semantic matching
- "Which provisions apply to this address?" is solvable with RAG

**Mitigation:** Add DA outcome validation (Opus can match, but PlotDetect knows which provisions actually matter for approval)

#### ⚠️ 3D Heritage Visualization
- CesiumJS is open source; Opus 4.6 could generate 3D scene code
- Heritage context layer could be auto-generated from spatial data

**Mitigation:** Differentiate on heritage-specific UI (view corridor diagrams, before/after, SOHI-ready exports)

---

## Business Model: Heritage-First Strategy

### Phase 1 (0-12 months): Heritage Consultancy Augmentation

**Target customers:** Heritage consultants (50-100 firms in NSW)

**Product:** "Heritage SOHI Assistant"
- Upload DA details → auto-generate SOHI first draft (3 hours → 30 min)
- Heritage provision matching
- Compliance matrix
- Draft written assessment

**Pricing:** $199/month per consultant (unlimited SOHIs)

**Revenue target:** 30 consultants × $199 × 12 = $71,640 Year 1

**Why consultants will pay:**
- Time savings: 2.5 hours per SOHI × 10 SOHIs/month = 25 hours saved
- Consultant hourly rate: $150/hour → $3,750 value per month
- Price: $199 (5% of value saved)
- Reduces junior staff time (SOHI drafts typically done by grads)

**Sales strategy:**
- Direct outreach to heritage firms (50 target list)
- Case study: "Artefact Heritage saves 25 hours/month with PlotDetect"
- Industry association: Australian Association of Consulting Archaeologists (AACA)

### Phase 2 (12-24 months): Architect/Developer Self-Service

**Target customers:** Architects and developers doing heritage DAs

**Product:** "Heritage Pre-Check"
- Upload design → heritage compliance report
- Identify issues before engaging consultant
- Avoid costly redesign after consultant review

**Pricing:** $49 per assessment (pay-per-use)

**Revenue target:** 200 assessments/month × $49 = $9,800/month = $117,600 Year 2

**Why architects will pay:**
- Heritage consultant quote: $3k-15k for SOHI
- If PlotDetect identifies major issue ($49), avoid wasting $3k on consultant for non-viable design
- ROI: 60:1 value-to-price ratio

**Marketing:**
- Content: "5 Heritage Compliance Mistakes That Cost Architects $50k"
- Case study: "Architect redesigns before engaging consultant, saves $8k"

### Phase 3 (24-36 months): Council Co-Pilot (White-Label)

**Target customers:** Councils with high heritage DA volume

**Product:** "Heritage Planning Co-Pilot"
- Auto-generate draft s4.15(1)(c) heritage assessment
- Precedent DA matching
- Standardized heritage provision application

**Pricing:** $10k/month per council (annual contract)

**Revenue target:** 3 councils × $10k × 12 = $360k Year 3

**Why councils will pay:**
- Planner cost: $80k salary → 2,000 hours/year → $40/hour
- Heritage DA time reduction: 1.5 hours saved per DA
- Heritage DA volume: 200/year per council
- Savings: 200 × 1.5 × $40 = $12,000 per year
- Price: $10k (breakeven in first year, profitable thereafter)
- Additional benefits: Standardization, precedent support, reduced refusal risk

**Sales strategy:**
- Pilot: Free 3-month trial with Inner West Council (leverage existing relationship)
- Case study: "Inner West Council processes heritage DAs 40% faster"
- Expand: City of Sydney, Bayside, Canada Bay, Woollahra (high heritage LGAs)

### Year 3 Revenue Projection

- Heritage consultants: 50 × $199 × 12 = $119,400
- Architect pre-checks: 300 × $49 × 12 = $176,400
- Council co-pilot: 3 × $10k × 12 = $360,000
- **Total: $655,800 ARR** (vs $281k in original roadmap, but focused on defensible niche)

---

## Competitive Moat Summary

### Heritage-First Strategy Moats

| Moat | Strength | Replicability (Opus 4.6) | Time to Replicate |
|---|---|---|---|
| Heritage DA outcome dataset (5k DAs) | ⭐⭐⭐⭐⭐ | Can't scrape/label without humans | 12-18 months |
| Heritage provision database (structured) | ⭐⭐⭐ | Could auto-extract with LLM | 3-6 months |
| Council partnerships (white-label) | ⭐⭐⭐⭐⭐ | Can't replicate relationships | 2-3 years |
| Heritage DA predictor (trained model) | ⭐⭐⭐⭐⭐ | Requires training data | 18-24 months |
| Heritage change detection (SAMGeo) | ⭐⭐⭐⭐ | Could build with open source | 6-12 months |
| Heritage consultancy network | ⭐⭐⭐⭐ | Can't replicate trust/adoption | 1-2 years |
| Subjective heritage judgment | ⭐⭐⭐⭐ | AI assists but can't replace | Not replicable |

**Average moat strength: 4.3/5** (vs 3.2/5 for original generic compliance strategy)

**Time for well-funded competitor to replicate: 2-3 years** (vs 6-12 months for generic compliance)

---

## Why This Beats Archistar

### Archistar's Weaknesses

1. **Horizontal play:** Trying to serve all development types (residential, commercial, industrial)
2. **Generic compliance:** 90+ checks but not deep in any domain
3. **No heritage focus:** Heritage is ~5% of their market, not core product
4. **Enterprise focus:** Targeting large developers, not consultancies

### PlotDetect's Vertical Play

1. **Heritage specialist:** Only player automating heritage compliance
2. **Consultancy model:** Augment heritage consultants (they won't adopt Archistar because it's competitor-built)
3. **Council partnership:** White-label co-pilot (Archistar does this generally, but PlotDetect does heritage specifically)
4. **Aboriginal heritage:** Unique capability (AHIMS integration, LALC workflows)

### Market Positioning

**Archistar:** "We do everything for everyone" (horizontal)
**PlotDetect:** "We do heritage better than anyone" (vertical)

**Analogy:**
- Archistar = Salesforce (general CRM)
- PlotDetect = Veeva (pharma-specific CRM that beats Salesforce in pharma)

**Strategy:** Own heritage compliance (20-30% of Inner West DAs), then expand to other complex domains (Aboriginal heritage, contaminated land, acid sulfate soils, biodiversity)

---

## Implementation Roadmap

### Q1 2026 (NOW → +3 months): Heritage Data Sprint

**Goal:** Structure ALL Inner West heritage data before competitors

**Deliverables:**
- [ ] Heritage provision database: 6,000 structured elements (DCP chapters, Area Character Statements, Inventory Sheets)
- [ ] Heritage spatial layers: HCA boundaries, heritage item points, view corridors, curtilage polygons
- [ ] Heritage photo library: 500 heritage items with facade/detail photos
- [ ] AHIMS integration: API connection + LALC boundary mapping

**Team:**
- 1 heritage consultant (contract, 3 months): $15k
- 1 data engineer: Existing PlotDetect dev
- 1 GIS specialist (contract, 1 month): $8k

**Budget:** $23k

### Q2 2026 (+4-6 months): Heritage SOHI Assistant MVP

**Goal:** Launch heritage consultancy product, acquire 10 paying customers

**Deliverables:**
- [ ] Heritage provision matching API
- [ ] SOHI first draft generator (LLM-based)
- [ ] Compliance matrix generator
- [ ] Web UI: Upload DA details → download SOHI draft
- [ ] Sales: Outreach to 50 heritage consultancies, acquire 10 customers

**Revenue:** 10 × $199 × 3 months = $5,970 (Q2 only)

### Q3 2026 (+7-9 months): Heritage Design Upload

**Goal:** Add design upload + compliance checking

**Deliverables:**
- [ ] DXF parser for site plans
- [ ] Elevation image analysis (extract roof form, materials, scale)
- [ ] Heritage compliance checker (roof, materials, scale, setbacks)
- [ ] 3D heritage context visualization (CesiumJS with heritage items)
- [ ] Architect self-service product launch

**Revenue:** 30 consultants × $199 × 3 = $17,910 + 50 architect assessments × $49 = $2,450 (Q3 only)

### Q4 2026 (+10-12 months): Heritage DA Outcome Dataset

**Goal:** Collect and label 2,000 heritage DAs

**Deliverables:**
- [ ] Web scraper: Ashfield, Leichhardt, Marrickville DA registers
- [ ] Manual labeling: Heritage DAs identified, outcomes labeled, provisions extracted
- [ ] Predictive model V1: Train on 2,000 DAs (baseline accuracy target: 65%)
- [ ] Heritage approval predictor product launch

**Revenue:** 50 consultants × $199 × 3 = $29,850 + 100 assessments × $49 = $4,900 (Q4 only)

**Year 1 Total Revenue:** $60,630 (vs target $71,640 - on track)

### Year 2 (Months 13-24): Scale + Council Pilot

**Q1 2027:**
- Heritage DA dataset: 5,000 DAs (3,000 more collected)
- Predictive model V2: 75% accuracy
- Aboriginal heritage module launch (AHIMS + LALC workflows)

**Q2 2027:**
- Council pilot: Inner West Council 3-month free trial
- Heritage Planning Co-Pilot MVP
- s4.15(1)(c) draft generator

**Q3 2027:**
- Council pilot results: "40% time reduction" case study
- Council sales: Outreach to 10 high-heritage councils
- Heritage change detection MVP (SAMGeo + Nearmap)

**Q4 2027:**
- Council customer #1: Inner West Council paid contract ($10k/month)
- Council customer #2: Woollahra Council pilot → paid
- Heritage consultancy customers: 75 (from 50 in Year 1)

**Year 2 Revenue:** $119,400 (consultants) + $58,800 (assessments) + $60,000 (councils 6 months) = $238,200

### Year 3 (Months 25-36): Expand Councils + New Verticals

**Q1-Q2 2028:**
- Council customers: 5 councils (Inner West, Woollahra, City of Sydney, Bayside, Canada Bay)
- Heritage consultancy: 100 customers
- Architect assessments: 400/month

**Q3-Q4 2028:**
- New vertical: Aboriginal heritage (separate product, $299/month for consultants)
- New vertical: Contaminated land compliance (partner with environmental consultants)
- Heritage change detection: 3 councils subscribed ($5k/month each)

**Year 3 Revenue:** $655,800 (as projected above)

---

## Risk Mitigation

### Risk 1: Heritage consultants see PlotDetect as competitor

**Mitigation:**
- Position as "augmentation" not "replacement"
- Explicitly state "final SOHI must be signed by qualified consultant"
- Revenue share: "Consultants using PlotDetect can take on 30% more projects"
- Freemium: First 5 SOHIs free (try before buy)

### Risk 2: Councils reluctant to adopt unproven tool

**Mitigation:**
- Free pilot with Inner West Council (leverage existing relationship)
- Publish case study: "40% time reduction" + "standardized assessments"
- Offer 6-month money-back guarantee
- Industry endorsement: Australian Institute of Architects, Planning Institute Australia

### Risk 3: Heritage DA dataset collection too slow

**Mitigation:**
- Hire 2 part-time heritage grads ($30/hour) to manually label DAs
- Use Opus 4 to assist with scraping (can speed up but not fully automate)
- Start with high-value subset: 1,000 DAs in high-heritage councils first

### Risk 4: Archistar notices and adds heritage module

**Mitigation:**
- Speed: Launch heritage product in 6 months (before Archistar can pivot)
- Consultancy relationships: Build network Archistar can't access (they're seen as competitor)
- Council partnerships: Lock in 3 councils Year 2 (switching cost)
- Data moat: 5,000 heritage DAs collected by Year 2 (Archistar would start from 0)

### Risk 5: Opus 4.6 makes heritage SOHI generation trivial

**Mitigation:**
- Accept this risk: If Opus 4.6 can generate perfect SOHIs, heritage consultants' value proposition changes
- Pivot: Become "heritage consultant co-pilot" rather than "SOHI generator"
- Focus on council partnerships: AI can't replace regulatory relationships
- Embrace AI: Use Opus 4.6 API to improve PlotDetect's SOHI quality

---

## Success Metrics

### Product Metrics

**Year 1:**
- Heritage provisions structured: 6,000 elements
- Heritage consultancy customers: 30
- SOHI drafts generated: 300
- Consultant time saved: 750 hours (300 × 2.5 hours)
- Net Promoter Score: >60

**Year 2:**
- Heritage DA dataset: 5,000 DAs labeled
- Heritage consultancy customers: 75
- Architect assessments: 600
- Council pilots: 2 (1 paid)
- Predictive model accuracy: 75%

**Year 3:**
- Council customers: 5 (paid)
- Heritage consultancy customers: 100
- Architect assessments: 3,600/year
- Heritage change detection: 3 councils
- Aboriginal heritage module: 20 customers

### Business Metrics

**Revenue:**
- Year 1: $60k ARR (consultants only)
- Year 2: $238k ARR (consultants + assessments + councils)
- Year 3: $656k ARR (all products)

**Customer Acquisition:**
- Year 1: 30 consultants
- Year 2: 75 consultants, 600 assessments, 2 councils
- Year 3: 100 consultants, 3,600 assessments, 5 councils, 20 Aboriginal heritage

**Market Penetration:**
- Year 1: 30% of Inner West heritage consultancies
- Year 2: 60% of Inner West, 20% of Sydney metro
- Year 3: 80% of Inner West, 40% of Sydney metro, expanding to Melbourne/Brisbane

---

## Conclusion: The Defensible Heritage Moat

### Why Heritage (Not Generic Compliance)

**Generic compliance** (Archistar's territory):
- ✅ Lots of customers (everyone does development)
- ❌ Commoditized by AI (Opus 4.6 can parse rules)
- ❌ Competitive (Archistar, PropCode, canibuild, Zoneomics, Autodesk)
- ❌ Horizontal (hard to differentiate)

**Heritage compliance** (PlotDetect's territory):
- ⚠️ Smaller customer base (20-30% of DAs have heritage component)
- ✅ Resists AI commoditization (subjective judgment, sparse training data)
- ✅ No competition (no automated heritage compliance exists)
- ✅ Vertical (deep expertise creates moat)

### The Heritage Flywheel

1. **Structure heritage data** → Heritage consultants adopt PlotDetect
2. **Consultants use PlotDetect** → Collect more heritage DA outcomes
3. **More DA outcomes** → Train better predictive model
4. **Better predictions** → Attract architects/developers to use pre-check
5. **More pre-check usage** → More outcome data collected
6. **More data** → Council co-pilot becomes more accurate
7. **Council adoption** → Regulatory endorsement → More consultants adopt
8. **More consultants** → Network effects strengthen moat

### Time to Market Leadership

**PlotDetect advantage:**
- Heritage data sprint: 3 months (Q1 2026)
- Heritage consultancy product: 6 months (Q2 2026)
- Heritage DA dataset: 18 months (Q4 2027, 5,000 DAs)
- Council partnerships: 24 months (Q4 2027, 2 councils)

**Competitor timeline (starting from scratch):**
- Realize heritage opportunity: 6 months
- Structure heritage data: 6 months (3 months behind)
- Build heritage product: 6 months
- Acquire consultancy customers: 12 months (trust-building)
- Collect DA outcome data: 18 months
- Council partnerships: 24 months
- **Total: 48 months (4 years)**

**PlotDetect's lead time: 30 months** (by the time competitor launches, PlotDetect has 5,000 DA dataset + 75 consultancy customers + 2 council partnerships)

### The Answer to "What's Defensible Post-Opus 4.6?"

**Not defensible:**
- Data curation (AI can parse)
- Generic spatial rules (AI can encode)
- 3D visualization (open source + AI code generation)
- BIM integration (Autodesk ecosystem owns this)

**Defensible:**
- **Domain-specific training data** (heritage DAs with outcomes - doesn't exist, must be created)
- **Network effects** (more users → more outcome data → better predictions)
- **Regulatory relationships** (council partnerships take years to build)
- **Subjective expert judgment** (AI assists but can't replace - liability/regulatory constraint)
- **Vertical specialization** (Archistar won't pivot to heritage-only; PlotDetect owns the niche)

**PlotDetect becomes "Veeva for Heritage"** - vertical depth beats horizontal breadth.

---

*END OF REVISED STRATEGIC ROADMAP*
