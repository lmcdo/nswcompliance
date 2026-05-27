# Conveyancing Pipeline — Adversarial QA Analysis

**Date:** 2026-05-27
**Scope:** `services/conveyancing.py`, `scripts/generate_conveyancing_report.py`, `scripts/conveyancing_db.py`
**Purpose:** Identify every defect class that would propagate into the intelligence brief if carried forward unchecked.
**Tier:** Critical (orchestrator pipeline, live data, user-facing, multiple external APIs)

---

## 1. Null / None Trap Audit

Every `.get()` call that feeds a downstream computation, API call, or user-visible field.

### 1.1 Unguarded `.get()` → computation

| Location | Expression | What breaks | Severity |
|----------|-----------|-------------|----------|
| `conveyancing.py:125` | `if req.lat and req.lng and req.prop_id` | `lat=0.0`, `lng=0.0`, or `prop_id=""` are all falsy. Falls through to address resolution even when coords are provided. NSW coords are never 0, but the pattern is wrong. | Medium |
| `conveyancing.py:127` | `int(req.prop_id)` | If `prop_id` is `"abc"` or empty string that sneaks past the falsy check, `int()` raises `ValueError`. Unhandled — returns 500 to user. | High |
| `conveyancing.py:167` | `calc_development_headroom(controls, valuation)` | If `controls` is `{}` (prop_id was None, line 149), headroom computation gets `None` for zone/height/fsr. Depends on whether `calc_development_headroom` guards internally. | Medium |
| `generate_conveyancing_report.py:467` | `zone = (controls.get("zone") or "").split()[0].upper()` | If zone is `""`, `.split()[0]` raises `IndexError` on empty list. The `or ""` doesn't help because `"".split()` returns `[]`. | High |
| `generate_conveyancing_report.py:1442` | `total = int(body.get("TotalCount", 0) or r.headers.get("TotalCount", 0) or 0)` | If both return `None`, the `or 0` catches it. But if API returns string `"abc"`, `int("abc")` raises `ValueError`. Inside a try/except that catches `Exception`, so it silently returns `[]`. | Medium (silent) |
| `conveyancing.py:155` | `unique_overlays, covered_layers, proximity_m = f_overlays.result(timeout=50)` | If `get_unique_overlays` raises (DB down), `f_overlays.result()` re-raises the exception. No try/except here — returns 500. | High |

### 1.2 Unguarded `.get()` → user display

| Location | Expression | Risk |
|----------|-----------|------|
| `conveyancing.py:217-225` | `controls.get("zone")`, `controls.get("height")`, etc. | All correctly return `None` if missing. Frontend must handle `null`. Not a backend bug. |
| `conveyancing.py:240-243` | `valuation.get("lot_area_m2")`, etc. | Same pattern — safe. |
| `conveyancing.py:252` | `_compute_confidence(controls, unique_overlays, valuation)` | Handles missing values correctly (checks before scoring). Safe. |

### 1.3 Three-state confusion (null vs empty vs not-queried)

| Field | Null means | Empty means | Not-queried means | Distinguishable? |
|-------|-----------|-------------|-------------------|-----------------|
| `heritage_items` | N/A (always list) | No heritage | N/A | No — `[]` could be "no heritage" or "portal didn't return heritage layer" |
| `heritage_hca` | N/A (always list) | No HCA | N/A | Same problem |
| `unique_overlays` | N/A (always list) | No overlays found | DB was down | No — `[]` returned on both "clean" and "DB error" |
| `da_count` | N/A (always int) | 0 DAs nearby | ePlanning API failed | No — `0` on both success-no-results and failure |
| `dcp_available` | N/A (always bool) | LGA not onboarded | N/A | Sort of — but doesn't distinguish "onboarded but empty table" |

**Intelligence brief impact:** The `DataField` wrapper with `confidence` + `reason` solves this. But every upstream function must be refactored to return `(value, success_bool)` or raise, not silently return `[]`/`0`.

---

## 2. Unguarded Type Coercion Audit

### 2.1 `float()` / `int()` without validation

