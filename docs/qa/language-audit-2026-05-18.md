# Language Audit — Satellite Product Pipelines

**Date:** 2026-05-18
**Scope:** All user-facing text in 7 satellite products (solar-yield, flood-truth, shadow, granny-flat, threat-radar, bushfire-prescreen, pre-da-history) across interactive UI components, shared report pages, and PDF report generators.
**Branch:** `chore/language-audit-liability-cleanup`
**Auditor:** Lawrence McDonell (founder) + Claude Code (automated grep + manual review)

---

## 1. Purpose

This document records the method, reasoning, legal basis, and assessment criteria for a systematic language audit of all satellite product user-facing text. The audit is part of a broader QA validation plan (`~/.claude/plans/ce-satellite-qa-validation-plan.md`) designed to make PlotDetect's satellite reports legally defensible under Australian Consumer Law and common law negligence principles.

The goal is not to water down the product. It is to ensure that every claim we make is **supportable by the data we actually have**, and that no user-facing text crosses the boundary from factual information into advice, recommendation, or assurance that we cannot back up.

---

## 2. Legal Basis

### 2.1 Australian Consumer Law s18 — Misleading or Deceptive Conduct

Section 18 of Schedule 2 to the *Competition and Consumer Act 2010* (Cth) prohibits conduct in trade or commerce that is misleading or deceptive, or is likely to mislead or deceive.

**Key characteristics:**
- **Strict liability** — intent to mislead is irrelevant. If a reasonable consumer would be misled, the conduct is unlawful regardless of whether we believed our statements were true.
- **Cannot be contracted out** — disclaimers cannot exclude s18 liability after the fact. They can reduce the likelihood of conduct being found misleading (by setting expectations), but they cannot override the prohibition.
- **Reliance** — the claimant must show they relied on the conduct to their detriment. For property purchase decisions, reliance is straightforward to establish.

**Application to PlotDetect:** If a report states "ADG compliant" and a user relies on this when purchasing a property, but the property later fails an ADG assessment, the user has a potential s18 claim. The word "compliant" implies a formal compliance determination that we are not qualified to make. Changing to "Meets ADG solar access test" describes what our model shows without making a compliance determination.

**Leading authority:** *Butcher v Lachlan Elder Realty Pty Ltd* [2004] HCA 60 — the High Court held that the relevant question is whether the conduct would mislead a reasonable member of the class to whom it is directed. For property reports, the class is property buyers and their advisors, who may place significant weight on written assessments.

### 2.2 Shaddock Negligence — Duty of Care for Information Providers

*Shaddock & Associates Pty Ltd v Parramatta City Council* [1981] HCA 59 established that a party who provides information, knowing or having reason to know that another will rely on it, owes a duty of care in the provision of that information.

**Application to PlotDetect:** We publish property-specific risk assessments that we know will be used in purchase and development decisions. This creates a duty of care. The duty is not to be perfect — it is to exercise reasonable care and skill, and to honestly represent the limitations of our analysis.

