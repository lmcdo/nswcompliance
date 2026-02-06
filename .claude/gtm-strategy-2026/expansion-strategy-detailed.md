# PlotDetect Expansion Strategy - Detailed Execution Plan

## **QUESTION 1: How to Find 50 Edge Cases**

**Answer:** Run the queries in `edge-case-finder.sql`

**Categories to review:**
1. **"Should" language** (10 provisions) - Objective vs weak control?
2. **"May" language** (10 provisions) - Permission vs optional guidance?
3. **Qualitative terms** (10 provisions) - "Adequate", "appropriate", "suitable"
4. **Short actionable** (10 provisions) - <80 chars marked actionable (false positives?)
5. **Figure references** (5 provisions) - Diagrams might contain actionable dimensions
6. **External references** (5 provisions) - ADG, BCA, AS - do we import or reference?

**Total: 50 provisions × 2 minutes each = 100 minutes (1.7 hours)**

**How to review:**
```
For each provision, ask:
1. Can a certifier measure compliance? (Yes → actionable, No → not actionable)
2. Is there a pass/fail test? (Yes → actionable, No → objective/guidance)
3. Does it reference external controls? (Yes → tag for import, No → standalone)
```

---

## **QUESTION 2: Law Student - Viable or Incompetent? How to Vet?**

