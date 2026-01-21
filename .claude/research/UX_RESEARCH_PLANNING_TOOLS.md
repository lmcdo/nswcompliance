# UX Research: Planning Compliance Assessment Tools

## Research Summary

This document synthesizes UX patterns and best practices from leading Australian property/planning tools and general compliance UX research to inform the PlotDetect/Compliance Engine interface design.

---

## Part 1: Competitor Analysis

### 1. Archistar (archistar.ai)

**Overview**: AI-powered property research, feasibility, and design generation platform.

**Key UX Patterns**:

- **Layered Information Architecture**: Moves from broad concepts (feasibility overview) to specific details (individual constraints)
- **Problem-Solution Pairs**: Each planning factor presented as a distinct problem with its solution
- **Visual Reports**: "Spell-check for zoning" - flags errors like incorrect setbacks, height violations with visual indicators
- **Instant Feedback Loop**: eCheck provides rapid compliance feedback before formal submission
- **2D/3D Visualization**: Height limits displayed as color-scaled layers with exact values on each site
- **Progressive Complexity**: Basic compliance check accessible immediately; deeper analysis available on demand

**Information Density Handling**:
- Accordion-style sections for different constraint categories
- Scannable bold headers as entry points
- Feature callouts reduce cognitive load
- Trust signals and data sources deferred to footer

**How They Present "Can I Build X Here?"**:
- AI-powered eCheck instantly assesses designs against local codes
- Traffic light-style pass/fail indicators
- Visual reports showing exactly where violations occur
- Iterative checking - users can modify and re-check before submission

