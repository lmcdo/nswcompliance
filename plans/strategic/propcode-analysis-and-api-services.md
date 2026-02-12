# PropCode LEP/DCP Digitization Analysis + PlotDetect API Services Strategy
**Date:** 2026-02-06

---

## 1. PropCode's LEP/DCP "Complete Digitization" - What It Actually Means

Based on competitive research, here's what PropCode likely has:

### What PropCode Digitized (Likely)

**Spatial Layers:**
- Zoning maps for all NSW councils (R2, R3, B4, etc. polygons)
- Height limit overlays (9m, 12m, 15m zones)
- FSR overlays (0.5, 0.7, 1.0 zones)
- Land use overlays (bushfire-prone, flood planning, heritage)

**LEP Controls (Structured Data):**
- Max FSR by zone (from LEP clause 4.4)
- Max height by zone (from LEP clause 4.3)
- Min lot size for subdivision (from LEP clause 4.1)
- Permitted/prohibited uses (from LEP Land Use Tables)
- Heritage item numbers (from LEP Schedule 5)

**SEPP Rules:**
- Codes SEPP complying development standards
- Housing SEPP minimum requirements

### What PropCode Likely Does NOT Have

**DCP Detailed Provisions:**
- ❌ Setback controls (front 6m, side 0.9m, rear 6m)
- ❌ Parking specifications (dimensions 5.5m × 2.4m, gradient 1:4)
- ❌ Landscaping requirements (20% of site, 3m depth, canopy trees)
- ❌ Materials requirements (roof pitch 25-35°, brick/masonry walls)
- ❌ Heritage Area Character Statements
- ❌ Provision-level filtering by development type

**Why?** DCP provisions are 300+ pages of NARRATIVE TEXT per council. Extracting this into structured data requires:
- Manual reading by planning experts
- Interpretation (which provisions are actionable vs informational)
- Taxonomy creation (v2_marker, v2_topic, v2_is_actionable)
- PDF page citation linking

PropCode's focus on "minutes vs weeks" and "instant analysis" suggests they provide **planning control lookup** (zoning, FSR, height) NOT **detailed DCP provision extraction** (setbacks, materials, parking specs).

### Comparison: PropCode vs PlotDetect

| Feature | PropCode | PlotDetect |
|---------|----------|------------|
| **Spatial layers** | ✅ All NSW zoning maps | ✅ Inner West only |
| **LEP controls** | ✅ FSR, height, min lot size | ✅ FSR, height, constraints |
| **Land use tables** | ✅ Permitted uses | ✅ Permissibility check |
| **DCP provisions (detailed)** | ❌ Unlikely | ✅ 47,818 provisions |
| **Heritage provisions** | ❌ Likely just "heritage item Y/N" | ✅ 306 heritage provisions with v2_topic |
| **Provision taxonomy** | ❌ No | ✅ v2_marker, v2_topic, v2_is_actionable |
| **PDF page citations** | ❌ Likely links to whole DCP | ✅ Specific page numbers |
| **Coverage** | ✅ All NSW (3M properties) | ⚠️ Inner West only (3 councils) |

### The Gap

**PropCode does:** "What zone is this property? What's the FSR? What uses are permitted?"
**PlotDetect does:** "What are the 395 DCP provisions that apply to my dual occupancy development? What's the exact parking setback requirement?"

PropCode = **Planning control lookup** (breadth across NSW)
PlotDetect = **DCP provision extraction** (depth in Inner West)

---

## 2. PlotDetect API Services - Feasibility & Competition Gap Analysis

API services PlotDetect could offer to PropTech companies and planning software:

### API Option 1: Heritage Provision API 🔥
**Endpoint:** `GET /api/heritage/provisions?address={address}`

