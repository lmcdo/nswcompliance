# Configuration Reference

Living reference for all env vars, feature flags, and code configs. Update this when adding new vars.

---

## Vercel Branch Configuration

| Branch type | `NEXT_PUBLIC_DCP_ENABLED` | `NEXT_PUBLIC_ENABLED_LGAS` |
|---|---|---|
| `main` (production) | **`true`** | **29 slugs — see below** |
| PR preview (DCP testing) | `true` | subset, e.g. `marrickville,leichhardt,ashfield` |

Set these in Vercel → Project Settings → Environment Variables → scoped to the branch.

> **⚠ CORRECTED 2026-08-08. This table previously said production had DCP switched OFF
> ("`main` (production, no DCP) | not set | not set"). That was false, and it was quoted as
> a premise by at least one session brief.** The DCP surface has been live in production.
>
> **How to check this rather than trust it** — `NEXT_PUBLIC_*` vars are inlined into the
> client bundle at build time, so the deployed JavaScript is the authority, not this file
> and not memory:
> ```bash
> curl -s https://verify.plotdetect.com.au/assessment \
>   | grep -oE '/_next/static/chunks/app/assessment/page-[a-z0-9]+\.js' | head -1
> # then fetch that chunk and read the compiled gate:
> #   `if(!it)return!0`  => DCP_ENABLED folded TRUE, `it` is the ENABLED_LGAS list
> #   whole fn folded to `return!1` => DCP_ENABLED is false/unset
> ```
> Verified this way 2026-08-08: `NEXT_PUBLIC_DCP_ENABLED=true`, and `NEXT_PUBLIC_ENABLED_LGAS`
> holds **29 slugs** — exactly the 29 non-statewide `lga` values in `dcp_setback_controls`:
>
> `marrickville, leichhardt, ashfield, inner_west, waverley, woollahra, ku_ring_gai,`
> `city_of_sydney, bayside, blacktown, campbelltown, canterbury_bankstown, cumberland,`
> `georges_river, hornsby, liverpool, northern_beaches, parramatta, penrith, randwick,`
> `sutherland_shire, ryde, strathfield, the_hills, camden, canada_bay, burwood, fairfield,`
> `wingecarribee`
>
> **13 of those 29 have numeric controls but NO provision text**, so users there get
> `DcpStructuredControls` + a Register Interest form, not the DCP browser. The gate meant to
> prevent enabling a council before its data is ready — `tests/test_lga_coverage.py` — is
> marked `pytest.mark.stale` and does not run.
>
> **`/api/dcp/coverage` returns 25**, not 24 and not 28: it excludes `nsw_statewide` and any
> slug with a `parent_lga`, which silently drops Ashfield/Leichhardt/Marrickville, and their
> parent `inner_west` has 0 `is_current` rows so it is never added back.

---

## Feature Flags (`NEXT_PUBLIC_*` — baked in at build time)

| Var | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_DCP_ENABLED` | `true` (local), **`true` (prod — verified in the deployed bundle 2026-08-08)** | Shows DCP tab with `ProvisionsByTocStructure`. When unset/false → Register Interest form. Also gates DA Mode section and DCP steps in Quick Guide. |
| `NEXT_PUBLIC_ENABLED_LGAS` | unset = all; **prod holds 29 slugs** (listed above) | Comma-separated `formerCouncil` slugs. When set, DCP tab only shows provisions for listed councils; others get Register Interest. When unset, all councils show provisions. **Do not treat the list above as canonical — read it from the deployed bundle.** |
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
| `CONVEYANCING_ACCESS_CODES` | `/api/reports/conveyancing/access` — comma-separated named early-access grant codes (one per grantee, e.g. `hamada-fm-xxxxxx,internal-fm-xxxxxx`). A valid `?access=<code>` link unlocks the full conveyancing PDF without checkout. Revoke a grant by removing its code. Unset = no grants (fails closed). Comp list itself lives outside git per outreach RULE 4. |

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

| Var | Purpose |
|---|---|
| `INTERNAL_REVIEWER_EMAILS` | Comma-separated emails allowed to use `/internal/dcp-review`, `/internal/setback-review` and their `/api/dcp-review*` and `/api/internal/setback-review*` routes (`lib/internal-reviewer.ts`). **Unset = those routes return 503 and the pages redirect to /login** — fail closed. Independent of `NEXT_PUBLIC_AUTH_ENABLED`. The reviewer signs in with the magic link at `/login`. |

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

## GitHub Actions Secrets

These must be set under repo Settings → Secrets and variables → Actions:

| Secret | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | All DCP workflows | Supabase pooler connection string |
| `R2_ACCOUNT_ID` | dcp-monitor, dcp-commit, post-commit check | Cloudflare R2 account |
| `R2_BUCKET_NAME` | As above | |
| `R2_ACCESS_KEY_ID` | As above | |
| `R2_SECRET_ACCESS_KEY` | As above | |
| `TELEGRAM_BOT_TOKEN` | All DCP workflows | Alert bot |
| `TELEGRAM_CHAT_ID` | All DCP workflows | Target chat/channel |
| `VERIFY_APP_URL` | dcp-commit post-commit check | Production app URL, e.g. `https://verify.plotdetect.com.au`. Used by API smoke test. |

---


## Notes

- Cross-references: no flag needed — DB enrichment feature, UI renders what's resolved
- New LGA onboarded: add its slug to `NEXT_PUBLIC_ENABLED_LGAS` in Vercel for the preview branch, then run the LGA onboarding checklist above

### Granny flat structure detection

- `MODAL_STRUCTURES_URL` — Modal GPU endpoint for LangSAM structure detection. When unset or unreachable, the Secondary Dwelling card reports the building count as UNKNOWN (three-state, #745 D4) — never a confident zero.

> ⚠ **DO NOT SET THIS IN PRODUCTION WITHOUT READING THIS FIRST.**
> The detector behind this variable was measured on 2026-08-10 against human
> review of 56 lots in four councils: it found **14 of 38** visible secondary
> structures (recall **0.368**) and reported **15** that were not there
> (precision 0.483). The pass mark, committed before any label existed, was
> recall ≥ 0.70 and precision ≥ 0.60. It failed in every council measured
> (0.30–0.42), so it cannot be scoped to easier areas.
>
> Leaving it unset is therefore the CORRECT production state, not an outage —
> the report then says "not assessed", which is true. Setting it makes the
> product assert a structure count that is wrong about two-thirds of the time,
> on the question that gates Housing SEPP eligibility.
>
> Evidence: `data/gf_recall_001_result.json`, ground truth in the
> `structure_labels` table (`sample_id = 'gf-recall-001'`), comparison in
> `scripts/measure_structure_detection_recall.py`.
