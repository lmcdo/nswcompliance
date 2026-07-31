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

import {
  getFormerCouncilFromPrecinctId,
  normalizeFormerCouncil,
  resolveFormerCouncil,
} from '@/lib/precinct-service';

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

describe('normalizeFormerCouncil', () => {
  test.each([
    // display names stored as-is pass through
    ['Waverley', 'Waverley'],
    ['Marrickville', 'Marrickville'],
    ['Parramatta', 'Parramatta'],
    ['Woollahra', 'Woollahra'],
    // slug form title-cases with lowercase joiners
    ['city_of_sydney', 'City of Sydney'],
    // hyphenated council preserved
    ['ku_ring_gai', 'Ku-ring-gai'],
  ])('%s -> %s', (raw, expected) => {
    expect(normalizeFormerCouncil(raw)).toBe(expected);
  });

  test('null, undefined and blank return null', () => {
    expect(normalizeFormerCouncil(null)).toBeNull();
    expect(normalizeFormerCouncil(undefined)).toBeNull();
    expect(normalizeFormerCouncil('   ')).toBeNull();
  });
});

describe('resolveFormerCouncil (column-first attribution)', () => {
  test('stored column wins over any pattern match', () => {
    // '9' is a Parramatta city-centre id; no pattern covers it — without the
    // column this would fall through to the 'Marrickville' default
    expect(resolveFormerCouncil('Parramatta', '9')).toBe('Parramatta');
    // even where a pattern WOULD match another council, the column wins
    expect(resolveFormerCouncil('Parramatta', 'E1')).toBe('Parramatta');
  });

  test('dotted Parramatta HCA ids attribute via column, not Marrickville default', () => {
    expect(resolveFormerCouncil('Parramatta', '7.10.1')).toBe('Parramatta');
  });

  test('name-keyed Woollahra ids attribute via column', () => {
    expect(resolveFormerCouncil('Woollahra', 'Paddington HCA')).toBe('Woollahra');
  });

  test('slug columns render as display names', () => {
    expect(resolveFormerCouncil('city_of_sydney', '6.3.3')).toBe('City of Sydney');
  });

  test('NULL column falls back to patterns (legacy Ku-ring-gai rows)', () => {
    expect(resolveFormerCouncil(null, '14B_T1')).toBe('Ku-ring-gai');
    expect(resolveFormerCouncil(undefined, 'E7')).toBe('Waverley');
  });
});