**What it returns:**
```json
{
  "address": "10 Railway Parade, Summer Hill NSW 2130",
  "heritage_context": {
    "hca": "C95",
    "hca_name": "Railway Parade Heritage Conservation Area",
    "heritage_items_nearby": ["I045 (Railway Station, State significant)"],
    "significance": "Local"
  },
  "provisions": [
    {
      "id": 1234,
      "topic": "roof",
      "text": "Hipped or gabled roofs of 25-35 degree pitch typical",
      "pdf_page": 156,
      "relevance": "high"
    },
    {
      "id": 1235,
      "topic": "materials",
      "text": "Face brick or rendered masonry with timber joinery",
      "pdf_page": 157,
      "relevance": "high"
    }
    // ... 18 total heritage provisions
  ],
  "area_character_statement": "The Railway Parade HCA is characterized by Federation-era detailing..."
}
```

**Competition gap:** ⭐⭐⭐⭐⭐ (NO ONE has heritage provision API)
**Implementation effort:** ⭐ (Already have 306 heritage provisions structured)
**Customer demand:** ⭐⭐⭐⭐ (Heritage consultancies, architects, town planners)

**Potential customers:**
- Heritage consultancy software (no dedicated tools exist - they use Word)
- Archistar/PropCode (could white-label heritage module)
- Council ePlanning systems (auto-populate heritage assessment section)

**Pricing:** $0.50 per API call or $500/month for 1,000 calls

---

### API Option 2: DCP Provision Filtering API 🔥
**Endpoint:** `GET /api/provisions/filter?address={address}&development_type={type}`

**What it returns:**
```json
{
  "address": "35 Albert Street, Ashfield NSW 2131",
  "development_type": "dual_occupancy",
  "zone": "R2",
  "provisions": {
    "total": 395,
    "by_topic": {
      "parking": 32,
      "landscaping": 11,
      "building_form": 20,
      "setbacks": 4,
      "materials": 15
    },
    "provisions_list": [
      {
        "id": 5678,
        "topic": "parking",
        "text": "Car spaces shall be setback minimum 1m from front boundary",
        "pdf_page": 245,
        "is_actionable": true,
        "layer": "generic"
      }
      // ... 395 provisions
    ]
  }
}
```

