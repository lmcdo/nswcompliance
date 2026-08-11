/**
 * Guard: /api/capacity/calculate must source its DCP rows from the ONE
 * guarded implementation via lib/dcp-controls-client (item 5 consolidation,
 * 2026-08-03), never from its own inline SQL.
 *
 * FLIPPED from the previous version, which pinned >=3 `FROM
 * dcp_setback_controls` queries in this route — the old doctrine this
 * consolidation removes: those queries returned an arbitrary LIMIT 3 with no
 * ORDER BY, weakened is_current to NULL-passes, and never applied the zone
 * filter. The guards (is_current, needs_review, zone, deterministic order)
 * now live solely in conveyancing_db.fetch_dcp_setbacks; this route SHAPES.
 * A source-level guard: it fails the moment anyone reintroduces inline SQL
 * against the controls table here.
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const routeSrc = readFileSync(
  join(process.cwd(), 'app/api/capacity/calculate/route.ts'),
  'utf8',
);

describe('capacity route table source', () => {
  it('runs NO inline SQL against dcp_setback_controls (proxy-only)', () => {
    // The is_current = TRUE + needs_review guards live in the ONE
    // implementation (conveyancing_db.fetch_dcp_setbacks) behind the proxy.

    const fromSetbackControls = routeSrc.match(/FROM dcp_setback_controls/g) || [];
    expect(fromSetbackControls.length).toBe(0);
    expect(routeSrc).toMatch(/from '@\/lib\/dcp-controls-client'/);
    expect(routeSrc).toMatch(/fetchDcpControls\(/);
  });

  it('never queries the frozen dcp_general_requirements table', () => {
    expect(routeSrc).not.toMatch(/FROM\s+dcp_general_requirements/);
  });

  it('includes universal_residential rows (not just the exact dev type)', () => {
    expect(routeSrc).toMatch(/r\.dev_type === 'universal_residential'/);
  });

  it('passes the zone through so the guarded source can apply its zone filter', () => {
    expect(routeSrc).toMatch(/fetchDcpControls\(formerCouncil, zone\)/);
  });

  it('covers the expected control-type families', () => {
    expect(routeSrc).toMatch(/'car_parking'/);
    expect(routeSrc).toMatch(/'landscaping_min'/);
    expect(routeSrc).toMatch(/'front_setback'/);
  });

  it('still reads precinct tables directly (out of consolidation scope)', () => {
    expect(routeSrc).toMatch(/FROM dcp_precinct_boundaries/);
    expect(routeSrc).toMatch(/FROM dcp_precinct_requirements/);
  });
});
