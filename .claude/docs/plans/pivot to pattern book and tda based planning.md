I am pivoting the application from a 'Planning Document Navigator' to a 'Technical Pathway & Compliance Synthesis Engine.'

he NSW planning system has moved away from local councils making all the rules. The State government has created "fast lanes" (SEPPs) to get houses built quicker. However, these fast lanes have "toll booths" (Exclusions)—if a property has heritage, flood, or bushfire risks, you are kicked out of the fast lane and back into the slow, complex local council process (DCPs).Your app's new job is to be a GPS for Planning Approvals: it tells the user exactly which lane they are in and how to avoid the roadblocks.1. The Core Strategy: From "Mapping" to "Matching"The current app shows what the rules are. The new strategy identifies which approval pathway is fastest.Existing App: "Here is a list of heritage and height rules for 10 Smith St."New Pivot: "10 Smith St is ineligible for the 20-day fast track because of a heritage tree. You must use the 50-day 'Targeted Assessment' path. Here are the 3 specific rules you must now follow to pass."2. The Four Distinct Elements (The "GPS" Components)These are the new features that make the app a professional-grade tool rather than a simple map:The Exclusion Triage (The "Red Zone" Detector):Automatically scans a property for "SEPP-Killers" (Heritage, PMF Flooding, Bushfire BAL-40). It tells a certifier immediately if they can even use the fast-track rules.Split-Lot Geometry:Many lots are half-constrained. The app calculates the "Safe Build Zone." Example: "The front half of your lot is heritage-listed, but the back half is eligible for a fast-track Granny Flat."Pattern Book Matcher:The NSW Government released "Pattern Books" (pre-approved house designs). The app checks the lot's dimensions against these designs and says: "Pattern #4 fits here with 100% certainty for a 10-day approval."TAD Triage (Targeted Assessment):The 2025 reforms allow a 50-day approval for "low-risk" projects. The app acts as a filter to prove to the Council that a project is "low risk" by checking it against state criteria.3. Target Markets: Who Pays and Why?Market NichePain PointWhy they need the AppTown Planners & ArchitectsSpending 10+ hours researching 2,000-page PDFs for one site.Reduces research to 5 minutes; provides a "legal logic" for the client.Private CertifiersRisk of losing their license if they fast-track a project that was actually excluded.Provides a "Safe to Proceed" certificate based on spatial data."Missing Middle" DevelopersBuying a site thinking it's a "quick win" only to find a 12-month delay.Feasibility testing before buying the land.Specialist ConsultantsHeritage/Arborists need to show why their report is mandatory.Identifies the exact "Exclusion" that triggers their employment.4. Market Size & Pricing (NSW SaaS Model)Total Addressable Market (TAM) - NSW FocusArchitects: ~6,300 registered professionals.Town Planners: ~4,600 professionals.Private Certifiers: ~1,300 professionals.Monthly Approvals: ~16,500 new applications every month.Estimated TAM: Based on ~12,000 professional users in NSW alone, a SaaS model could target a $25M+ annual market in one state.Potential Pricing StructureProfessional tools in this space (like PropCode or Archistar) have validated these price points:Single Report ($99 + GST):One-off "Pathway Feasibility Report" for homeowners or small builders.Includes a list of every exclusion and the "best-case" approval path.Professional SaaS ($199 / month):For small planning/architecture firms.Includes 10 site lookups and full access to "Pattern Book Matching."Enterprise SaaS ($495+ / month):For developers and large certifier firms.Includes unlimited site finding, API access to the NSW Spatial Digital Twin, and bulk feasibility scanning.How it all fits togetherThe app becomes the Integrated Logic Layer. It pulls raw data from the NSW Planning Portal via APIs, applies the "Legal Logic" of the 2025 reforms (TOD, TAD, and Pattern Books), and outputs a Decision Scorecard.Professionals use it because it replaces the "mechanical drudgery" of checking maps, allowing them to focus on the "engineering judgment" that AI cannot yet do.