**Sources**: [Archistar Property Development Feasibility](https://www.archistar.ai/property-development-feasibility-software/), [Archistar eCheck](https://www.archistar.ai/echeck/)

---

### 2. Landchecker

**Overview**: Property data and planning/zoning lookup platform covering all Australian states.

**Key UX Patterns**:

- **Map-First Interface**: Core visualization is interactive map with zoning overlays
- **Three Ways to Access Data**: Right panel, Planning Layers, or downloadable report
- **Traffic Light Filtering**: Approved (green), pending (yellow), rejected (red) permits
- **Information Panel**: Expandable sections for property info, planning info, permits
- **3D Terrain Views**: Integrated with high-res imagery and drawing tools

**Information Density Handling**:
- Tiered subscription model matches UX complexity to user sophistication
- Starter = basic zoning; Advanced = permits + alerts; Enterprise = API access
- Color-coded zones with direct links to planning scheme text
- Hover-to-preview for permit details

**Progressive Disclosure**:
- Essential zoning shown immediately on map
- Property details in collapsible right panel
- Full reports downloadable as PDF
- Planning scheme schedules linked (not embedded)

**Design Recognition**: Won 2017 TECH Design Award for "clear, concise graphical presentation" compared to cumbersome alternatives.

**Sources**: [Landchecker Zoning Maps](https://landchecker.com.au/functionalities/land-zoning-and-zoning-maps/), [Landchecker Planning Maps](https://landchecker.com.au/functionalities/property-planning-maps/)

---

### 3. PlanningAlerts (OpenAustralia Foundation)

**Overview**: Free email alert service for development applications near any address.

**Key UX Patterns**:

- **Single-Purpose Focus**: Does one thing well - alerts users to nearby DAs
- **Location-Based Subscription**: Enter address, get relevant applications
- **Community Transparency**: Shows council planning data without interpretation

**Information Density Handling**:
- Minimal interface - search box and map
- Email summaries with links to full applications
- No attempt to interpret or analyze - just inform

**Lesson for PlotDetect**: Sometimes simplicity and single-purpose clarity beats comprehensive dashboards.

**Sources**: [PlanningAlerts](https://www.planningalerts.org.au/), [OpenAustralia Foundation](https://www.oaf.org.au/projects/planningalerts/)

---

### 4. Nearmap / Aerometrex

**Overview**: Aerial imagery and AI-powered property intelligence.

**Key UX Patterns**:

- **MapBrowser**: Pan, zoom, measure, rotate in 2D and 3D
- **AI Feature Detection**: 130+ property features automatically detected
- **Change Detection**: Automatically identify construction progress
- **Timeline Scrubbing**: Explore site history visually
- **Marker/Annotation System**: Add markers, customize metadata, export lists

**Information Density Handling**:
- AI insights surface relevant data without overwhelming
- Layer-based approach - turn on/off different detection types
- High-res imagery as context for data overlays

**Sources**: [Nearmap MapBrowser](https://www.nearmap.com/products/mapbrowser), [Nearmap Property Services](https://www.nearmap.com/solutions/property-services)

---

### 5. CoreLogic / Cordell

**Overview**: Property data, analytics, and construction project information.

**Key UX Patterns**:

- **Minimal Input, Maximum Output**: Prompt for minimum information needed
- **Real-Time Report Generation**: Data from multiple global silos
- **Branded Consistency**: Fluid layouts with strict branding adherence
- **Early Project Alerts**: Cordell Connect alerts during planning stages

**Information Density Handling**:
- Reports generated on-demand rather than showing everything
- Structured templates reduce pagination fatigue
- Section-based organization with clear headers

**Sources**: [Archistar Property Development Tools](https://www.archistar.ai/blog/property-development-tools/)

---

### 6. NSW Planning Portal

**Overview**: Official NSW government planning and DA submission platform.

**Key UX Patterns**:

- **Spatial Viewer**: Map layers for SEPPs, LEPs, DCPs
- **Toggleable Layers**: Activate/deactivate constraint layers
- **Direct Links to Legal Text**: From map to relevant LEP clauses
- **Property Report PDF**: Summarizes all controls for a site
- **Historical Viewer**: See superseded planning instruments

**Information Hierarchy for Planning Controls**:
1. Zoning (primary - shown on map)
2. FSR and Height of Buildings (key development standards)
3. Overlays (heritage, flood, bushfire)
4. DCP provisions (detailed guidance)
5. Contribution Plans (infrastructure levies)

**Sources**: [NSW Planning Portal Spatial Viewer Guide](https://duplexbuildingdesign.com/nsw-planning-portal-spatial-viewer/), [NSW Planning System](https://www.planning.nsw.gov.au/assess-and-regulate/development-assessment/your-guide-to-the-da-process/getting-started/the-planning-system)

---

## Part 2: Design Pattern Research

### Building Envelope Visualization

**Key Tools**: Zoneomics + Autodesk Forma, Gridics MuniMap, TestFit, Modelur, ArcGIS Urban

**Best Practices**:

- **3D Envelope Models**: Display setbacks, heights as explorable 3D volumes
- **Push/Pull Interaction**: Let users adjust setbacks and see real-time impact
- **Interactive Zoning**: Rules adapt as building position changes
- **Step Visualization**: Show how stepped setbacks work in 3D space
- **Color-Coded Height Layers**: Gradient showing permissible heights

**Key Insight**: "Visualizing complex zoning ordinances in a 3D environment allows city planners a unique and transparent perspective on development potential."

**Sources**: [Autodesk + Zoneomics Partnership](https://blogs.autodesk.com/forma/2024/08/19/autodesk-and-zoneomics-partner-to-bring-zoning-responsive-building-envelopes-to-forma/), [Modelur Interactive 3D Zoning](https://modelur.com/interactive-3d-zoning-automate-site-zoning-ordinance-checks/), [Gridics MuniMap](https://gridics.com/)

---

### Progressive Disclosure Patterns

**Core Principle**: "Show users what they need when they need it."

**Implementation Techniques**:

1. **Accordions**: User-controlled content revelation (FAQs, constraint categories)
2. **Tabs**: Organize content into switchable categories
3. **Tooltips/Popovers**: Additional info on hover without leaving context
4. **Modal Windows**: Advanced features hidden until explicitly requested
5. **Staged Workflows**: Complex tasks broken into digestible steps

**Best Practices**:
- Maximum 2 levels of disclosure (3+ = too complex)
- Keep important information visible by default
- Use user research (card sorting, task analysis) to define essential vs advanced
- Present only minimum data required for current task

**Sources**: [NN/g Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/), [IxDF Progressive Disclosure](https://www.interaction-design.org/literature/topics/progressive-disclosure), [IBM Design Patterns](https://medium.com/design-ibm/designing-patterns-that-scale-with-progressive-disclosure-9341d53644ae)

---

### Traffic Light / RAG Status Patterns

**Definition**: Red-Amber-Green ratings to show compliance status at a glance.

**Color Meanings**:
- **Green**: Compliant / On track / Target met
- **Amber/Yellow**: Warning / Needs attention / In-between
- **Red**: Non-compliant / Critical issue / Action required

**Best Practices**:
- Don't overuse - highlight only vital measures
- Clearly define thresholds for each color
- Use shapes alongside colors for accessibility (circle, triangle, diamond)
- 2.7 million color blind people in UK alone - never rely on color alone

**Application to Planning Compliance**:
- Green: Meets requirement (e.g., setback compliant)
- Amber: Close to limit / Needs verification (e.g., 95% of max FSR)
- Red: Exceeds limit / Non-compliant (e.g., height exceeds 9m limit)

**Sources**: [Bernard Marr on RAG Ratings](https://bernardmarr.com/performance-reporting-how-to-use-traffic-light-colours-and-rag-ratings-in-dashboards/), [RAG Status Dashboard](https://www.mastt.com/blogs/project-rag-status-dashboard)

---

### Plain Language for Regulatory Content

**The Challenge**: Planning documents use jargon that confuses non-experts.

**Plain Language Principles**:
- Write at 6th-8th grade reading level
- Avoid jargon unless audience is familiar
- Keep sentences 15-20 words average (max 30-35)
- Use active voice over passive
- Put most important message first
- Break text into logical chunks with clear headers

**BUROC Framework** for UX empathy:
- **B**reaking down complex concepts
- **U**sing familiar terms
- **R**emoving unnecessary words
- **O**rganizing logically
- **C**larifying with examples

**Implementation**:
- Create glossaries mapping jargon to everyday words
- Test content with actual users
- Provide both technical term AND plain explanation

**Sources**: [UX Magazine Plain Language](https://uxmag.com/articles/plain-language-tenets-in-ux), [Understanding Group on Plain Language](https://understandinggroup.com/ia-practice/beyond-jargon-the-power-of-plain-language-in-information-architecture)

---

### UX in Regulated Industries

**Key Challenges**:
- Compliance demands layers of documentation, disclosures, security features
- Long forms, jargon-heavy instructions, excessive legal disclaimers overwhelm users
- Balancing strict requirements with intuitive experiences

**Best Practices**:
- Bring compliance officers and UX researchers together early
- Break long processes into bite-sized steps
- Show progress tracker
- Add real-time help (chatbots, tooltips)
- A/B test different approaches to find balance

**Sources**: [Cadabra Studio on Regulated UX](https://cadabra.studio/blog/ui-ux-design-regulated-industries/), [Optimal Workshop on Compliance UX](https://www.optimalworkshop.com/blog/navigating-the-regulatory-maze-ux-design-in-the-age-of-compliance)

---

### Government Digital Service Patterns

**GOV.UK Design System** established key patterns:
- Consistent solutions to common challenges
- Accessible by default (WCAG 2.0 AA)
- Components and patterns for common tasks
- "Check if a service is suitable" pattern particularly relevant

**Key Insight**: "Too often, government sites mirror the agency's internal bureaucracy rather than presenting information in a citizen-centric way."

**Permit Application Best Practices**:
- Online submission 24/7
- Progress tracking
- Self-service portals
- Timely status notifications
- Iterative checking before submission

**Sources**: [GOV.UK Design System](https://gds.blog.gov.uk/2018/06/22/introducing-the-gov-uk-design-system/), [USWDS](https://designsystem.digital.gov/)

---

## Part 3: Actionable UX Recommendations for PlotDetect

### A. Information Architecture

**Recommended Hierarchy (Top to Bottom)**:

1. **Address Search + Map** (primary entry point)
2. **Compliance Summary** (RAG status at a glance)
3. **Key Development Standards** (FSR, Height, Setbacks)
4. **Zoning + Permitted Uses**
5. **Overlays + Constraints** (heritage, flood, bushfire)
6. **DCP Detailed Controls** (on-demand)
7. **Full Report / Legal References** (downloadable)

### B. "Can I Build X Here?" Answer Pattern

**Recommended Approach**:

```
┌─────────────────────────────────────────┐
│  [Address]                              │
│  Zone: R2 Low Density Residential       │
├─────────────────────────────────────────┤
│  DWELLING HOUSE                    ✓    │
│  Permitted with consent                 │
├─────────────────────────────────────────┤
│  KEY STANDARDS                          │
│  ────────────────────────────────────── │
│  Max Height:    9m            ✓         │
│  Max FSR:       0.5:1         ✓         │
│  Front Setback: 6m            ⚠ Check   │
│  Side Setback:  0.9m          ✓         │
├─────────────────────────────────────────┤
│  CONSTRAINTS                            │
│  ────────────────────────────────────── │
│  Heritage:      None          ✓         │
│  Flood Zone:    None          ✓         │
│  Bushfire:      BAL-LOW       ⚠ Review  │
├─────────────────────────────────────────┤
│  [View Full Report] [See All Controls]  │
└─────────────────────────────────────────┘
```

**Key Elements**:
- Clear yes/no/maybe answer at top
- RAG indicators for each standard
- Progressive disclosure to detailed provisions
- Plain language with technical terms available

### C. Progressive Disclosure Implementation

**Level 1 - Immediate (Always Visible)**:
- Compliance summary (pass/warning/fail count)
- Zone name and basic description
- Top 5 key numerical standards

**Level 2 - On Request (Expandable Sections)**:
- Full list of development standards
- Overlay details
- DCP provisions by category

**Level 3 - Deep Dive (Separate Views/Modals)**:
- Full legal text of provisions
- Related clauses
- Historical changes
- Methodology explanations

### D. Handling Information Density

**Patterns to Implement**:

1. **Collapsible Sections**: Group related provisions (setbacks, landscaping, parking)
2. **Tabbed Interface**: LEP | DCP | SEPP | Heritage tabs
3. **Filter Controls**: Show only non-compliant items, show only relevant provisions
4. **Summary Cards**: Key numbers in scannable format before detail tables
5. **Tooltips**: Jargon terms explained on hover

### E. Visual Constraint Representation

**Recommended Visualizations**:

1. **Map Overlay**: Show property boundary with constraint zones
2. **Building Envelope 3D** (aspirational): Interactive setback visualization
3. **Height Diagram**: Simple 2D cross-section showing max height
4. **FSR Calculator**: Visual representation of floor area allowance

**Minimum Viable Visualization**:
- Property boundary on map
- Color-coded constraint overlays (toggle on/off)
- Numerical standards in clear table format

### F. Jargon vs Plain Language

**Dual-Language Approach**:

| Technical Term | Plain Language | Display Pattern |
|---------------|----------------|-----------------|
| FSR 0.5:1 | "Total floor area can be half the lot size" | Show both, technical first |
| Setback 6m | "Building must be 6 meters from boundary" | Tooltip explains term |
| Clause 4.3 | "Height of Buildings" | Link text is plain, ref shown |
| Merit assessment | "Council will decide based on context" | Expandable explanation |

**Implementation**:
- Default to plain language summaries
- Technical references available via expand/tooltip
- Glossary accessible from any page
- "What does this mean?" links on complex provisions

### G. Key UI Components Needed

1. **Compliance Status Badge**: Green check / Amber warning / Red X with count
2. **Standard Row Component**: Label | Value | Status | Expand for details
3. **Provision Card**: Section heading | Summary | RAG status | View provisions link
4. **Map Layer Toggle**: List of layers with visibility controls
5. **Report Section Accordion**: Collapsible sections for different control categories
6. **Glossary Tooltip**: Hover/click to see term definition

### H. User Flows

**Primary Flow - Property Lookup**:
1. Enter address
2. See compliance summary
3. Expand category of interest
4. View specific provision details
5. Download/export report

**Secondary Flow - "Can I Build..."**:
1. Enter address
2. Select development type from dropdown
3. See permissibility answer
4. View applicable standards
5. Check against proposed development parameters

**Tertiary Flow - Deep Research**:
1. Enter address
2. Navigate to specific instrument (LEP/DCP/SEPP)
3. Browse provisions by section
4. Read full clause text
5. View related clauses

---

## Part 4: Implementation Priority

### Phase 1 - Foundation (MVP)
- Address search with property identification
- Compliance summary with RAG status
- Key standards display (FSR, height, setbacks)
- Basic provision listing with expand/collapse

### Phase 2 - Enhanced Usability
- Tabbed interface for instrument types
- Glossary and tooltips
- Filterable provision lists
- PDF report generation

### Phase 3 - Advanced Features
- Interactive map with layer toggles
- "Can I build X?" development type selector
- Comparison tool (proposed vs allowed)
- Visual setback/height diagrams

### Phase 4 - Premium Features
- 3D building envelope visualization
- AI-powered compliance checking
- Integration with DA submission
- Historical provision tracking

---

## References

### Competitor Tools
- [Archistar](https://www.archistar.ai/)
- [Landchecker](https://landchecker.com.au/)
- [PlanningAlerts](https://www.planningalerts.org.au/)
- [Nearmap](https://www.nearmap.com/)
- [NSW Planning Portal](https://www.planningportal.nsw.gov.au/)

### Design Systems & Patterns
- [GOV.UK Design System](https://design-system.service.gov.uk/)
- [US Web Design System](https://designsystem.digital.gov/)
- [Nielsen Norman Group - Progressive Disclosure](https://www.nngroup.com/articles/progressive-disclosure/)

### 3D Zoning Tools
- [Gridics MuniMap](https://gridics.com/)
- [Modelur](https://modelur.com/)
- [Zoneomics](https://www.giraffe.build/partners/zoneomics)
- [ArcGIS Urban](https://www.esri.com/en-us/arcgis/products/arcgis-urban/overview)

---

*Research compiled: January 2026*
*For: PlotDetect / Compliance Engine UI/UX Design*
