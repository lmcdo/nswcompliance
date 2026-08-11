import { toLgaSlug, toLgaSlugs } from '@/lib/lga-slug';

/**
 * The mapping this covers used to exist twice, privately, inside route files.
 * It is the join key between a Planning-Portal display name and
 * `dcp_setback_controls.lga`; if it silently returns the wrong slug the query
 * returns zero rows, and zero rows reads as "this council has no parking rate"
 * rather than "we asked the wrong question".
 */
describe('toLgaSlug', () => {
  it('lower-cases and underscores a plain display name', () => {
    expect(toLgaSlug('Waverley')).toBe('waverley');
    expect(toLgaSlug('Georges River')).toBe('georges_river');
  });

  it('collapses hyphens, which the portal uses and the slug does not', () => {
    expect(toLgaSlug('Canterbury-Bankstown')).toBe('canterbury_bankstown');
    expect(toLgaSlug('Ku-ring-gai')).toBe('ku_ring_gai');
  });

  it.each([
    ['Sydney', 'city_of_sydney'],
    ['City of Parramatta', 'parramatta'],
    ['The Hills Shire', 'the_hills'],
    ['City of Canada Bay', 'canada_bay'],
    ['City of Ryde', 'ryde'],
    ['Strathfield Municipal', 'strathfield'],
  ])('maps the genuine rename %s -> %s', (display, slug) => {
    expect(toLgaSlug(display)).toBe(slug);
  });

  it('is idempotent, so an already-slugged value survives', () => {
    expect(toLgaSlug('canterbury_bankstown')).toBe('canterbury_bankstown');
    expect(toLgaSlug(toLgaSlug('Canterbury-Bankstown'))).toBe('canterbury_bankstown');
  });

  it('returns null rather than an empty string for absent input', () => {
    // An empty string would become `WHERE lga = ''` — zero rows, indistinguishable
    // from a council that genuinely has no controls. null forces the caller to skip.
    expect(toLgaSlug(undefined)).toBeNull();
    expect(toLgaSlug(null)).toBeNull();
    expect(toLgaSlug('')).toBeNull();
    expect(toLgaSlug('   ')).toBeNull();
    expect(toLgaSlug('!!!')).toBeNull();
  });

  it('toLgaSlugs gives an empty array, never [null], for absent input', () => {
    expect(toLgaSlugs('Waverley')).toEqual(['waverley']);
    expect(toLgaSlugs('')).toEqual([]);
  });
});