The Objective: Instead of just finding a rule, the app must synthesize data from SEPPs, LEPs, and DCPs to tell a user if they qualify for the 10-day Fast-Track (CDC) pathway or if they are forced into a traditional Council DA due to site constraints.

Task: Perform a structural analysis of the changes required for this pivot:

Pathway Triage Logic: How do we restructure the core logic to perform an 'Exclusion Check' first? (If site = Heritage/Flood/Bushfire, then Pathway = DA; Else, check CDC eligibility).

Numeric Metric Extraction: We need to move from storing provision text to extracting JSONB key-value pairs. What is the most efficient way to tag and extract 'Deep Soil %', 'Tree Canopy %', and 'Lot Width' from the Pattern Book and SEPPs to enable automated comparison?

Synthesis Engine Design: Analyze the requirement for a 'Setback & Parking Synthesis' workflow. This must combine Local DCP base rules with State SEPP overrides (like TOD parking reductions). How should the logic resolve these conflicting rules?

Pattern Matcher Integration: How can we build a comparison engine that takes 'Lot Geometry' (polygon data) and matches it against the 'Template Envelopes' in the NSW Housing Pattern Book?

UI/UX Re-Engineering: The current interface is a 'Compliance Table.' How should the UI be refactored to show a 'Pathway Status Bar' at the top, indicating eligibility and highlighting the specific 'blockers' (e.g., 'Ineligible: Frontage too narrow' or 'Ineligible: Heritage Overlay')?

Professional Safety Layer: How do we ensure that every synthesized calculation (e.g., 'Your required setback is 4.5m') maintains a deterministic link to the original PDF page and clause to ensure professional trust and auditability?

Please identify the primary structural bottlenecks in the current architecture that will hinder this shift from 'Search' to 'Synthesis'."

