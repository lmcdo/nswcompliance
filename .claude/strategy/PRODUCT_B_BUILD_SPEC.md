# Product B — "Was It Approved?" Build Spec

**Status:** spec (live build needs DB + API keys + outbound network — not available in this sandbox).
**Verdict basis:** VIABLE (framing-gated) — see `B2C_RESEARCH_EXTENSION_2026.md` Part 6.
**One-line:** at point of purchase, flag any structure with **no matching consent on the public
DA/CDC record**, framed strictly as a *records gap to verify with council* — never as "illegal".

## What already exists (assemble, don't rebuild)
| Piece | Module | Role in Product B |
|---|---|---|
| Geocode + DA/CDC fetch | `services/pre_da_history.py` | Pull OnlineDA/OnlineCDC records for the address |
| Lot geometry | `services/lot_dimensions.py` (`fetch_lot_geometry`) | Clip everything to the parcel |
| Imagery + change detection | `services/sentinel2.py` (`compute_change_score`), `services/nsw_imagery.py` | Detect *when* a structure appeared |
| Footprint/size | `services/spike_samgeo_buildings.py` (spike) **or** Geoscape Buildings+Height | Structure footprint m² + height |
| Exempt thresholds (DB-sourced) | `services/sepp_quantitative_extractor.py` (fixed: queries `housing_sepp_standards`) | Is the structure within exempt limits? |
| Planning controls | `services/nsw_planning_api.py` | Zone/height context |
| Orchestrator pattern | `services/conveyancing.py` | Report assembly + PDF |

## Data flow
```
address → geocode (pre_da_history) → lot geometry (lot_dimensions)
   → detect structures + first-appearance date (sentinel2 change-detection + nsw_imagery)
   → measure footprint m² + height (Geoscape Buildings+Height, paid-unlock only; or samgeo spike)
   → fetch DA/CDC records (pre_da_history) and match to structures
   → EXEMPT-DEVELOPMENT SCREEN (sepp_quantitative_extractor → DB thresholds)
   → reconcile → factual "approval-gap" findings → report (conveyancing PDF pattern)
```

## The exempt-development screen (credibility prerequisite — build FIRST)
Only surface a structure as an "approval gap" when ALL are true (else it's noise / false positive):
1. **Exceeds exempt limits** — footprint/height/setback over the Codes SEPP thresholds **sourced
   live from the DB** (`housing_sepp_standards` / `regulatory_provisions` — NEVER hardcoded), AND
2. **No matching DA/CDC record**, AND
3. **Appeared post-~2018** (ePlanning records reliable only from ~2018; older = paper records, not a
   gap). Pre-2018 structures → separate "older works — records may be paper-only" bucket, not a flag.

This screen is what converts a high-false-positive "no record found" into a defensible signal.

## Report template (the liability-bearing piece — framing IS the product)
Every finding uses factual + conduit + disclaimer framing (per *Butcher v Lachlan Elder* [2004] HCA 60):
- ✅ *"A structure (≈X m², appears c.20YY) was detected in the rear yard. We located **no matching
  development consent or CDC on the public register as at [DATE]**. Lawful explanations exist
  (exempt development, pre-2018 paper records). **Verify with council** — e.g. a Building Information
  Certificate enquiry (EP&A Act ss6.24–6.26)."*
- ❌ Never: "illegal", "unapproved", "unauthorised works", "non-compliant", or any determination of
  legality. Source + date every fact. Prominent "make your own enquiries" disclaimer; we are a
  conduit reporting records, not an authority on legality.

## Guardrails (CLAUDE.md)
- No hardcoded regulatory values — exempt thresholds via DB only (the `sepp_quantitative_extractor`
  fix already enforces this; returns None rather than a stale number).
- No internal pipeline names in any consumer-facing copy (use "Title-Check" / "approval gap").
- Free Snapshot uses free data only; **Geoscape footprint/height fires only on paid unlock** (GTM §7A).

## Scope limit (post-~2018) & honest positioning
The ePlanning OnlineDA/OnlineCDC API is reliable only from **~2018**; pre-2018 consents are paper
records at councils, not in the feed. Consequences (do not gloss over these):
- Product B can **only confidently assess structures built from ~2018 onward**. Older structures →
  "not assessed, paper records may exist — verify separately." Never flagged.
- **Low per-property hit rate.** Most structures predate 2018, so most reports find nothing
  flaggable → the GTM "scary teaser" only fires on a minority; the rest convert (if at all) as a
  **clean-check / peace-of-mind** result, like building-and-pest finding nothing.
- It is **not** an "is everything approved?" audit — only **"has anything gone up *recently*
  without a record?"** That bounded claim is also the liability shield.
- **Mitigant, not cure:** recent unpermitted works are the *highest-risk* slice (no BIC, active
  enforcement risk) and the post-2018 window roughly maps to the current owner's tenure.

**Honest positioning consequence:** with this limit, Product B is a **weak standalone $99 hero**.
Treat it as **(a) a component inside the conveyancing report, and/or (b) a bundle add-on to
Development Watch** — NOT the lead product. **Development Watch is the stronger B2C horse** because
it is *forward-looking* (monitors *new* DAs on a live feed) and so is **not** capped by the 2018
historical-data wall. Lead with Development Watch; attach Product B.

## Build phases (gated)
- **Phase 0 — exempt screen + report template.** Build the DB-sourced exempt-development screening
  calc and the factual report template. Unit-test the screen against known exempt/non-exempt cases.
  *(This is the credibility + liability core and is buildable offline against the DB.)*
- **Phase 1 — assemble pipeline.** Wire geocode → change-detection → DA/CDC match → screen → report
  for a handful of known addresses. Geoscape on free tier for testing only.
- **Phase 2 — checkout + conveyancer embed.** Stripe + the partner widget (GTM §4); switch Geoscape
  to Team plan before first paid sale (licence).
- **Gate to sell:** report renders correctly on 10 known addresses; legal review of the report
  template's liability framing.

## Sandbox note
Live pipeline needs DB (psycopg2 + creds), NSW ePlanning/imagery network access, and Geoscape/keys —
all 403/absent in this environment. Phase 0 (exempt screen + template) is the part buildable here
against the schema; the live wiring runs in the proper environment.
