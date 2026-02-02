# MVP Quality Bar - Realistic Strategy for Edge Cases

## **Edge Case Analysis Results**

**Total classified provisions:** 21,492
**Edge cases found:** 6,246 (29% of all provisions)

### **Breakdown by Category:**

| Category | Count | % of Edge Cases | Avg Priority | Issue |
|----------|-------|-----------------|--------------|-------|
| **Short Actionable** | 3,550 | 57% | 0.23 | False positives? |
| **"May" Language** | 1,700 | 27% | 0.65 | Permission vs optional |
| **Qualitative** | 735 | 12% | 0.89 | "Adequate", "appropriate" |
| **"Should" Language** | 300 | 5% | 1.42 | Ongoing requirements |
| **Figure References** | 252 | 4% | N/A | Diagrams might have data |
| **External Refs** | 9 | <1% | 2.33 | ADG, BCA, AS |

---

## **CRITICAL INSIGHT: Don't Fix Everything for MVP**

### **The False Positive vs False Negative Trade-off**

**In compliance tools:**
- **False positive** (showing extra provisions) = User wastes 10 seconds reading irrelevant provision
- **False negative** (missing critical provision) = User submits non-compliant DA, costs $5,000+ to remediate

**MVP Strategy:** Bias toward false positives. Better to show 50 provisions when 40 are relevant than miss 1 critical setback requirement.

---

## **Phased Quality Improvement Strategy**

### **PHASE 0: Pre-Outreach (NOW) - Fix Critical Gaps Only**

**Goal:** Eliminate false negatives that would destroy credibility

**What to fix (2 hours):**

1. **Review "Should" provisions with ongoing requirements (300 total)**
   - These are likely DCP controls that use soft language but are enforced
   - Example: "Building design should maintain heritage character" → ongoing DA requirement
   - **Action:** Sample 20, verify they're correctly marked actionable
   - **SQL:** Already in `edge-case-finder.sql` - Category 1

2. **Review External References (9 total)**
   - ADG, BCA, AS references are high-priority
   - Example: "Development must comply with ADG" → need to clarify in UI
   - **Action:** Review all 9, add UI note: "See [ADG document] for detailed requirements"
   - **SQL:** Already in `edge-case-finder.sql` - Category 6

3. **Spot-check 10 random provisions from each DCP part**
   - Verify Part 4.1 (Low Density) returns dwelling house provisions
   - Verify Part 8 (Heritage) returns heritage provisions
   - Verify precinct provisions match correct precinct
   - **Action:** Manual testing with known addresses

**Time: 2 hours**
**Impact: Prevents catastrophic "missing critical provisions" errors**

---

### **PHASE 1: MVP Outreach (Week 1-4) - Ship with Known Limitations**

**Goal:** Get 3 certifier testers using the tool weekly

**Accept these limitations (document in UI):**

1. **Short actionable provisions (3,550)** - SHIP AS-IS
   - Low priority score (0.23) suggests many are section headings or context
   - **UI solution:** Add "Show only controls with measurements" toggle
   - **Example:** User sees 50 provisions, toggles filter, sees 35 with numeric values
   - **Cost to fix:** 20 hours manual review → NOT WORTH IT for MVP
   - **Certifier feedback:** "Is this too many provisions?" If yes, add filter. If no, leave as-is.

2. **"May" language provisions (1,700)** - SHIP AS-IS
   - These are permissions ("development may include") or optional pathways
   - **UI solution:** Tag with pill: "Optional" or "Permission"
   - **Example:** "Garages may be setback 3m" → shown with "Optional" tag
   - **Cost to fix:** 10 hours manual review + tagging logic → DEFER to Phase 2
   - **Certifier feedback:** "Are these useful or noise?" Adjust based on usage data.

3. **Qualitative language (735)** - SHIP AS-IS
   - "Adequate", "appropriate", "suitable" are subjective but enforceable
   - **UI solution:** Show with context: "Requires council assessment"
   - **Example:** "Private open space must be adequate" → show but note it's interpretive
   - **Cost to fix:** Impossible without council interpretation → ACCEPT as limitation
   - **Certifier feedback:** "Do you trust these provisions?" If yes, keep. If no, add filter.

