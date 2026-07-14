/**
 * Guard: /api/capacity/calculate must read the MAINTAINED dcp_setback_controls,
 * never the frozen dcp_general_requirements (Oct-2025 snapshot, no live writer).
 *
 * This keeps the assessment-page capacity box on the same numeric source as the
 * conveyancing report + brief constraint engine, so an approved DCP change reaches
 * it. A source-level guard (the route can't be unit-run without a live DB); it fails
 * the moment a query is repointed back to the frozen table or loses the fail-closed
 * / universal-row handling.
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const routeSrc = readFileSync(
  join(process.cwd(), 'app/api/capacity/calculate/route.ts'),
  'utf8',
);

describe('capacity route table source', () => {
  it('reads dcp_setback_controls for parking, landscaping and setbacks (currency-guarded)', () => {
    const fromSetbackControls = routeSrc.match(/FROM dcp_setback_controls/g) || [];
    expect(fromSetbackControls.length).toBeGreaterThanOrEqual(3);
    // every dcp_setback_controls read is currency-guarded: WHERE is_current = TRUE
    expect(routeSrc).toMatch(/is_current IS NULL OR is_current = TRUE/);
  });

  it('never queries the frozen dcp_general_requirements table', () => {
    expect(routeSrc).not.toMatch(/FROM\s+dcp_general_requirements/);
  });

  it('includes universal_residential rows (not just the exact dev type)', () => {
    expect(routeSrc).toMatch(/dev_type IN \(\$2, 'universal_residential'\)/);
  });

  it('is fail-closed on currency (excludes needs_review rows)', () => {
    const guards = routeSrc.match(/needs_review IS NULL OR needs_review = FALSE/g) || [];
    expect(guards.length).toBeGreaterThanOrEqual(3);
  });

  it('covers the expected control-type families', () => {
    expect(routeSrc).toMatch(/'car_parking'/);
    expect(routeSrc).toMatch(/'landscaping_min'/);
    expect(routeSrc).toMatch(/'front_setback'/);
  });
});
