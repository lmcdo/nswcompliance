# PlotDetect — Test Matrix

**Date:** 2026-05-23
**Total tests:** 415 passed, 2 skipped, 15 deselected (quarantined)
**Execution time:** <2 seconds
**Framework:** pytest with pydantic validation
**Mock injection:** `tests/conftest_mocks.py` stubs psycopg2, requests, pyproj

---

## Test Distribution by Pipeline

| Test File | Tests | Pipeline | Coverage Focus |
|-----------|-------|----------|----------------|
| `tests/test_flood_truth.py` | 83 | Flood Truth | Multi-source validation, WOfS band indexing, EPI tier classification, null handling, edge cases |
| `tests/test_climate_risk_score.py` | 51 | Climate Risk | Multi-hazard scoring, raster query parsing, score aggregation, coastal/inland variants |
| `tests/test_bushfire_prescreen.py` | 51 | Bushfire Pre-Screen | BAL classification, multi-feature geometry, vegetation buffer, false DEM attribution |
| `tests/enrichment/test_applicability_tagger.py` | 33 | Enrichment | Zone extraction, dev type tagging, structural inheritance, council detection |
| `tests/test_solar_yield.py` | 31 | Solar Yield | Panel yield calculation, shading loss, battery sizing, orientation adjustment |
| `tests/enrichment/test_layer_topic_tagger.py` | 29 | Enrichment | Topic classification, layer assignment, DCP section mapping |
| `tests/test_threat_radar.py` | 25 | Threat Radar | DA monitoring, distance calculation, status parsing, timeline estimation |
| `tests/test_granny_flat_logic.py` | 21 | Granny Flat | CDC eligibility rules, SEPP Housing cl 58-62, lot size thresholds |
| `tests/enrichment/test_actionable_classifier.py` | 20 | Enrichment | Actionable vs boilerplate classification, false positive/negative prevention |
| `tests/test_shadow_detector.py` | 18 | Shadow Detector | Seasonal shadow geometry, height limit scenarios, boundary conditions |
| `tests/test_insert_scripts.py` | 17 | DCP Data | Insert script data integrity, dedup checks, value ranges, constraint compliance |
| `tests/test_qa_scanners.py` | 14 | QA Infrastructure | Scanner false positive/negative validation for all 4 heuristics |
| `tests/test_granny_flat_geometry.py` | 13 | Granny Flat | Lot geometry, setback calculations, building envelope |
| `tests/utils/test_document_finder.py` | 11 | Utilities | Document ID resolution, council name normalisation |

---

## Test Categories

### Satellite Products (7 pipelines — 262 tests)

Every satellite pipeline has a dedicated test suite covering:
- **Expected use cases** — correct outputs for known inputs
- **Edge cases** — boundary values, minimum/maximum lot sizes, zero values
- **Null handling** — missing API responses, empty geometries, null fields
- **Classification correctness** — thresholds, categories, scoring tiers

### Enrichment Pipeline (82 tests)

The regulatory provision enrichment pipeline has 3 test suites covering:
- **Actionable classification** — distinguishing enforceable controls from boilerplate, headers, TOC entries
- **Applicability tagging** — zone and development type extraction from provision text
- **Layer/topic classification** — mapping provisions to DCP sections and topics

### Data Integrity (17 tests)

Insert script tests validate all DCP control data before database insertion:
- Required fields present (lga, control_type, dev_type, source_ref)
- No duplicate entries per (lga, control_type, dev_type, condition)
- Value ranges within expected bounds (e.g., solar hours 2-8, setbacks 0-30m)
- LGA slugs match canonical set
- Constraint compliance (applicability field matches CHECK constraint)

### QA Infrastructure (14 tests)

Scanner tests validate the automated quality gates themselves:
- Falsy JSX guard detection (true positive + false positive suppression)
- Strict null check detection
- Empty catch block scoping (API routes only)
- Log-only catch detection (console.error vs res.error disambiguation)
- Success-on-error detection
- qa-ignore suppression

---

## Test Enforcement

| Enforcement Point | What Runs | Blocks On |
|-------------------|-----------|-----------|
| `pre-push` hook | Full pytest suite (415 tests) | Any test failure |
| `pre-commit` hook | TSC error count gate | New TypeScript errors |
| `commit-msg` hook | QA tier classification | Missing QA line |

---

## Quarantined Tests (15 deselected)

Tests that depend on external services or deprecated modules are quarantined in `conftest.py:collect_ignore`. They are not deleted — they can be revived when dependencies are available. Quarantined files:
- Tests requiring live database connection (`DATABASE_URL`)
- Tests for deprecated API endpoints
- Tests for modules pending refactoring

---

## Mock Strategy

External dependencies are stubbed at import time via `tests/conftest_mocks.py`:

| Dependency | Mock Reason |
|-----------|-------------|
| `psycopg2` | Database connection not available in test environment |
| `requests` | External API calls not made during unit tests |
| `pyproj` | Native GIS library not required for logic tests |

This allows all 415 tests to run in <2 seconds without any external dependencies, network access, or database connection.
