/**
 * The plan brief is served only for the councils, project type and zone whose first five clauses per topic were read against the
 * council's own section headings, and skips the clauses the scope file lists. See shared/brief-scope.json.
 *
 * prior-art-checked: reuse not viable because no test covers the brief's scope; the pure helpers sit beside shapeBriefRows in
 * lib/plan-brief.ts and follow __tests__/lib/plan-brief.test.ts's style.
 */
import briefScope from '@/shared/brief-scope.json';
import { inBriefScope, dropExcluded, type StoredBriefRow } from '@/lib/plan-brief';

const item = (id: number) => ({ id, verdict: 'MIGHT' as const, text: 'x', page: 1, pageLabel: null, clauseLabel: null, sectionHeader: null,
  chapterKey: null, pageProven: true, url: null, urlPage: null });
const row = (row_type: string, rank: number, id: number): StoredBriefRow => ({ row_type, rank, item: item(id) });

describe('inBriefScope', () => {
  const scope = { councils: ['penrith', 'wollongong'], dev_type: 'dwelling_house', zone_group: 'R2', excluded_provision_ids: [] };
  it('is true only for a named council, the house project type and zone group R2', () => {
    expect(inBriefScope(scope, 'penrith', 'dwelling_house', 'R2')).toBe(true);
    expect(inBriefScope(scope, 'hornsby', 'dwelling_house', 'R2')).toBe(false);          // council not named
    expect(inBriefScope(scope, 'penrith', 'dual_occupancy', 'R2')).toBe(false);          // another project type
    expect(inBriefScope(scope, 'penrith', 'dwelling_house', 'R3')).toBe(false);          // another zone group
    expect(inBriefScope(scope, 'penrith', 'dwelling_house', 'ANY')).toBe(false);         // the any-zone build was not read
  });
});

describe('dropExcluded', () => {
  it('removes skipped clauses and moves the next best up, per topic', () => {
    const stored = [row('front_setback', 1, 10), row('front_setback', 2, 11), row('front_setback', 3, 12), row('car_parking', 1, 20)];
    const out = dropExcluded(stored, new Set([10]));
    const front = out.filter((r) => r.row_type === 'front_setback').sort((a, b) => a.rank - b.rank);
    expect(front.map((r) => [r.rank, r.item.id])).toEqual([[1, 11], [2, 12]]);
    expect(out.find((r) => r.row_type === 'car_parking')?.item.id).toBe(20);
  });
  it('leaves a topic with no clause when every clause is skipped, never inventing one', () => {
    const out = dropExcluded([row('rear_setback', 1, 30), row('rear_setback', 2, 31)], new Set([30, 31]));
    expect(out).toEqual([]);
  });
  it('changes nothing when nothing is skipped', () => {
    const stored = [row('side_setback', 1, 40), row('side_setback', 2, 41)];
    expect(dropExcluded(stored, new Set()).map((r) => [r.rank, r.item.id])).toEqual([[1, 40], [2, 41]]);
  });
});

describe('shared/brief-scope.json', () => {
  it('names 10 councils for the house project type in zone R2, each in lower-case slug form', () => {
    expect(briefScope.dev_type).toBe('dwelling_house');
    expect(briefScope.zone_group).toBe('R2');
    expect(briefScope.councils).toHaveLength(10);
    briefScope.councils.forEach((c) => expect(c).toMatch(/^[a-z_]+$/));
  });
  it('lists unique positive integer clause ids to skip, and a recall figure of at least 80% for every named council', () => {
    const ids = briefScope.excluded_provision_ids;
    expect(new Set(ids).size).toBe(ids.length);
    ids.forEach((i) => expect(Number.isInteger(i) && i > 0).toBe(true));
    briefScope.councils.forEach((c) => expect((briefScope.recall_after_skip_percent as Record<string, number>)[c]).toBeGreaterThanOrEqual(80));
  });
});