| Location | Expression | Input source | Failure mode |
|----------|-----------|-------------|-------------|
| `conveyancing.py:127` | `int(req.prop_id)` | User input (string from frontend) | `ValueError` on non-numeric string. 500 error. |
| `conveyancing.py:365-370` | `raw_h = controls.get("height")` → `re.search(r"(\d+(?:\.\d+)?)", str(raw_h))` → `float(m.group(1))` | Planning Portal API | Safe — regex match is checked before `float()`. Good pattern. |
| `generate_conveyancing_report.py:758-760` | `cx = sum(p[0] for p in ring) / len(ring)` | Planning Portal lot geometry | `ZeroDivisionError` if `ring` is empty. `ring[0]` existence is checked at line 756 (`if rings and rings[0]`) but not `len(ring) > 0`. Theoretically safe because `rings[0]` truthy implies non-empty, but fragile. |
| `generate_conveyancing_report.py:1442` | `int(body.get("TotalCount", 0) or ...)` | ePlanning DA API | Wrapped in try/except. Silent failure (returns `[]`). |
| `conveyancing_db.py:77` | Parameterised query — no coercion needed | N/A | Safe. |

### 2.2 String → numeric assumptions

| Location | Assumed type | Actual type from source | Risk |
|----------|-------------|------------------------|------|
| `parse_controls` height | Numeric string like `"9"` or `"11.5"` | Can be `"W - 8.5"`, `"J - 12"`, `"AA"` (LEP map reference) | Regex handles this — extracts numeric portion. But `"AA"` → no match → `None`. Safe. |
| `parse_controls` FSR | Numeric string like `"0.5:1"` | Can be `"N/A"`, `"deferred"` | Passed through as string. Frontend must handle non-numeric FSR. |
| `parse_controls` lot_size | Numeric string | Can be `"N/A"`, `"As specified"` | Same — string passthrough. |

---

## 3. Connection Leak Audit

### 3.1 Database connections

| Location | Opens | Closes | Leak scenario |
|----------|-------|--------|--------------|
| `get_unique_overlays` (line 1007) | `psycopg2.connect(db_url)` | `conn.close()` in finally block (line ~1090) | **Leak if exception between connect and try block** — but looking at the code, the connect IS inside the try. Safe for single exception. But if `conn.close()` itself raises, the connection leaks. |
| `conveyancing.py:337` (PDF path) | `psycopg2.connect(db_url)` | `conn.close()` in finally block | Same pattern. Safe for normal operation. |
| `_save_pipeline_cache` (line 439) | `psycopg2.connect(db_url)` | `conn.close()` in finally block | Safe. |
| `_load_pipeline_cache` (line 465) | `psycopg2.connect(db_url)` | `conn.close()` in finally block | Safe. |

**Pattern problem:** A single conveyancing request opens up to 4 separate DB connections sequentially (overlays, cache save, and potentially cache load + PDF DB). No connection pooling. Each connection has TCP handshake + TLS + auth overhead to Supabase (~50-100ms per connection). For the intelligence brief (which adds DCP controls, SEPP standards, school catchments, EPA, easements), this could be 8+ connections per request.

### 3.2 HTTP connections

| Location | Client | Timeout | Cleanup |
|----------|--------|---------|---------|
| `resolve_address` → `_portal_get` | `requests.get()` | Not visible in snippet but likely has timeout | `requests` handles cleanup. Safe. |
| `get_nearby_das` (line 1430) | `requests.get()` | `timeout=25` | In a while loop with up to 10 pages. Each request is independent. Safe. |
| `get_shadow_risk` (line 1506) | `requests.post()` | `timeout=60` | Single request. Safe. |

### 3.3 ThreadPoolExecutor lifecycle

| Location | Pool | Shutdown |
|----------|------|----------|
| `conveyancing.py:143` | `ThreadPoolExecutor(max_workers=2)` | `with` statement — auto-shutdown. Safe. |
| `conveyancing.py:152` | `ThreadPoolExecutor(max_workers=2)` | `with` statement — auto-shutdown. Safe. |

**Problem:** Two separate pools created per request. Each pool creates 2 threads. 4 threads per request. Under load (10 concurrent requests), that's 40 threads. Not catastrophic, but wasteful. The intelligence brief should use a single shared pool.

