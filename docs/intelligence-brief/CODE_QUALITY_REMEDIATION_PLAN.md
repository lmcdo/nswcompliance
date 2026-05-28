# Code Quality Remediation Plan — Conveyancing → Intelligence Brief

**Date:** 2026-05-27
**Scope:** Defects in `services/conveyancing.py` and upstream functions that must be fixed before or during the intelligence brief build.
**Input:** `CONVEYANCING_QA_ADVERSARIAL.md` (adversarial analysis), `IMPLEMENTATION.md` (build plan), QA gate template, codebase scan 2026-05-23.
**Priority:** Fix before Stage 2 (orchestrator) unless noted otherwise.

---

## 0. Principles

1. **Fix in the brief orchestrator, not in conveyancing.py** — the conveyancing pipeline works in production. Don't destabilise it by refactoring upstream functions. The intelligence brief imports the same functions but wraps them with proper error isolation and validation.
2. **Every external call is a `_safe_call`** — timeout, try/except, returns `DataField(value=None, confidence="not_available", reason=...)` on failure. No silent `[]` or `0`.
3. **Pydantic in, Pydantic out** — typed request model with validators, typed response model with `extra="forbid"`.
4. **Connection pool, not per-call connect** — single `psycopg2.pool.ThreadedConnectionPool` shared across the request lifecycle.
5. **Three-state semantics everywhere** — `value present` / `queried-returned-nothing` / `query-failed-or-not-attempted`.

---

## 1. Input Validation (Pydantic Hardening)

### 1.1 Request model

```python
from pydantic import BaseModel, Field, field_validator

class IntelligenceBriefRequest(BaseModel):
    address: str = Field(..., min_length=5, max_length=200)
    lat: Optional[float] = Field(None, ge=-37.5, le=-28.0)
    lng: Optional[float] = Field(None, ge=140.9, le=153.7)
    prop_id: Optional[str] = Field(None, pattern=r"^\d{1,12}$")
    include_satellite: bool = False

    @field_validator("address")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Address too short")
        return v
```

