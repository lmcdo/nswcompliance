# Satellite Services QA — Task List

Objective: For each service, apply the same treatment as solar_yield.py received:
1. Full read + bug hunt
2. Fix all bugs (code + comments)
3. Pydantic models for external API responses where applicable
4. Adversarial unit test suite (pure-logic functions, no network/DB)

Reference: `tests/test_solar_yield.py` (31 tests) is the benchmark for what "done" looks like.

## Methodology (per service)
- Grep every `.get(key, default)` — null-value trap if key can exist with null
- Grep every `or 0 / or [] / or {}` — check zero-is-valid edge cases
- Grep every `float() / int()` — can the argument be None?
- Check every external API assumption (what if field is absent / null / empty string?)
- Check every `with _get_conn() as conn:` — psycopg2 `with conn:` does NOT close the connection
- Check `async def` endpoints that do blocking I/O (requests, psycopg2)
- Check signal/classification logic for edge cases (empty string, unknown class, boundary values)
- Write tests for all pure-logic functions before fixing (tests catch regressions)

---

## Status

### 1. flood_truth.py — NEXT
**Priority: Highest** — most consequential output (flood signal is safety-adjacent), zero tests, most pure-logic functions testable without mocks.

Known bugs from initial read:
- [ ] `_compute_confidence` line 452: `.get("wet_seasons_checked", 0)` null trap → TypeError when key exists with null
- [ ] `_compute_flood_signal` line 418: `epi_flood_class=""` not in `(None, "none")` → false in-overlay
- [ ] `_query_epi_overlay` line 177: unknown/empty `raw_class` defaults to `"flood_planning_area"` → false positive
- [ ] `run_flood` line 591: `with _get_conn() as conn:` — psycopg2 connection leak
- [ ] `_query_copernicus_ems` line 197: same connection leak

Pure-logic functions to test (no mocks needed):
- `_compute_flood_signal` — 5 output states, complex boolean combination
- `_compute_confidence` — 3 tiers, 4 input dimensions
- `_normalise_outputs` — legacy format migration + signal computation
- `_build_s1_gap_warning` — two output variants
- `_build_data_sources` — conditional source list
- `_s1b_gap_affected` — date range overlap
- `_jrc_tile_url` — coordinate → URL, pure math
- `_haversine_km` — math, verifiable against known distances

Deliverables:
- [ ] `tests/test_flood_truth.py` (target: ~35 tests)
- [ ] Bug fixes committed

---

### 2. shadow_detector.py — AFTER FLOOD
**Priority: High** — `_adg_compliant` is a compliance gate (wrong result = false assurance), zero tests.

Scan targets:
- `_arcgis_to_geojson` — coordinate transform, edge cases: empty rings, single-point ring, wrong wkid
- `_adg_compliant` — compliance gate: what if scenarios list is empty? what if jun21_12pm absent?
- `_worst_case` — what if all shadow_length_m are 0?
- `_build_scenario_list` — what if shadow_map has unexpected keys? what if SHADOW_SCENARIOS is empty?
- `_get_height_limit` — `.get()` null traps on DB row values
- `run_shadow` endpoint — async? blocking I/O pattern?

Deliverables:
- [ ] `tests/test_shadow_detector.py` (target: ~20 tests)
- [ ] Bug fixes committed

---

### 3. threat_radar.py — AFTER SHADOW
**Priority: Medium** — simplest service, but `_filter_nearby` + `_normalise_council` have correctness implications.

Scan targets:
- `_haversine` — test against known distances
- `_normalise_council` — exhaustiveness: what councils are missing from the map? Does it handle trailing spaces, mixed case, abbreviations?
- `_filter_nearby` — what if app has no Location or Latitude/Longitude fields? what if alat/alng are strings "0"?
- `_fetch_das` — what if `Application` key is null (not absent) in response?
- `subscribe` — what if email validation logic has gaps?
- `check` — what if `seen_application_numbers` is null in inputs JSONB?

Deliverables:
- [ ] `tests/test_threat_radar.py` (target: ~20 tests)
- [ ] Bug fixes committed

---

### 4. granny_flat.py — LAST
**Priority: Medium-Low** — 13 geometry tests already cover the core helpers.

Remaining untested areas:
- `_compute_confidence` — SEPP eligibility + detection quality scoring
- `_get_weekly_rent` — postcode lookup + fallback chain
- `confirm_and_calculate` — SEPP area checks, yield computation, rental estimate
- `detect_structures` endpoint — depends on SAM + real imagery (not unit-testable; integration test only)

Deliverables:
- [ ] `tests/test_granny_flat_logic.py` — pure-logic functions only (target: ~15 tests)
- [ ] Bug fixes committed

---

## Completion Criteria
Each service is "done" when:
1. All identified bugs fixed and committed
2. Test suite passes in pre-push hook (runs automatically on `git push`)
3. No `.get(key, default)` null traps remain for keys that can be null
4. No unguarded `float(x)` / `int(x)` where x could be None
5. No `with _get_conn() as conn:` connection leaks
6. No `async def` endpoints with blocking I/O