**Competition gap:** ⭐⭐⭐⭐ (PropCode likely doesn't have provision-level filtering)
**Implementation effort:** ⭐ (Already have /api/provisions/for-property)
**Customer demand:** ⭐⭐⭐⭐⭐ (High - architects, developers, town planners)

**Potential customers:**
- Archistar (augment their compliance checks with DCP provision citations)
- canibuild (add provision-level detail to granny flat feasibility)
- Architect design software (show applicable provisions during design)

**Pricing:** $0.30 per API call or $300/month for 1,000 calls

---

### API Option 3: CDC Blocker API
**Endpoint:** `GET /api/cdc/check?address={address}&development_type={type}`

**What it returns:**
```json
{
  "address": "10 Railway Parade, Summer Hill NSW 2130",
  "development_type": "dual_occupancy",
  "cdc_eligible": false,
  "pathway": "DA",
  "blockers": [
    {
      "blocker": "heritage_conservation_area",
      "description": "Property is within Heritage Conservation Area C95",
      "provision": "ISEPP 2021 cl 2.81(2)(c)",
      "citation": "Complying development is prohibited in heritage conservation areas"
    }
  ],
  "da_requirements": {
    "heritage_impact_statement": true,
    "notification": "20 days",
    "estimated_timeframe": "8-12 weeks"
  }
}
```

**Competition gap:** ⭐⭐⭐ (Archistar probably has this, but maybe not as API)
**Implementation effort:** ⭐ (Already have /api/cdc/preliminary-check)
**Customer demand:** ⭐⭐⭐⭐⭐ (Very high - certifiers, architects, conveyancers)

**Potential customers:**
- Conveyancing platforms (LEAP, InfoTrack) - add CDC check to property searches
- Real estate listing sites (Domain, REA) - "CDC eligible" badge on listings
- PropHero/Stash investment tools - CDC feasibility affects investment score

**Pricing:** $0.20 per API call or $200/month for 1,000 calls

---

### API Option 4: Heritage Proximity API
**Endpoint:** `GET /api/heritage/proximity?lat={lat}&lng={lng}&radius=100`

**What it returns:**
```json
{
  "location": {"lat": -33.9, "lng": 151.1},
  "within_hca": true,
  "hca_details": {
    "code": "C95",
    "name": "Railway Parade Heritage Conservation Area",
    "significance": "Local"
  },
  "heritage_items_nearby": [
    {
      "item_number": "I045",
      "name": "Summer Hill Railway Station",
      "significance": "State",
      "distance_meters": 45,
      "curtilage": true,
      "description": "Federation-era railway station with clock tower"
    }
  ],
  "aboriginal_heritage": {
    "ahims_sites_within_200m": 0,
    "lalc": "Deerubbin Local Aboriginal Land Council",
    "consultation_required": false
  }
}
```

**Competition gap:** ⭐⭐⭐⭐⭐ (NO ONE offers comprehensive heritage proximity API)
**Implementation effort:** ⭐⭐ (Have HCA boundaries, need heritage item points + AHIMS integration)
**Customer demand:** ⭐⭐⭐⭐ (Heritage consultants, conveyancers, valuers)

**Potential customers:**
- Property data providers (CoreLogic, PropTrack) - enrich property records
- Conveyancing software - automated heritage overlay search
- Heritage consultancies - pre-screen projects for heritage triggers

**Pricing:** $0.40 per API call or $400/month for 1,000 calls

---

### API Option 5: Provision Citation Search API
**Endpoint:** `GET /api/provisions/search?query={text}&council={council}`

**What it returns:**
```json
{
  "query": "parking setback",
  "council": "ashfield",
  "results": [
    {
      "provision_id": 5678,
      "text": "Car spaces shall be setback minimum 1m from front boundary",
      "topic": "parking",
      "pdf_reference": "Ashfield DCP 2015, Part E5, p.245",
      "relevance_score": 0.95
    },
    {
      "provision_id": 5679,
      "text": "Visitor parking spaces shall be setback minimum 0.5m from side boundaries",
      "topic": "parking",
      "pdf_reference": "Ashfield DCP 2015, Part E5, p.247",
      "relevance_score": 0.87
    }
  ],
  "total_results": 2
}
```

**Competition gap:** ⭐⭐⭐⭐⭐ (UNIQUE - no one offers DCP provision semantic search)
**Implementation effort:** ⭐⭐⭐ (Need to add text search/embeddings to provision database)
**Customer demand:** ⭐⭐⭐ (Niche - town planners researching provisions)

**Potential customers:**
- Town planning firms - research tool for DA report writing
- Council planners - quick provision lookup during assessment
- Legal firms - planning clause research for appeals

**Pricing:** $0.10 per API call or $100/month for 1,000 calls

---

## Summary: Best API Options (Ranked)

| API | Competition Gap | Implementation Effort | Customer Demand | Revenue Potential | Recommended? |
|-----|-----------------|----------------------|-----------------|-------------------|--------------|
| **Heritage Provision API** | ⭐⭐⭐⭐⭐ | ⭐ (Easy) | ⭐⭐⭐⭐ | $50k-200k/year | ✅ YES |
| **DCP Provision Filtering** | ⭐⭐⭐⭐ | ⭐ (Easy) | ⭐⭐⭐⭐⭐ | $100k-300k/year | ✅ YES |
| **CDC Blocker API** | ⭐⭐⭐ | ⭐ (Easy) | ⭐⭐⭐⭐⭐ | $75k-250k/year | ✅ YES |
| **Heritage Proximity API** | ⭐⭐⭐⭐⭐ | ⭐⭐ (Medium) | ⭐⭐⭐⭐ | $40k-150k/year | ⚠️ MAYBE |
| **Provision Search API** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ (Hard) | ⭐⭐⭐ | $20k-50k/year | ❌ NO (low ROI) |

---

## Recommended Launch Strategy

### Phase 1 (Immediate): Package Top 3 APIs as "PlotDetect Data API"

**Included endpoints:**
- Heritage Provision API
- DCP Provision Filtering API
- CDC Blocker API

**Pricing:** $500/month for 1,000 calls across all endpoints (volume discounts for >10k calls)

**Target customers:**
1. **Archistar/canibuild** (white-label heritage + provision data)
2. **CoreLogic/PropTrack** (enrich property records with heritage + DCP data)
3. **LEAP/InfoTrack** (conveyancing integration - CDC + heritage checks)
4. **Heritage consultancy software vendors** (if any exist, or individual consultancies building tools)

**Revenue projection:** 5 customers × $500/month = $2,500/month = $30k Year 1

### Customer Value Propositions

**For Archistar:**
- "Add heritage compliance module without building it yourself"
- "PlotDetect's 306 heritage provisions + Area Character Statements complement your 90+ generic checks"
- White-label as "Archistar Heritage powered by PlotDetect"

**For CoreLogic/PropTrack:**
- "Enrich your 3M property records with heritage + DCP provision data"
- "Differentiate from competitors - only property data platform with DCP provision depth"
- "Upsell to architects/developers: 'See applicable DCP provisions' feature"

**For LEAP/InfoTrack (Conveyancing):**
- "Automate heritage overlay searches (currently manual s10.7 cert review)"
- "CDC pathway check reduces conveyancer time by 15 min per property"
- "Professional indemnity protection: catch heritage constraints early"

**For Heritage Consultancies:**
- "API access to heritage provisions for custom SOHI generation tools"
- "If you're building internal software, integrate PlotDetect data vs manually maintaining provision database"

---

## Technical Implementation (Top 3 APIs)

### 1. Heritage Provision API

**Existing PlotDetect infrastructure:**
- ✅ 306 heritage provisions in `regulatory_provisions` table with `v2_marker='heritage'`
- ✅ HCA boundaries in `heritage_conservation_areas` table
- ✅ Heritage item spatial data (if exists, or needs to be added)

**Additional work required:**
```python
# New endpoint in Next.js API routes
# /api/v1/heritage/provisions

async def get_heritage_provisions(address: str):
    # 1. Geocode address
    coords = geocode_address(address)

    # 2. Check if in HCA
    hca = db.query("""
        SELECT hca_slug, hca_name, significance
        FROM heritage_conservation_areas
        WHERE ST_Contains(geom, ST_Point(%s, %s))
    """, coords.lng, coords.lat)

    # 3. Find nearby heritage items (PostGIS query)
    heritage_items = db.query("""
        SELECT item_number, name, significance,
               ST_Distance(geom, ST_Point(%s, %s)) as distance
        FROM heritage_items
        WHERE ST_DWithin(geom, ST_Point(%s, %s), 100)
        ORDER BY distance
    """, coords.lng, coords.lat, coords.lng, coords.lat)

    # 4. Get applicable heritage provisions
    provisions = db.query("""
        SELECT id, v2_topic, provision_text, pdf_page
        FROM regulatory_provisions
        WHERE v2_marker = 'heritage'
          AND (hca_slug = %s OR hca_slug IS NULL)
        ORDER BY v2_topic, id
    """, hca.hca_slug if hca else None)

    # 5. Return structured JSON
    return {
        "heritage_context": {
            "hca": hca.hca_slug,
            "hca_name": hca.hca_name,
            "heritage_items_nearby": heritage_items
        },
        "provisions": provisions,
        "area_character_statement": load_area_character_statement(hca.hca_slug)
    }
```

**Implementation effort:** 2-3 days (geocoding + PostGIS queries + API route)

---

### 2. DCP Provision Filtering API

**Existing PlotDetect infrastructure:**
- ✅ 47,818 provisions in `regulatory_provisions`
- ✅ `/api/provisions/for-property` already implements this logic

**Additional work required:**
```python
# Expose existing endpoint as public API with auth
# /api/v1/provisions/filter

# Add API key authentication
# Add rate limiting (1,000 calls/month per key)
# Add usage tracking for billing

# Existing logic:
async def filter_provisions(address: str, development_type: str):
    # Already implemented in frontend-nextjs/app/api/provisions/for-property/route.ts
    # Just need to:
    # 1. Add API key middleware
    # 2. Add CORS headers for external callers
    # 3. Version as /api/v1/
    # 4. Document in API docs
```

**Implementation effort:** 1 day (API key auth + docs)

---

### 3. CDC Blocker API

**Existing PlotDetect infrastructure:**
- ✅ `/api/cdc/preliminary-check` already implements this

**Additional work required:**
```python
# Expose as public API
# /api/v1/cdc/check

# Same as provision filtering:
# - Add API key auth
# - Add rate limiting
# - Version endpoint
# - Document

# Enhance response to include DA requirements estimate:
response = {
    "cdc_eligible": False,
    "pathway": "DA",
    "blockers": [...],
    "da_requirements": {
        "heritage_impact_statement": check_heritage(address),
        "notification": get_notification_period(zone, development_type),
        "estimated_timeframe": estimate_da_timeframe(blockers)
    }
}
```

**Implementation effort:** 2 days (auth + DA requirements logic)

---

## API Platform Requirements

### Authentication & Billing
- API key generation (UUID v4)
- Usage tracking (log each API call with timestamp, endpoint, customer_id)
- Monthly billing calculation (calls × rate)
- Rate limiting (per-key limits: 1,000/month basic, 10,000/month premium)

### Documentation
- OpenAPI/Swagger spec
- Interactive docs (Swagger UI or Postman collection)
- Code examples (Python, JavaScript, cURL)
- Sample responses

### Monitoring
- API uptime monitoring
- Error rate tracking
- Latency metrics (p50, p95, p99)
- Customer usage dashboards

**Total implementation effort:** 1-2 weeks for all 3 APIs + platform infrastructure

---

## Go-to-Market Strategy

### Month 1: Build
- Implement top 3 APIs
- Create API documentation
- Build customer dashboard (view usage, manage API keys)

### Month 2: Beta
- Invite 3 beta customers (1 PropTech, 1 heritage consultancy, 1 conveyancer)
- Free beta access for 2 months
- Collect feedback, iterate on API design

### Month 3: Launch
- Public launch: "PlotDetect Data API"
- Pricing: $500/month for 1,000 calls
- Target: 5 paying customers by end of Q1

### Month 4-6: Expand
- Add Heritage Proximity API (if customer demand)
- Volume discounts for >10k calls/month
- Enterprise tier: Custom SLA, dedicated support

---

## Risk Mitigation

### Risk 1: Low API adoption (no one wants to integrate)

**Mitigation:**
- Offer free tier: 100 calls/month free (like Stripe, Mapbox model)
- Build no-code integrations (Zapier, Make.com) for non-developers
- Create white-label widgets (embeddable heritage check widget for consultancy websites)

### Risk 2: Archistar builds heritage module internally

**Mitigation:**
- Speed: Launch API in 2 weeks before they notice
- Partnership pitch: "We maintain heritage data, you focus on core product"
- Exclusive: Offer Archistar 6-month exclusive white-label deal

### Risk 3: Heritage provision data becomes outdated

**Mitigation:**
- Council amendment monitoring (scrape council websites monthly for DCP amendments)
- Customer feedback: "Report incorrect provision" feature
- Annual audit: Heritage consultant reviews all provisions (budget $5k/year)

---

## Revenue Forecast (Conservative)

**Year 1:**
- 5 customers × $500/month × 12 = $30,000

**Year 2:**
- 15 customers × $500/month × 12 = $90,000
- Plus 3 enterprise customers (>10k calls) × $2,000/month × 12 = $72,000
- **Total: $162,000**

**Year 3:**
- 30 standard customers × $500 × 12 = $180,000
- 8 enterprise customers × $2,000 × 12 = $192,000
- **Total: $372,000**

**Margin:** >90% (API infrastructure cost ~$500/month AWS)

---

## Next Steps

1. **Week 1:** Build API authentication + rate limiting infrastructure
2. **Week 2:** Expose Heritage Provision, DCP Filtering, CDC Blocker as v1 APIs
3. **Week 3:** Create API documentation + developer portal
4. **Week 4:** Outreach to 10 target customers for beta (Archistar, CoreLogic, LEAP, heritage consultancies)
5. **Month 2:** Beta program with 3 customers
6. **Month 3:** Public launch

**Decision point:** Should we prioritize API business alongside heritage consultancy product, or focus on one GTM strategy?

---

*END OF ANALYSIS*
