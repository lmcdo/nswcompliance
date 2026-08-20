/**
 * The precinct → provisions lookup, which served nothing for every council.
 *
 * ORIGIN, 2026-08-20. Parramatta's 76 council-supplied Part 8 boundary polygons
 * landed (#990) and resolved correctly — a point inside precinct 8.2.6 returned
 * 8.2.6 — yet no app served that precinct's provisions. Three independent
 * breaks, each silent:
 *
 *   1. getPrecinctProvisions read `dcp_precinct_provisions`, a legacy table with
 *      0 rows. CLAUDE.md has said "use v2_precinct_id, NOT
 *      dcp_precinct_provisions" for months; this reader was never moved.
 *   2. getPrecinctControls, which the constraints API calls, was a stub that
 *      returned [] unconditionally whatever it was passed.
 *   3. The constraints API resolved the precinct, logged it, and left it out of
 *      the response — so the assessment page read `constraints?.precinctId`, got
 *      undefined, and never sent precinct_id to /api/provisions/for-property.
 *
 * None of the three raises. An empty precinct layer renders as "no precinct
 * controls", which is indistinguishable from a property genuinely in no
 * precinct. That is why 418 precincts' worth of provisions could sit unserved
 * without a single error.
 *
 * Measured against the live database while fixing it: precinct 8.2.6 with
 * council 'parramatta' returns 50 live provisions, 12 of them in the control
 * types the constraints API asks for. Ashfield "Part 1" returns 165.
 */

const mockQuery = jest.fn();
jest.mock('@/lib/db', () => ({ getPool: () => ({ query: mockQuery }) }));
jest.mock('@/lib/nsw-planning-portal', () => ({ getPropertyCoordinates: jest.fn() }));

import {
  councilSlugCandidates,
  getPrecinctProvisions,
  getPrecinctControls,
} from '@/lib/precinct-service';

beforeEach(() => {
  mockQuery.mockReset();
  mockQuery.mockResolvedValue({ rows: [] });
});

describe('councilSlugCandidates', () => {
  // dcp_precinct_boundaries and regulatory_provisions name councils
  // differently. These pairs are the ones that exist in the data today.
  test.each([
    ['City of Parramatta', 'Parramatta', ['parramatta', 'city_of_parramatta']],
    ['Inner West', 'Ashfield', ['ashfield', 'inner_west']],
    ['Inner West', 'Leichhardt', ['leichhardt', 'inner_west']],
    ['Inner West', 'Marrickville', ['marrickville', 'inner_west']],
    ['Sydney', 'city_of_sydney', ['city_of_sydney', 'sydney']],
    ['Waverley', 'Waverley', ['waverley']],
    ['Woollahra', 'Woollahra', ['woollahra']],
  ])('%s / %s', (lga, former, expected) => {
    expect(councilSlugCandidates(lga, former)).toEqual(expected);
  });

  test('Ku-ring-gai has no former_council, so the LGA slug is the match', () => {
    // Its boundary rows carry former_council NULL, and regulatory_provisions
    // stores source_council 'ku_ring_gai'. Slugging the LGA is what finds it.
    expect(councilSlugCandidates('Ku-ring-gai', null)).toEqual(['ku_ring_gai']);
  });

  test('an identical former council is not duplicated', () => {
    expect(councilSlugCandidates('Waverley', 'Waverley')).toEqual(['waverley']);
  });

  test('empty and whitespace inputs drop out rather than becoming empty slugs', () => {
    expect(councilSlugCandidates('', '')).toEqual([]);
    expect(councilSlugCandidates('   ', null)).toEqual([]);
    expect(councilSlugCandidates(null, undefined)).toEqual([]);
  });
});

