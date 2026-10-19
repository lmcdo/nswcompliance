import { cornerStatus, cornerSentence, isCornerOnlyRow } from '@/lib/geometry/corner-status';

const ok = { isCornerLot: false, adjacentRoads: ['BERRIGAN ST'], roadCount: 1, confidence: 1 };

describe('cornerStatus', () => {
  it('measured one road -> not_corner', () => expect(cornerStatus(ok)).toBe('not_corner'));
  it('measured two roads -> corner', () => expect(cornerStatus({ ...ok, isCornerLot: true, roadCount: 2 })).toBe('corner'));
  it('a failed road query is unknown, never not_corner', () => {
    expect(cornerStatus({ ...ok, confidence: 0, error: 'Failed to query road data: This operation was aborted' })).toBe('unknown');
    expect(cornerStatus(null)).toBe('unknown');
  });
  it('unknown is said in plain words', () => {
    expect(cornerSentence('unknown')).toMatch(/couldn't reach the NSW road map/);
  });
});

describe('isCornerOnlyRow', () => {
  it.each([
    [{ control_type: 'secondary_street_setback', condition: null }, true],
    [{ control_type: 'front_setback', condition: 'secondary street or corner allotment' }, true],
    [{ control_type: 'front_setback', condition: 'state and regional roads' }, false],
    [{ control_type: 'side_setback', condition: null }, false],
  ])('%o -> %s', (row, want) => expect(isCornerOnlyRow(row)).toBe(want));
});
