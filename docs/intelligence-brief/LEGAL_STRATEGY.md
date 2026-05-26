# Intelligence Brief — Legal & Liability Strategy

## Case Law Position

Based on analysis of Australian proptech litigation. Full case details in IMPLEMENTATION.md.

### Defences That Work For Us

| Case | Principle | Our application |
|------|-----------|-----------------|
| **Tepko v Water Board [2001] HCA** | Provisional info + recipient has professional advisers = no duty of care | Strong for B2B (buyer's agents, planners). Weak for DIY consumers. |
| **Butcher v Lachlan Elder [2004] HCA** | Prominent disclaimer + conduit + reasonable person understands = disclaimer effective | Blueprint: disclaimers must be visible, not buried. We are clearly a data conduit. |
| **Esanda v Peat Marwick [1997] HCA** | General class publication, no specific assumption of responsibility | We publish to subscriber class. Don't warrant fitness for any transaction. |
| **Hyder v McGrath [2018]** | Even if s18 ACL proven, contributory negligence reduces damages 50-67% | Brief says "verify with council" — failure to verify = contributory negligence. |

### The Risk Scenario

| Case | Principle | Our exposure |
|------|-----------|-------------|
| **Shaddock v Parramatta [1981] HCA** | Specific info, clearly relied upon, factually wrong = duty of care | Per-address product with numeric values. If user builds to our wrong setback without a planner. |

Mitigated by: "extracted" confidence label, "verify with council" CTA, prominent disclaimers, per-field source attribution.

### Industry Precedent

- CoreLogic: 40 years, no successful data accuracy claim
- PropTrack: $100 liability cap
- BYDA (life-safety data for underground utilities): $100 liability cap
- NSW Planning Portal itself disclaims its own accuracy

## Four-Layer Defence Architecture

### Layer 1: Don't Be Wrong
- PostGIS LGA boundary validation (Fix A)
- Zone dev_type advisory (Fix B)
- Shadow temporal disclaimer + DA compound constraint (Fix C)
- User error reporting → DCP re-verification queue
- Minimum viable brief policy: >30% Layer A fields not_available → refuse to serve + refund

### Layer 2: Make Uncertainty Visually Undeniable (Butcher Standard)
- Confidence badges on every non-authoritative field (amber visual indicator)
- Gap disclosure as FIRST section of brief
- Header banner: "Site screening data as of [date]. Conditions may have changed."
- DCP source attribution inline: "Extracted [date] — verify against current DCP"
- Per-source "data as at" dates visible on every field group
- Temporal coherence warning if oldest source >6 months from newest

### Layer 3: Product Framing (Information, Not Advice)
- Product name: "Site Screening Brief" — never "Assessment", "Report", or "Certificate"
- Every output: "For preliminary screening purposes only"
- Explicit limitations list (Archistar model):
  1. Generated without physical site inspection
  2. Does not consider site-specific conditions visible only on site
  3. Does not account for future development applications on adjacent lots
  4. Data sourced from NSW government and council sources — accuracy not independently verified
  5. Not a substitute for professional planning, legal, or building advice
- CTA: "Engage a qualified town planner for site-specific assessment"
- Compound constraint language: "Potential interaction identified" (not "conflict detected")

### Layer 4: Terms of Service (Last Resort)
- Liability cap: 6 months subscription fees or $500, whichever greater
- Consequential loss exclusion (universal industry practice)
- "As is, as available" baseline
- Pass-through NSW DPHI disclaimer verbatim
- Statutory rights preservation (ACL s64A)
- "Reasonable endeavours" for error correction (not "best efforts")
- Scope: standard residential properties only
- Solicitor review before public launch (non-negotiable)

## Competitor Disclaimer Patterns

| Company | Key approach | Liability cap |
|---------|-------------|---------------|
| **CoreLogic** | "As is", DB "not complete and accurate record", "reasonable endeavours" | $10K or annual fee |
| **Archistar** | 4-point explicit limitations (no site inspection, no market analysis, no human review, no observable features) | $100 free / 6mo fees paid |
| **PropTrack** | "Not professional advice", minimal | $100 |
| **Landchecker** | Pass-through state government disclaimers verbatim | Standard exclusion |
| **Microburbs** | Explicit property type scope limitation | Standard exclusion |

## Cases Where Disclaimers Failed

| Case | Why it failed | Lesson for us |
|------|---------------|---------------|
| **Makings v CBRE [2017] QSC** | Disclaimer on page 38 of 39 + agent verbally endorsed accuracy. $1.6M damages. | Disclaimers MUST be prominent. Never endorse accuracy verbally or in marketing. |
| **Shaddock v Parramatta [1981]** | Council gave wrong info as if authoritative. No disclaimer. | Don't frame screening data as authoritative. Always include confidence level. |

## Residual Risk After All 4 Layers

**Realistic worst case:** DIY homeowner, no planner, builds to wrong DCP setback (our extraction typo). Liability capped at 6 months fees (~$300-900). Consequential loss (demolition) excluded. Contributory negligence reduces 50-67%. No Australian proptech has ever lost this case.

**Nuclear scenario (near-zero probability):** ACCC enforcement for systematic misleading conduct. Mitigated by transparent confidence levels, gap disclosure, prominent disclaimers. ACCC has never pursued a proptech for data accuracy.
