/**
 * Council attribution from precinct IDs.
 *
 * A precinct id that matches no PRECINCT_ID_PATTERNS entry falls through to the
 * 'Marrickville' default and the provisions API gets scoped to the wrong council
 * (the #835 Waverley bug class). These tests pin the attribution for every id
 * format that exists in dcp_precinct_boundaries today.
 */

jest.mock('@/lib/db', () => ({ getPool: () => ({ query: jest.fn() }) }));
jest.mock('@/lib/nsw-planning-portal', () => ({ getPropertyCoordinates: jest.fn() }));

import { getFormerCouncilFromPrecinctId } from '@/lib/precinct-service';

describe('getFormerCouncilFromPrecinctId', () => {
  test.each([
    // City of Sydney — Sydney DCP 2012 section keys
    ['2.1', 'City of Sydney'],
    ['2.13', 'City of Sydney'],
    ['2.13.6', 'City of Sydney'],
    ['5.8', 'City of Sydney'],
    ['5.12', 'City of Sydney'],
    ['6.3.3', 'City of Sydney'],
    ['6.1.4', 'City of Sydney'],
    // Ku-ring-gai Part 14 local centres
    ['14B_T1', 'Ku-ring-gai'],
    ['14B_T4', 'Ku-ring-gai'],
    ['14I', 'Ku-ring-gai'],
    ['14O', 'Ku-ring-gai'],
    // Waverley Part E
    ['E1', 'Waverley'],
    ['E7', 'Waverley'],
    // Ashfield chapter D
    ['Part 1', 'Ashfield'],
    ['Part 13', 'Ashfield'],
    // Marrickville numeric
    ['19_', 'Marrickville'],
    ['9_10', 'Marrickville'],
    // Leichhardt distinctive neighbourhoods
    ['C2.2.1.1', 'Leichhardt'],
  ])('%s -> %s', (precinctId, council) => {
    expect(getFormerCouncilFromPrecinctId(precinctId)).toBe(council);
  });

  test('empty id returns Unknown', () => {
    expect(getFormerCouncilFromPrecinctId('')).toBe('Unknown');
  });
});