Strategic Analysis: The Conflict Between State Vision and Operational RealityThe New South Wales planning ecosystem is currently defined by a "territory war" between state-led industrialization and local regulatory friction . For the Plotdetect application, success depends on navigating the gap where government automation is legally unable to venture due to liability risks .1. Objective Analysis: Government Trajectory vs. Market RealityThe Government Narrative: Mass-Production PlanningThe DPHI is aiming for an "Industrialization of Planning".Goal: The state wants 75% of all proposals to bypass council merit-assessment through standardized checklists and pre-approved patterns .Centralization: The creation of the Development Coordination Authority (DCA) and Housing Delivery Authority (HDA) moves "yes/no" power away from local planners and into a "single front door" controlled by the state .The Competitor Risk: The government is building its own AI tools (AI Roadmap 2026) to suggest pathways and conduct QA on site plans . A generic "mapping" tool is at risk of being Sherlocked by free public portal features.The Oppositional Reality: The "Bifurcated" (Two-Tier) MarketThe state's vision of a frictionless pipeline will likely fracture due to three specific pressures:The Liability Gap: The NSW Planning Portal explicitly states its AI will not conduct "adequacy tests" or determine application outcomes . The state is terrified of being sued for "Computer Says Yes" errors on complex sites .The Economic Deadlock: Fast planning doesn't lower interest rates or construction costs, which currently sit between $3,200 and $4,300/sqm in Sydney . Many mid-rise projects are currently "negative feasibility" despite the new zoning uplift .The "Red Zone" Trap: Heritage items, flood zones, and high-risk bushfire land are strictly excluded from the fast-track SEPP rules . These constraints affect a massive percentage of high-value Inner West and growth corridor land .2. Exploiting Granular Resolution: Where the Moat ExistsThe assumption that granular DCP research will disappear is a trap. In the "High-Stakes Friction Zones" (Tier 2), DCPs will become more aggressive as councils use them to defend local character against state-led density .Profitability Strategies for Granular DataThe "Loophole" Engine: Government tools treat lots as binary (In/Out). Your app must find the "unconstrained merge." Under the Codes SEPP, if a heritage listing affects only the front house, the back half remains eligible for a 10-day fast track . Your moat is providing the Geometric Proof the government is legally afraid to provide.TAD Triage (Targeted Assessment): The new 50-day pathway requires proving "Upfront Compliance" . Your granular DCP engine can generate a "TAD Eligibility Scorecard" that proves to a council planner that a project's impacts are "likely but not significant" .Defensible Logic: Professionals won't pay for "AI data"; they pay for a Liability Shield. Your app should provide clickable citations (e.g., Inner West LEP 2022 Clause 5.10) for every check performed .3. Technical Roadmap for Codebase AdaptationAPI and Data IntegrityHAR-Gleaned APIs vs. Official Endpoints: Relying on public portal site APIs gleaned from HAR files is not recommended for a professional tool. These are unauthorized, brittle, and subject to change without notice .The Correct Path: You must secure a developer subscription key for the Online Section 10.7 Planning Certificate Service API and query the EPI Primary Planning Layers via ArcGIS REST endpoints for authoritative spatial geometry .Pivot Implementation ElementsGIS Geometry Engine: Move from text-based JSON reading to Geospatial Intersection. Use libraries like Shapely to subtract the heritage/hazard polygons from the property cadastre to find the Net Developable Area (NDA) .Pattern Matcher Logic: Compare the lot dimensions and NDA against the 2025 Housing Pattern Book criteria (e.g., 21m width for mid-rise patterns) .Refusal Predictor: Feed Land and Environment Court (LEC) precedent data into your engine to flag common reasons for refusal (e.g., "Overshadowing" in the Inner West) .4. Prompt for Codebase AdaptationUse the following prompt to instruct your technical team or AI to update the existing application logic:"Adapt the existing Plotdetect address-lookup engine to a Pathway Feasibility Engine using the following requirements:Data Sourcing: Transition from site-scraped APIs to the official NSW Planning Portal ArcGIS REST Services (MapServer Layers 0-6). Implement OAuth2 for the Online Section 10.7 API to retrieve authoritative property facts .Exclusion Logic: Implement a geospatial intersection module. If a property intersects with 'Item-General' or 'Conservation Area' polygons from the Heritage (HER) layer, calculate the remaining Net Developable Area (NDA). Do not return a binary 'IsHeritage' flag; return the specific square meterage of the unconstrained zone .Pathway Branching:Path A (CDC): If hazard/heritage = 0 AND lot width > 21m, flag as 'High-Probability 10-day CDC' .Path B (TAD): If lot has 'significant likely impacts' but meets strategic upfront codes, flag as '50-day Targeted Assessment' .Path C (DA): If in a 'Red Zone' exclusion, list the 5 specific local DCP design rules that must be met to pass merit assessment .Pattern Matching: Ingest the 2025 NSW Housing Pattern Book dimensions. Test the NDA against these patterns and provide a 3D-envelope visualization showing how Pattern #X fits within the lot setbacks.Output Requirement: Every result must include a Defensible Audit Trail—a list of clickable legislative citations for every SEPP, LEP, and DCP clause checked ."

4. Prompt for Codebase Adaptation
Use the following prompt to instruct your technical team or AI to update the existing application logic:

"Adapt the existing Plotdetect address-lookup engine to a Pathway Feasibility Engine using the following requirements:

Data Sourcing: Transition from site-scraped APIs to the official NSW Planning Portal ArcGIS REST Services (MapServer Layers 0-6). Implement OAuth2 for the Online Section 10.7 API to retrieve authoritative property facts .

Exclusion Logic: Implement a geospatial intersection module. If a property intersects with 'Item-General' or 'Conservation Area' polygons from the Heritage (HER) layer, calculate the remaining Net Developable Area (NDA). Do not return a binary 'IsHeritage' flag; return the specific square meterage of the unconstrained zone .

Pathway Branching:

Path A (CDC): If hazard/heritage = 0 AND lot width > 21m, flag as 'High-Probability 10-day CDC' .

