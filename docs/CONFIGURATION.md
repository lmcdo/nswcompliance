# Configuration Reference

Living reference for all env vars, feature flags, and code configs. Update this when adding new vars.

---

## Vercel Branch Configuration

| Branch type | `NEXT_PUBLIC_DCP_ENABLED` | `NEXT_PUBLIC_ENABLED_LGAS` |
|---|---|---|
| `main` (production, no DCP) | not set | not set |
| PR preview (DCP testing) | `true` | `inner_west,waverley,ku_ring_gai` |
| Future: full DCP release | `true` | `inner_west,waverley,ku_ring_gai,...` |

Set these in Vercel → Project Settings → Environment Variables → scoped to the branch.

---

## Feature Flags (`NEXT_PUBLIC_*` — baked in at build time)

| Var | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_DCP_ENABLED` | `true` (local), unset (prod) | Shows DCP tab with `ProvisionsByTocStructure`. When unset/false → Register Interest form. Also gates DA Mode section and DCP steps in Quick Guide. |
| `NEXT_PUBLIC_ENABLED_LGAS` | unset = all | *(Planned)* Comma-separated `formerCouncil` slugs. When set, DCP tab only shows provisions for listed councils; others get Register Interest. When unset, all councils with data show provisions. |
| `NEXT_PUBLIC_ENABLE_PRECINCT_CONTROLS` | — | Controls precinct-level sub-tab in DCP tab |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | required | Google Maps autocomplete |
| `NEXT_PUBLIC_POSTHOG_KEY` | optional | Analytics |

---

## Database

Single Supabase instance — changes are immediately production. No staging DB.

| Var | Notes |
|---|---|
| `DATABASE_URL` | Primary connection string (pooler). Use this. |
| `PGHOST` / `PGUSER` / `PGPASSWORD` / `PGDATABASE` / `PGPORT` | Direct connection vars — used by some scripts |
| `DB_POOL_MAX` / `DB_POOL_MIN` / `DB_CONNECTION_TIMEOUT` / `DB_IDLE_TIMEOUT` | Pool tuning |
| `USE_DIRECT_DATABASE` | Bypasses pooler — use only for scripts, not app |

Backup before any schema change. See `DB_SCHEMA.md` before writing queries.

---

## Server-side API Keys (never `NEXT_PUBLIC_`)

| Var | Used by |
|---|---|
| `RESEND_API_KEY` | `/api/dcp-interest` — emails `info@plotdetect.com.au` on registration |
| `ANTHROPIC_API_KEY` | `/api/ai/chat` |
| `GOOGLE_PLACES_API_KEY` | Server-side address validation |
| `TFNSW_API_KEY` | Transport for NSW — TOD parking calculator |
| `OPENAI_API_KEY` | Legacy — check if still used before removing |
| `DEEPSEEK_API_KEY` | — |
| `GEMINI_API_KEY` | — |
| `ADMIN_API_KEY` | Internal admin routes |
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | Redis cache |

---

## Server-side Feature Flags

| Var | Purpose |
|---|---|
| `ENABLE_PRECINCT_MATCHING` | Precinct matching in assessment API |
| `ENABLE_MIGRATION_AB_TESTING` | A/B test for compliance architecture migration |
| `USE_POSTGRESQL_PROVISIONS` | Use DB for provisions (vs legacy source) |
| `USE_POSTGRESQL_TOD_RATES` | Use DB for TOD parking rates |
| `USE_POSTGRESQL_VERSIONS` | — |
| `USE_POSTGRESQL_VERSION_COMPLIANCE` | — |
| `USE_POSTGRESQL_LIVE_CHECK` | — |
| `COMPLIANCE_ARCHITECTURE` | `v2` — provision tagging version |

Most of these are migration flags from an earlier architecture. They should all be `true`/`v2` — candidates for removal once confirmed stable.

---

## Code Configs (not env vars — edit files directly)

| File | Purpose | When to update |
|---|---|---|
| `frontend-nextjs/lib/dcp-format-configs.ts` | Per-council DCP text formatting rules | Every new LGA onboard |
| `enrichment/config/__init__.py` → `COUNCIL_CONFIGS` | Extraction tagger config per council | Every new LGA onboard |
| `frontend-nextjs/lib/pdf-image-url.ts` | R2 CDN base URL for PDF images | If R2 bucket changes |
| `frontend-nextjs/lib/inner-west-mapping-v2.ts` | `determineFormerCouncilArea()` — Inner West only currently | When abstracting to multi-LGA |

---

## LGA Onboarding Checklist

For each new council added:

1. `enrichment/config/__init__.py` — add to `COUNCIL_CONFIGS`
2. `frontend-nextjs/lib/dcp-format-configs.ts` — add format config
3. Run extraction pipeline → verify with `python scripts/verify_dcp_formatting.py --council <name>`
4. Update `NEXT_PUBLIC_ENABLED_LGAS` in Vercel for relevant preview branches
5. Update `docs/DCP_EXTRACTION_KNOWN_PATTERNS.md` if new artifact types found

---

## R2 Storage

Base URL: `https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev`

| Path pattern | Contents |
|---|---|
| `pdf-pages/sepp-exempt-complying/page_N.png` | SEPP E&C 2008 — 455 pages (1–454) |
| `pdf-pages/adg/` | Apartment Design Guide |
| `pdf-pages/adg-part3/` | ADG Part 3 |
| `pdf-pages/iwlep_clause_X_Y_page_N.png` | Inner West LEP clause images |

All PDF images served via `getPdfImageUrl()` in `lib/pdf-image-url.ts` — do not hardcode R2 URLs directly.

---

## Planned / Not Yet Implemented

| Config | Purpose | Status |
|---|---|---|
| `NEXT_PUBLIC_ENABLED_LGAS` | Per-LGA DCP gating without separate branches | Planned — implement when Waverley/KRG onboarded |
| `NEXT_PUBLIC_XREF_ENABLED` | Cross-reference resolution UI | Only if behind a flag — likely just DB feature, no flag needed |
