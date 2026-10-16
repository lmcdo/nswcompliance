/**
 * The heritage query must serve current rules only (address audit 2026-10-16: a retired Marrickville Part 8 row,
 * is_current = false, was shown at a heritage item). Every other provision query in the route filters is_current.
 * @jest-environment node
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const src = readFileSync(join(__dirname, '../../app/api/provisions/for-property/route.ts'), 'utf8');

describe('queryHeritageByHca', () => {
  it('filters to current rules', () => {
    const start = src.indexOf('async function queryHeritageByHca(');
    expect(start).toBeGreaterThan(-1);
    const body = src.slice(start, src.indexOf('\nasync function ', start + 10));
    expect(body).toMatch(/rp\.is_current = TRUE/);
  });
});