Path B (TAD): If lot has 'significant likely impacts' but meets strategic upfront codes, flag as '50-day Targeted Assessment' .

Path C (DA): If in a 'Red Zone' exclusion, list the 5 specific local DCP design rules that must be met to pass merit assessment .

Pattern Matching: Ingest the 2025 NSW Housing Pattern Book dimensions. Test the NDA against these patterns and provide a 3D-envelope visualization showing how Pattern #X fits within the lot setbacks.   

Output Requirement: Every result must include a Defensible Audit Trail—a list of clickable legislative citations for every SEPP, LEP, and DCP clause checked ."



 Data Availability via Official APIsAlmost every field in your current JSON output can be sourced more reliably through these official channels:Property Metadata (Zoning, FSR, Height, Heritage Facts): The Online Section 10.7 Planning Certificate Service API provides the official "legal facts" for an address in JSON format. This includes your maxFsr, maxHeight, zoneDescription, and heritage metadata.Spatial Geometry (Boundaries and Overlays): The coordinates and "rings" for your lotDetails and the polygons for heritage items are found in the EPI Primary Planning Layers (ArcGIS REST MapServer). Specifically, Layer 0 provides the heritage shapes, and Layer 6 provides the land application boundaries.Lot Dimensions and Frontage: While basic dimensions can be calculated from the NSW Land Parcel Theme, the most precise data (LandXML) comes from the Survey Plan Digitisation Project, which stores property boundary data in a defined structure to facilitate automation.Tree Canopy: This is available as a specific spatial dataset: Greater Sydney Tree Canopy Cover 2019/2022.2. The Technical Requirement for the PivotThe core of your pivot—finding the Net Developable Area (NDA) on split lots—is not a data retrieval problem; it is a computational geometry problem.The Planning Portal only tells you isHeritage: true. It does not tell you if that heritage constraint covers 5% or 95% of the land. To provide value, your code must:Retrieve the Lot Polygon (the property boundary).Retrieve the Heritage/Flood/Hazard Polygon (the constraint boundary).Perform a Spatial Subtraction (e.g., using a library like Shapely or Turf.js).Calculate the remaining area and its dimensions (width/depth) to see if it still fits a NSW Housing Pattern Book design.3. Revised Prompt for Codebase AdaptationUse this prompt to instruct your development team or an AI coding assistant to implement the pivot:"Adapt the Plotdetect backend to transition from a 'Reference Tool' to a 'Pathway Feasibility Engine' using official NSW spatial datasets.Task 1: Official Data IntegrationReplace internal/gleaned APIs with the NSW Planning Portal ArcGIS REST Services (MapServer layers 0–6) for authoritative geometry.Implement the Online Section 10.7 API to retrieve certified property metadata (Zoning, LEP Clauses, and Hazard facts).Task 2: Split-Lot Geometry EngineDevelop a module to perform a geospatial intersection. If a lot intersects a heritage or flood polygon, calculate the Net Developable Area (NDA).Do not return a binary 'IsHeritage' flag. Instead, return the specific area ($m^{2}$) and the dimensions of the 'Safe Zone'.Task 3: Pattern Matcher LogicIngest the 2025 NSW Housing Pattern Book standards (e.g., 21m site width for mid-rise patterns).Compare the calculated NDA and Lot Width against these patterns. If a match is found, flag as 'Fast-Track Eligible' (10-day approval target).Task 4: Defensible Audit TrailFor every result, generate a 'Legal Logic' report that cites the specific LEP/DCP clauses and SEPP sections checked (e.g., Codes SEPP Clause 1.19). This serves as a liability shield for the professional user."4. Market and Moat AnalysisTAM (Total Addressable Market): In NSW, there are ~12,000 relevant professionals (Architects, Town Planners, Certifiers) and ~16,500 new approvals every month.Pricing Opportunity: Professionals will pay a monthly SaaS fee ($149–$199/mo) for a "Liability Shield"—a tool that provides the defensible logic the government AI refuses to provide. "Mom and Dad" developers represent a high-volume market for one-off "Feasibility Snapshot" reports priced at $99.The Unique Moat: Because the state AIroadmap explicitly excludes adequacy tests on complex/constrained sites to avoid liability, your app's ability to mathematically prove SEPP eligibility on a "Red Zone" lot is your primary commercial differentiator.

