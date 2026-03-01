# Agricultural Water Rights Market Research & Product Requirements

**Date:** 2025-10-28
**Status:** Comprehensive Market Analysis
**Purpose:** Competition analysis, market targeting, go-to-market strategy, and detailed product requirements

---

## Executive Summary

**Market Opportunity:** Agricultural water compliance/allocation tracking is a **$50M+ underserved market** in Australia with:
- ✅ **NO comprehensive SaaS competitors** (existing solutions are fragmented)
- ✅ **Severe pain point** - over-extraction penalties up to $2.2M, farmers track manually
- ✅ **Regulatory tailwind** - mandatory telemetry rollout (95% metered by 2026)
- ✅ **Proven willingness to pay** - farmers currently pay $2K-10K for annual compliance audits
- ✅ **Clear ROI** - avoiding one penalty ($50K-2M) justifies 10+ years of subscription

**Competitive Landscape:**
- Water **trading** platforms exist (WaterExchange, Waterfind) but don't do compliance/allocation tracking
- Farm management software (Trimble, Granular) has irrigation scheduling but NOT regulatory compliance
- AQUAOSO (USA) focuses on water risk analytics for lenders, not farmer compliance

**Best Target Market:** Murrumbidgee Irrigation Area (MIA)
- 2,300+ farmers, 1,319 GL annual usage, $5B economic contribution
- Most sophisticated water market in Australia
- High compliance requirements, tech-savvy farmers

**Go-to-Market Strategy:** Partner with Murrumbidgee Irrigation (the infrastructure provider) for white-label deployment to their 2,300 customers

**Revenue Potential:**
- Year 1: 200 MIA farmers @ $75/month = $180K ARR
- Year 2: 1,000 farmers across 3 valleys = $900K ARR
- Year 3: 3,000 farmers + irrigation corporations = $2.5M ARR

---

## Table of Contents