### **Why Law Student Might Be Incompetent:**
- No planning law experience (contracts/torts ≠ planning)
- No practical DA experience (theory ≠ practice)
- Overly literal interpretation (can't distinguish "should" vs "must" in context)
- Expensive ($25-40/hr) for low-value work

### **Better Alternative: Planning Student or Junior Certifier**

**Option A: UNSW Planning Student ($20/hr)**
- 3rd year Bachelor of Planning or Master of Urban Planning
- Has taken "Development Control" or "Planning Law" course
- Familiar with LEP/DCP structure
- **Vet by:** "Explain the difference between LEP and DCP in 2 sentences"
- **Test task:** Review 10 edge cases, compare to your answers

**Option B: Junior Certifier ($40/hr, better value)**
- 1-2 years PCA experience
- Reviews DAs daily (knows what's enforceable)
- **Vet by:** "What's the difference between CDC and DA pathway?"
- **Test task:** "Tag these 20 provisions as CDC-eligible, DA-only, or both"

**Option C: You (4 hours, $0)**
- You've built the engine, you understand the data
- Review 50 edge cases while drinking coffee
- Faster than explaining context to student
- **Recommended for first expansion LGA**

### **Vetting Criteria (If You Do Hire):**

**Test Task (30 min, $10 payment):**
```
Review these 10 provisions from Waverley DCP and classify:

1. "Building height should not exceed the prevailing streetscape character."
   → Actionable? (Yes/No)
   → Type? (Control / Objective / Guidance)
   → Reasoning?

2. "C4.2 Minimum front setback: 6m for dwelling houses."
   → Actionable? (Yes/No)
   → Compliance pathway? (CDC / DA / Both)
   → Reasoning?

[... 8 more examples]

Correct answers: 8+/10 → hire
5-7/10 → maybe (review answers)
<5/10 → pass
```

---

## **QUESTION 3: Should You Apply for Grant at This Stage?**

### **MVP Ventures Grant Requirements:**
- **Minimum viable product** ✅ (you have this)
- **User traction** ❌ (0 professional users)
- **Market validation** ❌ (no revenue, no testimonials)
- **Growth plan** ✅ (LGA expansion roadmap)

**Assessment: TOO EARLY**

**Why:**
- Grants are competitive (100+ applicants for $100k)
- Selection criteria heavily weight traction metrics:
  - Active users (you have 0 professional users)
  - Revenue/LOIs (you have $0)
  - Professional endorsements (you have 0)
- Application takes 20-40 hours (pitch deck, financials, milestones)

**Better Timeline:**

**Now (Month 1-2):**
- Get 5-10 certifier testers
- Expand to Waverley (1 additional LGA)
- Collect feedback/testimonials

**Month 3-4:**
- Launch freemium tier publicly
- Get 50+ homeowner users
- Get 1-2 paying Pro subscribers ($149/mo)

**Month 5 (Q2 2026):**
- **THEN apply for MVP Ventures**
- Pitch: "3 LGAs live, 10 professional testers, 50 homeowner users, $300 MRR, seeking $100k to expand to 10 LGAs"
- Much stronger application

**Alternative: R&D Tax Incentive (Apply Now)**
- No traction required
- No application (just annual tax filing)
- Claim development costs backdated to July 2025
- Estimated $15-30k refund for 2025-26 FY
- **Action:** Register activities with accountant this month

---

## **QUESTION 4: Outreach Timing - Before or After Law Student Review?**

### **ANSWER: Outreach FIRST, Expansion SECOND**

**Why:**
1. **Validation before expansion** - What if certifiers say "Waverley isn't valuable, do Canterbury-Bankstown instead"?
2. **Feature prioritization** - Certifiers might say "don't care about more LGAs, want API access"
3. **Free labor** - Experienced certifiers will spot edge cases faster than law students
4. **Commitment test** - If certifiers won't test Inner West (already done), they won't test Waverley

### **Recommended Sequence:**

**Week 1: Outreach to 10 Inner West Certifiers**
- Use LinkedIn script from GTM strategy
- Offer 3-month free unlimited access
- Goal: 3 active testers

**Week 2-3: Feedback Collection**
- Daily Slack/WhatsApp check-ins
- "What's missing? What's wrong? What's confusing?"
- **Ask explicitly:** "Which LGA should I add next?"

**Week 4: Decide Next LGA Based on Feedback**
- If certifiers say "Waverley would be huge" → do Waverley
- If certifiers say "API access more important" → build API
- If certifiers say "too complex, needs simpler UI" → pause expansion

**Month 2: Expand to 1 LGA (certifier-validated choice)**
- Run edge case queries yourself (2 hours)
- QGIS georeferencing (10 hours)
- DCP config file (4 hours)

**Month 3: Apply for Grant**
- Now you have proof: "10 certifiers tested, 3 actively use weekly, requested Waverley expansion"

---

## **QUESTION 5: Details to Ensure Outreach Success**

### **LinkedIn Outreach Script (Revised with Success Details)**

**Subject:** Free early access to NSW planning compliance engine (Inner West)

```
Hi [First Name],

I saw you're a certifier in Inner West Council. I've built an automated
compliance engine that might save you 4-6 hours per DA.

**What it does:**
- Address lookup → 15-40 actionable provisions in 3 seconds
- Filters 47,818 NSW regulations by property context (zone, precinct, heritage)
- Covers LEP + DCP + SEPP Housing + Heritage overlays
- AI chat for quick lookups ("What's the parking rate for dual occupancy?")

**Example:** Try 185 Parramatta Rd, Leichhardt (demo link below)
[Loom 2-min video: Record screen showing property lookup]

**What I need:**
- 2-3 experienced certifiers to test for 3 months (free)
- Feedback on accuracy, missing provisions, UI improvements
- 30-min call after first month to hear what's broken

**What you get:**
- Unlimited free access (no credit card, no expiry)
- Direct WhatsApp to me for bugs/questions
- Early API access when launched (discounted)
- Optional case study for LinkedIn (good for marketing your firm)

Interested? I'll send login details today.

Cheers,
Lawrence
```

**Critical success factors:**
1. **Lead with time savings** - "4-6 hours per DA" (certifiers bill $200-400/hr)
2. **Show, don't tell** - Loom video showing actual property lookup
3. **Concrete example** - 185 Parramatta Rd (they can verify accuracy)
4. **Low friction** - No credit card, no forms, just "reply and I'll send login"
5. **Mutual benefit** - Case study = free marketing for their firm

### **How to Create the Loom Video (15 minutes):**

**Script (Updated 2026-02-05 with NEW heritage architecture):**
1. Go to verify.plotdetect.com.au (production URL)
2. Screen record with Loom (free)
3. "Hi, I'm Lawrence. Let me show you this compliance engine in 90 seconds."
4. Enter: **185 Parramatta Rd, Annandale** (not Leichhardt — Annandale is the suburb)
5. Show property card: **C1 Annandale Heritage Conservation Area** badge
6. Expand heritage card — council-specific text appears: "Leichhardt DCP 2013, Part C Section 1. General controls apply to all HCAs — no HCA-specific controls."
7. Click DCP tab → Heritage button: **494 provisions filtered to 16 heritage controls**
8. Show subtopics: Materials (5), Additions (2), Parking (2), Demolition (2), Solar (2), Signage (2), Verandah (1), Roof (1)
9. "That's it. 16 heritage provisions, all general controls, zero false positives. Usually takes 4-6 hours manually. Here it's 30 seconds. Interested in testing?"
10. Upload to Loom, get shareable link

**Key talking points (updated):**
- Single-table heritage architecture (no more fallback false positives)
- Council-specific explanatory text (Leichhardt vs Ashfield vs Marrickville)
- Correct provision counts: Leichhardt 16 general, Marrickville 193 general + 3 HCA-specific per HCA, Ashfield 306 general

**Expected response rate:**
- 10 messages sent → 3-4 replies (30-40%)
- 3-4 replies → 2-3 testers (50-75% conversion)
- 2-3 testers → 1 active user (50% retention after week 1)

**If response rate <20% after 10 messages:**
- Video unclear? (Re-record with simpler example)
- Wrong audience? (Try town planners instead)
- Wrong value prop? (Change "4-6 hours" to "instant parking calculations")

---

## **QUESTION 6: Which Single LGA to Prepare Next?**

### **Evaluation Criteria:**

| LGA | Market Size (DAs/year) | Complexity | Data Availability | Certifier Demand | Score |
|-----|------------------------|------------|-------------------|------------------|-------|
| **Waverley** | 850 | High (heritage) | Good (DCP online) | High (Bondi boom) | **9/10** |
| Randwick | 720 | High (UNSW area) | Good | Medium | 7/10 |
| Willoughby | 650 | Medium | Good | Medium (North Shore) | 7/10 |
| Canterbury-Bankstown | 1,200 | Medium | Fragmented (merged council) | High (volume market) | 6/10 |
| Bayside | 580 | Low | Good | Low | 5/10 |

### **RECOMMENDATION: Waverley**

**Why Waverley:**
1. **High-value market** - Bondi, Bronte, Dover Heights (wealthy, high DA fees)
2. **Complex overlays** - Heritage, coastal zone, flood = tests your engine's robustness
3. **Certifier demand** - Most certifiers work across Inner West + Waverley (geographic proximity)
4. **Good test case** - If engine handles Waverley heritage complexity, it'll handle anywhere
5. **Data quality** - Waverley DCP is well-structured, recent (2012, amended 2023)

**Data Availability Check:**
- LEP: https://legislation.nsw.gov.au/view/html/inforce/current/epi-2012-0159 ✅
- DCP: https://www.waverley.nsw.gov.au/council/codes_and_policies/planning_controls ✅
- Heritage: 7 HCAs + 200+ heritage items (state register) ✅
- Precinct maps: DCP Part E has precinct boundaries (PDF maps for QGIS) ✅

**Preparation Checklist (Waverley):**

**Week 1: Data Collection (4 hours)**
- [ ] Download Waverley LEP 2012 (legislation.nsw.gov.au)
- [ ] Download Waverley DCP 2012 (all parts A-E as PDFs)
- [ ] Download precinct maps from DCP Part E
- [ ] Verify Planning Portal has Waverley zone data (test with random address)

**Week 2: GeoJSON Creation (10 hours)**
- [ ] Open QGIS, load NSW cadastre as base layer
- [ ] Overlay DCP Part E precinct maps as raster
- [ ] Georeference each precinct map to cadastre
- [ ] Manually trace precinct boundaries (Waverley has ~15 precincts)
- [ ] Export as GeoJSON, validate with test addresses
- [ ] Upload to `dcp_precinct_boundaries` table

**Week 3: Provision Extraction (8 hours)**
- [ ] Run PDF extraction script on Waverley DCP (existing scripts)
- [ ] Review extraction quality (spot-check 20 random provisions)
- [ ] Create `enrichment/config/waverley_config.py` (DCP structure mapping)
- [ ] Run actionable classifier (automated)
- [ ] Run edge case queries, review 50 provisions (2 hours)

**Week 4: Testing & QA (4 hours)**
- [ ] Test 10 random Waverley addresses in app
- [ ] Verify provision counts match DCP (Part B = residential, Part C = commercial, etc.)
- [ ] Check precinct assignment accuracy (5 addresses across different precincts)
- [ ] Compare against council's online DA tracker (verify same provisions apply)

**Total: 26 hours over 4 weeks (6-7 hours/week)**

---

## **FINAL RECOMMENDATION: Execution Order**

### **Month 1 (February 2026):**
**Week 1:**
- ✅ Create Loom demo video (2 hours)
- ✅ Send LinkedIn outreach to 10 Inner West certifiers (1 hour)
- ✅ Set up WhatsApp/Slack for tester support (30 min)

**Week 2-4:**
- ✅ Onboard 2-3 certifier testers
- ✅ Daily check-ins, collect feedback
- ✅ Ask: "Which LGA should I add next?"

### **Month 2 (March 2026):**
**Week 1-2:**
- ✅ Download Waverley data (based on certifier validation)
- ✅ QGIS georeferencing (10 hours)

**Week 3-4:**
- ✅ Provision extraction + edge case review (8 hours)
- ✅ Testing & QA (4 hours)

### **Month 3 (April 2026):**
**Week 1-2:**
- ✅ Launch Waverley to testers
- ✅ Collect testimonials from certifiers

**Week 3-4:**
- ✅ Apply for MVP Ventures grant ($100k)
- ✅ Register R&D activities with accountant (claim $15-30k)

### **Month 4 (May 2026):**
- ✅ Launch freemium tier publicly (if tester feedback positive)
- ✅ Set up Stripe for Pro tier ($149/mo)

---

## **DO NOT:**
- ❌ Hire law student now (premature, expensive, unvalidated need)
- ❌ Apply for grant without traction (waste 40 hours on rejected application)
- ❌ Expand to 3+ LGAs before certifier validation (build what they don't want)
- ❌ Build API before UI validation (certifiers might not want API yet)

## **DO:**
- ✅ Outreach to 10 certifiers THIS WEEK
- ✅ Create Loom demo video (2 hours, huge ROI)
- ✅ Review 50 edge cases yourself (4 hours, save $100)
- ✅ Prepare Waverley ONLY AFTER certifier feedback validates demand
- ✅ Register R&D activities with accountant NOW (backdated claim for 2025-26 FY)

---

## **SUCCESS METRICS (90 Days):**

**Minimum viable success:**
- 2 active certifier testers (using weekly)
- 1 LGA expansion completed (Waverley)
- 10 pieces of feedback collected
- 1 testimonial for grant application

**Stretch success:**
- 5 active certifier testers
- 2 LGA expansions (Waverley + Randwick)
- 1 paying Pro subscriber ($149/mo)
- Grant application submitted

**Failure signals (pivot if you see these):**
- 0 certifier replies after 20 outreach messages → wrong audience or value prop
- Certifiers say "too complex, can't use" → UI problem, not expansion problem
- Certifiers say "inaccurate provisions" → data quality problem, not LGA coverage problem

---

**Next Action (Today):**
1. Record Loom video (2 hours)
2. Send 10 LinkedIn messages (1 hour)
3. Run edge case queries (save to spreadsheet for later review)

**Next Action (This Week):**
1. Onboard first certifier tester
2. Set up WhatsApp support channel
3. Review 50 edge cases while waiting for feedback (4 hours)