To determine if soil and landscaping meet the **NSW Housing Pattern Book** and **Landscape Design Guide (LDG)** numeric requirements, the app must transition from a "text-reader" to a **"Metric Synthesis Engine."** This involves cross-referencing site geometry with structured regulatory data to perform automated compliance checks.

### **1. Determining Soil & Landscaping Compliance**

The current architecture needs to be enhanced to calculate three primary metrics against the property's polygon data:

* **Deep Soil Zone (DSZ) Calculation:**
* **Source:** The app must query the `v2_extracted_values` (JSONB) column in the `regulatory_provisions` table for the specific "Deep Soil %" requirement.
* **Logic:** The system calculates the `lot_size` from the property's spatial polygon (a feature currently listed as "needs implementation") and multiplies it by the required percentage (e.g., 25%) to determine the mandatory area in square meters.
* **Verification:** The app uses the **Landscape Design Guide** provisions to check for "unobstructed" requirements (e.g., no structures above or below) to flag if proposed soil areas are valid.


* **Tree Canopy Requirements:**
* **Numeric Matching:** The engine parses the **Housing SEPP** or **Pattern Book LDG** to find the minimum canopy target (often 15-25%).
* **Spatial Check:** It compares this against the "Tree Canopy" spatial data (identified as a "quick win" in Phase 1) to determine if the existing canopy is sufficient or if additional planting is required for compliance.


* **Soil Volume & Depth:**
* **Synthesis:** For more complex multi-dwelling developments, the app must synthesize the **Apartment Design Guide (ADG)** standards for "Soil Volume" (e.g., 10m³ for small trees) with the property's depth and setback constraints.



### **2. Managing Design Templates for the App**

To manage the **Pattern Book** templates effectively, you should treat them as a new data layer in your multi-layer model.

* **Template Metadata Storage:**
Create a new `pattern_book_templates` table structured similarly to your `regulatory_provisions`:
```sql
-- Proposed Template Management Schema
template_id        TEXT PRIMARY KEY -- e.g., "PB-01-Terrace"
min_lot_width      DECIMAL          -- e.g., 12.0m
min_lot_depth      DECIMAL          -- e.g., 30.0m
envelope_m2        DECIMAL          -- Building footprint
required_deep_soil DECIMAL          -- As per LDG standards
source_citation    TEXT             -- Link to Pattern Book PDF/Page

```


* **The "Pattern Matcher" Workflow:**
A new **Phase 5B** workflow (Day 15) should be built to perform "Template-to-Site" matching:
1. **Site Query:** Get the property's width and depth from the PostGIS polygon.
2. **Exclusion Check:** Check `v2_site_condition_required` for "Heritage" or "Flood" flags. If detected, the app must inform the user that Pattern Book designs may be "Incompatible" or require a full DA.
3. **Template Filter:** Query the templates table for all designs where `min_lot_width <= site_width` AND `min_lot_depth <= site_depth`.
4. **Feasibility Score:** Output a "Pass/Fail" list of compatible designs to the user.



### **Status Check: Are these in your DB?**

* **Setbacks & Parking:** Current coverage includes 47,818 provisions across Inner West DCPs and LEPs.
* **Pattern Book:** These are **NOT** in your DB yet. You will need to ingest the 2025 NSW Housing Pattern Book and Landscape Design Guide into the `regulatory_provisions` table, specifically tagging them with `v2_dcp_layer = 'generic'` or a new `state_standard` layer.

To address your questions, it is critical to distinguish between the **spatial summary data** provided by the Planning Portal and the **detailed regulatory provisions** extracted from gazetted legal documents.

### **1. Setback Requirements: The "Actual Position"**

