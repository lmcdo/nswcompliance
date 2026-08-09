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
> Counts measured 2026-08-08 at `origin/main` f5acb080. **Re-run rather than quote** —
> `python -m pytest --collect-only -q | tail -1` prints the current number.
- `python -m pytest` — all active Python tests (**4,101 passed, 16 skipped, ~90s**)
- `python -m pytest tests/test_flood_truth.py -v` — single file
- `python -m pytest -m database` — DB-dependent tests (needs DATABASE_URL)
- `cd frontend-nextjs && npx jest` — all frontend Jest tests (**80 suites, 1,034 tests**)
- `cd frontend-nextjs && npx jest --testPathPattern=council-config` — single test file
- Test deps: `pip install -r requirements-test.txt` (pytest, pydantic, fastapi)
- Mock injection: `tests/conftest_mocks.py` stubs psycopg2/requests/pyproj so pure-logic tests run without native deps

## Quarantined tests — now ZERO
- **No test file is excluded from collection.** The list was 16 on 2026-05-23 and is now empty.
- `python scripts/check_test_quarantine.py` — the ratchet, in CI. **Two rules:** adding a file
  to `collect_ignore` without a recorded reason FAILS, and a listed file that starts PASSING
  also FAILS, so it is released rather than left as standing amnesty.
- **What the 16 turned out to be:** six already passed · two were broken BY the quarantining
  (a marker inserted above a `from __future__` import — a SyntaxError) · two had drifted
  behind the code · five were not tests at all (1,090 lines, **zero assertions**, deleted) ·
  three needed a live server or a real database and now carry skip guards.
- **Integration tests:** `pytest -m integration` with the dev server running. They skip with an
  actionable reason otherwise, rather than being hidden.
- **Database tests:** `PYTEST_REAL_DB=1 DATABASE_URL=... pytest tests/test_lga_coverage.py -o addopts=`.
  The opt-in is required because `conftest_mocks.py` stubs psycopg2 by default, so a DB test
  would otherwise get a MagicMock and fail on nonsense comparisons.

## QA Three-Phase Workflow (Critical/Standard tier)
1. `/qa-write` — defensive patterns (null boundaries, three-state semantics, error isolation). No tests yet.
2. `/qa-break` — re-read adversarially. Find silent wrong results. Write break-it scenarios, then tests.
3. `/qa-verify` — mutation analysis (would `return []` still pass?). Delete WEAK tests, fill gaps.
