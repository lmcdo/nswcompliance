# LLM Intelligence Layer — Strategic Analysis

**Date:** 2026-05-18
**Status:** Research complete
**Depends on:** ce-ml-inference-augmentation.md (82 existing opportunities), ce-value-exploitation-audit.md (35 FT opportunities), pipeline-ideas-log.md (30+ satellite ideas), reference-llm-finetuning-market-research-2026-05.md (competitor analysis)

---

## The Core Insight

PlotDetect has 47K structured provisions, 14 spatial overlay types, 5-hazard climate risk scores, 7 satellite product pipelines, 28 councils with structured DCP controls, and a deterministic compliance engine. None of it uses LLM for user interaction.

**The competitive moat is NOT "AI" — it's "structured data + AI."** PropCode has PropChat (RAG over document text). It has 6 known failure modes: numeric precision, cross-reference chains, table parsing, staleness, citation granularity, conflicting provisions. All 6 are architecturally eliminated when the LLM synthesizes from pre-computed structured data instead of extracting from raw text.

**Architecture:** Structured Data + Tool Use + LLM Synthesis
1. User asks natural language question
2. LLM decomposes into structured API calls (Claude tool use)
3. Existing deterministic endpoints return structured data
4. LLM synthesizes human-readable answer with provision ID citations
5. Every factual claim maps to a data source — no hallucination surface

This is the Thomson Reuters/CoCounsel model (ground AI in proprietary verified data) applied to Australian planning compliance. Spellbook ($100M ARR legal AI) abandoned fine-tuning because it "encourages hallucinations." We should never fine-tune on regulatory text — fine-tune for format/behavior only.

---

## Competitive Landscape (AU Proptech, May 2026)

| Competitor | AI Status | Gap vs PlotDetect |
|---|---|---|
| PropCode | PropChat (RAG over PDFs) | Unstructured text, 6 failure modes, no spatial data |
| Archistar | Generative design AI (3D massing) | No regulatory depth, no satellite intelligence |
| CoreLogic/Cotality | Exploring, no production LLM | No planning data, no compliance |
| XDI/Climate Valuation | Engineering-based, no LLM | No planning/regulatory context |
| REA/Domain | No visible LLM features | No compliance, no satellite |
| CivCheck (US) | AI plan review for municipalities | US only, $4.6M/5yr gov contract |
| ReZone AI (US) | Fine-tuned on 65 US city zoning codes | US only, no AU presence |

**No Australian company has an LLM interface over structured planning compliance data.** The field is wide open.

---

## 10 Intelligence Layer Ideas (Ranked by Revenue/Effort)

### Tier 1 — Build Now (Weeks, Proven Distribution)

**1. Conveyancing Intelligence Layer** — $240K ARR potential
LLM-generated "Material Risk Summary" at top of existing conveyancing PDF. Plain English: "3 items need attention: (1) flood planning area affects renovation, (2) approved 4-storey DA 150m away will shadow rear garden 40%, (3) heritage conservation area requires consent for external mods." Data already exists. InfoTrack distribution channel exists. 2-3 weeks. Per-report add-on: $15-25.

**2. Narrative Report Generator** — $90-150K ARR
Machine-generated narrative summaries for any report type: 10.7 commentary, development feasibility summary, climate risk disclosure, pre-DA assessment. Template-controlled, every sentence cites a provision ID. 1-2 weeks per report type. Per-report pricing.

**3. Property Intelligence Copilot ("Ask This Property")** — conversion driver
Natural language over all property data: "Can I build a granny flat here?" → synthesizes zone, lot area, SEPP Housing, setbacks, overlays into one answer with citations. The free tier hook — truncated answers convert to paid. 2-3 weeks for v1.

**4. Regulatory Interpretation Assistant** — conversion feature
"Explain this" button on every provision. Translates legalese to plain English applied to the specific lot dimensions. "6m rear setback on your 450m2 lot with 15m width leaves ~9m depth for building footprint." Safe: translation not interpretation. 1-2 weeks.

### Tier 2 — Build Next (Months, Higher Value)

**5. Climate Risk Disclosure for APRA/AASB S2** — $250K-1.5M ARR institutional
Batch API: portfolio of addresses → structured risk narratives aligned to AASB S2 framework. Unique: connects physical hazard to planning controls (no competitor does this). Needs Finity validation letter first. 6-8 weeks + legal. $50-150K/yr per institutional client.

