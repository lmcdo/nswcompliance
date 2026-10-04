/**
 * DQ-122: the property lookup must return the asked-for property or nothing -- never a neighbour.
 * Candidate lists are the NSW Planning Portal's real responses, recorded 2026-10-04.
 */
import {
  filterToAskedProperty,
  parseStreetNumber,
  streetNumbersMatch,
} from '@/lib/address-number-match';
import { NSWPlanningPortalService, ADDRESS_SEARCH_UNAVAILABLE } from '@/lib/nsw-planning-portal';

const c = (address: string, propId = 1) => ({ address, propId, GURASID: propId });

// Portal answer for '700 New South Head Rd, Rose Bay NSW 2029' (700 is not in the NSW address register).
const ROSE_BAY_700 = [
  c('893 NEW SOUTH HEAD ROAD ROSE BAY 2029', 2095648),
  c('774 NEW SOUTH HEAD ROAD ROSE BAY 2029', 2093831),
  c('SE 1 795 NEW SOUTH HEAD ROAD ROSE BAY 2029', 2095553),
  c('2 650 NEW SOUTH HEAD ROAD ROSE BAY 2029', 2094007),
  c('SHOP 1 710 NEW SOUTH HEAD ROAD ROSE BAY 2029', 2093957),
  c('SHOP 1 702 NEW SOUTH HEAD ROAD ROSE BAY 2029', 2093959),
  c('3 614-622 NEW SOUTH HEAD ROAD ROSE BAY 2029', 2094034),
  c('4 699 NEW SOUTH HEAD ROAD ROSE BAY 2029', 3190258),
];

describe('parseStreetNumber', () => {
  it.each([
    ['700 New South Head Rd, Rose Bay NSW 2029', 700, 700],
    ['5/12 Smith St, Summer Hill NSW 2130', 12, 12],
    ['SE 1 795 NEW SOUTH HEAD ROAD ROSE BAY 2029', 795, 795],
    ['SHOP 24A 203-233 NEW SOUTH HEAD ROAD EDGECLIFF 2027', 203, 233],
    ['L1 32 PHILLIP STREET PARRAMATTA 2150', 32, 32],
    ['674-680 New South Head Rd, Rose Bay NSW 2029', 674, 680],
  ])('%s -> %i..%i', (addr, lo, hi) => {
    expect(parseStreetNumber(addr)).toMatchObject({ lo, hi });
  });

  it('returns null when no number precedes the street name', () => {
    expect(parseStreetNumber('New South Head Rd, Rose Bay NSW 2029')).toBeNull();
    expect(parseStreetNumber('')).toBeNull();
    expect(parseStreetNumber(null)).toBeNull();
  });

  it('keeps a letter suffix so 869 and 869A stay different properties', () => {
    const a = parseStreetNumber('869 NEW SOUTH HEAD ROAD')!;
    const b = parseStreetNumber('869A NEW SOUTH HEAD ROAD')!;
    expect(streetNumbersMatch(a, b)).toBe(false);
    expect(streetNumbersMatch(b, b)).toBe(true);
  });
});

describe('filterToAskedProperty', () => {
  it('700 Rose Bay: every Portal candidate is another property, so nothing is kept', () => {
    expect(filterToAskedProperty('700 New South Head Rd, Rose Bay NSW 2029', ROSE_BAY_700)).toEqual([]);
  });

  it('235 New South Head Rd (Google said Point Piper): 582 is not 235', () => {
    const portal = [
      c('582 NEW SOUTH HEAD ROAD POINT PIPER 2027'),
      c('2 574 NEW SOUTH HEAD ROAD POINT PIPER 2027'),
      c('550-550A NEW SOUTH HEAD ROAD POINT PIPER 2027'),
    ];
    expect(filterToAskedProperty('235 New South Head Rd, Point Piper NSW 2027', portal)).toEqual([]);
  });

  it('same number on a different street is a different property', () => {
    const portal = [c('14 ST JOHN STREET LEWISHAM 2049'), c('15 HUNTER STREET LEWISHAM 2049')];
    expect(filterToAskedProperty('14 Hunter St, Lewisham NSW 2049', portal)).toEqual([]);
  });

  it('same number and street in another postcode is a different property', () => {
    const portal = [c('12 SMITH STREET ASHFIELD 2131')];
    expect(filterToAskedProperty('12 Smith St, Summer Hill NSW 2130', portal)).toEqual([]);
  });

  it('a different street type is a different street', () => {
    const portal = [c('60 HALL AVENUE BONDI BEACH 2026')];
    expect(filterToAskedProperty('60 Hall St, Bondi Beach NSW 2026', portal)).toEqual([]);
  });

  it('keeps the asked property when it is present, wherever the Portal ranked it', () => {
    const portal = [c('61 HALL STREET BONDI BEACH 2026', 1), c('60 HALL STREET BONDI BEACH 2026', 2)];
    expect(filterToAskedProperty('60 Hall St, Bondi Beach NSW 2026', portal).map((r) => r.propId)).toEqual([2]);
  });

  it('a number inside a range lot is that lot (680 -> 674-680)', () => {
    const portal = [c('674-680 NEW SOUTH HEAD ROAD ROSE BAY 2029', 7), c('682 NEW SOUTH HEAD ROAD ROSE BAY 2029', 8)];
    expect(filterToAskedProperty('680 New South Head Rd, Rose Bay NSW 2029', portal).map((r) => r.propId)).toEqual([7]);
  });

  it('a unit address matches its building, with the unit and level words skipped', () => {
    expect(filterToAskedProperty('SHOP 24A 203-233 New South Head Rd, Edgecliff NSW 2027',
      [c('SE 305 203-233 NEW SOUTH HEAD ROAD EDGECLIFF 2027')])).toHaveLength(1);
    expect(filterToAskedProperty('32 Phillip St, Parramatta NSW 2150',
      [c('L1 32 PHILLIP STREET PARRAMATTA 2150')])).toHaveLength(1);
  });

  it('a street whose name starts with an abbreviation-like word (St Johns Rd) still matches', () => {
    expect(filterToAskedProperty('5 St Johns Rd, Glebe NSW 2037', [c('5 ST JOHNS ROAD GLEBE 2037')])).toHaveLength(1);
  });
});

