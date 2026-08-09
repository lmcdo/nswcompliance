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
- `python -m pytest` — all active Python tests (**4,013 passed, 2 skipped, ~90s**)
- `python -m pytest tests/test_flood_truth.py -v` — single file
- `python -m pytest -m database` — DB-dependent tests (needs DATABASE_URL)
- `cd frontend-nextjs && npx jest` — all frontend Jest tests (**80 suites, 1,034 tests**)
- `cd frontend-nextjs && npx jest --testPathPattern=council-config` — single test file
- Test deps: `pip install -r requirements-test.txt` (pytest, pydantic, fastapi)
- Mock injection: `tests/conftest_mocks.py` stubs psycopg2/requests/pyproj so pure-logic tests run without native deps

## Quarantined tests — a number that may only go down
- **10 test files are excluded from collection.** Every run prints the count in its
  header; the reason for each is recorded in `tests/quarantine-baseline.json`.
- `python scripts/check_test_quarantine.py` — the ratchet. **Two rules:** adding a file
  to `collect_ignore` without a baseline entry FAILS, and a baseline file that starts
  PASSING also FAILS, so it gets released rather than left as standing amnesty.
- **Why this exists:** all 16 files were quarantined in one commit on 2026-05-23 (#362) —
  the same commit that turned CI and the pre-push hook on. Re-measured 2026-08-09,
  **six passed with no changes at all** (43 tests) and were released. Two had been broken
  BY the quarantining itself: inserting `pytestmark = pytest.mark.stale` at the top of a
  file pushed `from __future__ import annotations` below other statements — a SyntaxError.
  One of those was `test_lga_coverage.py`, the gate that enforces "do not enable an LGA
  before its data is ready".
- **A quarantined file is invisible, which is worse than a skip.** It produces no output,
  counts as nothing, and `pytest -m stale` returns zero. Hence the header line and the
  ratchet.

## QA Three-Phase Workflow (Critical/Standard tier)
1. `/qa-write` — defensive patterns (null boundaries, three-state semantics, error isolation). No tests yet.
2. `/qa-break` — re-read adversarially. Find silent wrong results. Write break-it scenarios, then tests.
3. `/qa-verify` — mutation analysis (would `return []` still pass?). Delete WEAK tests, fill gaps.