---

## 4. Async / Blocking I/O Audit

### 4.1 FastAPI sync handlers blocking the event loop

`conveyancing.py` uses `@router.post("/conveyancing")` with a **synchronous** handler (`def run_conveyancing`, not `async def`). FastAPI runs sync handlers in a threadpool, so they don't block the event loop. This is correct for a pipeline that calls blocking `requests.get()` and `psycopg2.connect()`.

**However:** The ThreadPoolExecutor inside the sync handler creates threads-within-threads. The outer FastAPI threadpool thread spawns inner ThreadPoolExecutor threads. This works but is architecturally messy. Under high concurrency, thread exhaustion is possible.

**Intelligence brief impact:** If the brief uses `async def` with `asyncio.gather()` and `httpx`/`asyncpg`, this entire pattern needs reworking. If it stays sync (recommended for v1 — matches existing code), the thread-in-thread pattern is acceptable.

### 4.2 Blocking calls inside ThreadPoolExecutor

| Call | Blocking duration | Risk |
|------|------------------|------|
| `get_raw_controls(resolved_prop_id)` | Planning Portal HTTP — 2-8s typical, 50s timeout | Acceptable |
| `get_valuation(resolved_prop_id)` | VG API HTTP — 1-3s typical | Acceptable |
| `get_unique_overlays(lat, lng, lot_wkt)` | PostGIS query — 0.5-2s typical | Acceptable |
| `detect_strata(address, lat, lng)` | Cadastre API HTTP — 1-3s typical | Acceptable |

**No async/await mismatch detected.** All blocking calls are in sync functions, run in threads. Correct pattern for this codebase.

---

## 5. Pydantic Model Gaps

### 5.1 Request models

| Model | Field | Validation | Gap |
|-------|-------|-----------|-----|
| `ConveyancingRequest.address` | `str` | No min length, no format validation | Empty string `""` passes validation, then `resolve_address("")` calls the Planning Portal with `a=""`. Portal returns `[]`, pipeline returns 422. Works, but wastes an API call. |
| `ConveyancingRequest.lat` | `Optional[float]` | No range validation | `lat=999.0` passes validation. Pipeline proceeds with nonsensical coordinates. PostGIS returns empty results. No error — just empty data. |
| `ConveyancingRequest.lng` | `Optional[float]` | No range validation | Same. |
| `ConveyancingRequest.prop_id` | `Optional[str]` | No format validation | `prop_id="DROP TABLE"` passes. Used in `int(req.prop_id)` which raises ValueError → 500. No SQL injection risk (parameterised queries downstream). |
| `ConveyancingPdfRequest.lat/lng` | `float` (required) | No range validation | Same as above. |
| `ConveyancingPdfRequest.report_id` | `str` | No format validation | Used in SQL parameterised query and R2 key. No injection risk, but `report_id="../../etc/passwd"` would create a weird R2 key. |

### 5.2 Response models

**No response model defined.** The endpoint returns a raw dict. This means:
- No output validation — if a field is accidentally omitted, no error raised
- No OpenAPI schema generation for clients
- No guarantee that the response contract documented in the docstring is enforced
- If `_compute_confidence` returns `None` instead of a string, the response includes `"confidence": null` silently

### 5.3 Recommendations for intelligence brief

```python
# Input validation
class IntelligenceBriefRequest(BaseModel):
    address: str = Field(..., min_length=5, max_length=200)
    lat: Optional[float] = Field(None, ge=-37.5, le=-28.0)  # NSW bbox
    lng: Optional[float] = Field(None, ge=140.9, le=153.7)
    prop_id: Optional[str] = Field(None, pattern=r"^\d+$")
    include_satellite: bool = False

# Output validation — enforce contract
class IntelligenceBriefResponse(BaseModel):
    address: str
    lat: float
    lng: float
    # ... all fields typed and validated
    model_config = ConfigDict(extra="forbid")  # catch accidental fields
```

---

## 6. Adversarial Break-It Scenarios

### 6.1 Boundary value attacks