4. **Figure references (252)** - DEFER TO PHASE 2
   - Currently marked NOT actionable
   - **UI solution:** Show PDF page link: "See Figure 4.2 on page 42 for setback diagram"
   - **Cost to fix:** 15 hours manual extraction of diagram data → DEFER
   - **Certifier feedback:** "Do you need the diagram data extracted?" If yes, prioritize Phase 2.

**Transparent Communication with Testers:**

Include in onboarding email:
```
**Known Limitations (Feb 2026 MVP):**
- Some provisions use qualitative language ("adequate", "appropriate")
  that requires council interpretation
- Figure/diagram references shown but data not yet extracted (see PDF page link)
- Optional provisions ("may", "should") included but not yet tagged as such

**What I need feedback on:**
- Are there too many provisions? (Should I add filters?)
- Are provisions accurate? (Any false negatives - missing critical controls?)
- Which improvements matter most? (Filters, tags, diagram extraction?)
```

**MVP Quality Bar:**
- ✅ Zero false negatives for "must/shall" provisions with measurements
- ✅ Correct precinct assignment (test with 10 addresses)
- ✅ Correct DCP part filtering (residential vs commercial vs heritage)
- ⚠️ Accept 20-30% "noise" provisions (false positives) - filter in Phase 2
- ⚠️ Accept qualitative provisions without interpretation guidance
- ❌ Do NOT ship if missing entire DCP parts or precincts

---

### **PHASE 2: Post-Tester Feedback (Month 2-3) - Iterative Improvement**

**Goal:** Fix highest-impact issues identified by certifiers

**Likely feedback patterns:**

**Scenario A: "Too many provisions, hard to find critical ones"**
→ **Solution:** Add filters
- "Show only quantitative controls" (has measurements)
- "Show only mandatory" (must/shall only)
- "Hide objectives" (exclude "should" language)
- **Cost:** 4 hours frontend work
- **Impact:** High (improves UX immediately)

**Scenario B: "Missing provisions from Part X"**
→ **Solution:** Review DCP extraction for that part
- Check PDF parsing quality
- Verify precinct assignment logic
- Re-run actionable classifier with adjusted thresholds
- **Cost:** 2-4 hours per part
- **Impact:** Critical (false negatives destroy trust)

**Scenario C: "These qualitative provisions are useless"**
→ **Solution:** Add interpretation guidance
- Link to council assessment guidelines
- Show historical DA examples (if available)
- Add "Requires professional judgment" tag
- **Cost:** 6 hours research + UI work
- **Impact:** Medium (nice-to-have, not critical)

**Scenario D: "Need diagram data extracted"**
→ **Solution:** Manual extraction for high-value diagrams
- Identify top 20 most-referenced diagrams (setbacks, parking layouts)
- Manually extract dimensions, add to provision metadata
- Display as structured data in UI
- **Cost:** 10-15 hours
- **Impact:** Medium-High (depends on frequency of use)

**Prioritization Framework:**

```
Priority = (Frequency of feedback × Impact on trust) / Hours to fix

High priority (do immediately):
- Missing provisions (false negatives) - destroys trust
- Wrong precinct assignment - shows irrelevant provisions
- Entire DCP parts missing - unusable for that dev type

Medium priority (do in 2-4 weeks):
- Too many provisions (add filters)
- Diagram data extraction (top 20 diagrams)
- Optional vs mandatory tagging

Low priority (defer to Phase 3):
- Qualitative interpretation guidance
- Cross-document references (ADG import)
- Historical DA examples
```

---

### **PHASE 3: Pre-Public Launch (Month 4+) - Polish for Scale**

**Goal:** Reduce false positive rate from 30% to <10%

**After certifier validation, invest in:**

