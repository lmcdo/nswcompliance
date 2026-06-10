/**
 * Prospector filter logic tests — URL parsing/serialisation and API body builders.
 */
import {
  DEFAULT_FILTERS,
  PAGE_SIZE,
  buildSearchBody,
  buildSummaryBody,
  parseFilters,
  serializeFilters,
} from '@/lib/prospector/filter-params';

describe('parseFilters', () => {
  test('empty params return defaults', () => {
    expect(parseFilters(new URLSearchParams())).toEqual(DEFAULT_FILTERS);
  });

  test('parses all params', () => {
    const params = new URLSearchParams(
      'lga=INNER WEST&zones=R2,R3&min_area=300&max_area=900&min_gfa=200&max_gfa=600' +
        '&min_dwellings=3&heritage=no&flood=yes&bushfire=no&min_confidence=medium' +
        '&binding=lep_fsr,lep_height&order_by=lot_area_m2&order_dir=asc&page=4',
    );
    expect(parseFilters(params)).toEqual({
      lga_name: 'INNER WEST',
      zone_codes: ['R2', 'R3'],
      min_area_m2: 300,
      max_area_m2: 900,
      min_gfa_m2: 200,
      max_gfa_m2: 600,
      min_dwellings: 3,
      heritage: 'no',
      flood_prone: 'yes',
      bushfire_prone: 'no',
      min_confidence: 'medium',
      binding_constraint: ['lep_fsr', 'lep_height'],
      order_by: 'lot_area_m2',
      order_dir: 'asc',
      page: 4,
    });
  });

  test('invalid numeric values fall back to null', () => {
    const params = new URLSearchParams('min_area=abc&max_area=-50&min_gfa=0&min_dwellings=NaN');
    const filters = parseFilters(params);
    expect(filters.min_area_m2).toBeNull();
    expect(filters.max_area_m2).toBeNull();
    expect(filters.min_gfa_m2).toBeNull();
    expect(filters.min_dwellings).toBeNull();
  });

  test('fractional min_dwellings is floored to an integer', () => {
    expect(parseFilters(new URLSearchParams('min_dwellings=2.7')).min_dwellings).toBe(2);
  });

  test('invalid order_by falls back to default', () => {
    const filters = parseFilters(new URLSearchParams('order_by=evil_column'));
    expect(filters.order_by).toBe('ca_realistic_gfa_m2');
  });

  test('invalid order_dir falls back to desc', () => {
    expect(parseFilters(new URLSearchParams('order_dir=sideways')).order_dir).toBe('desc');
  });

  test('invalid tri-state values fall back to any', () => {
    const filters = parseFilters(new URLSearchParams('heritage=maybe&flood=1&bushfire=true'));
    expect(filters.heritage).toBe('any');
    expect(filters.flood_prone).toBe('any');
    expect(filters.bushfire_prone).toBe('any');
  });

  test('invalid confidence falls back to any', () => {
    expect(parseFilters(new URLSearchParams('min_confidence=ultra')).min_confidence).toBe('any');
  });

  test('invalid page falls back to 1', () => {
    expect(parseFilters(new URLSearchParams('page=0')).page).toBe(1);
    expect(parseFilters(new URLSearchParams('page=-3')).page).toBe(1);
    expect(parseFilters(new URLSearchParams('page=xyz')).page).toBe(1);
  });

  test('empty list entries are dropped', () => {
    expect(parseFilters(new URLSearchParams('zones=R2,,R3, ')).zone_codes).toEqual(['R2', 'R3']);
  });
});

describe('serializeFilters', () => {
  test('defaults serialise to empty params', () => {
    expect(serializeFilters(DEFAULT_FILTERS).toString()).toBe('');
  });

  test('round-trips through parseFilters', () => {
    const filters = {
      ...DEFAULT_FILTERS,
      zone_codes: ['R3', 'MU1'],
      min_area_m2: 450,
      heritage: 'no' as const,
      min_confidence: 'high' as const,
      binding_constraint: ['lep_fsr'],
      order_by: 'lep_height_m' as const,
      order_dir: 'asc' as const,
      page: 7,
    };
    expect(parseFilters(serializeFilters(filters))).toEqual(filters);
  });

  test('page 1 is omitted from URL', () => {
    const params = serializeFilters({ ...DEFAULT_FILTERS, page: 1 });
    expect(params.get('page')).toBeNull();
  });

  test('page beyond 1 is included', () => {
    const params = serializeFilters({ ...DEFAULT_FILTERS, page: 3 });
    expect(params.get('page')).toBe('3');
  });
});

describe('buildSearchBody', () => {
  test('defaults produce lga + pagination + ordering only', () => {
    expect(buildSearchBody(DEFAULT_FILTERS)).toEqual({
      lga_name: 'INNER WEST',
      limit: PAGE_SIZE,
      offset: 0,
      order_by: 'ca_realistic_gfa_m2',
      order_dir: 'desc',
    });
  });

  test('offset is computed from 1-based page', () => {
    expect(buildSearchBody({ ...DEFAULT_FILTERS, page: 3 }).offset).toBe(100);
  });

  test('tri-state yes/no map to booleans, any is omitted', () => {
    const body = buildSearchBody({
      ...DEFAULT_FILTERS,
      heritage: 'yes',
      flood_prone: 'no',
      bushfire_prone: 'any',
    });
    expect(body.heritage).toBe(true);
    expect(body.flood_prone).toBe(false);
    expect('bushfire_prone' in body).toBe(false);
  });

  test('any confidence is omitted, explicit level is included', () => {
    expect('min_confidence' in buildSearchBody(DEFAULT_FILTERS)).toBe(false);
    expect(
      buildSearchBody({ ...DEFAULT_FILTERS, min_confidence: 'medium' }).min_confidence,
    ).toBe('medium');
  });

  test('empty arrays are omitted, populated arrays included', () => {
    expect('zone_codes' in buildSearchBody(DEFAULT_FILTERS)).toBe(false);
    expect(buildSearchBody({ ...DEFAULT_FILTERS, zone_codes: ['R2'] }).zone_codes).toEqual([
      'R2',
    ]);
    expect(
      buildSearchBody({ ...DEFAULT_FILTERS, binding_constraint: ['lep_fsr'] }).binding_constraint,
    ).toEqual(['lep_fsr']);
  });

  test('numeric range filters pass through', () => {
    const body = buildSearchBody({
      ...DEFAULT_FILTERS,
      min_area_m2: 300,
      max_area_m2: 900,
      min_gfa_m2: 150,
      max_gfa_m2: 500,
      min_dwellings: 2,
    });
    expect(body.min_area_m2).toBe(300);
    expect(body.max_area_m2).toBe(900);
    expect(body.min_gfa_m2).toBe(150);
    expect(body.max_gfa_m2).toBe(500);
    expect(body.min_dwellings).toBe(2);
  });
});

describe('buildSummaryBody', () => {
  test('contains no pagination or ordering fields', () => {
    const body = buildSummaryBody({ ...DEFAULT_FILTERS, page: 5 });
    expect('limit' in body).toBe(false);
    expect('offset' in body).toBe(false);
    expect('order_by' in body).toBe(false);
    expect('order_dir' in body).toBe(false);
    expect(body.lga_name).toBe('INNER WEST');
  });

  test('carries filter fields', () => {
    const body = buildSummaryBody({ ...DEFAULT_FILTERS, zone_codes: ['R3'], heritage: 'yes' });
    expect(body.zone_codes).toEqual(['R3']);
    expect(body.heritage).toBe(true);
  });
});