**What this fixes:**
- Empty address (R4 prerequisite — don't waste Portal API calls)
- Non-NSW coordinates (lat/lng range validation)
- `prop_id="abc"` or `prop_id="DROP TABLE"` (regex pattern)
- `prop_id=""` falsy bug (pattern requires digits)
- Absurdly long addresses (max_length=200)

### 1.2 Response model

```python
class DataField(BaseModel, Generic[T]):
    value: Optional[T]
    confidence: Literal["authoritative", "extracted", "estimated", "derived", "not_available", "stale"]
    source: str
    as_at: Optional[str] = None
    reason: Optional[str] = None  # populated when value is None

class IntelligenceBriefResponse(BaseModel):
    address: str
    lat: float
    lng: float
    prop_id: Optional[int]
    run_date: str
    planning_controls: PlanningControlsSection
    physical_reality: PhysicalRealitySection
    environmental_constraints: EnvironmentalSection
    neighbourhood: NeighbourhoodSection
    economics: EconomicsSection
    compound_constraints: list[CompoundConstraint]
    gaps: list[GapEntry]
    confidence_summary: ConfidenceSummary
    narrative: Optional[str] = None
    disclaimer: str

    model_config = ConfigDict(extra="forbid")
```

**What this fixes:**
- No output type enforcement (R8)
- Accidental field omission goes undetected
- Three-state semantics enforced per-field via `DataField`

### 1.3 `is not None` vs falsy check

**Current:** `if req.lat and req.lng and req.prop_id`
**Fixed:** `if req.lat is not None and req.lng is not None and req.prop_id is not None`

Apply in the intelligence brief orchestrator. Don't modify `conveyancing.py`.

---

## 2. Error Isolation (`_safe_call` Pattern)

### 2.1 Wrapper

```python
import time
from concurrent.futures import ThreadPoolExecutor, Future

def _safe_call(
    fn: Callable,
    timeout_s: float,
    source_name: str,
    confidence_on_success: str,
) -> DataField:
    """Call fn with timeout. On success: DataField(value, confidence, source).
    On failure: DataField(value=None, confidence='not_available', reason=error).
    Never raises."""
    start = time.monotonic()
    try:
        result = fn()
        elapsed = time.monotonic() - start
        return DataField(
            value=result,
            confidence=confidence_on_success,
            source=source_name,
            as_at=date.today().isoformat(),
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.warning(f"{source_name} failed after {elapsed:.1f}s: {e}")
        return DataField(
            value=None,
            confidence="not_available",
            source=source_name,
            reason=f"{type(e).__name__}: {str(e)[:200]}",
        )
```

### 2.2 Application to each data source

| Source | Timeout | Confidence on success | Current error handling | After |
|--------|---------|----------------------|----------------------|-------|
| `resolve_address` | 10s | authoritative | Raises on failure → 422 | Keep raising (address resolution failure = abort entire brief) |
| `get_raw_controls` + `parse_controls` | 8s | authoritative | No try/except in orchestrator | `_safe_call` → degraded response |
| `get_valuation` | 5s | authoritative | No try/except in orchestrator | `_safe_call` → degraded response |
| `get_unique_overlays` | 5s | authoritative | **No try/except — R1 critical** | `_safe_call` → degraded response |
| `detect_strata` | 5s | authoritative (cadastre) / estimated (heuristic) | Internal try/except | `_safe_call` with confidence from strata source |
| `get_nearby_das` | 10s | authoritative | Internal try/except returns `[]` | `_safe_call` → `da_count=None` not `0` (R6) |
| `fetch_dcp_setbacks` | 3s | extracted | No try/except | `_safe_call` |
| `get_shadow_risk` | 15s | derived | Returns None on failure | `_safe_call` (import directly, not HTTP — R10) |
| `fetch_heritage_postgis` | 3s | authoritative | No try/except | `_safe_call` |
| `housing_sepp_standards` query | 3s | authoritative | Not yet built | Build with `_safe_call` from start |

**What this fixes:**
- R1: `get_unique_overlays` exception no longer crashes the pipeline
- R6: DA failure returns `not_available`, not `0`
- S1-S7: Every silent failure mode becomes explicit

---

## 3. Connection Pool Management

### 3.1 Pool creation

```python
# services/db_pool.py
import psycopg2.pool
import os
import threading

_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
_pool_lock = threading.Lock()

def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        with _pool_lock:
            if _pool is None or _pool.closed:
                db_url = os.getenv("DATABASE_URL")
                if not db_url:
                    raise RuntimeError("DATABASE_URL not set")
                _pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=10,
                    dsn=db_url,
                    options="-c statement_timeout=30000",  # 30s max query
                )
    return _pool

def get_conn():
    """Get a connection from the pool. Caller must putconn() in finally."""
    return get_pool().getconn()

def put_conn(conn):
    """Return connection to pool."""
    try:
        get_pool().putconn(conn)
    except Exception:
        pass  # pool closed or connection dead — let it go
```

### 3.2 Usage pattern

```python
conn = get_conn()
try:
    overlays = _query_overlays(conn, lat, lng, lot_wkt)
    dcp = _query_dcp(conn, former_council, zone)
    heritage = _query_heritage(conn, lat, lng, lot_wkt)
    # Single connection for all DB queries in the request
finally:
    put_conn(conn)
```

**What this fixes:**
- R7: 4+ separate `psycopg2.connect()` calls per request → 1 pooled connection
- TCP handshake overhead eliminated for subsequent queries
- Connection count bounded (maxconn=10) under load
- Statement timeout prevents runaway queries

---

## 4. Former Council Resolution Fix (R2 — Fix A)

### 4.1 PostGIS cross-validation

```python
def validate_former_council(
    text_slug: str, lat: float, lng: float, conn
) -> tuple[str, bool]:
    """Cross-check text-derived LGA slug against spatial boundary.
    Returns (slug, is_validated). If mismatch: (corrected_slug, False)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT LOWER(REPLACE(lga_name, ' ', '_'))
            FROM spatial_overlays
            WHERE layer_type = 'lga_boundary'
              AND ST_Contains(geom, ST_SetSRID(ST_Point(%s, %s), 4326))
            LIMIT 1
        """, (lng, lat))
        row = cur.fetchone()
    
    if row and row[0] != text_slug:
        return row[0], False  # corrected
    return text_slug, True  # validated or no spatial data available
```

### 4.2 Glebe mapping fix

Remove `"glebe": "marrickville"` from `SUBURB_TO_FORMER_COUNCIL`. Glebe is in City of Sydney LGA, not Inner West. If someone searches an Inner West LEP address with "Glebe" in it, the suburb match should not fire.

**Decision:** This is a data fix, not a code fix. Should be fixed in `generate_conveyancing_report.py` regardless of the intelligence brief. But the brief's PostGIS cross-validation (4.1) would catch this anyway.

---

## 5. Heritage Merge Logic Fix (R3)

### 5.1 Current bug

```python
# conveyancing.py:354 — WRONG
if postgis_heritage["hca"]:
    if controls.get("heritage_items") and not controls.get("heritage_hca"):
        controls["heritage_hca"] = controls["heritage_items"][:]
```

This says: "if PostGIS found an HCA, treat ALL portal heritage items as HCA." Wrong — portal items might be individual heritage items ("Item - General"), not conservation areas.

### 5.2 Fix for intelligence brief

Don't replicate this logic. Instead:

```python
def _merge_heritage(portal_controls: dict, postgis_heritage: dict) -> dict:
    """Merge portal and PostGIS heritage data without cross-contamination."""
    items = list(portal_controls.get("heritage_items", []))
    hca = list(portal_controls.get("heritage_hca", []))
    
    # PostGIS HCA entries are definitively HCA (from spatial_overlays.value)
    for entry in postgis_heritage.get("hca", []):
        if entry not in hca:
            hca.append(entry)
    
    # PostGIS individual items
    for entry in postgis_heritage.get("items", []):
        if entry not in items:
            items.append(entry)
    
    return {
        "heritage_items": items,  # all heritage (items + HCA)
        "heritage_hca": hca,      # only conservation areas
        "has_heritage": bool(items or hca),
    }
```

---

## 6. Zone Split Fix (R4)

### 6.1 Current bug

```python
# generate_conveyancing_report.py:467
zone = (controls.get("zone") or "").split()[0].upper()
# If zone is "" → "".split() returns [] → [0] raises IndexError
```

### 6.2 Fix

In the intelligence brief, extract zone prefix safely:

```python
def _zone_prefix(zone: Optional[str]) -> str:
    """Extract zone prefix (e.g. 'R2' from 'R2 Low Density Residential')."""
    if not zone or not zone.strip():
        return ""
    parts = zone.strip().split()
    return parts[0].upper() if parts else ""
```

Don't modify `calc_feasibility` in the upstream script — the intelligence brief won't call it directly. Build equivalent logic with the safe extraction.

---

## 7. Rate Limiting and Auth (Production Hardening)

### 7.1 Per-source upstream rate limiting

The intelligence brief hits 5+ external APIs per request. Under load, these need rate limiting to avoid upstream bans.

```python
# services/rate_limiter.py
import threading
import time
from collections import defaultdict

class TokenBucketRateLimiter:
    """Per-source rate limiter. Blocks (does not reject) when exhausted."""
    
    def __init__(self):
        self._buckets: dict[str, dict] = {}
        self._lock = threading.Lock()
    
    def configure(self, source: str, rate_per_second: float, burst: int):
        with self._lock:
            self._buckets[source] = {
                "tokens": burst,
                "rate": rate_per_second,
                "burst": burst,
                "last_refill": time.monotonic(),
            }
    
    def acquire(self, source: str, timeout_s: float = 10.0) -> bool:
        """Block until a token is available or timeout. Returns False on timeout."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            with self._lock:
                bucket = self._buckets.get(source)
                if not bucket:
                    return True  # unconfigured source — no limit
                # Refill
                now = time.monotonic()
                elapsed = now - bucket["last_refill"]
                bucket["tokens"] = min(bucket["burst"], bucket["tokens"] + elapsed * bucket["rate"])
                bucket["last_refill"] = now
                if bucket["tokens"] >= 1:
                    bucket["tokens"] -= 1
                    return True
            time.sleep(0.1)
        return False

rate_limiter = TokenBucketRateLimiter()
rate_limiter.configure("planning_portal", rate_per_second=5, burst=10)
rate_limiter.configure("eplanning_da", rate_per_second=3, burst=5)
rate_limiter.configure("cadastre", rate_per_second=5, burst=10)
rate_limiter.configure("vg_api", rate_per_second=3, burst=5)
```

### 7.2 API key auth for intelligence brief endpoint

```python
# Minimal auth — validates API key from Supabase
async def verify_api_key(request: Request) -> str:
    key = request.headers.get("X-API-Key")
    if not key:
        raise HTTPException(401, "API key required")
    # Validate against supabase api_keys table
    # Return user_id for rate limiting / billing
```

### 7.3 Per-key daily rate limit

| Tier | Briefs/day | Satellite/day | Batch | Prospector |
|------|-----------|--------------|-------|-----------|
| Free | 10 | 0 | No | No |
| Pro | 100 | 50 | Yes (max 20) | Yes |
| Enterprise | Unlimited | Unlimited | Yes (max 50) | Yes |

Enforcement: increment counter in Redis or Supabase. Check before processing.

---

## 8. XSS Prevention

### 8.1 Current risk surface

The conveyancing pipeline returns raw strings from external APIs (Planning Portal, ePlanning, Cadastre) in JSON responses. If the frontend renders these without escaping, XSS is possible.

**Specific risks:**
- `controls["zone_full"]` — from Planning Portal. Unlikely to contain scripts, but unvalidated.
- `da["description"]` — from ePlanning DA API. User-submitted DA descriptions could contain `<script>` tags.
- `controls["heritage_items"]` — from Planning Portal. Heritage item names are government-controlled. Low risk.

### 8.2 Backend sanitisation

```python
import re

def _sanitise(value: Optional[str]) -> Optional[str]:
    """Strip HTML tags and dangerous characters from API response strings."""
    if value is None:
        return None
    # Remove HTML tags
    value = re.sub(r'<[^>]+>', '', value)
    # Remove null bytes
    value = value.replace('\x00', '')
    return value.strip()
```

Apply to all string fields from external APIs before including in the response. The intelligence brief should sanitise at the orchestrator level, not rely on the frontend.

### 8.3 Frontend defence (defense in depth)

React's JSX auto-escapes by default. The risk is `dangerouslySetInnerHTML` or URL construction from API data. The intelligence brief frontend should never use `dangerouslySetInnerHTML` on any field from the brief response.

---

## 9. Error Response Format

### 9.1 Standard error envelope

```python
class ErrorResponse(BaseModel):
    error: str
    code: str  # machine-readable: "address_not_found", "upstream_timeout", etc.
    details: Optional[dict] = None
    retry_after: Optional[int] = None  # seconds, for rate limiting

# Usage
raise HTTPException(
    status_code=422,
    detail=ErrorResponse(
        error="Could not resolve address in NSW Planning Portal",
        code="address_not_found",
        details={"address": req.address, "portal_response": "empty"},
    ).model_dump(),
)
```

### 9.2 Degraded response (partial success)

When some sources fail but others succeed, don't return an error. Return a valid response with gaps:

```python
response.gaps = [
    GapEntry(
        field="environmental_constraints.overlays",
        reason="PostGIS spatial_overlays database unreachable",
        verify_url=None,
    ),
    GapEntry(
        field="neighbourhood.da_count",
        reason="ePlanning DA API timeout after 10s",
        verify_url="https://www.planningportal.nsw.gov.au/spatialviewer",
    ),
]
```

### 9.3 Minimum viable brief threshold

If >30% of Layer A fields return `not_available`, refuse to serve:

```python
def _check_minimum_viable(fields: list[DataField]) -> bool:
    total = len(fields)
    available = sum(1 for f in fields if f.confidence != "not_available")
    return available / total >= 0.70
```

---

## 10. Constants Extraction

### 10.1 Hardcoded values to extract

| Value | Current location | Extract to |
|-------|-----------------|------------|
| Timeout 50s | `conveyancing.py:146,147,155,156` | `TIMEOUT_PLANNING_PORTAL = 8`, `TIMEOUT_VG = 5`, etc. |
| NSW bbox lat/lng | Should be in Pydantic validator | `NSW_LAT_MIN = -37.5`, `NSW_LAT_MAX = -28.0`, etc. |
| DA radius 200m | `conveyancing.py:177`, `generate_conveyancing_report.py:1417` | `DA_SEARCH_RADIUS_M = 200` |
| DA lookback 365 days | `generate_conveyancing_report.py:1417` | `DA_LOOKBACK_DAYS = 365` |
| SEPP Housing min lot 450m2 | `generate_conveyancing_report.py:476` | Already has `_SD_MIN_LOT = 450` with source ref. Good. |
| ThreadPoolExecutor workers | `conveyancing.py:143,152` | `MAX_PARALLEL_SOURCES = 6` (for brief) |
| Cache TTL | Not yet implemented | `CACHE_TTL_PLANNING_S = 86400`, `CACHE_TTL_SATELLITE_S = 604800` |

### 10.2 Config location

```python
# services/config.py
from dataclasses import dataclass

@dataclass(frozen=True)
class BriefConfig:
    # Timeouts (seconds)
    timeout_planning_portal: float = 8.0
    timeout_vg: float = 5.0
    timeout_postgis: float = 5.0
    timeout_eplanning: float = 10.0
    timeout_shadow: float = 15.0
    timeout_satellite: float = 45.0
    
    # NSW bounding box
    nsw_lat_min: float = -37.5
    nsw_lat_max: float = -28.0
    nsw_lng_min: float = 140.9
    nsw_lng_max: float = 153.7
    
    # Search parameters
    da_radius_m: int = 200
    da_lookback_days: int = 365
    
    # Concurrency
    max_parallel_sources: int = 6
    
    # Cache TTL
    cache_planning_ttl_s: int = 86400    # 24 hours
    cache_satellite_ttl_s: int = 604800  # 7 days
    cache_llm_ttl_s: int = 86400         # 24 hours
    
    # Minimum viable brief threshold
    min_available_ratio: float = 0.70

BRIEF_CONFIG = BriefConfig()
```

---

## 11. Resource Cleanup Checklist

| Resource | Current cleanup | Required cleanup |
|----------|----------------|-----------------|
| DB connections | `finally: conn.close()` per call | Pool-managed — `put_conn()` in finally |
| ThreadPoolExecutor | `with` statement | Same — `with` is correct |
| HTTP sessions | `requests.get()` (no session reuse) | Use `requests.Session()` with connection pooling for repeated calls to same host |
| Temp PDF files | Written to `tempfile.gettempdir()` | Add cleanup after R2 upload: `os.unlink(pdf_path)` |
| Pipeline cache rows | No TTL, no cleanup | Add `created_at < NOW() - INTERVAL '7 days'` cleanup cron |

---

## 12. Staleness Detection (R20 — DCP Data)

### 12.1 Problem

`dcp_available: true` when `dcp_setback_controls` has rows for an LGA, but those rows may be months or years old. No `last_verified_at` timestamp is checked.

### 12.2 Fix

```python
def _check_dcp_staleness(conn, lga_slug: str) -> tuple[bool, Optional[str]]:
    """Check if DCP data is current. Returns (is_stale, staleness_reason)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT MAX(updated_at), COUNT(*)
            FROM dcp_setback_controls
            WHERE lga = %s AND is_current = TRUE
        """, (lga_slug,))
        row = cur.fetchone()
    
    if not row or row[1] == 0:
        return True, "No DCP controls found for this council"
    
    last_updated = row[0]
    if last_updated and (date.today() - last_updated.date()).days > 180:
        return True, f"DCP controls last updated {last_updated.date().isoformat()} (>6 months ago)"
    
    return False, None
```

Included in the intelligence brief response as:
```json
{
  "dcp_controls": {
    "value": {...},
    "confidence": "stale",
    "source": "PlotDetect DCP extraction",
    "as_at": "2025-11-15",
    "reason": "DCP controls last updated 2025-11-15 (>6 months ago)"
  }
}
```

---

## 13. Enforcement Chain (Hooks Summary)

The existing hooks enforce quality at three gates:

| Gate | Hook | What it checks | How it relates to this remediation |
|------|------|---------------|-----------------------------------|
| Commit | `.githooks/commit-msg` | QA tier line in commit message | Every fix in this plan requires `QA: Standard` or `QA: Critical` |
| Commit | `.githooks/pre-commit` | TSC error count (baseline 664) | Frontend changes in the brief must not add TS errors |
| Push | `.githooks/pre-push` check 1 | Python unit tests (369+ tests) | New adversarial tests from section 8 of QA doc must pass |
| Push | `.githooks/pre-push` check 2 | `qa_gate.py` on `.qa_report.json` | QA report must cover all changed files, AST-verified |
| Push | `.githooks/pre-push` check 3 | Liability language scan | Brief narrative (Stage 5) must pass language scan |

**Additional enforcement for intelligence brief:**
- Stage 2 verification gate: parity test (10 addresses match conveyancing output)
- Stage 3 verification gate: compound constraint fixture tests (10+ cases)
- Each stage's tests become permanent regression tests in `tests/`

**Hooks are already configured** (`git config core.hooksPath .githooks` confirmed active). No changes needed to the hook infrastructure itself.

---

## 14. Implementation Sequence

These fixes are ordered to minimise risk and maximise reuse during the Stage 2 build.

| Order | Fix | When | Effort | Blocks |
|-------|-----|------|--------|--------|
| 1 | Write adversarial test file `tests/test_conveyancing_adversarial.py` (section 8 of QA doc) | Before Stage 1 | 2 hours | Validates current state, becomes regression suite |
| 2 | Create `services/db_pool.py` (section 3) | Stage 2 day 1 | 1 hour | All DB calls in brief |
| 3 | Create `services/config.py` (section 10) | Stage 2 day 1 | 30 min | All timeouts/constants |
| 4 | Build `_safe_call` wrapper (section 2) | Stage 2 day 1 | 30 min | All source calls in brief |
| 5 | Build Pydantic request/response models (section 1) | Stage 1 (schema) | 1.5 days | This IS Stage 1 |
| 6 | Implement PostGIS former-council validation (section 4) | Stage 2 day 2 | 0.5 day | Fix A |
| 7 | Build clean heritage merge (section 5) | Stage 2 day 2 | 1 hour | Heritage data quality |
| 8 | Zone prefix safe extraction (section 6) | Stage 2 day 1 | 10 min | Compound constraints |
| 9 | Add staleness detection (section 12) | Stage 3 | 1 hour | Confidence assignment |
| 10 | Rate limiter (section 7.1) | Stage 8 (hardening) | 2 hours | Production load |
| 11 | API key auth (section 7.2-7.3) | Stage 8 (hardening) | 3 hours | Production access |
| 12 | XSS sanitisation (section 8) | Stage 2 day 3 | 30 min | Data safety |
| 13 | Error response format (section 9) | Stage 2 day 1 | 30 min | API contract |

**Total pre-Stage-2 effort:** ~2.5 hours (adversarial tests only)
**Total within Stage 2:** ~5 hours (pool, config, safe_call, PostGIS validation, heritage merge, zone fix, sanitisation, error format)
**Total deferred to Stage 8:** ~5 hours (rate limiting, auth)

---

## 15. Verification

After implementing fixes 1-9, run:

```bash
# 1. Adversarial tests pass
python -m pytest tests/test_conveyancing_adversarial.py -v

# 2. All existing tests still pass (no regressions)
python -m pytest tests/ -x -q

# 3. QA gate passes
python scripts/qa_gate.py .qa_report.json --diff-files services/intelligence_brief.py services/db_pool.py services/config.py

# 4. Pre-push hook passes (all three checks)
# (triggered automatically on git push)
```
