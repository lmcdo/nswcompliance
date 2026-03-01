# Strategic Analysis: NSW Property Intelligence Suite

**Date:** 2025-10-23
**Status:** Current State Assessment & Recommendations
**Purpose:** Grant Applications & Strategic Planning

---

## EXECUTIVE SUMMARY

### What You Have
Three functional applications with complementary capabilities:
- **Map-Viewer**: NSW property data visualization (zoning, DAs, environmental overlays)
- **Chart-Viewer**: DA/CDC analytics dashboard (approval rates, trends, council performance)
- **Compliance Engine**: LightRAG-powered regulatory interpretation (Inner West only, 1,725 provisions)

### Current Reality
- **Revenue:** $0
- **Customers:** 0
- **Market Awareness:** None
- **Geographic Coverage:** Inner West (compliance), NSW-wide (data)
- **Competitive Advantage:** Knowledge graph of 217 Inner West planning documents

### Strategic Recommendation
**Focus:** "Inner West Property Development Intelligence" - dominate one geography where competitive advantage exists, then expand.

---

## PART 1: CURRENT STATE ANALYSIS

### 1.1 Application Capabilities

#### Map-Viewer: Property Intelligence Platform
**Working Features:**
- ✅ NSW Planning Portal integration (zoning, LEP, SEPP layers)
- ✅ DA/CDC search (1000+ records per council)
- ✅ BASIX climate zones (layer 149)
- ✅ Environmental overlays (bushfire, flood, heritage, tree canopy)
- ✅ Interactive mapping with clustering

**Limitations:**
- ❌ View-only (no analysis or recommendations)
- ❌ No integration with other apps
- ❌ No export or reporting functionality

**Technical Stack:**
- Next.js frontend
- NSW Planning Portal APIs
- Supabase for DA/CDC storage

#### Chart-Viewer: Planning Analytics Dashboard
**Working Features:**
- ✅ Real-time DA/CDC metrics from Supabase
- ✅ Council performance analysis (approval rates, processing times)
- ✅ Development type breakdowns
- ✅ Daily ETL from NSW Planning Portal

**Limitations:**
- ❌ No predictive analytics
- ❌ No benchmarking tools
- ❌ Static visualizations (no interactive drilling)

**Technical Stack:**
- Next.js frontend
- Supabase backend
- Daily sync jobs

#### Compliance Engine: Regulatory AI
**Working Features:**
- ✅ LightRAG conversational queries (1,725 provisions)
- ✅ AutoSchemaKG knowledge graph (6.47MB GraphML)
- ✅ LangExtract source citations (char-level provenance)
- ✅ Complex rule processing (setbacks, conditionals)

**Limitations:**
- ❌ Inner West only (Ashfield, Leichhardt, Marrickville)
- ❌ ~300K properties vs 3M+ NSW-wide
- ❌ No BASIX calculations
- ❌ No NCC 2025 integration

**Technical Stack:**
- RagAnything (PDF extraction)
- LangExtract (source grounding)
- AutoSchemaKG (knowledge graphs)
- LightRAG (semantic queries)
- Ollama + Llama 3.1 8B (local LLM)

### 1.2 Critical Gaps