describe('filterToAskedProperty -- an address must identify ONE property', () => {
  const portal = [c('893 NEW SOUTH HEAD ROAD ROSE BAY 2029'), c('774 NEW SOUTH HEAD ROAD ROSE BAY 2029')];

  it('no house number: nothing matches (was: any candidate on the street)', () => {
    expect(filterToAskedProperty('New South Head Rd, Rose Bay NSW 2029', portal)).toEqual([]);
  });

  it('no postcode: the suburb must match', () => {
    const cands = [c('12 SMITH STREET ASHFIELD 2131', 1), c('12 SMITH STREET SUMMER HILL 2130', 2)];
    expect(filterToAskedProperty('12 Smith St, Summer Hill', cands).map((r) => r.propId)).toEqual([2]);
    expect(filterToAskedProperty('12 Smith St, Summer Hill NSW', cands).map((r) => r.propId)).toEqual([2]);
  });

  it('a postcode was asked for: a candidate without one is not accepted', () => {
    expect(filterToAskedProperty('60 Hall St, Bondi Beach NSW 2026', [c('60 HALL STREET BONDI BEACH')])).toEqual([]);
  });

  it('neither postcode nor suburb: nothing matches', () => {
    expect(filterToAskedProperty('60 Hall St', [c('60 HALL STREET BONDI BEACH 2026')])).toEqual([]);
  });
});

describe('NSWPlanningPortalService.searchProperty', () => {
  const realFetch = global.fetch;
  afterEach(() => {
    global.fetch = realFetch;
  });
  const respond = (status: number, body: unknown) => {
    global.fetch = jest.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body }) as any;
  };

  it('returns null -- not the top fuzzy hit -- when no candidate is the asked property', async () => {
    respond(200, ROSE_BAY_700);
    await expect(NSWPlanningPortalService.searchProperty('700 New South Head Rd, Rose Bay NSW 2029')).resolves.toBeNull();
  });

  it('returns the asked property even when the Portal ranks it below neighbours', async () => {
    respond(200, [c('893 NEW SOUTH HEAD ROAD ROSE BAY 2029', 1), c('699 NEW SOUTH HEAD ROAD ROSE BAY 2029', 2)]);
    const got = await NSWPlanningPortalService.searchProperty('699 New South Head Rd, Rose Bay NSW 2029');
    expect(got?.propId).toBe(2);
  });

  it('a rate limit is an outage, not "property not found"', async () => {
    respond(429, { statusCode: 429, message: 'Rate limit is exceeded.' });
    await expect(NSWPlanningPortalService.searchProperty('60 Hall St, Bondi Beach NSW 2026'))
      .rejects.toThrow(ADDRESS_SEARCH_UNAVAILABLE);
  });

  it('a 200 whose body is not a list is an outage, not "property not found"', async () => {
    respond(200, { statusCode: 429, message: 'Rate limit is exceeded.' });
    await expect(NSWPlanningPortalService.searchProperty('60 Hall St, Bondi Beach NSW 2026'))
      .rejects.toThrow(ADDRESS_SEARCH_UNAVAILABLE);
  });
});