1. **LLM-based re-classification** ($48 per LGA)
   - Use Claude/Gemini to re-classify the 6,246 edge cases
   - Prompt: "Is this an enforceable control or design guidance?"
   - Compare to regex results, improve patterns
   - **Cost:** $48/LGA + 4 hours prompt engineering
   - **Impact:** Reduces false positives by 50-70%

2. **Compliance pathway tagging** (CDC vs DA)
   - Junior certifier reviews 200 high-value provisions
   - Tags as: "CDC-eligible", "DA-only", "Both"
   - Enables future CDC pathway feature
   - **Cost:** $200 (5 hours @ $40/hr)
   - **Impact:** Unlocks new feature (CDC filtering)

3. **Diagram data extraction** (automated)
   - OCR + GPT-4V to extract dimensions from diagrams
   - Parse setback diagrams, parking layouts
   - Store as structured data
   - **Cost:** $100 API costs + 8 hours dev
   - **Impact:** High for visual learners

---

## **Realistic MVP Onboarding Strategy**

### **Target: 3 Active Certifier Testers in 30 Days**

**Week 1: Outreach (10 messages)**
- Send LinkedIn script to 10 Inner West certifiers
- Expected: 3-4 replies (30-40% response rate)
- **Qualifying question:** "Do you certify 5+ DAs/month in Inner West?" (ensure active users)

**Week 2: Onboarding (3 testers)**
- Send login credentials immediately upon reply
- Include:
  - Loom demo video (2 min)
  - Known limitations doc (be transparent)
  - Test task: "Look up 3 properties you're currently certifying, verify accuracy"
  - WhatsApp/Slack invite for support

**Day 1-3 after signup:**
- Daily check-in: "Did you try it? What broke?"
- Track first session activity (which provisions clicked, which filtered)
- **Critical metric:** Did they look up 3+ properties? (Yes = engaged, No = churned)

**Week 3: Feedback Collection**
- Send survey:
  ```
  1. Accuracy: Were provisions correct for your test properties? (1-5 scale)
  2. Completeness: Any missing provisions you expected to see? (free text)
  3. Usability: Too many/too few provisions shown? (1-5 scale)
  4. Value: Would you pay $149/mo for this? (Yes/No/Maybe)
  5. Next LGA: Which council should I add next? (Waverley, Randwick, other?)
  ```

**Week 4: Iteration Based on Feedback**
- If accuracy <4/5 → fix false negatives (highest priority)
- If usability <3/5 → add filters (medium priority)
- If value = "No" → revisit product positioning
- If value = "Yes" → prepare Stripe paywall

**Success Criteria (30 days):**
- ✅ 3/3 testers looked up 5+ properties each
- ✅ Accuracy rating ≥4/5 average
- ✅ 2/3 testers say "would consider paying"
- ✅ 10+ pieces of specific feedback collected
- ✅ 1 testimonial ("This saved me 4 hours on a DA for [address]")

**Failure Signals (pivot if you see):**
- ❌ 0 signups after 20 outreach messages → wrong audience or value prop
- ❌ Testers sign up but don't use (0 properties looked up) → onboarding problem
- ❌ Testers say "inaccurate" → data quality problem (fix before expansion)
- ❌ Testers say "too complex" → UX problem (simplify before expansion)

---

## **Quality Acceptance Matrix for MVP**

| Metric | Acceptable for MVP | Needs Fixing Before Public Launch |
|--------|-------------------|-----------------------------------|
| **False Negative Rate** | <2% (missing <1 in 50 critical provisions) | <0.5% (near-zero missing provisions) |
| **False Positive Rate** | <30% (showing 30 extra provisions per 100 relevant) | <10% (minimal noise) |
| **Precinct Accuracy** | >95% (correct for 19/20 addresses) | >99% (correct for 99/100) |
| **DCP Part Coverage** | 100% (all parts extracted) | 100% (no change) |
| **Provision Text Quality** | >90% readable (minor PDF artifacts OK) | >98% clean text |
| **Qualitative Provisions** | Shown as-is (no interpretation) | Tagged with guidance |
| **Figure Data** | PDF link only | Extracted dimensions (top 20) |
| **External Refs** | Noted but not imported | Linked or summarized |

