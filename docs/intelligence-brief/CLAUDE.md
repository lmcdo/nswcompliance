# Intelligence Brief — Build Context

## Read Order (mandatory before any implementation work)

1. **`IMPLEMENTATION.md`** — THE AUTHORITY. 8 stages, verification gates, silent failure fixes, legal strategy, liability matrix. Build from this.
2. **`PRODUCT_SCOPE.md`** — What to build and why. Data stack, creative uses, bulk scenarios. Frozen reference.
3. **`QA_ANALYSIS.md`** — 9-mode adversity audit. Boundary traces, adversarial scenarios, dependency failures. Frozen reference. Section 12 (implementation phases) is SUPERSEDED by IMPLEMENTATION.md.
4. **`LLM_STRATEGY.md`** — LLM architecture decisions. Only needed for Stage 5.
5. **`LEGAL_STRATEGY.md`** — Four-layer legal defence, case law, competitor disclaimer patterns.

## Key Architecture Decisions (already made — do not revisit)

- **"Show Everything, Conclude Nothing"** — present data with citations, never synthesise into recommendations
- **Extend conveyancing.py, don't rebuild** — orchestrator reuses existing service imports
- **DataField wrapper** — every field carries `{value, confidence, source, as_at, reason}`
- **Three-state semantics** — data present / queried-no-results / not-queried
- **Synchronous response for v1** — accept 30-45s with loading state, no polling
- **Shadow is free tier** (planning-derived geometry, not satellite)
- **Strata gate on building type** — not just strata flag (strata townhouses have dev potential)
- **Pre-computed search index only** — never served as authoritative per-address data
- **LLM validation cage** — every factual claim mapped to input JSON, prohibited language scan

## Existing Code That Matters

| File | What it does | Relevance |
|------|-------------|-----------|
| `services/conveyancing.py` | Parallel fan-out orchestrator (ThreadPoolExecutor) | THE pattern to extend — lines 139-156 |
| `scripts/conveyancing_db.py` | `fetch_dcp_setbacks()`, `fetch_heritage_postgis()` | DCP + heritage queries already exist |
| `scripts/generate_conveyancing_report.py` | `detect_former_council()`, `resolve_address()` | Address resolution + LGA detection |
| `services/shadow_detector.py` | `get_shadow_risk()` — geometric shadow model | Already called in conveyancing PDF path |
| `services/flood_truth.py` | 6-source flood fusion | Satellite pipeline to wire |
| `services/bushfire_prescreen.py` | RFS BFPL live API | Free tier (designation is authoritative) |
| `services/granny_flat.py` | SAMGeo structure detection | Paid tier satellite |
| `services/climate_risk_score.py` | 6-hazard composite score | Paid tier satellite |
| `services/threat_radar.py` | ePlanning DA/CDC search | Already used for nearby DAs |
| `services/pre_da_history.py` | Tessera + spectral timeline | Premium tier satellite |

## Three Silent Failure Fixes (integrated into Stages 2-3)

These are mandatory — identified through adversity drill-down with case law analysis:

1. **Fix A (Stage 2):** PostGIS cross-check on `detect_former_council` — currently pure text matching, misclassifies boundary suburbs
2. **Fix B (Stage 3):** Zone-aware dev_type advisory — R3/R4 lots shown dwelling_house controls without awareness of higher-density permitted uses
3. **Fix C (Stage 3):** Shadow temporal disclaimer + DA-shadow compound constraint — shadow=0 today doesn't account for approved RFB next door

## Sync Protocol During Build

- **IMPLEMENTATION.md** is the living document — update stage status here as work progresses
- Other docs are frozen reference — don't modify unless product scope changes
- At each stage gate: add completion date to IMPLEMENTATION.md timing table
- New failure modes discovered → add to IMPLEMENTATION.md liability matrix