1. [Competitive Landscape Analysis](#competitive-landscape-analysis)
2. [Best Market Targets](#best-market-targets)
3. [Optimal Market Approach](#optimal-market-approach)
4. [Product Requirements: Real-time Allocation Dashboard](#product-requirements-allocation-dashboard)
5. [Product Requirements: Usage Tracking](#product-requirements-usage-tracking)
6. [Product Requirements: Compliance Alerts](#product-requirements-compliance-alerts)
7. [Technical Architecture](#technical-architecture)
8. [Go-to-Market Roadmap](#go-to-market-roadmap)

---

## Competitive Landscape Analysis

### Category 1: Water Trading Platforms 🔵 NOT DIRECT COMPETITORS

#### **WaterExchange**
- **Founded:** 2002
- **Focus:** Water entitlement and allocation trading marketplace
- **Coverage:** Entire Murray-Darling Basin
- **Features:**
  - Buy/sell water allocations (temporary) and entitlements (permanent)
  - 10,000+ trades processed online since 2002
  - Exchange-based platform (bid/ask matching)
  - Entitlement auction system
  - Approval authority portal (water authorities approve/refuse trades digitally)
- **Pricing:** Brokerage fees (typically 1-3% of trade value)
- **Customer Base:** Irrigators, farmers, investors, water brokers

**Gap They Don't Fill:**
- ❌ No allocation tracking (farmers don't know how much water they have left)
- ❌ No usage monitoring (no integration with water meters)
- ❌ No compliance alerts (no warning when approaching limits)
- ❌ No regulatory intelligence (water sharing plan changes)

**Positioning vs. WaterExchange:** Complementary, not competitive
- WaterRight tracks your allocation and usage
- When you need more water, WaterRight links to WaterExchange to buy
- Integration opportunity: "You need 50ML - click to buy on WaterExchange"

---

#### **Waterfind**
- **Founded:** 2003
- **Focus:** Water brokering services (human brokers + online platform)
- **Coverage:** Australia-wide (MDB focus)
- **Features:**
  - 24/7 online water market (desktop + mobile)
  - Water brokering (permanent transfers, temporary trades)
  - Market intelligence (allocation announcements, price trends)
  - Water Sharing Plan summaries (static PDFs)
- **Pricing:** Brokerage fees
- **Customer Base:** 1,000s of farmers, institutional investors

**Gap They Don't Fill:**
- ❌ Static allocation announcements (not integrated with farmer's account)
- ❌ No personal allocation tracking ("your farm has 80ML left")
- ❌ No usage tracking or compliance monitoring
- ❌ Broker-centric (farmers still need to call/email for guidance)

**Positioning vs. Waterfind:**
- WaterRight automates what Waterfind does manually
- Waterfind provides market intelligence as PDF reports → WaterRight provides real-time dashboard
- Potential partnership: Waterfind white-labels WaterRight for their clients

---

### Category 2: Farm Management Software 🟡 PARTIAL OVERLAP

#### **Trimble Ag Software**
- **Focus:** GPS-guided precision agriculture
- **Features:**
  - Field planning, crop yield logging
  - Fleet management (tractors, harvesters)
  - **Irrigation optimization** (Trimble irrigation module)
  - Soil moisture monitoring
  - Real-time data on crop performance
- **Pricing:** $500-2,000/year (varies by modules)
- **Australian Presence:** Yes, significant market share

**Water Management Capabilities:**
- ✅ Irrigation scheduling (when to irrigate based on soil moisture)
- ✅ Water application optimization (reduce waste)
- ❌ NO regulatory allocation tracking (doesn't know your water entitlement)
- ❌ NO compliance with Water Sharing Plans
- ❌ NO integration with WaterNSW allocation announcements

**Positioning vs. Trimble:**
- Trimble = agronomic efficiency ("use water optimally for crop yield")
- WaterRight = regulatory compliance ("don't exceed your legal allocation")
- **Integration opportunity:** WaterRight API feeds allocation data to Trimble
  - Trimble schedules irrigation, checks with WaterRight: "Can I use 50ML today?"
  - If farmer has 30ML left, Trimble adjusts irrigation plan

---

#### **Granular** (Corteva Agriscience)
- **Focus:** Farm financial management and field operations
- **Features:**
  - Crop planning, budgeting, ROI analysis
  - Field activity logging (planting, spraying, harvest)
  - Financial planning (connects field data with invoices/budgets)
  - Granular Insights for farm advisors
- **Pricing:** $600-1,500/year
- **Australian Presence:** Limited (more popular in USA)

**Water Management Capabilities:**
- ✅ Irrigation cost tracking ($/ML spent)
- ❌ NO regulatory compliance
- ❌ NO water allocation tracking

**Positioning vs. Granular:** Non-overlapping
- Granular is financial planning tool
- WaterRight is compliance/regulatory tool
- Farmers might use both (Granular for budgets, WaterRight for water compliance)

---

#### **FarmLogs**
- **Focus:** Simple, user-friendly farm record-keeping
- **Features:**
  - Field activity logging (scouting, planting, harvest)
  - Soil moisture alerts
  - Historical disease alerts
  - Rainfall tracking
- **Pricing:** Free tier + $500/year premium
- **Australian Presence:** Minimal

**Water Management Capabilities:**
- ✅ Rainfall tracking, soil moisture alerts
- ❌ NO water allocation tracking
- ❌ NO regulatory compliance

**Positioning vs. FarmLogs:** Different market segment
- FarmLogs targets small-scale farmers (simple record-keeping)
- WaterRight targets irrigation farmers with water entitlements (compliance-focused)

---

### Category 3: Water Risk Analytics 🟠 USA-FOCUSED (NOT AUSTRALIAN COMPETITOR)

#### **AQUAOSO** (USA)
- **Founded:** ~2017
- **Focus:** Water risk analytics for agricultural lenders and investors
- **Geography:** USA (California primary market)
- **Features:**
  - Map-based water research tool
  - Parcel-level water security scoring
  - Groundwater allocation analysis (California SGMA compliance)
  - Climate stress testing
  - Multi-parcel PDF reports
  - GIS Connect (integrate location data with financial data)
- **Pricing:** Not publicly disclosed (likely $5K-20K/year for lenders)
- **Customer Base:** 30%+ of California agricultural lenders, institutional investors, insurance companies

**Why AQUAOSO Hasn't Entered Australia:**
- USA water rights are extremely complex (state-by-state, prior appropriation vs. riparian)
- California SGMA (Sustainable Groundwater Management Act) created massive compliance market
- AQUAOSO's data infrastructure is US-specific (USGS, California DWR, etc.)

**Gap in Australian Market:**
- ❌ NO AQUAOSO equivalent for Murray-Darling Basin
- ❌ NO SaaS platform for Australian water risk analytics
- ❌ Australian farmers/lenders lack data-driven water security tools

**AQUAOSO's Value Proposition (We Can Replicate):**
- Cut water research time by 85% (month's work → minutes)
- Location-based intelligence (parcel → water entitlement → allocation → risk score)
- Evergreen data updates (no manual PDF chasing)
- Export reports (PDF, HTML, XLS)

**Positioning vs. AQUAOSO:**
- AQUAOSO = lender risk assessment ("Is this farm a safe loan?")
- WaterRight = farmer operational compliance ("Am I staying within my allocation?")
- Both are complementary (lenders could use both)

**Opportunity:** Build "AQUAOSO for Australia" targeting:
1. **Farmers** (allocation/compliance tracking) - PRIMARY
2. **Agricultural lenders** (water risk scoring for loan underwriting) - SECONDARY
3. **Investors** (due diligence on agricultural land) - TERTIARY

---

### Category 4: Government Portals 🔴 BASELINE (NOT COMPETITORS, BUT SUBSTITUTES)

#### **NSW WaterNSW Portals**

**iWAS (Online Water Accounting System)**
- **Free** for registered WaterNSW customers
- **Features:**
  - View water account balance
  - All transactions (allocations credited, water usage debited)
  - Order water (release from storage)
  - Trade water (submit transfer applications)
- **Access:** 24/7 online portal, requires account login

**Limitations:**
- ❌ **Read-only for allocation data** (no API for programmatic access)
- ❌ **Manual usage entry** (farmers must log extractions themselves)
- ❌ **No telemetry integration** (even if farmer has smart meter, iWAS doesn't auto-sync)
- ❌ **No predictive alerts** ("you'll exceed allocation in 14 days at current usage")
- ❌ **No compliance intelligence** (doesn't warn about Water Sharing Plan restrictions)
- ❌ **Clunky UX** (government portal, not user-friendly)

**Allocation Announcements**
- **Published:** NSW Department of Planning & Environment website
- **Format:** PDF statements (updated weekly/biweekly during irrigation season)
- **Coverage:** Each valley (Murrumbidgee, Murray, Lachlan, etc.) publishes separately
- **Content:**
  - Allocation percentages (e.g., "General Security allocation increased to 45%")
  - Storage levels, rainfall, inflows
  - Supplementary access announcements (flood flows available)

**Limitations:**
- ❌ **Manual tracking** (farmer must read PDF, calculate their allocation)
- ❌ **No centralized view** (if farmer has entitlements in multiple valleys, must check 3+ PDFs)
- ❌ **No historical tracking** (past announcements archived, hard to see trends)
- ❌ **No personalization** ("your allocation changed" vs. "general security changed")

**WaterNSW API Developer Portal**
- **Exists:** api-portal.waternsw.com.au
- **Available Data:**
  - Hydrometric data (stream levels, dam levels)
  - Water quality data
  - Weather data (Bureau of Meteorology stations)
- **Limitations:**
  - ❌ **NO allocation data API** (allocation announcements not in API)
  - ❌ **NO water account API** (iWAS data not accessible programmatically)
  - ❌ Monitoring data only (useful for surface water availability, not personal allocations)

**Opportunity for WaterRight:**
- Government portals provide data but terrible UX
- WaterRight scrapes allocation announcements (PDFs) → structures into database
- Matches announcements to farmer's entitlements → "Your allocation: 180ML (up from 160ML)"
- Eventually negotiate API access with WaterNSW (if we prove value with 1,000+ users)

---

#### **Victorian Water Authority Portals** (Goulburn-Murray Water, Southern Rural Water, etc.)
- Similar to NSW (clunky portals, PDF announcements)
- Slightly better telemetry adoption (50%+ of meters have telemetry in irrigation districts)
- Same gaps (no predictive alerts, no compliance intelligence)

---

### Category 5: Compliance Consulting 💼 HUMAN-POWERED (OUR PRIMARY SUBSTITUTES)

**Water Resource Consultants**
- **Services:**
  - Annual compliance audits ($2K-10K per farm)
  - Water Sharing Plan interpretation
  - Overdrawn account remediation (when farmer exceeds allocation)
  - Water trading advice (optimal buy/sell timing)
  - Expert witness (if farmer faces enforcement action)
- **Pricing:** $150-300/hour, or annual retainers ($5K-50K)
- **Examples:**
  - Aither (water economics consultancy)
  - Marsden Jacob Associates
  - Independent consultants (ex-government water planners)

**Limitations of Consultants:**
- ❌ **Not scalable** (human time = expensive)
- ❌ **Reactive** (farmer calls consultant when problem arises)
- ❌ **No real-time monitoring** (consultant reviews accounts quarterly/annually)
- ❌ **High cost for small farmers** ($10K retainer unrealistic for farm with 100ML entitlement)

**WaterRight Value Proposition vs. Consultants:**
- Automates 80% of what consultants do (allocation tracking, compliance monitoring)
- $75/month ($900/year) vs. $5K-10K/year consultant
- Proactive alerts vs. reactive advice
- 24/7 monitoring vs. quarterly reviews
- Consultants still needed for complex issues (enforcement, appeals) → WaterRight doesn't replace, it reduces dependency

---

## Competitive Summary Matrix

| Competitor | Category | Overlap with WaterRight | Threat Level | Partnership Opportunity |
|------------|----------|------------------------|--------------|------------------------|
| **WaterExchange** | Trading Platform | 10% (market intelligence) | LOW | HIGH (buy water integration) |
| **Waterfind** | Water Broker | 20% (allocation announcements) | LOW | HIGH (white-label for clients) |
| **Trimble Ag** | Farm Mgmt Software | 30% (irrigation optimization) | MEDIUM | HIGH (API integration) |
| **Granular** | Farm Financial Mgmt | 10% (cost tracking) | LOW | MEDIUM (data sharing) |
| **FarmLogs** | Simple Record-Keeping | 5% (rainfall tracking) | LOW | LOW |
| **AQUAOSO** | Water Risk (USA) | 40% (if they entered AU market) | LOW (geo-limited) | LOW (different market) |
| **WaterNSW iWAS** | Government Portal | 60% (water account view) | LOW (terrible UX) | CRITICAL (data source) |
| **Consultants** | Human Services | 80% (compliance audits) | MEDIUM | HIGH (refer complex cases) |

**Key Insight:** There is **NO direct SaaS competitor** offering comprehensive allocation tracking + usage monitoring + compliance alerts for Australian farmers. The market is **wide open**.

---

## Best Market Targets

### Target Valley Selection Criteria

| Criterion | Weight | Murrumbidgee | Murray | Lachlan | Namoi | Gwydir |
|-----------|--------|-------------|--------|---------|-------|--------|
| **Farmer Count** | 25% | ⭐⭐⭐⭐⭐ (2,300+) | ⭐⭐⭐⭐⭐ (2,400+) | ⭐⭐⭐⭐ (800+) | ⭐⭐⭐ (500+) | ⭐⭐ (300+) |
| **Water Volume** | 20% | ⭐⭐⭐⭐⭐ (1,319 GL) | ⭐⭐⭐⭐⭐ (1,500+ GL) | ⭐⭐⭐⭐ (400 GL) | ⭐⭐⭐ (300 GL) | ⭐⭐ (200 GL) |
| **Economic Value** | 15% | ⭐⭐⭐⭐⭐ ($5B) | ⭐⭐⭐⭐⭐ ($6B) | ⭐⭐⭐⭐ ($1.5B) | ⭐⭐⭐ ($800M) | ⭐⭐ ($400M) |
| **Tech Sophistication** | 15% | ⭐⭐⭐⭐⭐ (high) | ⭐⭐⭐⭐ (med-high) | ⭐⭐⭐⭐ (medium) | ⭐⭐⭐ (medium) | ⭐⭐ (low) |
| **Compliance Pressure** | 15% | ⭐⭐⭐⭐⭐ (very high) | ⭐⭐⭐⭐⭐ (very high) | ⭐⭐⭐⭐ (high) | ⭐⭐⭐⭐ (high) | ⭐⭐⭐ (medium) |
| **Telemetry Adoption** | 10% | ⭐⭐⭐⭐ (60%+) | ⭐⭐⭐⭐ (65%+) | ⭐⭐⭐ (50%) | ⭐⭐⭐ (45%) | ⭐⭐ (30%) |
| **TOTAL SCORE** | 100% | **96/100** | **94/100** | **78/100** | **68/100** | **44/100** |

### Recommended Target: Murrumbidgee Valley 🥇

**Why Murrumbidgee First:**

1. **Infrastructure Partner Available**
   - **Murrumbidgee Irrigation (MI)** is the infrastructure operator (canals, channels)
   - MI serves 2,300+ shareholder customers across 378,911 hectares
   - MI already provides water delivery → natural partner for compliance tool
   - **White-label opportunity:** MI could offer WaterRight as value-added service to customers

2. **Most Sophisticated Market**
   - Murrumbidgee farmers are among most tech-savvy in Australia
   - High adoption of precision agriculture (Trimble, soil moisture sensors)
   - Already use water trading platforms (active WaterExchange/Waterfind users)
   - Comfortable with software subscriptions ($500-2,000/year typical)

3. **High Compliance Pressure**
   - Water Sharing Plan is complex (6 different allocation categories)
   - High enforcement activity by NSW NRAR (Natural Resources Access Regulator)
   - Recent high-profile prosecutions ($500K+ fines for over-extraction)
   - Farmers anxious about compliance (perfect pain point)

4. **Strong Economic Base**
   - $5 billion annual economic contribution
   - High-value crops (wine grapes, rice, vegetables, orchards)
   - Water is valuable ($200-400/ML temporary market price)
   - Farmers can afford $75-150/month subscription

5. **Data Infrastructure Ready**
   - 60%+ of farms have telemetry on water meters
   - MI operates centralized water ordering system (integration opportunity)
   - Good internet connectivity (rural broadband available)

**Farmer Profile (Murrumbidgee):**
- **Farm size:** 100-500 hectares typical
- **Water entitlement:** 200-2,000 ML (median ~500 ML)
- **Crops:** Rice, wine grapes, citrus, vegetables, cotton
- **Age:** 45-65 years (older farmers, some tech adoption)
- **Tech comfort:** Medium-high (use Trimble guidance, online banking, water trading platforms)
- **Income:** $200K-2M gross revenue per farm

**TAM (Total Addressable Market) - Murrumbidgee:**
- 2,300 farms × $75/month = $2.07M annual revenue potential (at 100% penetration)
- Realistic Year 1 target: 5% penetration (115 farms) = $103K ARR
- Realistic Year 3 target: 30% penetration (690 farms) = $621K ARR

---

### Secondary Target: Murray Irrigation District 🥈

**Why Murray Second:**

1. **Largest Farmer Base**
   - Murray Irrigation Limited (MIL) serves 2,400+ customers
   - 748,000 hectares of farmland
   - Similar infrastructure operator model to Murrumbidgee Irrigation

2. **Very Active Water Market**
   - Highest volume of water trades in MDB
   - Farmers are sophisticated water traders
   - Strong use of temporary allocation market

3. **Good Telemetry Adoption**
   - 65%+ of meters have telemetry (higher than Murrumbidgee)
   - WaterWell platform (MIL's customer portal) could integrate with WaterRight

4. **Challenges:**
   - More geographically dispersed than Murrumbidgee (harder to build local brand)
   - MIL may want to build in-house tool (competitive threat)
   - Recommend: Launch AFTER proving model in Murrumbidgee

**TAM - Murray:**
- 2,400 farms × $75/month = $2.16M annual revenue potential

---

### Tertiary Target: Lachlan Valley 🥉

**Why Lachlan Third:**

1. **Medium-Sized Market**
   - 800+ water entitlement holders
   - Good mix of irrigators and dryland farmers
   - Less competitive than Murrumbidgee/Murray

2. **High Water Stress**
   - Lachlan is more drought-prone (lower allocation reliability)
   - Farmers very price-sensitive to water (high value)
   - Compliance anxiety is high

3. **Challenges:**
   - Lower tech adoption than Murrumbidgee
   - Smaller average farm sizes (less revenue per customer)
   - Limited telemetry adoption (40-50%)

**TAM - Lachlan:**
- 800 farms × $75/month = $720K annual revenue potential

---

### Markets to AVOID (Initially)

**Namoi Valley** ❌
- High groundwater extraction (more complex regulation)
- Lower farmer density (harder customer acquisition)
- Recent compliance scandals (farmers may distrust software)

**Gwydir Valley** ❌
- Small market (300 farmers)
- Low tech adoption
- Primarily cotton (seasonal water demand, not year-round)

**Groundwater-Only Regions** ❌
- Groundwater compliance is even more complex (depth restrictions, interference rules)
- Recommendation: Launch with surface water first, add groundwater in Year 2

---

## Optimal Market Approach

### Phase 1: Murrumbidgee Valley Pilot (Months 1-6)

**Strategy:** Partner with Murrumbidgee Irrigation (MI) for co-marketing

**Step 1: Secure MI Partnership (Month 1-2)**

**Approach:**
1. **Initial meeting with MI leadership**
   - Present WaterRight as value-added service for their 2,300 customers
   - Position as "white-label compliance tool" (MI branding optional)
   - Revenue share model: MI gets 20% of subscription revenue from their customers
   - MI benefits:
     - Customer retention (farmers less likely to leave MI service area)
     - Risk reduction (compliant customers = fewer NRAR enforcement actions)
     - Modern image (MI seen as tech-forward)

2. **Pilot proposal:**
   - Free trial for 20 MI customers (hand-selected by MI)
   - 3-month pilot (irrigation season: Oct-Jan)
   - Success criteria:
     - 80%+ pilot users say they'd pay $75/month
     - Zero over-extraction events among pilot users
     - 90%+ user satisfaction score

3. **Data integration:**
   - Negotiate access to MI's water ordering system data (when farmers order water releases)
   - Potential integration with MI's telemetry infrastructure (if they have centralized monitoring)

**Expected Outcome:**
- MI agrees to pilot (high probability - low risk for them, high value for farmers)
- 20 pilot users recruited by end of Month 2

---

**Step 2: Build MVP + Pilot (Month 2-4)**

**Development:**
- 90% code reuse from planning compliance platform
- New components:
  - Allocation announcement scraper (NSW DPIE PDFs)
  - Water account parser (if iWAS API unavailable, web scraping)
  - Telemetry integration (common protocols: LoRaWAN, NB-IoT, cellular)
- Timeline: 6-8 weeks development

**Pilot Launch:**
- Onboard 20 MI customers (hand-holding, in-person training)
- Weekly check-ins (gather feedback, identify bugs)
- Iterate rapidly (2-week sprints for feature additions)

---

**Step 3: Pilot Results + Launch Preparation (Month 5-6)**

**Success Metrics:**
- Pilot user feedback: "Would you pay $75/month?" (target: 80% yes)
- Usage frequency: Daily active users (target: 50%+ of pilots check app daily during irrigation season)
- Value demonstration:
  - Count of "near-miss" alerts (farmer was about to exceed allocation, WaterRight warned them)
  - Estimated penalty avoidance (if 3 farmers avoided over-extraction, saved $50K-500K in fines)

**Launch Preparation:**
- Pricing finalization (pilot tested $75/month, adjust if needed)
- Sales materials (case studies from pilot farmers)
- Partnership agreement with MI (finalize revenue share, co-marketing terms)

---

### Phase 2: Murrumbidgee Valley Expansion (Months 7-12)

**Strategy:** Scale from 20 pilots to 200 paying customers (10% of MI customer base)

**Marketing Channels:**

1. **MI Direct Marketing** (Primary Channel)
   - MI sends email to all 2,300 customers: "New compliance tool available"
   - MI includes flyer in water bill (quarterly)
   - MI mentions at farmer meetings (MI hosts regular customer forums)
   - Expected conversion: 5-10% (115-230 signups)

2. **Peer Referral** (Secondary Channel)
   - Pilot farmers refer neighbors (word-of-mouth in tight-knit farming community)
   - Referral incentive: "Refer 3 farmers, get 1 month free"
   - Expected: 20-40 signups

3. **Trade Shows / Field Days** (Tertiary Channel)
   - Attend Murrumbidgee field days (annual farm expos)
   - Demo at precision agriculture events
   - Expected: 10-20 signups

4. **Facebook / Rural Press** (Awareness)
   - Ads in "The Land" newspaper (rural farming weekly)
   - Facebook ads targeted to Murrumbidgee postcodes (2680, 2650, 2700s)
   - Expected: 5-10 signups

**Pricing:**
- **Base tier:** $75/month (up to 500 ML entitlement)
- **Pro tier:** $150/month (500-2,000 ML entitlement, includes trading recommendations)
- **Enterprise tier:** $300/month (2,000+ ML, includes consultant hotline)

**Expected Revenue (Month 12):**
- 200 paying customers (mix of tiers, avg $90/month) = $216K ARR

---

### Phase 3: Multi-Valley Expansion (Year 2)

**Strategy:** Launch in Murray + Lachlan valleys

**Murray Valley Approach:**
- Similar partnership model with Murray Irrigation Limited (MIL)
- Leverage Murrumbidgee case studies ("200 farmers saved $X in compliance costs")
- Target: 300 Murray customers (12.5% penetration) = $324K ARR

**Lachlan Valley Approach:**
- No single dominant irrigation operator (more fragmented)
- Direct-to-farmer marketing (Facebook, rural press, field days)
- Target: 100 Lachlan customers (12.5% penetration) = $108K ARR

**Year 2 Total Revenue:** $648K ARR (200 Murrumbidgee + 300 Murray + 100 Lachlan + 48 other)

---

### Phase 4: Platform Expansion (Year 3)

**New Features:**
1. **Water trading integration** (WaterExchange/Waterfind API)
   - "You need 50ML - current market price $180/ML - buy now?"
2. **Irrigation district expansion** (Queensland, Victoria)
   - QLD: Sunwater schemes (Dawson, Nogoa, etc.)
   - VIC: Goulburn-Murray Water
3. **Lender/investor tier** (AQUAOSO-style water risk analytics)
   - Sell to agricultural banks (ANZ, NAB, Rabobank)
   - Pricing: $10K-50K/year enterprise license
4. **Consultant white-label** (Aither, MJA can resell to their clients)

**Year 3 Revenue:** $2.5M ARR (3,000 farmers + 5 enterprise customers)

---

## Product Requirements: Real-time Allocation Dashboard

### Overview

**Purpose:** Display farmer's current water allocation in real-time, personalized to their specific entitlements across multiple water sources.

**User Story:**
> "As a farmer with 500 ML of General Security allocation in the Murrumbidgee Valley, I want to see my current allocation balance at a glance, so I know how much water I can use this season without exceeding my entitlement."

---

### Feature 1.1: Water Account Summary Card

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  💧 Water Account Summary                                   │
│  Updated: 15 minutes ago                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Total Allocation:              450 ML                      │
│  Used to Date:                  275 ML  (61%)              │
│  ──────────────────────────────────────────────             │
│  Remaining:                     175 ML  (39%)              │
│                                                             │
│  ██████████████████████░░░░░░░░░░░░░░  61% used            │
│                                                             │
│  Status: ✅ Compliant                                       │
│                                                             │
│  🔔 Next allocation announcement: Dec 18, 2024             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Data Fields:**
1. **Total Allocation** (ML)
   - Calculated: Entitlement (ML) × Allocation % announced by WaterNSW
   - Example: 1,000 ML entitlement × 45% allocation = 450 ML
   - Updates automatically when new allocation announcement published

2. **Used to Date** (ML)
   - Source: Telemetry data (if available) OR manual entry
   - Running total since July 1 (water year start)
   - Percentage of total allocation

3. **Remaining** (ML)
   - Calculated: Total Allocation - Used to Date
   - Highlighted in GREEN if >20% remaining, YELLOW if 10-20%, RED if <10%

4. **Status**
   - ✅ Compliant (usage < allocation)
   - ⚠️ Near Limit (usage 90-100% of allocation)
   - ❌ Over-Allocated (usage > allocation - triggers compliance action)

5. **Progress Bar**
   - Visual representation of usage percentage
   - Color-coded (green → yellow → red as usage increases)

6. **Next Announcement Date**
   - Predict next allocation update based on historical patterns
   - Link to NSW DPIE allocation statement schedule

---

### Feature 1.2: Entitlement Breakdown (Multi-Source Support)

**Challenge:** Farmers often have multiple water entitlements (different categories, different valleys)

**Example Farmer Portfolio:**
- 800 ML General Security (Murrumbidgee)
- 200 ML High Security (Murrumbidgee)
- 150 ML Supplementary (Murrumbidgee)
- 100 ML General Security (Murray)

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  📋 My Water Entitlements (4)                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. General Security - Murrumbidgee                         │
│     Entitlement: 800 ML                                     │
│     Allocation: 45% (360 ML)                                │
│     Used: 220 ML (61%)                                      │
│     Remaining: 140 ML                                       │
│     ██████████████████████░░░░░░░░░░  61% used              │
│                                                             │
│  2. High Security - Murrumbidgee                            │
│     Entitlement: 200 ML                                     │
│     Allocation: 95% (190 ML)                                │
│     Used: 50 ML (26%)                                       │
│     Remaining: 140 ML                                       │
│     ████████░░░░░░░░░░░░░░░░░░░░░░░░  26% used              │
│                                                             │
│  3. Supplementary - Murrumbidgee                            │
│     Entitlement: 150 ML (not allocated)                     │
│     Status: Awaiting flow announcement                      │
│     🔔 Will alert when supplementary event declared         │
│                                                             │
│  4. General Security - Murray                               │
│     Entitlement: 100 ML                                     │
│     Allocation: 60% (60 ML)                                 │
│     Used: 35 ML (58%)                                       │
│     Remaining: 25 ML                                        │
│     ██████████████████░░░░░░░░░░░░░░  58% used              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Data Requirements:**

1. **Farmer Onboarding**
   - During signup, farmer enters all water access licenses (WALs)
   - Fetch from WaterNSW if possible (WAL number → entitlement details)
   - OR manual entry:
     - Water source (valley/aquifer)
     - Entitlement category (General Security, High Security, Supplementary, Groundwater, etc.)
     - Entitlement volume (ML)
     - WAL number (for verification)

2. **Allocation Data Source**
   - **NSW:** Scrape PDF allocation statements from water.dpie.nsw.gov.au
   - Parse tables showing allocation % by category and water source
   - Example extraction:
     ```
     Murrumbidgee Regulated River - Water Allocation Statement (Dec 16, 2024)
     General Security: 45%
     High Security: 95%
     Conveyance: 100%
     ```
   - Store in database with timestamp

3. **Usage Data Source**
   - **Option A (Telemetry):** Fetch from telemetry provider API
     - Common providers: Observant, Goanna Ag, ICT International
     - Protocols: LoRaWAN, NB-IoT, cellular (3G/4G)
     - Data format: Typically JSON or CSV
       ```json
       {
         "meter_id": "12345",
         "timestamp": "2024-12-16T14:30:00Z",
         "cumulative_volume_ML": 275.3,
         "flow_rate_L_per_sec": 15.2
       }
       ```
   - **Option B (Manual Entry):** Farmer logs water use
     - "I irrigated 20 ML on Dec 15, 2024"
     - System tracks cumulative total
   - **Option C (iWAS Scraping):** If farmer provides iWAS login credentials
     - Web scrape their water account balance
     - Legal/ethical considerations (need farmer explicit consent)

4. **Calculated Fields**
   - Total Allocation = Entitlement × (Allocation % / 100)
   - Remaining = Total Allocation - Used to Date
   - Percentage Used = (Used to Date / Total Allocation) × 100

---

### Feature 1.3: Allocation History Chart

**Purpose:** Show allocation trends over time (farmer can see how allocation percentage changes throughout the year)

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  📊 Allocation History - General Security Murrumbidgee     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  100% ┤                                                     │
│       │                                                     │
│   80% ┤                                        ●            │
│       │                                   ●●●●              │
│   60% ┤                              ●●●●                   │
│       │                         ●●●●●                       │
│   40% ┤                    ●●●●●                            │
│       │               ●●●●●          Current: 45%           │
│   20% ┤          ●●●●●                                      │
│       │     ●●●●●                                           │
│    0% ┤●●●●●                                                │
│       └──┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬──  │
│         Jul Aug Sep Oct Nov Dec Jan Feb Mar Apr May Jun    │
│                                                             │
│  This year (2024-25):  45%  ▲ (up from 40% last month)     │
│  Last year (2023-24):  38%  (same date)                    │
│  5-year average:       52%  (same date)                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Data Requirements:**
1. **Historical allocation announcements**
   - Scrape past statements (NSW DPIE archives PDFs going back ~10 years)
   - Store in time-series database (e.g., TimescaleDB extension for PostgreSQL)
   - Table structure:
     ```sql
     CREATE TABLE allocation_history (
       id SERIAL PRIMARY KEY,
       water_source TEXT NOT NULL,  -- 'Murrumbidgee Regulated River'
       category TEXT NOT NULL,       -- 'General Security'
       allocation_pct FLOAT NOT NULL,
       announced_date DATE NOT NULL,
       water_year INT NOT NULL,      -- 2024 (for July 2024 - June 2025)
       created_at TIMESTAMP DEFAULT NOW()
     );
     ```

2. **Comparison Metrics**
   - Current year vs. last year (same date)
   - Current year vs. 5-year average
   - Trend indicator (↑ allocation increased, ↓ decreased, → steady)

3. **Interactive Features**
   - Hover over data point → tooltip shows exact date and allocation %
   - Click data point → see full allocation statement (PDF link)
   - Toggle between chart view and table view

---

### Feature 1.4: Allocation Announcement Feed

**Purpose:** Show all recent allocation announcements across all farmer's water sources

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  📢 Recent Allocation Announcements                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Dec 16, 2024 - Murrumbidgee Regulated River               │
│  ─────────────────────────────────────────────────────      │
│  General Security: 45% (up from 40%)  ▲ +5%                │
│  High Security: 95% (unchanged)       →                     │
│                                                             │
│  Highlights:                                                │
│  • Improved inflows from recent rainfall                    │
│  • Blowering Dam at 67% capacity                            │
│  • Next review: Jan 2, 2025                                 │
│                                                             │
│  📄 View full statement  |  📊 See impact on my account     │
│                                                             │
│  ──────────────────────────────────────────────────────     │
│                                                             │
│  Dec 9, 2024 - Lachlan Regulated River                     │
│  ─────────────────────────────────────────────────────      │
│  General Security: 15% (down from 18%)  ▼ -3%              │
│  High Security: 100% (unchanged)        →                   │
│                                                             │
│  Highlights:                                                │
│  • Below-average inflows                                    │
│  • Wyangala Dam at 42% capacity                             │
│  • Water conservation measures in effect                    │
│                                                             │
│  📄 View full statement                                     │
│                                                             │
│  ──────────────────────────────────────────────────────     │
│                                                             │
│  🔔 Get alerts for new announcements (Email, SMS, Push)     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Data Requirements:**
1. **Announcement Scraping**
   - Automated scraper runs daily at 6:00 AM (announcements typically published by 5:00 PM previous day)
   - Scrape water.dpie.nsw.gov.au/allocations for all NSW valleys
   - Parse PDF using pdfplumber (your existing platform already does this!)
   - Extract key data:
     - Water source
     - Allocation categories and percentages
     - Dam levels
     - Rainfall/inflow commentary
     - Next review date

2. **Change Detection**
   - Compare new announcement to previous announcement
   - Calculate delta (e.g., 45% - 40% = +5%)
   - Flag as "increase" (▲), "decrease" (▼), or "unchanged" (→)

3. **Personalization**
   - Only show announcements for farmer's water sources
   - Highlight announcements that affect farmer's largest entitlements
   - "This affects your 800 ML General Security allocation"

4. **Notification Triggers**
   - Send alert when:
     - New announcement published for farmer's water source
     - Allocation percentage changes (up or down)
     - Supplementary access declared (time-sensitive!)

---

### Feature 1.5: Supplementary Access Alerts

**Special Case:** Supplementary water access is time-sensitive (24-72 hour windows)

**Challenge:**
- Supplementary announcements happen when river has high flows (after rain/dam releases)
- Farmers must act quickly (order water within 24-48 hours before opportunity closes)
- Missing a supplementary event = lost irrigation opportunity

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  🚨 SUPPLEMENTARY ACCESS DECLARED - ACT NOW!                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Murrumbidgee Regulated River                               │
│  Supplementary Access: AVAILABLE                            │
│                                                             │
│  Window: Dec 16, 2024 10:00 AM - Dec 18, 2024 6:00 PM      │
│  Time remaining: 38 hours  ⏳                               │
│                                                             │
│  Your supplementary entitlement: 150 ML                     │
│  You can order UP TO 150 ML during this event               │
│                                                             │
│  Conditions:                                                │
│  • Flow rate at Wagga Wagga weir: 15,000 ML/day            │
│  • Environmental flows satisfied                            │
│  • Delivery may take 3-5 days                               │
│                                                             │
│  ⚡ Quick Actions:                                          │
│  ┌───────────────────┐  ┌───────────────────┐              │
│  │  Order Water Now  │  │  Set Alert (6hrs) │              │
│  │  via WaterNSW     │  │  before closing   │              │
│  └───────────────────┘  └───────────────────┘              │
│                                                             │
│  📊 Historical: Last supplementary event was Oct 2024       │
│      (3 months ago). Average: 2-4 events per year.          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Data Requirements:**
1. **Supplementary Announcement Scraping**
   - WaterNSW publishes "Supplementary Announcements" on separate page
   - These are time-critical (not part of regular allocation statements)
   - Scraper must run EVERY HOUR during irrigation season (Oct-Apr)

2. **Alert Mechanisms**
   - **SMS:** High-priority (send immediately when event declared)
   - **Push notification:** Mobile app
   - **Email:** Backup
   - User preference: "Alert me X hours before supplementary window closes"

3. **Countdown Timer**
   - Calculate hours remaining until window closes
   - Visual urgency (red flashing if <6 hours remaining)

4. **Integration with WaterNSW**
   - "Order Water Now" button deep-links to WaterNSW water ordering page
   - Pre-fill farmer's WAL number (if possible via URL parameters)

---

### Technical Architecture (Allocation Dashboard)

**Backend (Python FastAPI)**

```python
# app/services/allocation_service.py

class AllocationService:
    """Manages water allocation data fetching and calculation"""

    def __init__(self, db_connection, pdf_scraper):
        self.db = db_connection
        self.scraper = pdf_scraper

    async def update_allocations(self):
        """
        Run daily at 6:00 AM to fetch latest allocation statements
        """
        valleys = [
            'murrumbidgee', 'murray', 'lachlan', 'namoi',
            'gwydir', 'macquarie', 'border_rivers'
        ]

        for valley in valleys:
            # Fetch latest PDF statement
            pdf_url = f"https://water.dpie.nsw.gov.au/allocations/{valley}/latest.pdf"
            pdf_content = await self.scraper.fetch_pdf(pdf_url)

            # Extract allocation percentages using pdfplumber
            allocations = self.scraper.extract_allocation_table(pdf_content)
            # Returns: {'General Security': 45, 'High Security': 95, ...}

            # Store in database
            for category, percentage in allocations.items():
                await self.db.execute("""
                    INSERT INTO allocation_history
                    (water_source, category, allocation_pct, announced_date, water_year)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (water_source, category, announced_date) DO UPDATE
                    SET allocation_pct = EXCLUDED.allocation_pct
                """, valley, category, percentage, datetime.now().date(), 2024)

    async def get_farmer_allocation_summary(self, farmer_id: int):
        """
        Calculate farmer's total allocation across all entitlements
        """
        # Fetch farmer's entitlements
        entitlements = await self.db.fetch("""
            SELECT entitlement_id, water_source, category, volume_ML
            FROM farmer_entitlements
            WHERE farmer_id = $1
        """, farmer_id)

        summary = {
            'total_allocation_ML': 0,
            'total_used_ML': 0,
            'entitlements': []
        }

        for ent in entitlements:
            # Get latest allocation percentage for this water source + category
            alloc_pct = await self.db.fetchval("""
                SELECT allocation_pct
                FROM allocation_history
                WHERE water_source = $1 AND category = $2
                ORDER BY announced_date DESC
                LIMIT 1
            """, ent['water_source'], ent['category'])

            # Calculate allocation in ML
            allocation_ML = ent['volume_ML'] * (alloc_pct / 100.0)

            # Get usage to date (from telemetry or manual entry)
            used_ML = await self.get_usage_to_date(ent['entitlement_id'])

            # Calculate remaining
            remaining_ML = allocation_ML - used_ML

            summary['entitlements'].append({
                'water_source': ent['water_source'],
                'category': ent['category'],
                'entitlement_ML': ent['volume_ML'],
                'allocation_pct': alloc_pct,
                'allocation_ML': allocation_ML,
                'used_ML': used_ML,
                'remaining_ML': remaining_ML,
                'pct_used': (used_ML / allocation_ML * 100) if allocation_ML > 0 else 0
            })

            summary['total_allocation_ML'] += allocation_ML
            summary['total_used_ML'] += used_ML

        summary['total_remaining_ML'] = summary['total_allocation_ML'] - summary['total_used_ML']
        summary['pct_used'] = (summary['total_used_ML'] / summary['total_allocation_ML'] * 100) if summary['total_allocation_ML'] > 0 else 0

        # Determine status
        if summary['pct_used'] > 100:
            summary['status'] = 'over_allocated'
        elif summary['pct_used'] > 90:
            summary['status'] = 'near_limit'
        else:
            summary['status'] = 'compliant'

        return summary
```

**Database Schema**

```sql
-- Farmer's water entitlements
CREATE TABLE farmer_entitlements (
    entitlement_id SERIAL PRIMARY KEY,
    farmer_id INT NOT NULL REFERENCES farmers(id),
    water_source TEXT NOT NULL,  -- 'Murrumbidgee Regulated River'
    category TEXT NOT NULL,       -- 'General Security', 'High Security', etc.
    volume_ML FLOAT NOT NULL,     -- Entitlement volume (e.g., 800 ML)
    wal_number TEXT,              -- Water Access License number (for verification)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Historical allocation announcements
CREATE TABLE allocation_history (
    id SERIAL PRIMARY KEY,
    water_source TEXT NOT NULL,
    category TEXT NOT NULL,
    allocation_pct FLOAT NOT NULL,  -- 0-100 (e.g., 45 for 45%)
    announced_date DATE NOT NULL,
    water_year INT NOT NULL,         -- 2024 for 2024-25 water year
    dam_levels JSONB,                -- {'Blowering': 67, 'Burrinjuck': 82}
    commentary TEXT,                 -- Free text from announcement
    next_review_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (water_source, category, announced_date)
);

CREATE INDEX idx_allocation_history_source_cat ON allocation_history(water_source, category, announced_date DESC);

-- Supplementary access events
CREATE TABLE supplementary_events (
    event_id SERIAL PRIMARY KEY,
    water_source TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    flow_rate_ML_per_day FLOAT,
    conditions TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_supplementary_events_active ON supplementary_events(water_source, end_time)
WHERE end_time > NOW();
```

**Frontend (Next.js React)**

```typescript
// components/AllocationDashboard.tsx

'use client';

import { useState, useEffect } from 'react';

interface AllocationSummary {
  total_allocation_ML: number;
  total_used_ML: number;
  total_remaining_ML: number;
  pct_used: number;
  status: 'compliant' | 'near_limit' | 'over_allocated';
  entitlements: Array<{
    water_source: string;
    category: string;
    entitlement_ML: number;
    allocation_pct: number;
    allocation_ML: number;
    used_ML: number;
    remaining_ML: number;
    pct_used: number;
  }>;
}

export function AllocationDashboard({ farmerId }: { farmerId: number }) {
  const [summary, setSummary] = useState<AllocationSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAllocationSummary();
    // Refresh every 15 minutes
    const interval = setInterval(fetchAllocationSummary, 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, [farmerId]);

  async function fetchAllocationSummary() {
    const response = await fetch(`/api/allocation/summary?farmer_id=${farmerId}`);
    const data = await response.json();
    setSummary(data);
    setLoading(false);
  }

  if (loading) {
    return <div className="animate-pulse">Loading allocation data...</div>;
  }

  if (!summary) {
    return <div>No allocation data available</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">💧 Water Account Summary</h2>
        <span className="text-sm text-gray-500">Updated: 15 minutes ago</span>
      </div>

      {/* Summary Card */}
      <div className="bg-blue-50 rounded-lg p-6 mb-6">
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <p className="text-sm text-gray-600">Total Allocation</p>
            <p className="text-3xl font-bold">{summary.total_allocation_ML.toFixed(0)} ML</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Used to Date</p>
            <p className="text-3xl font-bold">{summary.total_used_ML.toFixed(0)} ML</p>
            <p className="text-sm text-gray-500">({summary.pct_used.toFixed(0)}%)</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Remaining</p>
            <p className="text-3xl font-bold text-green-600">
              {summary.total_remaining_ML.toFixed(0)} ML
            </p>
            <p className="text-sm text-gray-500">({(100 - summary.pct_used).toFixed(0)}%)</p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="w-full bg-gray-200 rounded-full h-6">
            <div
              className={`h-6 rounded-full flex items-center justify-end pr-2 text-white text-sm font-semibold ${
                summary.pct_used > 90 ? 'bg-red-500' :
                summary.pct_used > 70 ? 'bg-yellow-500' :
                'bg-green-500'
              }`}
              style={{ width: `${Math.min(summary.pct_used, 100)}%` }}
            >
              {summary.pct_used.toFixed(0)}% used
            </div>
          </div>
        </div>

        {/* Status */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">Status:</span>
          {summary.status === 'compliant' && (
            <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-semibold">
              ✅ Compliant
            </span>
          )}
          {summary.status === 'near_limit' && (
            <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-semibold">
              ⚠️ Near Limit
            </span>
          )}
          {summary.status === 'over_allocated' && (
            <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-semibold">
              ❌ Over-Allocated
            </span>
          )}
        </div>
      </div>

      {/* Entitlement Breakdown */}
      <div>
        <h3 className="text-lg font-semibold mb-3">📋 My Water Entitlements ({summary.entitlements.length})</h3>
        <div className="space-y-4">
          {summary.entitlements.map((ent, index) => (
            <div key={index} className="border rounded-lg p-4">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <h4 className="font-semibold">{ent.category} - {ent.water_source}</h4>
                  <p className="text-sm text-gray-600">Entitlement: {ent.entitlement_ML} ML</p>
                </div>
                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm font-semibold">
                  {ent.allocation_pct}% allocated
                </span>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-2 text-sm">
                <div>
                  <p className="text-gray-600">Allocation</p>
                  <p className="font-semibold">{ent.allocation_ML.toFixed(0)} ML</p>
                </div>
                <div>
                  <p className="text-gray-600">Used</p>
                  <p className="font-semibold">{ent.used_ML.toFixed(0)} ML ({ent.pct_used.toFixed(0)}%)</p>
                </div>
                <div>
                  <p className="text-gray-600">Remaining</p>
                  <p className="font-semibold text-green-600">{ent.remaining_ML.toFixed(0)} ML</p>
                </div>
              </div>

              <div className="w-full bg-gray-200 rounded-full h-4">
                <div
                  className={`h-4 rounded-full ${
                    ent.pct_used > 90 ? 'bg-red-500' :
                    ent.pct_used > 70 ? 'bg-yellow-500' :
                    'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(ent.pct_used, 100)}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## Product Requirements: Usage Tracking

### Overview

**Purpose:** Track farmer's actual water usage (extractions) in real-time to compare against allocation.

**User Story:**
> "As a farmer, I want to automatically track how much water I've extracted from the river/dam/bore, so I don't have to manually calculate whether I'm within my allocation limit."

---

### Feature 2.1: Telemetry Integration (Automated Usage Tracking)

**Priority:** HIGH (telemetry is becoming mandatory for 100ML+ entitlements by 2026)

**Data Flow:**
```
Water Meter (physical device)
    ↓
Telemetry Device (LoRaWAN/cellular transmitter)
    ↓
Telemetry Provider Cloud (Observant, Goanna Ag, ICT International)
    ↓
WaterRight API (fetch via provider API)
    ↓
WaterRight Database (store cumulative usage)
    ↓
WaterRight Dashboard (display to farmer)
```

**Supported Telemetry Providers:**

1. **Observant** (market leader in Australia)
   - API: Yes (RESTful JSON API)
   - Protocol: LoRaWAN, NB-IoT, 4G
   - Data: Flow rate, cumulative volume, battery level, signal strength
   - Refresh rate: Every 15 minutes to hourly

2. **Goanna Ag**
   - API: Yes
   - Protocol: NB-IoT
   - Data: Cumulative volume, flow events
   - Refresh rate: Configurable (15 min to 4 hours)

3. **ICT International**
   - API: Limited (CSV export)
   - Protocol: Cellular (3G/4G)
   - Data: Cumulative volume
   - Refresh rate: Hourly

4. **Generic (Direct Cellular)**
   - Some farmers have meters that send SMS/email alerts
   - Can parse structured SMS: "Meter 12345: 275.3 ML total"

**Integration Approach:**

**Option A: Direct API Integration (Preferred)**
```python
# app/services/telemetry_service.py

class TelemetryService:
    """Fetch water meter data from telemetry providers"""

    async def fetch_observant_data(self, farmer_id: int):
        """Fetch from Observant API"""
        # Get farmer's Observant credentials (stored encrypted)
        credentials = await self.db.fetchrow("""
            SELECT observant_api_key, observant_account_id
            FROM farmer_telemetry_config
            WHERE farmer_id = $1 AND provider = 'observant'
        """, farmer_id)

        if not credentials:
            return None

        # Fetch meter readings
        headers = {'Authorization': f"Bearer {credentials['observant_api_key']}"}
        response = await httpx.get(
            f"https://api.observant.net/v1/accounts/{credentials['observant_account_id']}/meters",
            headers=headers
        )

        meters = response.json()

        # Store readings in database
        for meter in meters:
            await self.db.execute("""
                INSERT INTO water_usage_readings
                (farmer_id, meter_id, reading_ML, timestamp, source)
                VALUES ($1, $2, $3, $4, 'observant')
                ON CONFLICT (meter_id, timestamp) DO UPDATE
                SET reading_ML = EXCLUDED.reading_ML
            """, farmer_id, meter['id'], meter['cumulative_volume_ML'],
                 meter['timestamp'], 'observant')

        return meters

    async def calculate_usage_to_date(self, farmer_id: int, entitlement_id: int):
        """
        Calculate total water usage for an entitlement since July 1 (water year start)
        """
        # Get water year start date
        today = datetime.now().date()
        if today.month >= 7:
            water_year_start = date(today.year, 7, 1)
        else:
            water_year_start = date(today.year - 1, 7, 1)

        # Get meter IDs linked to this entitlement
        meter_ids = await self.db.fetch("""
            SELECT meter_id
            FROM entitlement_meters
            WHERE entitlement_id = $1
        """, entitlement_id)

        if not meter_ids:
            # No telemetry - use manual entries
            return await self.get_manual_usage(farmer_id, entitlement_id, water_year_start)

        # Get latest reading for each meter
        total_usage = 0.0
        for meter in meter_ids:
            latest_reading = await self.db.fetchval("""
                SELECT reading_ML
                FROM water_usage_readings
                WHERE meter_id = $1 AND timestamp >= $2
                ORDER BY timestamp DESC
                LIMIT 1
            """, meter['meter_id'], water_year_start)

            # Get baseline reading (July 1)
            baseline_reading = await self.db.fetchval("""
                SELECT reading_ML
                FROM water_usage_readings
                WHERE meter_id = $1 AND timestamp >= $2
                ORDER BY timestamp ASC
                LIMIT 1
            """, meter['meter_id'], water_year_start)

            # Usage = Latest - Baseline
            if latest_reading and baseline_reading:
                total_usage += (latest_reading - baseline_reading)

        return total_usage
```

**Option B: Farmer Provides Portal Access (Secondary)**
- Farmer provides WaterRight with login credentials to telemetry provider portal
- WaterRight uses web scraping (Playwright/Selenium) to fetch data
- Less reliable (portal changes break scraper), but works if API unavailable

**Option C: Manual CSV Upload (Fallback)**
- Farmer downloads usage report from telemetry provider (CSV/Excel)
- Uploads to WaterRight monthly
- System parses and imports data

---

### Feature 2.2: Manual Usage Entry (For Non-Telemetry Farmers)

**Challenge:** Not all farmers have telemetry (especially those <100 ML entitlement)

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  ➕ Log Water Use                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Date: [__/__/____]  (default: today)                       │
│                                                             │
│  Water Source:                                              │
│  ┌───────────────────────────────────────────┐              │
│  │ General Security - Murrumbidgee    ▼      │              │
│  └───────────────────────────────────────────┘              │
│                                                             │
│  Volume Used (ML):                                          │
│  ┌─────────┐                                                │
│  │  25.5   │  ML                                            │
│  └─────────┘                                                │
│                                                             │
│  Purpose (optional):                                        │
│  ┌───────────────────────────────────────────┐              │
│  │ Irrigated rice paddock 5 (50 hectares)    │              │
│  └───────────────────────────────────────────┘              │
│                                                             │
│  Meter Reading (optional):                                  │
│  ┌─────────┐  ML (cumulative)                               │
│  │  275.5  │                                                │
│  └─────────┘                                                │
│                                                             │
│  ┌──────────────┐                                           │
│  │  Save Entry  │                                           │
│  └──────────────┘                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
1. **Quick Entry**
   - Mobile-friendly (farmers often in field, use phone)
   - Pre-fill today's date
   - Autocomplete water source (from farmer's entitlements)

2. **Batch Entry**
   - Upload CSV: `Date, Water Source, Volume ML`
   - Useful for farmers who keep manual logs in Excel

3. **Validation**
   - Check: Is volume reasonable? (Alert if >100 ML in single day - likely typo)
   - Check: Does this exceed allocation? (Warn before saving if overdrawn)

4. **Recurring Entries**
   - "I irrigate 20 ML every Monday" → auto-create recurring entry
   - Farmer can edit/confirm each week

---

### Feature 2.3: Usage History & Trends

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  📊 Water Usage History - General Security Murrumbidgee    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Current Water Year (Jul 2024 - Jun 2025)                  │
│                                                             │
│  Total Used: 275 ML  /  Allocation: 450 ML  (61% used)     │
│                                                             │
│  ──────────────────────────────────────────────────────     │
│                                                             │
│  Monthly Usage:                                             │
│                                                             │
│   80 ML ┤                               ███                 │
│         │                               ███                 │
│   60 ML ┤                      ███      ███                 │
│         │             ███      ███      ███                 │
│   40 ML ┤    ███      ███      ███      ███                 │
│         │    ███      ███      ███      ███                 │
│   20 ML ┤    ███      ███      ███      ███      ███        │
│         │    ███      ███      ███      ███      ███        │
│    0 ML ┤────┴────────┴────────┴────────┴────────┴──────   │
│         │   Jul   Aug   Sep   Oct   Nov   Dec   Jan ...    │
│                                                             │
│  Peak usage: November (75 ML)  - Rice irrigation            │
│  Average: 45 ML/month                                       │
│                                                             │
│  ──────────────────────────────────────────────────────     │
│                                                             │
│  Daily Usage (Last 30 Days):                                │
│                                                             │
│  Dec 15: 5.2 ML   Rice paddock 3                            │
│  Dec 14: 4.8 ML   Rice paddock 2                            │
│  Dec 13: 0.0 ML   (no irrigation - rain)                    │
│  Dec 12: 6.1 ML   Rice paddock 1, 3                         │
│  Dec 11: 5.5 ML   Rice paddock 2                            │
│  ...                                                        │
│                                                             │
│  📥 Export Usage Report (PDF, CSV, Excel)                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Data Requirements:**
1. **Time-Series Storage**
   - Store daily usage readings
   - Aggregate to monthly totals for charts
   - Allow drill-down (click month → see daily breakdown)

2. **Comparison Metrics**
   - This year vs. last year (same period)
   - This year vs. 5-year average
   - Identify anomalies (unusually high usage days)

3. **Export Functionality**
   - Farmers may need usage reports for:
     - Annual compliance audits
     - Water trading records
     - Tax deductions (water costs are farm expenses)
   - Export formats: PDF (for printing), CSV/Excel (for accountants)

---

### Feature 2.4: Predictive Usage Alerts

**Purpose:** Warn farmer BEFORE they exceed allocation

**Algorithm:**
```python
def predict_days_until_exceed(current_usage_ML, allocation_ML, recent_usage_pattern):
    """
    Predict how many days until farmer exceeds allocation at current usage rate
    """
    remaining_ML = allocation_ML - current_usage_ML

    # Calculate average daily usage over last 30 days
    avg_daily_usage = sum(recent_usage_pattern) / len(recent_usage_pattern)

    if avg_daily_usage <= 0:
        return None  # No usage, won't exceed

    days_until_exceed = remaining_ML / avg_daily_usage

    return days_until_exceed

# Example
current_usage = 275  # ML
allocation = 450  # ML
recent_usage = [5.2, 4.8, 0.0, 6.1, 5.5, ...]  # Last 30 days

days_left = predict_days_until_exceed(current_usage, allocation, recent_usage)
# Returns: 35 days (if avg usage is 5 ML/day, 175 ML remaining / 5 = 35 days)
```

**Alert Scenarios:**

1. **Yellow Alert: Approaching Limit**
   - Trigger: 80% of allocation used OR <30 days until exceed
   - Message: "⚠️ You've used 80% of your allocation (360 ML of 450 ML). At your current usage rate (5 ML/day), you'll reach your limit in 18 days."

2. **Red Alert: Near Limit**
   - Trigger: 90% of allocation used OR <14 days until exceed
   - Message: "🚨 You've used 90% of your allocation (405 ML of 450 ML). You have 45 ML remaining. At your current usage rate, you'll reach your limit in 9 days. Consider reducing irrigation or purchasing temporary water."

3. **Critical Alert: Over Limit**
   - Trigger: Usage > allocation
   - Message: "❌ OVER-ALLOCATION ALERT: You've exceeded your allocation by 25 ML (475 ML used, 450 ML allocated). This is a compliance violation. Contact WaterRight support immediately."

**Alert Delivery:**
- SMS (immediate for red/critical)
- Email (daily digest for yellow)
- Push notification (mobile app)
- In-app banner (when farmer logs in)

---

### Technical Architecture (Usage Tracking)

**Database Schema:**

```sql
-- Water meter telemetry readings
CREATE TABLE water_usage_readings (
    reading_id SERIAL PRIMARY KEY,
    farmer_id INT NOT NULL REFERENCES farmers(id),
    meter_id TEXT NOT NULL,          -- Unique meter identifier from telemetry provider
    reading_ML FLOAT NOT NULL,        -- Cumulative reading (meter's total since installation)
    flow_rate_L_per_sec FLOAT,       -- Instantaneous flow rate (optional)
    timestamp TIMESTAMP NOT NULL,
    source TEXT NOT NULL,             -- 'observant', 'goanna_ag', 'manual', etc.
    metadata JSONB,                   -- Additional data (battery, signal strength, etc.)
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (meter_id, timestamp)
);

CREATE INDEX idx_usage_readings_farmer_time ON water_usage_readings(farmer_id, timestamp DESC);
CREATE INDEX idx_usage_readings_meter_time ON water_usage_readings(meter_id, timestamp DESC);

-- Link meters to entitlements
CREATE TABLE entitlement_meters (
    id SERIAL PRIMARY KEY,
    entitlement_id INT NOT NULL REFERENCES farmer_entitlements(entitlement_id),
    meter_id TEXT NOT NULL,
    meter_location TEXT,              -- 'Pump 1 - Murrumbidgee River offtake'
    installation_date DATE,
    telemetry_provider TEXT,          -- 'observant', 'goanna_ag', etc.
    created_at TIMESTAMP DEFAULT NOW()
);

-- Manual usage entries (for non-telemetry farmers)
CREATE TABLE manual_water_usage (
    entry_id SERIAL PRIMARY KEY,
    farmer_id INT NOT NULL REFERENCES farmers(id),
    entitlement_id INT NOT NULL REFERENCES farmer_entitlements(entitlement_id),
    usage_date DATE NOT NULL,
    volume_ML FLOAT NOT NULL,
    purpose TEXT,                     -- 'Irrigated rice paddock 5'
    meter_reading_ML FLOAT,           -- Optional: farmer's meter reading
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_manual_usage_farmer_date ON manual_water_usage(farmer_id, usage_date DESC);

-- Farmer telemetry configuration (API credentials)
CREATE TABLE farmer_telemetry_config (
    config_id SERIAL PRIMARY KEY,
    farmer_id INT NOT NULL REFERENCES farmers(id),
    provider TEXT NOT NULL,           -- 'observant', 'goanna_ag', 'ict_international'
    api_key TEXT,                     -- Encrypted
    account_id TEXT,
    username TEXT,                    -- For providers without API (web scraping)
    password TEXT,                    -- Encrypted
    last_sync_at TIMESTAMP,
    sync_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (farmer_id, provider)
);
```

**API Endpoint:**

```python
# app/api/usage.py

from fastapi import APIRouter, Depends
from app.services.telemetry_service import TelemetryService
from app.auth import get_current_farmer

router = APIRouter(prefix="/api/usage")

@router.get("/summary")
async def get_usage_summary(
    farmer_id: int = Depends(get_current_farmer),
    telemetry_service: TelemetryService = Depends()
):
    """
    Get usage summary for farmer's entitlements
    """
    # Sync latest telemetry data (if configured)
    await telemetry_service.sync_all_meters(farmer_id)

    # Calculate usage for each entitlement
    entitlements = await db.fetch("""
        SELECT entitlement_id, water_source, category, volume_ML
        FROM farmer_entitlements
        WHERE farmer_id = $1
    """, farmer_id)

    usage_summary = []
    for ent in entitlements:
        usage_ML = await telemetry_service.calculate_usage_to_date(
            farmer_id, ent['entitlement_id']
        )

        usage_summary.append({
            'entitlement_id': ent['entitlement_id'],
            'water_source': ent['water_source'],
            'category': ent['category'],
            'usage_ML': usage_ML
        })

    return {'success': True, 'data': usage_summary}

@router.post("/manual-entry")
async def log_manual_usage(
    entry: dict,
    farmer_id: int = Depends(get_current_farmer)
):
    """
    Farmer manually logs water usage
    """
    # Validate entry
    if entry['volume_ML'] <= 0:
        return {'success': False, 'error': 'Volume must be positive'}

    # Check if this would exceed allocation
    current_usage = await telemetry_service.calculate_usage_to_date(
        farmer_id, entry['entitlement_id']
    )

    # Get allocation
    allocation = await get_allocation_for_entitlement(entry['entitlement_id'])

    new_total = current_usage + entry['volume_ML']
    if new_total > allocation:
        # Warning, but allow entry (farmer may have valid reason)
        return {
            'success': True,
            'warning': f'This entry will put you over allocation ({new_total:.1f} ML > {allocation:.1f} ML allocated)'
        }

    # Save entry
    await db.execute("""
        INSERT INTO manual_water_usage
        (farmer_id, entitlement_id, usage_date, volume_ML, purpose, meter_reading_ML)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, farmer_id, entry['entitlement_id'], entry['date'],
         entry['volume_ML'], entry.get('purpose'), entry.get('meter_reading'))

    return {'success': True}
```

---

## Product Requirements: Compliance Alerts

### Overview

**Purpose:** Proactively alert farmer to compliance risks BEFORE violations occur.

**User Story:**
> "As a farmer, I want to be warned when I'm at risk of exceeding my allocation, breaching a restriction, or missing a regulatory deadline, so I can take corrective action before facing penalties."

---

### Feature 3.1: Real-Time Compliance Monitoring

**Monitored Conditions:**

1. **Allocation Limit Approaching**
   - 80% threshold → Yellow alert
   - 90% threshold → Red alert
   - 100% exceeded → Critical alert

2. **Water Sharing Plan Restrictions**
   - Seasonal restrictions (e.g., "No extraction Nov 1 - Feb 28 in dry years")
   - Flow-based restrictions (e.g., "No extraction when river flow <500 ML/day")
   - Environmental water restrictions (e.g., "Buffer zone around wetland")

3. **Regulatory Deadlines**
   - Water account must be positive by June 30 (end of water year)
   - Meter validation due (NSW requires 5-yearly meter validation)
   - Annual usage reporting to NRAR (due Aug 31 each year)

4. **Overdrawn Account**
   - Account balance negative = compliance violation
   - Must be remediated within 60 days (buy water or reduce usage)

5. **Telemetry Failure**
   - Meter not transmitting (could indicate tampering or malfunction)
   - NRAR requires operational telemetry for 100ML+ entitlements

---

### Feature 3.2: Compliance Alert Dashboard

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  🔔 Compliance Alerts (3)                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🚨 CRITICAL (1)                                            │
│  ─────────────────────────────────────────────────────      │
│                                                             │
│  Overdrawn Account - Immediate Action Required             │
│  Your General Security account is -15 ML overdrawn.         │
│  This is a compliance violation under Water Management      │
│  Act 2000.                                                  │
│                                                             │
│  Action Required:                                           │
│  1. Purchase 15 ML temporary allocation, OR                 │
│  2. Cease all extractions until allocation announcement     │
│                                                             │
│  Deadline: Remediate within 60 days (by Feb 14, 2025)      │
│                                                             │
│  Consequences if not remediated:                            │
│  • Penalty: Up to $264,000 (individuals)                    │
│  • NRAR enforcement action                                  │
│  • Account suspension                                       │
│                                                             │
│  🛒 Buy Water on WaterExchange  |  📞 Contact Support       │
│                                                             │
│  ──────────────────────────────────────────────────────     │
│                                                             │
│  ⚠️ WARNING (2)                                             │
│  ─────────────────────────────────────────────────────      │
│                                                             │
│  Approaching Allocation Limit                               │
│  You've used 405 ML of 450 ML allocated (90%)               │
│                                                             │
│  Predicted: You'll exceed allocation in 9 days at current   │
│  usage rate (5 ML/day).                                     │
│                                                             │
│  Recommended Actions:                                       │
│  • Reduce irrigation to 2 ML/day, OR                        │
│  • Purchase additional temporary water (50 ML recommended)  │
│                                                             │
│  Current market price: $180/ML (temporary allocation)       │
│                                                             │
│  ──────────────────────────────────────────────────────     │
│                                                             │
│  Seasonal Restriction Upcoming                              │
│  Embargo period starts in 14 days (Jan 1 - Mar 31)         │
│                                                             │
│  During embargo:                                            │
│  • No extractions allowed (environmental flows protection)  │
│  • Exemption: High Security license holders only            │
│                                                             │
│  Ensure you have sufficient water ordered before Jan 1.     │
│                                                             │
│  Current account balance: 45 ML (may be insufficient for    │
│  3-month embargo period if planning to irrigate)            │
│                                                             │
│  📅 Set Reminder  |  📖 Read Full Restriction Details       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Alert Prioritization:**

| Priority | Color | Icon | Criteria | Delivery |
|----------|-------|------|----------|----------|
| CRITICAL | Red | 🚨 | Account overdrawn, usage >100% allocation, telemetry failure | SMS + Email + Push (immediate) |
| WARNING | Yellow | ⚠️ | Usage >80% allocation, deadline <30 days, restriction upcoming | Email + Push (daily digest) |
| INFO | Blue | ℹ️ | Allocation announcement, market intel, system updates | Email (weekly digest) |

---

### Feature 3.3: Smart Alert Rules Engine

**Rule Definition (Database-Driven):**

```sql
CREATE TABLE compliance_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL,          -- 'allocation_limit', 'restriction', 'deadline'
    condition_sql TEXT NOT NULL,      -- SQL expression to evaluate
    alert_priority TEXT NOT NULL,     -- 'critical', 'warning', 'info'
    alert_message_template TEXT NOT NULL,
    action_recommendations JSONB,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Example rules
INSERT INTO compliance_rules (rule_name, rule_type, condition_sql, alert_priority, alert_message_template)
VALUES
(
    'Allocation Limit 90%',
    'allocation_limit',
    'pct_used >= 90 AND pct_used < 100',
    'warning',
    'You have used {pct_used}% of your {water_source} {category} allocation ({used_ML} ML of {allocation_ML} ML). You have {remaining_ML} ML remaining.'
),
(
    'Overdrawn Account',
    'overdrawn',
    'remaining_ML < 0',
    'critical',
    'Your {water_source} {category} account is overdrawn by {abs(remaining_ML)} ML. This is a compliance violation. You must purchase water or cease extractions within 60 days.'
),
(
    'Meter Telemetry Offline',
    'telemetry_failure',
    'last_reading_timestamp < NOW() - INTERVAL ''48 hours'' AND entitlement_volume_ML >= 100',
    'critical',
    'Meter {meter_id} has not transmitted data for 48 hours. NRAR requires operational telemetry for entitlements ≥100 ML. Check meter battery/connectivity.'
);
```

**Alert Evaluation Engine:**

```python
# app/services/compliance_service.py

class ComplianceService:
    """Evaluate compliance rules and generate alerts"""

    async def check_all_farmers_compliance(self):
        """
        Run daily (scheduled task) to check compliance for all farmers
        """
        farmers = await self.db.fetch("SELECT id FROM farmers WHERE active = TRUE")

        for farmer in farmers:
            await self.check_farmer_compliance(farmer['id'])

    async def check_farmer_compliance(self, farmer_id: int):
        """
        Evaluate all compliance rules for a single farmer
        """
        # Get farmer's entitlements and current usage
        entitlements = await self.get_farmer_entitlements_with_usage(farmer_id)

        # Get all enabled compliance rules
        rules = await self.db.fetch("""
            SELECT rule_id, rule_name, rule_type, condition_sql,
                   alert_priority, alert_message_template, action_recommendations
            FROM compliance_rules
            WHERE enabled = TRUE
        """)

        alerts_to_send = []

        for ent in entitlements:
            context = {
                'farmer_id': farmer_id,
                'entitlement_id': ent['entitlement_id'],
                'water_source': ent['water_source'],
                'category': ent['category'],
                'entitlement_volume_ML': ent['volume_ML'],
                'allocation_pct': ent['allocation_pct'],
                'allocation_ML': ent['allocation_ML'],
                'used_ML': ent['used_ML'],
                'remaining_ML': ent['remaining_ML'],
                'pct_used': ent['pct_used']
            }

            for rule in rules:
                # Evaluate condition (safely execute SQL with context)
                condition_result = await self.evaluate_condition(rule['condition_sql'], context)

                if condition_result:
                    # Rule triggered! Generate alert
                    alert_message = self.format_message_template(
                        rule['alert_message_template'], context
                    )

                    alerts_to_send.append({
                        'farmer_id': farmer_id,
                        'rule_id': rule['rule_id'],
                        'priority': rule['alert_priority'],
                        'message': alert_message,
                        'recommendations': rule['action_recommendations'],
                        'entitlement_id': ent['entitlement_id']
                    })

        # Send alerts (deduplicate if same alert already sent recently)
        for alert in alerts_to_send:
            await self.send_alert(alert)

    async def send_alert(self, alert: dict):
        """
        Send alert via appropriate channel based on priority
        """
        # Check if we already sent this alert recently (avoid spam)
        recent_alert = await self.db.fetchrow("""
            SELECT alert_id FROM farmer_alerts
            WHERE farmer_id = $1 AND rule_id = $2
            AND created_at > NOW() - INTERVAL '24 hours'
            AND acknowledged = FALSE
        """, alert['farmer_id'], alert['rule_id'])

        if recent_alert:
            # Already alerted in last 24 hours, skip
            return

        # Store alert in database
        alert_id = await self.db.fetchval("""
            INSERT INTO farmer_alerts
            (farmer_id, rule_id, priority, message, recommendations, entitlement_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING alert_id
        """, alert['farmer_id'], alert['rule_id'], alert['priority'],
             alert['message'], alert['recommendations'], alert['entitlement_id'])

        # Determine delivery channels based on priority
        if alert['priority'] == 'critical':
            # Send SMS immediately
            await self.send_sms(alert['farmer_id'], alert['message'])
            # AND email
            await self.send_email(alert['farmer_id'], alert['message'], alert['recommendations'])
            # AND push notification
            await self.send_push_notification(alert['farmer_id'], alert['message'])

        elif alert['priority'] == 'warning':
            # Email + push (no SMS to avoid alert fatigue)
            await self.send_email(alert['farmer_id'], alert['message'], alert['recommendations'])
            await self.send_push_notification(alert['farmer_id'], alert['message'])

        else:  # info
            # Queue for weekly digest email
            await self.queue_for_digest(alert['farmer_id'], alert['message'])
```

**Database Schema for Alerts:**

```sql
CREATE TABLE farmer_alerts (
    alert_id SERIAL PRIMARY KEY,
    farmer_id INT NOT NULL REFERENCES farmers(id),
    rule_id INT NOT NULL REFERENCES compliance_rules(rule_id),
    entitlement_id INT REFERENCES farmer_entitlements(entitlement_id),
    priority TEXT NOT NULL,           -- 'critical', 'warning', 'info'
    message TEXT NOT NULL,
    recommendations JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_farmer_alerts_farmer_unack ON farmer_alerts(farmer_id, acknowledged)
WHERE acknowledged = FALSE;

CREATE INDEX idx_farmer_alerts_created ON farmer_alerts(created_at DESC);
```

---

### Feature 3.4: Alert Acknowledgement & Actions

**Farmer Workflow:**

1. **Receive Alert** (SMS/email/push)
2. **View in Dashboard** (see full details + recommendations)
3. **Acknowledge Alert** (mark as "I've seen this")
4. **Take Action:**
   - Buy water (link to WaterExchange)
   - Reduce irrigation (log reduced usage)
   - Contact consultant (request callback)
   - Snooze (remind me in 7 days)

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  Alert: Approaching Allocation Limit                        │
│  Created: Dec 16, 2024 8:00 AM                              │
│  Status: Unacknowledged  ⚠️                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  You've used 405 ML of 450 ML allocated (90%)               │
│                                                             │
│  At current usage rate (5 ML/day), you'll exceed           │
│  allocation in 9 days.                                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Recommended Actions:                               │   │
│  │                                                     │   │
│  │  1. Purchase 50 ML temporary water                  │   │
│  │     Current market: $180/ML = $9,000                │   │
│  │     → Buy on WaterExchange                          │   │
│  │                                                     │   │
│  │  2. Reduce irrigation to 2 ML/day                   │   │
│  │     Savings: Extend allocation by 15 days           │   │
│  │                                                     │   │
│  │  3. Contact water consultant                        │   │
│  │     → Request callback from Aither                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  What did you do?                                           │
│  ○ Purchased water                                          │
│  ○ Reduced irrigation                                       │
│  ○ Contacted consultant                                     │
│  ○ Other action: [_______________]                          │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Acknowledge      │  │ Snooze (7 days)  │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Benefits of Acknowledgement System:**
1. **Farmer:** Peace of mind (won't get repeated alerts for same issue)
2. **WaterRight:** Track alert effectiveness (which alerts lead to action?)
3. **Analytics:** "80% of farmers who received 90% warning purchased water within 5 days"

---

### Feature 3.5: Regulatory Calendar & Reminders

**Purpose:** Never miss a compliance deadline

**Visual Design:**
```
┌─────────────────────────────────────────────────────────────┐
│  📅 Compliance Calendar                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Upcoming Deadlines:                                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Jan 1, 2025 (16 days)                                │  │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │  │
│  │ 🚫 Extraction Embargo Begins (Jan 1 - Mar 31)        │  │
│  │                                                      │  │
│  │ General Security holders: No extractions allowed    │  │
│  │ during environmental flow protection period.        │  │
│  │                                                      │  │
│  │ Action: Ensure sufficient water ordered by Dec 31   │  │
│  │                                                      │  │
│  │ ✓ Dismiss  |  🔔 Remind me Dec 28                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Jun 30, 2025 (197 days)                              │  │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │  │
│  │ 📊 Water Year End - Account Must Be Positive        │  │
│  │                                                      │  │
│  │ Current account balance: +45 ML ✓                   │  │
│  │ Status: On track                                     │  │
│  │                                                      │  │
│  │ If negative on Jun 30:                               │  │
│  │ • Account suspended until remediated                 │  │
│  │ • Penalties apply                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Aug 31, 2025 (259 days)                              │  │
│  │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │  │
│  │ 📄 Annual Usage Report Due to NRAR                   │  │
│  │                                                      │  │
│  │ You must submit annual water usage report by        │  │
│  │ Aug 31, 2025 (for 2024-25 water year).               │  │
│  │                                                      │  │
│  │ WaterRight can auto-generate your report.           │  │
│  │                                                      │  │
│  │ 📥 Generate Report (available after Jun 30)          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  📥 Export Calendar (iCal, Google Calendar)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Data Source:**
- Water Sharing Plans (PDF → extract restriction dates)
- NRAR compliance deadlines (published on website)
- WaterNSW operational dates (allocation announcement schedule)
- Farmer-specific dates (meter validation due, license renewal)

**Smart Reminders:**
- "Your meter validation is due in 60 days (Apr 15, 2025). Would you like us to book a certified validator?"
- "Annual usage report due in 30 days. Click here to preview your auto-generated report."

---

## Technical Architecture (Overview)

### System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                        WATERRIGHT PLATFORM                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐         ┌────────────────┐              │
│  │ Frontend       │         │ Backend        │              │
│  │ (Next.js)      │◄───────►│ (Python        │              │
│  │                │  REST   │  FastAPI)      │              │
│  │ - Dashboard    │  API    │                │              │
│  │ - Mobile App   │         │ - Allocation   │              │
│  │                │         │   Service      │              │
│  └────────────────┘         │ - Usage        │              │
│                             │   Service      │              │
│                             │ - Compliance   │              │
│                             │   Service      │              │
│                             │ - Telemetry    │              │
│                             │   Service      │              │
│                             │ - Alert        │              │
│                             │   Service      │              │
│                             └────────┬───────┘              │
│                                      │                       │
│                             ┌────────▼────────┐             │
│                             │ PostgreSQL      │             │
│                             │ with PostGIS    │             │
│                             │                 │             │
│                             │ - Farmers       │             │
│                             │ - Entitlements  │             │
│                             │ - Allocations   │             │
│                             │ - Usage         │             │
│                             │ - Alerts        │             │
│                             └─────────────────┘             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                                  │
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐      ┌──────────────────┐     ┌──────────────────┐
│ NSW Water     │      │ Telemetry        │     │ Water Trading    │
│ DPIE          │      │ Providers        │     │ Platforms        │
│               │      │                  │     │                  │
│ - Allocation  │      │ - Observant      │     │ - WaterExchange  │
│   PDFs        │      │ - Goanna Ag      │     │ - Waterfind      │
│ - WSP docs    │      │ - ICT Intl       │     │                  │
│               │      │                  │     │ - Market prices  │
│ (Web scraper) │      │ (API/Web scrape) │     │ (API/Web scrape) │
└───────────────┘      └──────────────────┘     └──────────────────┘
```

---

## Go-to-Market Roadmap

### Phase 1: MVP Development (Months 1-3)

**Deliverables:**
1. **Allocation Dashboard**
   - Water account summary (total allocation, used, remaining)
   - Entitlement breakdown (support 1-5 entitlements per farmer)
   - Allocation history chart (2 years of data)

2. **Usage Tracking**
   - Manual usage entry (web + mobile-friendly)
   - Telemetry integration (Observant API only - most common provider)
   - Usage history & trends

3. **Compliance Alerts**
   - Basic rules (80% warning, 90% alert, 100% critical)
   - Email + SMS delivery
   - Alert dashboard (view/acknowledge alerts)

4. **Data Foundation**
   - Allocation scraper (Murrumbidgee Valley only - 1 water source to start)
   - Database schema (farmers, entitlements, usage, alerts)
   - User authentication (email/password login)

**Exclusions (Save for Post-MVP):**
- Multiple valley support (Murray, Lachlan - add later)
- Advanced telemetry (Goanna Ag, ICT - add if demand)
- Water trading integration (WaterExchange API - add later)
- Mobile app (start with responsive web, native app later)
- Supplementary access alerts (complex, add after basic allocations work)

**Success Criteria:**
- 20 Murrumbidgee farmers complete onboarding
- 80%+ say "I would pay $75/month for this"
- Zero critical bugs (data accuracy issues)

---

### Phase 2: Pilot Launch (Months 4-6)

**Partner:** Murrumbidgee Irrigation (MI)

**Pilot Terms:**
- 20 MI customers (hand-selected by MI)
- Free for 3 months (Oct-Dec 2024 irrigation season)
- In-person onboarding (site visits to farms)
- Weekly feedback calls

**Metrics to Track:**
1. **Engagement**
   - Daily active users (target: 50%+ check dashboard daily)
   - Alerts acknowledged (target: 80%+ acknowledge within 24 hours)

2. **Value Demonstration**
   - Count "near-miss" events (farmer warned before exceeding allocation)
   - Estimated penalty avoidance ($50K-500K per incident)

3. **Satisfaction**
   - NPS score (target: 50+)
   - Willingness to pay (target: 80%+ say yes to $75/month)

**Pilot Success = Move to Paid Launch**

---

### Phase 3: Murrumbidgee Scale-Up (Months 7-12)

**Go-Live Date:** January 2025 (start of irrigation season)

**Marketing:**
- MI co-marketing (email blast, water bill insert, farmer forums)
- Case studies from pilot (video testimonials)
- Field day demos (Murrumbidgee Irrigation Expo)

**Pricing:**
- Base: $75/month (individual farmers, <500 ML entitlement)
- Pro: $150/month (500-2,000 ML entitlement, includes trading intel)
- Enterprise: $300/month (2,000+ ML, includes consultant hotline)

**Targets:**
- End of Month 12: 200 paying customers (10% of MI customer base)
- Revenue: $216K ARR (avg $90/month per customer)

---

### Phase 4: Multi-Valley Expansion (Year 2)

**New Valleys:**
- Murray (partner with Murray Irrigation Limited)
- Lachlan (direct-to-farmer, no single irrigation operator)

**New Features:**
- Water trading integration (buy water via WaterExchange API)
- Supplementary access alerts (time-critical flow events)
- Mobile app (iOS + Android native)
- Advanced analytics (predictive usage forecasting)

**Targets:**
- End of Year 2: 648 paying customers across 3 valleys
- Revenue: $648K ARR

---

### Phase 5: Enterprise Tier (Year 3)

**New Customer Segments:**
1. **Agricultural Lenders** (AQUAOSO model)
   - $10K-50K/year for portfolio water risk analytics
   - Target: ANZ, NAB, Rabobank, Westpac Agribusiness

2. **Consultant White-Label**
   - $5K-20K/year for reselling to clients
   - Target: Aither, MJA, regional consultants

3. **Irrigation Corporations** (SaaS Platform)
   - $50K-200K/year for entire customer base
   - White-label as "MI Water Compliance Portal"

**Targets:**
- End of Year 3: 3,000 farmers + 10 enterprise customers
- Revenue: $2.5M ARR

---

## Conclusion

**Market Opportunity:**
- **$50M+ TAM** in Australian agricultural water compliance
- **NO comprehensive SaaS competitor** (market is wide open)
- **Severe pain point** (over-extraction penalties up to $2.2M)
- **Regulatory tailwind** (mandatory telemetry by 2026)

**Competitive Positioning:**
- WaterRight is the **ONLY platform** offering allocation tracking + usage monitoring + compliance alerts in one place
- Existing solutions are fragmented (trading platforms, farm mgmt software, government portals)
- Our advantage: **Comprehensive + User-friendly + Proactive alerts**

**Best Market Entry:**
- **Start:** Murrumbidgee Valley (2,300 farmers, sophisticated, Murrumbidgee Irrigation partnership)
- **Expand:** Murray, Lachlan valleys (Year 2)
- **Scale:** Enterprise tier for lenders, consultants, irrigation corporations (Year 3)

**Revenue Potential:**
- **Year 1:** $180K ARR (200 Murrumbidgee farmers)
- **Year 2:** $648K ARR (650 farmers across 3 valleys)
- **Year 3:** $2.5M ARR (3,000 farmers + 10 enterprise customers)

**Technical Reusability:**
- **90% code reuse** from existing planning compliance platform
- **2-3 months to MVP** (fastest path to revenue)
- Proven architecture (PostGIS + Document extraction + RAG + Compliance validation)

**Next Steps:**
1. **Validate market** (interview 20-30 Murrumbidgee farmers - Weeks 1-2)
2. **Secure MI partnership** (pilot agreement - Weeks 3-4)
3. **Build MVP** (Months 2-3)
4. **Launch pilot** (Month 4, 20 farmers, 3-month free trial)
5. **Scale to 200 paying customers** (Months 7-12)

**This is a HIGH OPPORTUNITY, LOW COMPETITION market with proven pain and clear path to revenue.**

---

**Document Status:** Market Research Complete
**Recommendation:** Proceed with customer discovery interviews
**Next Action:** Interview 20-30 Murrumbidgee farmers (customer discovery script provided separately if needed)