**6. RAG-Enhanced Provision Explorer** — Pro tier differentiator
Cross-council regulatory comparison: "Compare rear setbacks for R3 across Inner West, Canterbury-Bankstown, Randwick." Structured data for 28 councils, RAG fallback for rest. Transparently labels confidence levels. 3-4 weeks.

**7. Cross-Product Intelligence Synthesizer** — platform premium
Connects all 7 satellite products + compliance + climate risk + envelope 3D for compound queries: "How does the flood risk affect the development potential of this R3 site?" Only possible because we have all data layers. 4-6 weeks.

**8. SEE/EIS Draft Generator** — $240-480K ARR
Template-based SEE generation with pre-populated compliance analysis. NSW gov tendered for this — validated demand. Planning consultants save 4-8 hours per SEE. $99-199/report. 6-8 weeks for v1 covering R3/R4 in Inner West.

### Tier 3 — Future (Quarters, Strategic)

**9. Developer Site Scoring & Comparison** — $299K ARR
Multi-site ranked comparison with constraint-adjusted yield calculations. 4-6 weeks. $249-499/mo subscription.

**10. Council Planning Chatbot (B2G)** — $250K-1M ARR
Repackage the Property Copilot for council customer service. $50-200K/yr per council. 3+ month procurement cycle. Year 2 play.

---

## What's New vs Already Documented

**Already documented (82+ opportunities):** FT-1 to FT-9 fine-tuning use cases, INF-1 to INF-13 inference use cases, FT-1 to FT-35 value exploitation opportunities, 30+ satellite pipeline ideas, 30 Tessera embedding ideas.

**New in this analysis:**
1. **Competitive landscape grounding** — PropCode's PropChat is closest competitor; specific failure modes documented
2. **Architecture decision crystallized** — structured data + tool use + LLM synthesis (not RAG, not fine-tuning on regulations)
3. **Conveyancing Intelligence Layer** as highest near-term ROI (InfoTrack channel + existing pipeline)
4. **"Ask This Property" copilot** as the free-tier conversion mechanism
5. **AASB S2 climate narrative** as the institutional revenue play — connecting planning controls to climate risk is unique globally
6. **Safe boundary framework** for regulatory interpretation — specific safe/unsafe taxonomy
7. **SEE/EIS generator** validated by NSW gov tender
8. **Council chatbot B2G** revenue model — CivCheck's $4.6M contract as pricing precedent

---

## Critical Implementation Principles

1. **Never fine-tune on regulatory text** — changes too fast, encourages hallucinations
2. **LLM is presentation layer, not interpretation engine** — synthesizes from deterministic outputs
3. **Every claim must cite a provision ID or data source** — zero hallucination surface
4. **Prohibited outputs:** predictions, recommendations, likelihood assessments, "should" statements
5. **Disclaimers on every output:** "Factual summary of planning controls. Consult a planning professional for advice."
6. **Confidence labeling:** clearly distinguish structured data answers (high) from RAG fallback (lower)
7. **Audit trail:** log every query, every data source consulted, every output generated

---

## Recommended Sequence

| Week | Build | Revenue Signal |
|---|---|---|
| 1-3 | Conveyancing Intelligence Layer | $15-25/report via InfoTrack |
| 2-4 | "Explain This" provision button | Conversion feature (free→paid) |
| 4-6 | Property Intelligence Copilot v1 | Verify Pro tier justification |
| 6-8 | Narrative report generator (conveyancing + climate) | $29-99/report |
| 8-12 | Climate Risk Disclosure batch API | $50K+/yr institutional |
| 12-16 | SEE Draft Generator v1 | $99-199/report |
| 16+ | Cross-product synthesizer, developer scoring | Platform premium |

---

## Revenue Projection (Conservative, Year 1)

| Product | Price | Volume/mo | ARR |
|---|---|---|---|
| Conveyancing intelligence add-on | $20/report | 500 | $120K |
| Narrative reports | $49/report | 200 | $118K |
| Verify Pro (copilot) | $149/mo | 100 users | $179K |
| Climate risk institutional | $75K/yr | 2 clients | $150K |
| **Total** | | | **$567K** |

Probability-weighted at 40% adoption: ~$227K ARR realistic Year 1.