You are correct that setbacks are rarely simple numeric values. In the NSW planning system, setbacks are typically structured as a complex "waterfall" of requirements sourced from **Local Environmental Plans (LEPs)** and **Development Control Plans (DCPs)**.

* **LEP (Tier 2 - Statutory):** This provides the high-level mandatory constraints, such as the maximum building height or Floor Space Ratio (FSR), which indirectly influence the building envelope but often do not specify setbacks.
* **DCP (Tier 3 - Performance-Based):** This is where the actual setback "position" is defined. These documents contain verbatim provisions that include both **quantitative controls** (e.g., "6m front setback") and **qualitative objectives** (e.g., "consistent with the existing streetscape rhythm").
* **Contextual Overrides:** A setback is rarely a single number because it changes based on:
* **Zone & Use:** Different rules apply for R2 (low density) vs. R3 (medium density).
* **Precinct-Specific Controls:** For example, a property in the "Norton Street Precinct" may have a bespoke setback that overrides the general council-wide rule.
* **Site Conditions:** Properties adjacent to heritage items or within a Heritage Conservation Area (HCA) often face stricter setback requirements to preserve "curtilage" or "view corridors".



### **2. Deep Soil and Tree Canopy Sourcing**

While the Planning Portal provides high-level "Tree Canopy Trends," the **actionable requirements** for your development are sourced from three distinct technical layers:

* **DCP Landscaping Chapters:** These are the primary sources for **Deep Soil Zones (DSZ)**. Requirements are typically expressed as a percentage of the total site area (e.g., "25% deep soil") and are found in the specific "Landscaping" or "Site Layout" chapters of the DCP.
* **The Housing SEPP (State Level):** For "Fast-Track" pathways (like Complying Development), the **Housing SEPP** provides standardized numeric standards for tree canopy and deep soil that override local DCPs if the project meets certain criteria.
* **Area Character Statements:** For heritage-sensitive areas, "Tree Canopy" is not just a trend but a **contributory element**. The app sources these from narrative **Character Statements** (1-2 page documents per HCA) that describe the specific species or "landscape character" (e.g., "mature Brush Box street trees") that must be maintained.

### **Summary of Sourcing**

| Metric | Planning Portal Source | PlotDetect (DCP/LEP) Source |
| --- | --- | --- |
| **Setbacks** | General Spatial Layers (Approximate) | **Verbatim DCP Provisions** (e.g., Part C Section 1) |
| **Deep Soil** | Not provided | **Technical Controls** in the Landscaping Chapter |
| **Tree Canopy** | Historical Trend Data | **Area Character Statements** & Housing SEPP Standards |

By treating the **Provision as the Requirement**, the system ensures you aren't looking at an "interpreted" summary, but the actual gazetted rule with a direct link to the PDF page for verification.

Instrument Category,Specific Source Documents,Purpose in Synthesis Engine
State Gatekeepers,State Environmental Planning Policy (Housing) 2021,"Determines eligibility for Manor Houses, Dual Occs, and Granny Flats."
,State Environmental Planning Policy (Exempt and Complying Development Codes) 2008,"The ""Bible"" for the 10-day fast-track pathway. Contains the ""Ineligibility Triggers."""
,NSW Housing Pattern Book (2025),"The ""pre-approved"" designs. Requires matching lot width/depth to design templates."
Technical Guides,NSW Housing Pattern Book Landscape Design Guide,Source for the numeric Deep Soil and Tree Canopy requirements.
,Apartment Design Guide (ADG),"Source for setbacks, solar, and cross-ventilation for mid-rise."
Local Baselines,Local Environmental Plan (LEP 2022),"Statutory height, FSR, and Land Use Permissibility."
,Development Control Plan (DCP),"The ""fallback"" rules for setbacks, parking, and heritage character."
Spatial Overlays,NSW Planning Portal Spatial Layers,"Triggers for: Flood, Bushfire, Heritage, Acid Sulfate, and TOD proximity."