| # | Scenario | Input | Expected | Actual | Severity |
|---|----------|-------|----------|--------|----------|
| 1 | Empty address | `address=""` | 422 with clear message | 422 after wasting a Portal API call (`_portal_get("address", {"a": "", ...})` returns `[]`) | Low (works, but wasteful) |
| 2 | Address with SQL metacharacters | `address="'; DROP TABLE--"` | Safe (parameterised) | Safe — `resolve_address` passes to Portal API as URL param, not SQL. Portal returns `[]`. | None |
| 3 | Address outside NSW | `address="1 Collins St, Melbourne VIC 3000"` | 422 or empty data with warning | Portal returns `[]` → pipeline returns 422. Correct but message says "Could not resolve address" — doesn't mention NSW-only. | Low |
| 4 | Unicode address | `address="42 Ünit Straße"` | Handle gracefully | `requests.get` URL-encodes it. Portal returns `[]`. Pipeline returns 422. Acceptable. | None |
| 5 | Very long address | `address="A" * 10000` | Reject early | No length limit on Pydantic model. Passes to Portal API. Portal likely returns error or truncates. | Low |
| 6 | `lat` at NSW boundary | `lat=-28.0, lng=153.7` (Tweed Heads, extreme north-east) | Resolve correctly | Works — valid NSW coordinates. No boundary validation issue. | None |
| 7 | `lat/lng` outside NSW with valid `prop_id` | `lat=0, lng=0, prop_id="12345"` | Use prop_id, ignore bad coords | `if req.lat and req.lng and req.prop_id` — `lat=0` is falsy, falls through to address resolution. If `prop_id` was meant to be used directly, it's ignored. | Medium |
| 8 | `prop_id` as negative number | `prop_id="-1"` | Reject or handle | `int("-1")` succeeds. Portal queried with propId=-1. Returns `[]` or error. Depends on Portal behaviour. | Low |
| 9 | `report_id` with path traversal | `report_id="../../etc/passwd"` | Sanitise | Used in SQL (parameterised — safe) and R2 key `f"conveyancing/{report_id}.pdf"`. R2 key becomes `conveyancing/../../etc/passwd.pdf`. Boto3 may reject or create a weird key. No actual file system traversal. | Low |

### 6.2 Empty / missing data from external sources