**Integration:**
- Apps operate independently
- No shared user accounts
- No cross-referencing (e.g., can't jump from map to compliance check)

**Coverage:**
- Compliance engine works for 10% of NSW properties
- No expansion strategy to other councils

**Monetization:**
- All features currently free
- No payment infrastructure
- No pricing strategy

**Distribution:**
- Zero marketing
- No SEO content
- No user acquisition strategy

---

## PART 2: TARGET USER ANALYSIS

### 2.1 User Personas & Pain Points

#### Persona 1: Property Investors (Pre-Purchase)
**Demographics:**
- Age: 30-55
- Income: $100K+
- Property budget: $800K-$2M
- Tech-savvy

**Current Pain Points:**
1. "What can I actually build here?" - Unknown before purchase
2. Hiring town planner costs $1,500-3,000 (pre-commitment)
3. Council pre-DA meetings take 4-6 weeks
4. Zoning reports ($200-500) show rules but no interpretation
5. Risk of buying wrong property for intended development

**Willingness to Pay:** $199-299 for comprehensive report before purchase

**Decision Criteria:**
- Speed (need answer in days, not weeks)
- Reliability (legal citations, not guesses)
- Comparable examples (what's been approved nearby)
- Cost implications (construction requirements, fees)

#### Persona 2: Real Estate Agents
**Demographics:**
- Commission-driven (2-3% of sale price)
- Time-poor (managing 5-10 listings simultaneously)
- Need competitive edge

**Current Pain Points:**
1. Buyers ask development questions agents can't answer
2. Sending all buyers to planners is expensive/slow
3. Properties with development potential sell for 20-40% premium
4. Need to identify development sites proactively

**Willingness to Pay:** $99-149/month unlimited reports (5-10 uses per month)

**Decision Criteria:**
- Easy to use (30 seconds to generate report)
- Professional presentation (branded reports for clients)
- Accuracy (can't risk reputation on wrong info)
- ROI (helps close 1 extra deal = 10x cost)

#### Persona 3: Small Developers (2-10 projects/year)
**Demographics:**
- Portfolio: Dual occupancies, townhouses, small units
- Budget: $500K-$3M per project
- Risk-averse (self-funded or small investors)

**Current Pain Points:**
1. Site selection takes months (drive around suburbs, check zoning manually)
2. "Due diligence paralysis" - never sure if checked everything
3. Consultants expensive (feasibility study $5-10K)
4. Don't know actual approval patterns (LEP says yes, council says no)

**Willingness to Pay:** $299-499 per detailed feasibility report

**Decision Criteria:**
- Comprehensive (all risks identified upfront)
- Data-driven (show approval rates for similar projects)
- Investment decision support (build vs don't build)
- Risk mitigation (contamination, heritage, constraints)

#### Persona 4: Architects & Certifiers
**Demographics:**
- Professional service providers
- 10-50+ projects per year
- Need ongoing research capability

**Current Pain Points:**
1. Pre-DA research takes 5-10 hours per project (manually reading DCPs)
2. Complex provisions hard to interpret (conditional clauses, references)
3. Keeping up with DCP amendments (50+ councils × annual updates)
4. Client questions: "Why did this get approved but not that?"

**Willingness to Pay:** $199-299/month subscription (unlimited queries)

**Decision Criteria:**
- Time savings (reduce research from 5 hours to 30 minutes)
- Accuracy (legal citations for client documentation)
- Comprehensive (all relevant provisions in one place)
- Up-to-date (latest DCP versions, amendments)

#### Persona 5: Council Planning Staff
**Demographics:**
- Statutory planners, assessment officers
- Processing 50-200 DAs per year
- Budget: $10-50K software procurement

**Current Pain Points:**
1. Manual DCP lookups slow (30-60 min per complex DA)
2. Training new staff takes 6-12 months (learning DCPs)
3. State government reporting requirements (manual data compilation)
4. Inconsistent assessments (different planners interpret differently)

**Willingness to Pay:** $12-18K/year per council

**Decision Criteria:**
- Accuracy (must match official DCP interpretations)
- Integration (fits into existing workflows)
- Auditability (decisions need documentation)
- Training reduction (new staff productive faster)

### 2.2 Underserved Needs (Ranked by Opportunity)

#### Need #1: Pre-Purchase Development Feasibility ⭐⭐⭐
**Gap in Market:**
- CoreLogic/RP Data: Static zoning reports ($200-500), no interpretation
- Council websites: Rules listed, no analysis
- PropTrack: Sales data, no planning intelligence
- Town planners: Expensive ($1,500+), slow (weeks)

**Your Unique Position:**
- Zoning data + DA outcomes + regulatory interpretation
- Example: "10 similar 2-storey DAs approved within 500m, avg cost $420K, 89-day timeline"
- Automated delivery (instant vs weeks)

**Market Size:**
- 100K+ property purchases per year in NSW
- 20-30% have development potential
- 20-30K potential customers annually
- At $249 average = $5-7.5M TAM

**Realistic Capture Rate:** 1-2% = 200-600 reports/year = $50-150K revenue potential

---

#### Need #2: "What Actually Gets Approved?" Pattern Intelligence ⭐⭐⭐
**Gap in Market:**
- No systematic approval pattern analysis exists
- Industry relies on anecdotes and consultant experience
- LEP/DCP say one thing, council behavior is different

**Your Unique Position:**
- 10K+ historical DAs with outcomes
- Can show: "Dual occupancy permitted by zoning BUT 70% refused in this suburb for character concerns"
- Geographic clustering of approvals/refusals
- Temporal trends (council getting stricter/more lenient)

**Market Size:**
- Professional users (architects, planners, developers)
- ~5,000 professionals doing regular research
- At $99/month = $6M annual subscription TAM

**Realistic Capture Rate:** 2-5% = 100-250 subscribers = $120-300K ARR potential

---

#### Need #3: Inner West "Instant Feasibility Check" ⭐⭐⭐
**Gap in Market:**
- No automated feasibility checking exists
- Inner West has complex overlapping controls (3 merged councils)
- Generic NSW tools don't handle Inner West complexity

**Your Unique Position:**
- ONLY platform with complete Inner West DCP/LEP in queryable knowledge graph
- Can answer complex questions with source citations
- Geographic constraint = competitive moat

**Market Size:**
- Inner West: 300K properties, ~12K sales per year
- 30% have development potential = 3,600 potential users
- At $199 average = $720K TAM

**Realistic Capture Rate:** 5-10% = 180-360 reports = $36-72K revenue potential

**Strategic Value:**
- Better to dominate one LGA than weak coverage everywhere
- Proven model can expand to adjacent councils
- Network effects (word of mouth in local area)

---

#### Need #4: Council Performance Benchmarking ⭐⭐
**Gap in Market:**
- Consulting firms produce annual reports ($5K+), outdated data
- No real-time, accessible benchmarking exists
- Industry associations want this data

**Your Unique Position:**
- Chart-viewer has 30-day rolling data across 128 councils
- Can rank by: approval rate, processing time, refusal reasons
- Free dashboard = brand building + lead generation

**Market Size:**
- Small (niche B2B)
- ~50 potential customers (industry associations, large developers, government)
- At $499-999 custom reports = $25-50K revenue potential

**Strategic Value:**
- PR/media attention ("Study shows X council most developer-friendly")
- Government relations (state government wants this data)
- Lead generation for other products

---

## PART 3: OPTIMAL FEATURE ADDITIONS

### 3.1 Tier 1: Build First (High Impact, Low Effort)

#### Feature 1: "Show Comparable DAs" Radius Search
**Effort:** 2 weeks (80 hours)
**Value:** Core differentiation for pre-purchase use case

**Implementation:**
```typescript
// Map-viewer enhancement
function showComparableDAs(property: Property, radius: number = 500) {
  const filters = {
    lat: property.lat,
    lng: property.lng,
    radius: radius,
    developmentType: classifyDevelopmentType(property.proposedUse),
    status: ['Approved', 'Determined - Approved'],
    dateRange: 'last24months'
  };

  const comparables = await fetchDAs(filters);

  displayMarkers(comparables);
  showStats({
    avgApprovalTime: calculateAvg(comparables, 'processingDays'),
    approvalRate: calculateRate(comparables),
    costRange: calculateRange(comparables, 'cost')
  });
}
```

**No New APIs Required:** Uses existing Supabase DA data

**User Value:**
- "8 similar second-storey additions approved within 500m"
- "Average approval time: 89 days"
- "Cost range: $380K-$520K"

**Monetization:** Core feature of $199 property report

---

#### Feature 2: Council Performance Dashboard
**Effort:** 3 weeks (120 hours)
**Value:** Media attention, B2B lead generation

**New Visualizations (Chart-viewer):**
1. Council ranking table (sortable)
2. Approval rate trends (12 months)
3. Development type breakdown by council
4. Processing time distribution

**SQL for Metrics:**
```sql
SELECT
  council_name,
  COUNT(*) as total_das,
  AVG(CASE WHEN status LIKE '%Approved%' THEN 1 ELSE 0 END) * 100 as approval_rate_pct,
  AVG(EXTRACT(DAY FROM (determination_date - submission_date))) as avg_processing_days,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cost_of_development) as median_cost
FROM development_applications
WHERE determination_date > CURRENT_DATE - INTERVAL '12 months'
GROUP BY council_name
ORDER BY approval_rate_pct DESC
```

**Monetization:**
- Free public dashboard (SEO, brand awareness)
- Custom reports: $499 (specific criteria, exportable)
- API access: $299/month (developers/researchers)

---

#### Feature 3: BASIX Guidance Integration
**Effort:** 2 weeks (80 hours)
**Value:** Rides regulatory momentum, low technical risk

**What You CAN Build (realistic):**
- Display BASIX climate zone (already have from layer 149)
- Show static targets by zone (water 40%, energy 45 pts)
- Link to official BASIX portal
- LightRAG answers about requirements

**What You CANNOT Build (no API exists):**
- BASIX certificate validation
- Automated compliance checking
- Historical BASIX data

**Implementation:**
```typescript
interface BasixGuidance {
  climateZone: string; // From existing layer 149
  waterTarget: string; // From existing layer 149
  energyTarget: number; // Static lookup table
  thermalStars: number; // Static (7 stars post-Oct 2023)
  officialPortalLink: string;
  estimatedCompliance: string; // "Typical: 5kW solar + heat pump hot water"
}

// Static data file (one-time manual entry)
const BASIX_TARGETS = {
  "56": { energy: 45, water: 40, thermal: 7, lga: "Inner West" },
  "57": { energy: 45, water: 40, thermal: 7, lga: "City of Sydney" },
  // ~50 climate zones total for NSW
};
```

**Value Proposition:** "Know your BASIX requirements before hiring consultant" (NOT "automated compliance")

---

### 3.2 Tier 2: Build Second (Medium Effort, Clear Value)

#### Feature 4: Automated Feasibility Checker (Inner West Only)
**Effort:** 4 weeks (160 hours)
**Value:** High willingness-to-pay, strong competitive moat

**Implementation:**
```typescript
POST /api/feasibility/check
{
  "address": "123 Smith St, Marrickville",
  "proposedDevelopment": "second storey addition",
  "proposedHeight": "3.5m"
}

// Response
{
  "feasibility": "LIKELY FEASIBLE",
  "confidence": 0.85,
  "analysis": {
    "heightCheck": {
      "current": "5.2m",
      "limit": "9.5m",
      "proposed": "8.7m",
      "compliant": true,
      "source": "Inner West LEP 2022 Clause 4.3"
    },
    "setbackCheck": {
      "required": {"side": "1.5m", "rear": "6m"},
      "assessment": "Subject to detailed design",
      "source": "Marrickville DCP 2011 Part 2.5.1"
    },
    "comparableApprovals": {
      "similar": 8,
      "within500m": true,
      "avgApprovalTime": "92 days"
    }
  }
}
```

**Data Sources (All Existing):**
- Property data, LEP controls, DCP provisions (via LightRAG)
- Comparable DAs from Supabase

**Monetization:**
- Freemium: 1 free check
- $29 per property
- $99/month unlimited (real estate agents)
- $199/month teams (architects)

---

#### Feature 5: DA Success Probability Score
**Effort:** 6 weeks (240 hours - includes ML model training)
**Value:** Highly differentiated, data-driven

**Implementation:**
```python
# Train model on historical DA outcomes
features = [
    'development_type',
    'cost_of_development',
    'property_zone',
    'proposed_height_vs_limit_ratio',
    'setback_compliance_score',
    'heritage_overlay',
    'bushfire_flood_constraints',
    'council_approval_rate_for_type',
    'similar_approvals_in_area'
]

from sklearn.ensemble import RandomForestClassifier
model = RandomForestClassifier()
model.fit(X_train[features], y_train['approved'])

# Predict for new proposal
probability_approved = model.predict_proba(new_proposal)[0][1]
```

**Training Data:** Existing 10K+ DAs in Supabase

**Output:** "72% likelihood of approval based on similar DAs in this area"

**Caveat:** "Indicative only - not a guarantee. Historical patterns may not predict future decisions."

---

### 3.3 Feature Packaging Strategy

#### Free Tier
- Basic property search (Map-Viewer)
- Zoning + environmental overlays
- Recent DA search (limited to 10)

#### Standard Report ($199)
- Property details + zoning
- BASIX requirements
- 5 comparable DAs
- Contaminated land check (NEW)
- Property DA history (NEW)
- Buildable area calculation (NEW)

#### Premium Report ($299)
- Everything in Standard
- Transport proximity + TOD eligibility
- Bushfire cost analysis
- Climate-adapted design recommendations
- Market demographics analysis

#### Pro Subscription ($99/month)
**Target:** Real estate agents, architects
- Unlimited standard reports
- Approval probability score
- Hidden development rights finder
- API access (5,000 calls/month)

---

## PART 4: COMPETITIVE POSITIONING

### 4.1 Current Competitive Landscape

#### Direct Competitors
**CoreLogic RP Data**
- Strengths: Established brand, comprehensive property data, sales history
- Weaknesses: Static zoning reports, no interpretation, expensive ($500+)
- Your Advantage: Dynamic analysis, DA outcomes, automated

**PropTrack (REA Group)**
- Strengths: Massive distribution (realestate.com.au), sales data
- Weaknesses: No planning intelligence, no compliance checking
- Your Advantage: Planning focus, regulatory interpretation

**Archistar**
- Strengths: 3D visualization, FSR calculators, professional focus
- Weaknesses: $999+/month (SME inaccessible), no compliance engine
- Your Advantage: Affordable, regulatory Q&A capability

**Town Planners (Traditional)**
- Strengths: Personalized advice, professional indemnity, relationships
- Weaknesses: Expensive ($1,500+), slow (weeks), limited scale
- Your Advantage: Instant, affordable, scalable

#### Indirect Competitors
**Council Pre-DA Meetings**
- Free but 4-6 week wait, no written confirmation
- Your Advantage: Immediate, documented citations

**DIY Research (Google + Council PDFs)**
- Free but time-consuming, error-prone, overwhelming
- Your Advantage: Curated, interpreted, actionable

### 4.2 Positioning Strategy

**NOT: "Climate compliance platform"**
- Too narrow (niche audience)
- Regulatory burden framing (negative)
- Competitive market (established players)

**YES: "NSW Property Development Intelligence"**
- Outcome-focused ("see what gets approved before you apply")
- Broad appeal (investors, agents, developers, professionals)
- Market gap (no comprehensive solution exists)

**Tagline Options:**
1. "Research your development in minutes, not weeks"
2. "See what actually gets approved before you apply"
3. "Property planning intelligence for NSW"
4. "Know what you can build before you buy"

**Brand Positioning:**
- **Practical** (not aspirational)
- **Data-driven** (not opinion-based)
- **Transparent** (show sources, not black box)
- **Accessible** (affordable vs consultant pricing)

---

## PART 5: GO-TO-MARKET STRATEGY

### 5.1 Phased Rollout

#### Phase 1 (Months 1-3): Free Tools + Validation
**Build:**
- Tier 1 features (comparable DAs, council dashboard, BASIX guidance)

**Launch:**
- Free tools to drive traffic
- "Upgrade for detailed reports" CTAs
- Track conversion metrics religiously

**Success Metrics:**
- 5,000+ monthly active users (free tier)
- 5% click "Upgrade" button
- 10% of those convert = 25 paying customers/month

**Revenue Target:** $5-7K MRR by Month 3

---

#### Phase 2 (Months 4-6): Monetize + Inner West Focus
**Build:**
- Automated feasibility checker (Inner West only)

**Launch:**
- Premium tier: $99/month for professionals
- Target Inner West real estate agents (300+ agencies)

**Success Metrics:**
- 50+ paying subscribers
- $5K+ MRR
- <30% churn month-over-month

**Revenue Target:** $10-15K MRR by Month 6

---

#### Phase 3 (Months 7-12): Scale or Pivot
**If Phase 2 Successful:**
- Expand compliance engine to 2-3 more councils
- Build ML approval prediction model
- Raise angel round ($100-150K)

**If Struggling:**
- Pivot to pure analytics (Chart-Viewer focus)
- Drop compliance complexity
- Partner with established players

**Decision Criteria:**
- $10K+ MRR = continue independent growth
- $5-10K MRR = raise capital to accelerate
- <$5K MRR = pivot or partner

---

### 5.2 Distribution Strategy

#### Channel 1: SEO Content Marketing
**Effort:** 10-15 hours/week
**Timeline:** 3-6 months to traction

**Content Types:**
1. Hyper-specific guides ("Can I subdivide in Marrickville? 2025 guide")
2. Data journalism ("We analyzed 1,000 Inner West DAs - here's what gets approved")
3. Comparison articles ("Marrickville vs Leichhardt for development: Data comparison")
4. Regulatory updates ("Inner West DCP changes 2025: What developers need to know")

**SEO Strategy:**
- Target long-tail keywords (low competition, high intent)
- Include unique data/charts (Chart-Viewer screenshots)
- Answer specific questions (People Also Ask)
- Internal linking to paid reports

**Expected Results:**
- Month 1-2: 500 visitors/month
- Month 3-4: 2,000 visitors/month
- Month 5-6: 5,000+ visitors/month
- 2-5% conversion to email signup
- 10-20% email-to-paid conversion

---

#### Channel 2: Real Estate Agent Partnerships
**Effort:** 5 hours/week
**Timeline:** 1-3 months to first partner

**Outreach Strategy:**
1. Identify Inner West agencies (300+ total)
2. Cold email with free trial offer
3. Provide 3 free reports (worth $597)
4. Ask for feedback + testimonial
5. Convert to $99/month unlimited

**Email Template:**
```
Subject: Free tool for your Inner West buyers

Hi [Agent Name],

I built a property intelligence tool specifically for Inner West - shows zoning, recent DA approvals, and development potential in seconds.

I'm offering free reports for your next 3 buyer clients (worth $199 each) to get feedback.

Interested? Just send me the addresses.

[Your Name]
Inner West Property Intelligence
[Link to tool]
```

**Expected Results:**
- 10% response rate (30 agents interested)
- 30% conversion to trial (9 agents try it)
- 33% trial-to-paid (3 paying agents @ $99/month)

---

#### Channel 3: Social Media + Community
**Effort:** 3-5 hours/week
**Timeline:** Immediate, ongoing

**Platforms:**
1. Reddit (r/Sydney, r/AusProperty)
2. Facebook groups (Inner West BSS, Sydney Property Investors)
3. LinkedIn (property professionals)

**Content Strategy:**
- Share genuinely helpful insights ("I analyzed 1,000 DAs...")
- Answer questions in comments
- NO direct selling (profile link only)
- Build reputation as data expert

**Expected Results:**
- Month 1: 1-2 paying customers from organic reach
- Month 2-3: 3-5 customers/month
- Month 4+: Snowball effect (reputation established)

---

#### Channel 4: Google My Business
**Effort:** 1 hour setup + 30 min/week
**Timeline:** 2-3 months to ranking

**Setup:**
- Business name: "Inner West Property Development Intelligence"
- Category: "Real Estate Consultant"
- Service area: All Inner West suburbs
- Weekly posts (auto via n8n)

**Expected Results:**
- Appear in "property development planning near me" searches
- 5-10 inquiries/month from local search

---

### 5.3 Customer Acquisition Cost (CAC) Estimates

**Channel Performance:**
| Channel | CAC | LTV (12mo) | LTV:CAC Ratio | Scalability |
|---------|-----|------------|---------------|-------------|
| SEO Content | $20 | $199-299 | 10-15x | High |
| Agent Partnerships | $50 | $1,188 | 24x | Medium |
| Social/Community | $10 | $199-299 | 20-30x | Low |
| Google My Business | $15 | $199-299 | 13-20x | Medium |

**Target Blended CAC:** $30 (85% margin at $199 price point)

---

## PART 6: FINANCIAL PROJECTIONS

### 6.1 Conservative 12-Month Forecast

#### Revenue Streams
| Stream | Month 1 | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|---------|----------|
| One-time reports ($199) | $600 | $2,000 | $4,000 | $6,000 |
| Agent subscriptions ($99/mo) | $0 | $300 | $1,000 | $2,500 |
| Pro subscriptions ($199/mo) | $0 | $0 | $400 | $1,200 |
| Custom reports ($499) | $0 | $500 | $500 | $1,000 |
| **Total MRR** | $600 | $2,800 | $5,900 | $10,700 |

#### Cost Structure
| Expense | Monthly |
|---------|---------|
| Infrastructure (hosting, DBs) | $50 |
| Tools (Stripe, email, etc) | $30 |
| Marketing | $200 |
| **Total Monthly Costs** | $280 |

**Gross Margin:** 95% (digital product, minimal COGS)
**Net Margin:** 80-85% (after fixed costs)

#### Year 1 Summary
- **Total Revenue:** $52K
- **Total Costs:** $3.4K
- **Net Profit:** $48.6K
- **Customer Acquisition:** 300 one-time + 40 subscribers
- **Time Investment:** 30 hours/week

**Hourly Effective Rate:** $48.6K / 1,560 hours = $31/hour

*(Note: Low hourly rate in Year 1 is investment in building asset. Year 2+ improves dramatically with compounding growth and reduced time investment)*

---

### 6.2 Moderate Growth Scenario (With Angel Investment)

**Assumptions:**
- Month 6: Raise $100K at 10% equity
- Hire part-time developer ($2K/month)
- Marketing budget ($3K/month)
- Expand to 3 more councils

#### Revenue Projections (With Investment)
| Month | MRR | Growth Rate |
|-------|-----|-------------|
| 6 | $5,900 | Baseline |
| 7 | $7,700 | 30% |
| 8 | $10,000 | 30% |
| 9 | $13,000 | 30% |
| 10 | $16,900 | 30% |
| 11 | $22,000 | 30% |
| 12 | $28,600 | 30% |

#### Cost Structure (With Investment)
| Expense | Monthly |
|---------|---------|
| Infrastructure | $200 |
| Developer contractor | $2,000 |
| Marketing (ads + SEO) | $3,000 |
| Your salary | $3,000 |
| **Total Monthly Costs** | $8,200 |

#### Year 1 Summary (Months 7-12)
- **Revenue:** $98,200 (Months 7-12 only)
- **Costs:** $49,200
- **Burn:** $8.2K/month avg
- **Runway:** 12 months from $100K raise
- **Exit Month 12:** $28.6K MRR ($343K ARR run rate)

**Valuation at Month 12:**
- ARR: $343K
- Multiple: 3-5x for SaaS
- Estimated valuation: $1-1.7M
- Your ownership: 90% = $900K-1.5M paper value

---

## PART 7: CRITICAL RISKS & MITIGATIONS

### Risk 1: NSW Planning Portal Could Add These Features
**Likelihood:** Medium (government sites notoriously slow to innovate)
**Impact:** High (would commoditize your offering)

**Mitigation:**
- Focus on UX and speed (government sites are slow)
- Build proprietary data moat (ML models, historical analysis)
- Aim to become de facto standard
- Partner with government as official provider (rather than compete)

---

### Risk 2: Limited Compliance Engine Coverage
**Likelihood:** Certain (only Inner West works today)
**Impact:** Medium (limits addressable market)

**Mitigation:**
- Market Inner West focus as strength ("Most comprehensive Inner West tool")
- Dominate one market before expanding
- Expand only after proving model works
- Use profits to fund expansion (not debt/dilution)

---

### Risk 3: Professional Indemnity Liability
**Likelihood:** Low (if proper disclaimers used)
**Impact:** Critical (could shut down business)

**Mitigation:**
- Clear disclaimers ("Information only, not professional advice")
- Never claim to replace consultants
- Always cite official sources
- Recommend users verify with professionals
- Get professional indemnity insurance ($500-1K/year)

---

### Risk 4: Consultants See You as Threat
**Likelihood:** Medium (some will resist)
**Impact:** Low-Medium (word-of-mouth damage)

**Mitigation:**
- Position as tool FOR consultants (makes their job easier)
- Partner with firms for referrals
- White-label offering (they rebrand as their tool)
- Emphasize "preliminary screening" not "final advice"

---

### Risk 5: Data Quality Issues
**Likelihood:** Low (NSW Planning Portal is authoritative)
**Impact:** High (erodes trust)

**Mitigation:**
- Daily data syncs (stay current)
- Version control (track when data changed)
- User reporting (flag errors)
- Manual QA checks (sample 10% monthly)
- Insurance for errors & omissions

---

## PART 8: SUCCESS METRICS & KPIs

### North Star Metric
**Monthly Recurring Revenue (MRR)** - captures both volume and value

### Supporting Metrics

#### Product Metrics
- Free users (monthly actives)
- Free-to-paid conversion rate
- Paid customer count
- Average revenue per user (ARPU)
- Net revenue retention (NRR)

#### Growth Metrics
- Month-over-month growth rate
- Customer acquisition cost (CAC)
- Lifetime value (LTV)
- LTV:CAC ratio
- Payback period

#### Engagement Metrics
- Reports generated per user
- Features used (which are valuable?)
- Return usage (weekly active users)
- Churn rate

### Milestone Targets

**Month 3:** $2K MRR, 15 paying customers
**Month 6:** $5K MRR, 40 paying customers
**Month 9:** $10K MRR, 80 paying customers
**Month 12:** $20K MRR, 150 paying customers

**Decision Gates:**
- Month 3 < $1K MRR → Pivot or stop
- Month 6 > $5K MRR → Raise angel round
- Month 12 > $20K MRR → Raise Series A or stay profitable

---

## PART 9: RECOMMENDED IMMEDIATE ACTIONS

### Week 1: Foundation
- [ ] Choose domain name + setup hosting
- [ ] Create landing page for "Inner West Development Report" ($199)
- [ ] Set up Stripe payment processing
- [ ] Create PDF report template (manual delivery initially)
- [ ] Write 3 SEO blog posts (publish schedule)

### Week 2: Distribution Setup
- [ ] Set up Google My Business
- [ ] Create n8n workflow: Blog → Social media auto-post
- [ ] Join 10 Sydney property Facebook groups
- [ ] Set up Google Analytics + conversion tracking
- [ ] Email 30 Inner West real estate agents (free trial offer)

### Week 3: Content + Marketing
- [ ] Write 7 more blog posts (queue in CMS)
- [ ] Post in Reddit/Facebook (genuine help, not spam)
- [ ] Set up email capture (lead magnet: "Free Inner West Zoning Guide")
- [ ] Create email nurture sequence (5 emails over 14 days)
- [ ] Track metrics: Visitors, signups, paying customers

### Week 4: Iteration
- [ ] If 2+ sales: Start automating report generation
- [ ] If 0 sales: Interview 5 potential customers (why didn't they buy?)
- [ ] Double down on top-performing content
- [ ] Plan Month 2 feature additions (Tier 1 from this document)
- [ ] Decide: Continue bootstrap, or start grant applications?

---

## APPENDICES

### Appendix A: Target Keywords (SEO)
1. "can I subdivide in Marrickville"
2. "Leichhardt second storey addition"
3. "Inner West dual occupancy"
4. "Ashfield DCP requirements"
5. "development potential Inner West"
6. "Marrickville R2 zoning"
7. "Inner West DA approval time"
8. "property development Leichhardt"
9. "Ashfield heritage overlay"
10. "Inner West BASIX requirements"

### Appendix B: Email Templates
*(See growth strategies document for detailed templates)*

### Appendix C: Feature Prioritization Matrix
| Feature | Effort | Value | ROI | Priority |
|---------|--------|-------|-----|----------|
| Comparable DAs | 80h | High | 9/10 | P0 |
| BASIX Guidance | 80h | Med | 7/10 | P0 |
| Council Dashboard | 120h | Med | 6/10 | P1 |
| Feasibility Checker | 160h | High | 8/10 | P1 |
| ML Approval Score | 240h | High | 7/10 | P2 |

---

**Document Version:** 1.0
**Last Updated:** 2025-10-23
**Next Review:** After Month 3 results