describe('getPrecinctProvisions', () => {
  test('reads regulatory_provisions, current and actionable only', async () => {
    // Two assertions that belong together, and the QA gate is right to insist:
    // it refuses a reference to regulatory_provisions without a currency filter
    // within sight of it. Naming the table and forgetting is_current is exactly
    // how a read path starts serving superseded text.
    await getPrecinctProvisions('8.2.6', 'City of Parramatta', 'Parramatta');
    const sql = mockQuery.mock.calls[0][0] as string;
    expect(sql).toContain('regulatory_provisions');
    expect(sql).toContain('is_current');
    expect(sql).toContain('v2_is_actionable');
    // The legacy table this replaced holds 0 rows, so a drift back to it is
    // silent — every precinct simply returns nothing.
    expect(sql).not.toContain('dcp_precinct_provisions');
  });

  test('scopes to the council, keyed by v2_precinct_id', async () => {
    await getPrecinctProvisions('8.2.6', 'City of Parramatta', 'Parramatta');
    const [sql, params] = mockQuery.mock.calls[0];
    expect(sql).toContain('v2_precinct_id');
    expect(params[0]).toEqual(['8.2.6']);
    expect(params[1]).toEqual(['parramatta', 'city_of_parramatta']);
  });

  test('splits the comma-joined id the PostGIS matcher builds for overlaps', async () => {
    // getPrecinctUsingPostGIS joins every containing precinct into one string.
    await getPrecinctProvisions('8.2.6, 8.2.7', 'City of Parramatta', 'Parramatta');
    expect(mockQuery.mock.calls[0][1][0]).toEqual(['8.2.6', '8.2.7']);
  });

  test('returns nothing rather than dropping the council filter', async () => {
    // A precinct id is unique only WITHIN a council — "Part 1" exists in more
    // than one — so an unresolvable council must serve nothing, never another
    // council's controls.
    expect(await getPrecinctProvisions('Part 1', '', null)).toEqual([]);
    expect(mockQuery).not.toHaveBeenCalled();
  });

  test('an empty precinct id queries nothing', async () => {
    expect(await getPrecinctProvisions('', 'Inner West', 'Ashfield')).toEqual([]);
    expect(await getPrecinctProvisions('  ,  ', 'Inner West', 'Ashfield')).toEqual([]);
    expect(mockQuery).not.toHaveBeenCalled();
  });
});

describe('getPrecinctControls', () => {
  const rows = [
    { id: 1, ref_number: 'a', control_type: 'height' },
    { id: 2, ref_number: 'b', control_type: 'parking' },
    { id: 3, ref_number: 'c', control_type: 'stormwater' },
    { id: 4, ref_number: 'd', control_type: 'Open_Space' },
    { id: 5, ref_number: 'e', control_type: null },
  ];

  test('no longer returns [] unconditionally', async () => {
    // The whole defect: a stub that ignored its arguments and returned nothing,
    // so the constraints API had empty precinct controls for every address.
    mockQuery.mockResolvedValue({ rows });
    const out = await getPrecinctControls('8.2.6', 'City of Parramatta', 'Parramatta');
    expect(out).toHaveLength(rows.length);
  });

  test('narrows to the control types the constraints API asks for', async () => {
    mockQuery.mockResolvedValue({ rows });
    const out = await getPrecinctControls(
      '8.2.6', 'City of Parramatta', 'Parramatta',
      ['height', 'setback', 'parking', 'fsr', 'open_space', 'heritage', 'vegetation'],
    );
    expect(out.map(r => r.id)).toEqual([1, 2, 4]);
  });

  test('matches control types case-insensitively', async () => {
    // v2_topic casing is a convention, not a constraint — 'Open_Space' above.
    mockQuery.mockResolvedValue({ rows });
    const out = await getPrecinctControls('8.2.6', 'City of Parramatta', 'Parramatta', ['OPEN_SPACE']);
    expect(out.map(r => r.id)).toEqual([4]);
  });

  test('a null control_type is excluded rather than crashing', async () => {
    mockQuery.mockResolvedValue({ rows });
    const out = await getPrecinctControls('8.2.6', 'City of Parramatta', 'Parramatta', ['height']);
    expect(out.map(r => r.id)).toEqual([1]);
  });

  test('an unresolvable council still yields nothing', async () => {
    expect(await getPrecinctControls('Part 1', '', null, ['height'])).toEqual([]);
    expect(mockQuery).not.toHaveBeenCalled();
  });
});
