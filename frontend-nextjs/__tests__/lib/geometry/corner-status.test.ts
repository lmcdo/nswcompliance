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
    // Sol 2026-10-20: these are rules FOR non-corner lots, not corner-only rules
    [{ control_type: 'front_setback', condition: 'all lots excluding corner lots' }, false],
    [{ control_type: 'front_setback', condition: 'not applicable to corner allotments' }, false],
    // ... and these ARE corner-only
    [{ control_type: 'side_setback', condition: 'must not be less than 3 m on corner lots' }, true],
    [{ control_type: 'side_setback', condition: 'excluding non-corner lots' }, true],
    [{ control_type: 'side_setback', condition: 'Other than garages, corner lots must have a 3 m setback' }, true],
    [{ control_type: 'side_setback', condition: 'Other than garages corner lots must have a 3 m setback' }, true],
    [{ control_type: 'front_setback', condition: 'except those on corner allotments' }, false],
    // "non-corner" is not a corner row
    [{ control_type: 'front_setback', condition: 'applies to non-corner lots' }, false],
    [{ control_type: 'front_setback', condition: 'except for corner allotments' }, false],
    [{ control_type: 'front_setback', condition: 'exclude corner lots' }, false],
    [{ control_type: 'side_setback', condition: 'exclude non-corner lots' }, true],
    [{ control_type: 'side_setback', condition: 'not applicable to non-corner lots' }, true],
    [{ control_type: 'side_setback', condition: 'except for non-corner lots' }, true],
    [{ control_type: 'front_setback', condition: 'for non-corner lots' }, false],
  ])('%o -> %s', (row, want) => expect(isCornerOnlyRow(row)).toBe(want));
});