| # | Scenario | What breaks | Mitigation status |
|---|----------|-------------|-------------------|
| 10 | Planning Portal returns `[]` for valid address | `resolved_prop_id` is `None`. Lines 142-148: `if resolved_prop_id:` skips controls+valuation. `controls = parse_controls([])` → all fields None. Pipeline returns valid but empty response. | Partial — returns data but no error signal. Intelligence brief should return "insufficient data" error. |
| 11 | Planning Portal returns valid propId but lot geometry fails | `lat, lng` may be None if lot query fails (line 765-766: caught, returns `None, None, None`). Then `if not lat or not lng: raise HTTPException(422)`. | Handled. |
| 12 | VG API returns no valuation | `valuation` stays as default dict with all `None` values. Headroom/feasibility degrade gracefully. | Handled. |
| 13 | PostGIS spatial_overlays DB is down | `get_unique_overlays` raises exception. `f_overlays.result(timeout=50)` re-raises. **No try/except — returns 500.** | **NOT HANDLED.** The overlay fetch is not error-isolated. One DB outage kills the entire pipeline. |
| 14 | ePlanning DA API timeout | Caught in try/except inside `get_nearby_das` (line 1448). Returns `[]`. `da_count = 0`. | Handled (silently — user sees 0 DAs, doesn't know API failed). |
| 15 | Cadastre API down for strata detection | `detect_strata` has internal try/except. Falls back to address heuristic. | Handled. |
| 16 | Shadow pipeline Railway service down | `get_shadow_risk` returns `None` (line 1510). PDF path handles None (omits section). Free tier doesn't call shadow. | Handled (PDF path). Free tier never calls it. |

### 6.3 Race conditions / concurrency

| # | Scenario | Risk |
|---|----------|------|
| 17 | Two requests for same address simultaneously | Each creates its own ThreadPoolExecutor, DB connections, API calls. No shared state. No race. Cache write is idempotent (`ON CONFLICT DO UPDATE`). | None |
| 18 | Pipeline cache written then immediately read by PDF endpoint | `_save_pipeline_cache` commits synchronously. `_load_pipeline_cache` reads after commit. Supabase transaction isolation handles this. | None |
| 19 | Portal API rate limiting under concurrent requests | Multiple requests hit Planning Portal simultaneously. No request-level rate limiting. Portal could return 429. Caught by try/except but surfaced as "Could not resolve address" — misleading. | Medium |

### 6.4 Data integrity attacks

| # | Scenario | Risk |
|---|----------|------|
| 20 | Stale DCP data served as current | `dcp_available: true` but `dcp_setback_controls` rows are 2+ years old. No staleness check. User sees old setbacks without warning. | **High — intelligence brief must add staleness detection.** |
| 21 | Wrong former council for boundary suburb | `detect_former_council` resolves "Stanmore" to "marrickville" via substring match. Parts of Stanmore are in Leichhardt. Wrong DCP controls served. No error, no warning. | **High — Fix A in IMPLEMENTATION.md.** |
| 22 | `"glebe": "marrickville"` in SUBURB_TO_FORMER_COUNCIL | Glebe is in City of Sydney, not Inner West. If someone searches an Inner West LEP address containing "Glebe" (e.g. "42 Glebe Point Rd, Glebe" which might resolve to IW LEP), it maps to marrickville. | **High — data error in mapping table.** |
| 23 | Heritage merge overwrites individual items as HCA | `conveyancing.py:354`: if PostGIS finds HCA, all portal heritage items are assumed to be HCA. An individual heritage item (e.g. "Item - General") would be miscategorised. | **Medium — logic error.** |
| 24 | Zone EPI matching is bidirectional substring | `generate_conveyancing_report.py:443`: `if epi_key in epi_upper or epi_upper in epi_key`. This means "INNER WEST" matches "INNER WEST LOCAL ENVIRONMENTAL PLAN" (correct) but also means a short epi like "SYDNEY" would match "CITY OF SYDNEY LOCAL ENVIRONMENTAL PLAN" AND any other EPI containing "SYDNEY". The `break` on first match means order-dependent results. | **Medium — fragile matching.** |

---

## 7. Silent Failure Mode Catalogue

Every code path where an error produces valid-looking output instead of an error signal.

| # | Location | Failure | User sees | Should see |
|---|----------|---------|-----------|------------|
| S1 | `conveyancing.py:178-180` | ePlanning DA API fails | `da_count: 0` | `da_count: null` + `"da_fetch_failed": true` |
| S2 | `conveyancing.py:149` | `prop_id` is None (address not found in Portal but didn't raise) | `controls = parse_controls([])` → all fields null. Response looks like valid-but-empty. | Should return 422 or include `"resolution_quality": "failed"` |
| S3 | `get_unique_overlays` → `conn.close()` in except | DB error caught, returns `([], set(), {})` | Empty overlays — looks like "no environmental constraints" | Should indicate DB was unreachable |
| S4 | `detect_former_council` wrong match | Returns wrong slug silently | Wrong DCP controls (user has no way to know they're wrong) | Should cross-validate with PostGIS boundary |
| S5 | `parse_controls` zone parsing | Portal returns unexpected layer name | Zone = None, other fields possibly populated | Should flag which layers were missing vs not returned |
| S6 | Shadow HTTP call fails | Returns None → section omitted from PDF | User doesn't know shadow was attempted and failed | PDF should note "Shadow analysis unavailable — service error" |
| S7 | `_compute_confidence` returns "high" when overlays empty due to DB error | DB down → no overlays → confidence score still counts zone/height/fsr | `confidence: "high"` when half the data is actually missing | Confidence should penalise for DB errors, not just missing fields |

---

## 8. Specific Adversarial Unit Test Specifications

Tests that should exist before the intelligence brief build begins. Each targets a specific defect identified above.

### 8.1 Null trap tests

```python
# test_conveyancing_adversarial.py

def test_empty_zone_split_does_not_crash():
    """Bug: ''.split()[0] raises IndexError."""
    controls = {"zone": "", "zone_full": None}
    valuation = {"lot_area_m2": None}
    # Should not raise
    result = calc_feasibility(controls, valuation, [], is_strata=False)
    assert isinstance(result, list)

def test_prop_id_non_numeric_returns_422():
    """Bug: int('abc') raises ValueError, returns 500 instead of 422."""
    req = ConveyancingRequest(address="test", prop_id="abc", lat=-33.9, lng=151.1)
    # Should return 422, not 500
    with pytest.raises(HTTPException) as exc_info:
        run_conveyancing(req)
    assert exc_info.value.status_code == 422

def test_lat_zero_with_prop_id_uses_prop_id():
    """Bug: lat=0.0 is falsy, skips the if branch."""
    req = ConveyancingRequest(address="test", prop_id="12345", lat=0.0, lng=0.0)
    # Should use prop_id directly, not fall through to address resolution
    # (In practice NSW coords are never 0, but the pattern is wrong)

def test_overlay_db_down_does_not_return_500(monkeypatch):
    """Bug: get_unique_overlays exception propagates unhandled."""
    monkeypatch.setattr("services.conveyancing.get_unique_overlays",
                        lambda *a, **k: (_ for _ in ()).throw(ConnectionError("DB down")))
    # Should return degraded response, not 500
```

### 8.2 Boundary value tests

```python
def test_address_empty_string():
    """Should reject early, not waste Portal API call."""
    req = ConveyancingRequest(address="")
    with pytest.raises(HTTPException) as exc_info:
        run_conveyancing(req)
    assert exc_info.value.status_code == 422

def test_address_max_length():
    """Should reject absurdly long addresses."""
    req = ConveyancingRequest(address="A" * 10000)
    # Should reject at Pydantic level with max_length validator

def test_lat_lng_outside_nsw():
    """Should warn or reject non-NSW coordinates."""
    req = ConveyancingRequest(address="test", lat=-37.8, lng=144.9)  # Melbourne
    # Should include address_quality warning or reject
```

### 8.3 Silent failure detection tests

```python
def test_da_api_failure_distinguishable_from_zero_das(monkeypatch):
    """da_count=0 must be distinguishable from 'API failed'."""
    # Mock get_nearby_das to raise
    monkeypatch.setattr("services.conveyancing.get_nearby_das",
                        lambda *a, **k: (_ for _ in ()).throw(ConnectionError()))
    result = run_conveyancing(make_request("42 Smith St, Marrickville"))
    # Result should indicate failure, not just da_count=0
    # Current code: da_count=0 (WRONG — silent failure)
    # Expected: da_count=null or da_error=true

def test_confidence_penalised_when_overlays_fail(monkeypatch):
    """Confidence must not be 'high' when DB was unreachable."""
    # Mock overlay fetch to return empty due to error
    result = _compute_confidence(
        controls={"zone": "R2", "height": "9", "fsr": "0.5:1"},
        overlays=[],  # empty because DB was down, not because no overlays
        valuation={"lot_area_m2": 450}
    )
    # Current: returns "high" (5 points from zone+height+fsr+lot_area)
    # This is wrong when overlays are missing due to error, not absence
```

### 8.4 Data integrity tests

```python
def test_former_council_glebe_not_marrickville():
    """Glebe is City of Sydney, not Marrickville."""
    from generate_conveyancing_report import SUBURB_TO_FORMER_COUNCIL
    # If Glebe is in the mapping at all, it should NOT map to marrickville
    if "glebe" in SUBURB_TO_FORMER_COUNCIL:
        assert SUBURB_TO_FORMER_COUNCIL["glebe"] != "marrickville", \
            "Glebe is in City of Sydney LGA, not Inner West/Marrickville"

def test_boundary_suburbs_resolve_correctly():
    """Boundary suburbs must resolve to correct former council."""
    # These are the five addresses from IMPLEMENTATION.md Fix A verification
    boundary_cases = {
        "42 Stanmore Rd, Stanmore NSW 2048": None,  # ambiguous — needs PostGIS
        "10 Crystal St, Petersham NSW 2049": "marrickville",
        "5 Marion St, Leichhardt NSW 2040": "leichhardt",
        "88 Alt St, Ashfield NSW 2131": "ashfield",
    }
    for addr, expected in boundary_cases.items():
        result = detect_former_council(addr, "INNER WEST LOCAL ENVIRONMENTAL PLAN 2022")
        if expected is None:
            pass  # Stanmore is genuinely ambiguous without PostGIS
        else:
            assert result == expected, f"{addr} → {result}, expected {expected}"

def test_heritage_merge_does_not_overwrite_individual_items():
    """PostGIS HCA should not cause portal individual items to be misclassified."""
    controls = {
        "heritage_items": ["Item - General: Marrickville Town Hall"],
        "heritage_hca": [],
    }
    postgis_heritage = {
        "hca": ["Conservation Area - General: Marrickville South"],
        "items": [],
        "has_heritage": True,
        "raw": [],
    }
    # The current merge logic (conveyancing.py:354) would set
    # heritage_hca = heritage_items[:] — WRONG
    # Individual items are not HCAs

def test_zone_epi_matching_order_independence():
    """EPI matching should not depend on dict iteration order."""
    from generate_conveyancing_report import ZONE_EPI_TO_LGA_SLUG
    # "SYDNEY" should not match before "CITY OF SYDNEY" due to substring
    result = detect_former_council("1 George St, Sydney", "Sydney Local Environmental Plan 2012")
    # Should resolve to City of Sydney, not match on another EPI containing "SYDNEY"
```

### 8.5 Unknown / unexpected class tests

```python
def test_unknown_heritage_significance_type():
    """Portal may return new heritage significance types not in our taxonomy."""
    results = [{"Heritage Significance": "Conservation Area - Maritime", "title": "test"}]
    controls = parse_controls([{"layerName": "Heritage", "results": results}])
    # Should capture the item even if significance type is unfamiliar
    assert len(controls["heritage_items"]) > 0

def test_unknown_overlay_layer_type():
    """spatial_overlays may contain layer_types we don't recognise."""
    # get_unique_overlays queries for specific layer types only
    # Unknown types are correctly excluded by the WHERE clause
    # But if a new type is added to the DB without code update, it's invisible

def test_unknown_bushfire_category():
    """BFPL API may return categories beyond our mapping."""
    from generate_conveyancing_report import BUSHFIRE_CATEGORIES
    # Category "5" is not in our mapping
    assert "5" not in BUSHFIRE_CATEGORIES
    # Should fall back to BUSHFIRE_NOTE_DEFAULT, not crash
```

---

## 9. Remediation Priority Matrix

| # | Issue | Severity | Fix effort | Block intelligence brief? |
|---|-------|----------|-----------|--------------------------|
| R1 | `get_unique_overlays` exception not caught (S3, #13) | High | 30 min | Yes — orchestrator must isolate every data source |
| R2 | `detect_former_council` wrong suburb mapping (#21, #22) | High | 0.5 day | Yes — Fix A in IMPLEMENTATION.md |
| R3 | Heritage merge logic overwrites items as HCA (#23) | Medium | 1 hour | Yes — don't replicate this bug |
| R4 | `zone.split()[0]` IndexError on empty string (#5 in 1.1) | High | 10 min | Yes — will crash the brief |
| R5 | `int(req.prop_id)` unguarded ValueError (#2 in 1.1) | Medium | 10 min | Yes — add Pydantic validator |
| R6 | `da_count=0` indistinguishable from API failure (S1) | Medium | 30 min | Yes — brief needs three-state |
| R7 | No connection pooling (3.1) | Medium | 2 hours | Should — brief adds 4+ more DB calls |
| R8 | No Pydantic response model (5.2) | Low | 1 hour | Should — brief must have typed responses |
| R9 | Zone EPI substring matching fragility (#24) | Medium | 1 hour | Should — brief serves more LGAs |
| R10 | Shadow via HTTP instead of direct import (review finding #9) | Low | 30 min | Nice-to-have |
| R11 | DA fetch downloads entire council (review finding #8) | Low | 2 hours (add cache) | Nice-to-have for brief perf |
| R12 | `_compute_confidence` too coarse (review finding #7) | Low | N/A | Replaced by DataField in brief |