**Relevance to language:** Words like "safe", "confirmed", "verified", and "certified" imply a level of assurance that exceeds what our automated data aggregation can provide. Words like "recommend" and "should" imply professional advice. Replacing these with factual descriptions of what the data shows (not what it means for the user's decision) reduces the scope of any duty.

### 2.3 ACL s54 — Fitness for Purpose

Section 54 of the ACL provides a consumer guarantee that goods (including software, per Federal Court precedent) are reasonably fit for a purpose that the consumer makes known. Property reports used for purchase decisions trigger this guarantee.

**Application to PlotDetect:** If a user states or implies they are using our report for a property purchase, the fitness-for-purpose guarantee applies. We cannot exclude it for consumer transactions. However, we can narrow the scope of what the product purports to do — "preliminary data screening" creates a different fitness standard than "compliance assessment."

### 2.4 Information vs Advice Boundary (ASIC RG 244)

ASIC Regulatory Guide 244 distinguishes between **factual information** (no AFSL required), **general advice** (AFSL required), and **personal advice** (AFSL + know-your-client). The boundary is:
- **Factual information:** presents data outputs without recommendations. "Your property is in a flood planning area."
- **General advice:** includes a recommendation or opinion intended to influence a decision. "Your property is in a flood planning area — you should obtain flood insurance."

Words like "recommend", "should", "consider [action]" push text toward the advice side. Factual statements about what the data shows stay on the information side.

---

## 3. Methodology

### 3.1 Identification — Automated Search

A regex search was executed across all satellite product frontend files for the following word list:

```
safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|
approved|guaranteed|certified|confirmed|verified|ensure|assure|accurate|
definitive|comprehensive|complete|reliable|risk-free|no risk|low risk|
high risk|determine|proof|proves|protect
```

**Scope of search:**
- `frontend-nextjs/components/tools/` — interactive UI components (7 products)
- `frontend-nextjs/app/reports/` — report landing pages and shared report detail pages
- `frontend-nextjs/app/api/satellite/` — API route handlers (checked for user-facing error messages)
- `frontend-nextjs/lib/pdf/` — PDF report generators (the most legally sensitive output — these are saved, forwarded to solicitors, and would be the primary exhibit in any dispute)

**Files NOT in scope:** Internal code comments, variable names, TypeScript type definitions, test files, backend Python services (not user-facing). These may use terms like `is_compliant` or `confirmed_structure_count` as internal identifiers — this is not a legal risk because end users never see them.

### 3.2 Classification — Manual Review

Each match was manually reviewed in context and classified into one of:

| Category | Legal risk | Action |
|----------|-----------|--------|
| **Recommendation language** | HIGH — crosses into advice territory (ASIC RG 244) | Replace with factual description |
| **Assurance language** | HIGH — implies formal assessment we can't provide (s18) | Replace with "indicates" / "based on available data" |
| **Risk assessment language** | HIGH — "low risk" is a professional judgment (Shaddock) | Replace with factual description of what was/wasn't found |
| **Compliance determination** | HIGH — "compliant" implies formal compliance check | Replace with "meets [test name]" or "passes screening" |
| **Action-directing language** | MEDIUM — "should", "consider" push toward advice | Replace with factual statement of options or rights |
| **Regulatory fact-stating** | LOW — quoting legislation or stating regulatory requirements | No change needed (stating law is factual information) |
| **Internal/technical** | NONE — not user-facing | No change needed |

### 3.3 Replacement Principles

Every replacement followed these rules:

1. **Describe what the data shows, not what the user should do.** "Multiple independent sources indicate flood exposure" instead of "Multiple independent sources confirm flood exposure."

2. **Name the test, not the conclusion.** "Meets ADG solar access test" instead of "ADG compliant." The test is factual; the compliance determination is a legal judgment.

3. **State what was checked, not what is true.** "No indicators of unapproved works were found in the data sources checked" instead of "low risk of unapproved works." The former describes our process; the latter makes a risk assessment.

4. **Attribute to the data, not to us.** "Based on available data" grounds the statement in its source. "This roof has strong solar potential based on available data" is defensible. "This roof has excellent solar potential" is an assertion.

5. **State rights, not recommendations.** "Affected neighbours have a right to make submissions during the public notification period" states a legal fact. "Consider lodging an objection" is a recommendation.

6. **Preserve commercial value.** The changes should not make the product feel less useful. The goal is precision, not timidity. "Meets ADG solar access test" is still a clear, actionable finding — it just doesn't overstate what we've actually done.

---

## 4. Changes Made

### 4.1 Summary Statistics

- **Files changed:** 16
- **Individual text changes:** 28
- **Categories:** 6 recommendation, 8 assurance, 5 risk assessment, 4 compliance determination, 3 action-directing, 2 fitness/sufficiency
- **Code logic changed:** 0 (text-only changes)
- **TypeScript errors introduced:** 0 (verified with `npx tsc --noEmit`)

### 4.2 Change Register

Each change is recorded with: file, line (approximate — may shift after edits), original text, replacement text, category, and legal reasoning.

#### BushfireResultCard.tsx

| # | Original | Replacement | Category | Reasoning |
|---|----------|-------------|----------|-----------|
| 1 | "This doesn't mean the property is safe" | "This does not indicate absence of risk" | Assurance | "Safe" implies a safety determination. Even in negation, using the word frames safety as something we measure. |
| 2 | "Your architect or planner should factor this into the project schedule" | "Factor this into the project schedule" | Recommendation | "Should" directs action. The factual statement (RFS adds 4-6 weeks) already communicates the point. |

#### SolarYieldTool.tsx + solar-yield-report.tsx (PDF)

| # | Original | Replacement | Category | Reasoning |
|---|----------|-------------|----------|-----------|
| 3 | "an installer would consider this a premium site" | "typically considered a premium site by installers" | Assurance | Slight softening — attribution to industry norm rather than assertion. |
| 4 | "Most installers would recommend proceeding" | "still a strong candidate for solar installation" | Recommendation | Explicitly recommends action via proxy ("installers would recommend"). Highest-risk single line in all products. |
| 5 | "Consider whether the investment makes sense" | "The investment case at current panel prices may be marginal" | Recommendation | "Consider" directs the user's decision process. The replacement states a factual observation. |

#### FloodTool.tsx

| # | Original | Replacement | Category | Reasoning |
|---|----------|-------------|----------|-----------|
| 6 | "get this confirmed before settlement" | "see limitations below" | Recommendation | Directs user action. Replacement points to information without directing. |
| 7 | "no-one has certified it safe" | "flood status has not been formally assessed" | Assurance | "Certified safe" frames safety as certifiable. Replacement states the factual gap. |

#### FloodTool PDF (flood-truth-report.tsx)

| # | Original | Replacement | Category | Reasoning |
|---|----------|-------------|----------|-----------|
| 8 | "confirm flood exposure" | "indicate flood exposure" | Assurance | "Confirm" implies definitive proof. Satellite data and overlays indicate, they don't confirm. |
| 9 | "professional flood assessment recommended" | "professional flood study advisable" | Recommendation | "Recommended" is recommendation language. "Advisable" is softer and more commonly used in information contexts. |

#### ShadowTool.tsx + shadow report page + shadow PDF

| # | Original | Replacement | Category | Reasoning |
|---|----------|-------------|----------|-----------|
| 10 | "ADG compliant" | "Meets ADG solar access test" | Compliance determination | "Compliant" is a legal determination that only a consent authority or certifier can make. We ran a model — we can describe the model result. |
| 11 | "ADG concern" | "ADG solar access concern" | Compliance determination | Consistent with #10. |
| 12 | "this property meets the ADG 2-hour solar access requirement" | "this property appears to meet the ADG 2-hour solar access test... This is an indicative analysis, not a formal compliance assessment" | Compliance determination | Added explicit disclaimer that this is indicative, not formal. |
| 13 | "this is the evidence you need to object" | "this analysis may support an objection submission" | Recommendation | Original directs user to object and asserts evidentiary sufficiency. Replacement states a factual possibility. |
| 14 | Shadow report page: "Compliant" label | "Meets test" | Compliance determination | Same principle as #10. |
| 15 | PDF: "ADG compliant — no shadow overlap" | "Meets ADG solar access test — no shadow overlap" | Compliance determination | Same principle, PDF output. |

#### ThreatRadarTool.tsx

| # | Original | Replacement | Category | Reasoning |
|---|----------|-------------|----------|-----------|
| 16 | "Consider lodging an objection if any are near your property" | "Affected neighbours have a right to make submissions during the public notification period" | Recommendation | "Consider lodging an objection" is a direct recommendation. Replacement states a legal right — factual information. |
| 17 | "These developers are asking council to bend the rules" | "These applications request exceptions to height limits, setbacks, or floor space ratios" | Assurance | "Bend the rules" is editorialising. EPI variations are a standard planning mechanism. Replacement is factual. |

#### PreDAHistoryTool.tsx + pre-da-history PDF

| # | Original | Replacement | Category | Reasoning |
|---|----------|-------------|----------|-----------|
| 18 | "low risk of undisclosed or unapproved works" | "No indicators of undisclosed or unapproved works were found in the data sources checked" | Risk assessment | "Low risk" is a professional risk judgment. Replacement describes what we found (nothing) in the sources we checked — honest and bounded. |
| 19 | "Your conveyancer should verify" | "A conveyancer can verify" | Recommendation | "Should" directs action. "Can" states capability. |
| 20 | "align with approved applications" | "align with lodged applications" | Assurance | We can see lodgements, not approval status (ePlanning limitation documented in granny-flat API). "Approved" overstates what we know. |
| 21 | Summary "low risk of unapproved works or undisclosed changes" | "No indicators of unapproved works or undisclosed changes were found in the data sources checked" | Risk assessment | Same as #18, repeated in summary section. |
| 22 | PDF: "is sufficient" | "includes a s10.7 certificate, site inspection, and planner consultation" | Fitness/sufficiency | "Sufficient" is a professional adequacy judgment. Replacement lists what standard due diligence includes — factual. |
| 23 | PDF: "Review recommended" | "Further review advisable" | Recommendation | Softer phrasing that stays on the information side. |
| 24 | PDF: "Recommended next steps" | "Suggested next steps" | Recommendation | "Recommended" implies professional recommendation. "Suggested" is informational. |

#### GrannyFlatTool.tsx + granny-flat page + granny-flat PDF

| # | Original | Replacement | Category | Reasoning |
|---|----------|-------------|----------|-----------|
| 25 | "feasibility report" | "eligibility screening report" | Assurance | "Feasibility" implies a professional feasibility assessment. "Eligibility screening" accurately describes what we do — automated rule checks. |
| 26 | "confirmed eligible" | "passed the automated eligibility screening" | Assurance | "Confirmed" implies certainty. "Passed automated screening" is honest about what happened. |
| 27 | "sufficient rear yard space" | "whether adequate rear yard space appears to exist" | Fitness/sufficiency | "Sufficient" is a determination. "Appears to exist" is an observation. |
| 28 | "approved within 500m" | "applications lodged within 500m" | Assurance | We see lodgements not approvals (ePlanning API limitation). Changed to match what the data actually shows. |
| 29 | PDF: "confirm SEPP compliance" | "assess SEPP compliance" | Assurance | Certifiers assess, then confirm. We can't presume the outcome. |
| 30 | PDF: "can be confirmed" | "can proceed" | Assurance | Same principle — we describe the pathway without presuming the outcome. |
| 31 | PDF: "assess feasibility" | "assess the options" | Assurance | Avoids "feasibility" framing. |
| 32 | "more accurate buildability estimate" | "a buildability estimate that accounts for existing structures" + added "Aerial detection is indicative and may not identify all structures" | Assurance | "More accurate" is a comparative claim about our accuracy. Replacement describes what the tool does. Added limitation statement. |

#### Reports landing page (page.tsx)

| # | Original | Replacement | Category | Reasoning |
|---|----------|-------------|----------|-----------|
| 33 | "Everything your conveyancer should check — instantly" | "Planning data a conveyancer needs — instantly" | Recommendation | "Should check" directs professional action. "Needs" describes the data product. |

---

## 5. How to Assess These Changes

### 5.1 The Test: Would a Reasonable Consumer Be Misled?

For each change, apply the *Butcher v Lachlan Elder Realty* test:

> Would a reasonable member of the class to whom this is directed (property buyers, investors, conveyancers) understand this text to be:
> (a) a factual description of data and model outputs, OR
> (b) a professional assessment, recommendation, or assurance about the property?

If (b), the text creates liability under s18 if the assessment turns out to be wrong. If (a), we are providing information — which can still attract liability if negligently wrong (Shaddock), but the standard of care is lower and the exposure is narrower.

**Before this audit:** Multiple instances of (b) across all products.
**After this audit:** All user-facing text should be (a).

### 5.2 Verification Method

To verify the audit was effective:

1. **Re-run the automated grep** with the same word list. Any remaining matches should be either:
   - Internal code (variable names, comments) — not user-facing
   - Regulatory fact-stating (quoting legislation) — factual information
   - Appropriately softened (e.g., "advisable" instead of "recommended")

2. **Read each product's output end-to-end** as a consumer would. Ask:
   - Does any sentence tell me what to DO? (Should not — that's advice)
   - Does any sentence tell me what IS TRUE about my property? (Should be bounded: "based on available data", "in the sources checked")
   - Does any sentence imply a formal assessment was done? (Should not — we run automated screens, not professional assessments)

3. **Have a lawyer review** the post-audit text. This document provides the reasoning; a lawyer should confirm the classification.

### 5.3 Ongoing Maintenance

Any new user-facing text added to satellite products must be reviewed against the word list before merge. The pre-PR review checklist (CLAUDE.md) already includes a language check — this audit makes the criteria explicit.

**Grep command for future checks:**
```bash
grep -rniE '\b(safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|approved|guaranteed|certified|confirmed|verified|ensure|assure|accurate|definitive|comprehensive|reliable)\b' \
  frontend-nextjs/components/tools/ \
  frontend-nextjs/app/reports/ \
  frontend-nextjs/lib/pdf/ \
  --include='*.tsx' --include='*.ts'
```

Filter out: internal variable names, TypeScript types, code comments, regulatory quotations.

---

## 6. What This Audit Does NOT Cover

This audit addresses **language risk only** — whether our words overstate what we deliver. It does not cover:

- **Data accuracy** — whether the underlying data sources return correct results (covered by Passes 1-4 of the QA validation plan)
- **Algorithm correctness** — whether our code correctly processes the data (covered by Pass 2)
- **Disclaimer adequacy** — whether our disclaimers are legally sufficient (requires lawyer review)
- **Audit trail implementation** — whether we can prove what data was used for each report (requires engineering work — see QA plan Part E)
- **PI insurance** — whether our professional indemnity coverage is adequate for the claims we make

These are addressed by other components of the QA validation plan.

---

## 7. Legal Status of This Document

This document is an internal record of a quality assurance process. It is not legal advice. The legal reasoning cited (ACL s18, Shaddock, RG 244) represents the author's understanding of the law as applied to this product category, informed by research but not reviewed by a practicing lawyer.

**This document should be reviewed by a lawyer** before being relied upon as evidence of legal compliance. The changes made are a reasonable first step, but lawyer review may identify additional issues or suggest different formulations.

**Retention:** This document should be retained for the life of the product plus the applicable limitation period (10 years for building-related claims under the *Design and Building Practitioners Act 2020* (NSW)).