---

## **Recommendation: Ship MVP This Week**

### **What to Do NOW (4 hours):**

1. **Run edge case spot-checks (2 hours):**
   ```sql
   -- Check "should" provisions (sample 20)
   SELECT * FROM regulatory_provisions
   WHERE provision_text ILIKE '%should%'
   AND v2_is_actionable = true
   ORDER BY random() LIMIT 20;

   -- Check external refs (all 9)
   SELECT * FROM regulatory_provisions
   WHERE provision_text ILIKE '%ADG%'
   OR provision_text ILIKE '%BCA%';

   -- Test 10 random addresses across different precincts
   -- (manual testing in UI)
   ```

2. **Add "Known Limitations" to UI (1 hour):**
   - Footer or info icon on provisions list
   - "Some provisions use qualitative language requiring interpretation"
   - "Figure references link to PDF pages (data extraction coming soon)"

3. **Create tester onboarding doc (1 hour):**
   - Loom video (2 min demo)
   - Known limitations
   - Test task (lookup 3 properties)
   - Feedback survey link

4. **Send first 5 LinkedIn messages (30 min):**
   - Don't wait for perfection
   - Professional feedback > perfect product
   - Iterate based on real-world usage

### **What NOT to Do:**

- ❌ Review all 6,246 edge cases manually (100+ hours, diminishing returns)
- ❌ Build filters before knowing if they're needed (4 hours wasted if testers don't care)
- ❌ Extract diagram data before validating demand (15 hours premature)
- ❌ Hire law student to classify edge cases (certifiers will do this for free via feedback)
- ❌ Wait for 100% accuracy before outreach (impossible, perfectionism kills MVPs)

---

## **The 80/20 Rule for MVP Quality**

**80% of value comes from:**
- ✅ Correct DCP part filtering (residential vs commercial)
- ✅ Correct precinct assignment (address → precinct boundary matching)
- ✅ Zero false negatives for "must/shall" + numeric provisions
- ✅ All provisions have PDF page links for verification

**Remaining 20% of value (defer to Phase 2):**
- ⏸️ Filtering false positives (qualitative, optional provisions)
- ⏸️ Diagram data extraction
- ⏸️ Interpretation guidance
- ⏸️ Cross-document imports (ADG, BCA)

**You already have the 80%.** Ship it, get feedback, iterate.

---

## **Final Answer to "What's the Best Strategy?"**

### **For Edge Cases:**
1. **NOW:** Spot-check 30 provisions (2 hours) - verify no catastrophic false negatives
2. **Week 1-4:** Ship MVP with known limitations, collect professional feedback
3. **Month 2-3:** Fix highest-impact issues identified by certifiers
4. **Month 4+:** Polish for public launch (LLM re-classification, filters, diagrams)

### **For MVP Outreach:**
1. **Week 1:** 10 LinkedIn messages → 3 signups
2. **Week 2:** Onboard with transparency (known limitations doc)
3. **Week 3:** Daily check-ins, collect feedback
4. **Week 4:** Iterate based on usage data

### **Quality Bar:**
- **MVP:** <2% false negatives, <30% false positives, >95% precinct accuracy
- **Public Launch:** <0.5% false negatives, <10% false positives, >99% precinct accuracy

### **Success Metric:**
**1 testimonial in 30 days:** "This saved me 4 hours on a DA for [address]"

If you get that, you have product-market fit. Everything else is optimization.

---

## **Next Action (Monday Morning):**

1. ✅ Record Loom demo (2 hours)
2. ✅ Run edge case spot-checks (2 hours)
3. ✅ Send 5 LinkedIn messages (30 min)
4. ✅ Wait for replies (patience is a strategy)

**DO NOT:**
- Spend 20 hours reviewing edge cases
- Build features before validating demand
- Wait for 100% accuracy

**DO:**
- Ship imperfect MVP
- Get professional feedback
- Iterate weekly

The best strategy is **speed + transparency**. Certifiers will forgive imperfection if you're responsive and honest about limitations.
