---
globs:
  - "tests/**"
  - "frontend-nextjs/__tests__/**"
  - "frontend-nextjs/**/*.test.*"
  - "scripts/qa_*"
  - ".qa_report.json"
---

# Testing & QA

## Running Tests
- `python -m pytest` — all active Python tests (~1794 tests, <1s)
- `python -m pytest tests/test_flood_truth.py -v` — single file
- `python -m pytest -m database` — DB-dependent tests (needs DATABASE_URL)
- `cd frontend-nextjs && npx jest` — all frontend Jest tests (~615 tests, ~6s)
- `cd frontend-nextjs && npx jest --testPathPattern=council-config` — single test file
- Test deps: `pip install -r requirements-test.txt` (pytest, pydantic, fastapi)
- Mock injection: `tests/conftest_mocks.py` stubs psycopg2/requests/pyproj so pure-logic tests run without native deps
- Stale tests quarantined in `collect_ignore` (conftest.py) — not deleted, can be revived

## QA Three-Phase Workflow (Critical/Standard tier)
1. `/qa-write` — defensive patterns (null boundaries, three-state semantics, error isolation). No tests yet.
2. `/qa-break` — re-read adversarially. Find silent wrong results. Write break-it scenarios, then tests.
3. `/qa-verify` — mutation analysis (would `return []` still pass?). Delete WEAK tests, fill gaps.
