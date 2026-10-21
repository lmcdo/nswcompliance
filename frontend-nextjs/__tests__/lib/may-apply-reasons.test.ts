import { MAY_APPLY_REASONS, reasonText, normaliseSuburb, suburbFromAddress } from '@/lib/may-apply-reasons';

describe('may-apply-reasons', () => {
  it('has text for the seven codes and null for unknown', () => {
    expect(Object.keys(MAY_APPLY_REASONS).sort()).toEqual(
      ['DRAWING_NOT_MATCHED', 'LOT_LIST_UNPROVEN', 'MAP_NOT_PUBLISHED', 'NOT_YET_MAPPED', 'PART_MAPPED', 'SOUND_AREA_MAP', 'WORDS_ONLY'],
    );
    expect(reasonText('WORDS_ONLY')).toBe('The plan describes this area in words only, with no map.');
    expect(reasonText('NOPE')).toBeNull();
    expect(reasonText('toString')).toBeNull();
    expect(reasonText(undefined)).toBeNull();
  });

  it('normaliseSuburb uppercases, collapses spaces, strips NSW and postcode', () => {
    expect(normaliseSuburb('  winston   hills NSW 2153 ')).toBe('WINSTON HILLS');
    expect(normaliseSuburb('Dee Why, NSW, 2099')).toBe('DEE WHY');
    expect(normaliseSuburb(null)).toBe('');
  });

  it('suburbFromAddress reads comma and no-comma forms', () => {
    expect(suburbFromAddress('12 Smith Street, Winston Hills NSW 2153')).toBe('WINSTON HILLS');
    expect(suburbFromAddress('12 Smith St Winston Hills NSW 2153')).toBe('WINSTON HILLS');
    // Sol 2026-10-20: a unit address with commas, and a multi-word street name without commas
    expect(suburbFromAddress('Unit 3, 12 Smith Street, Winston Hills NSW 2153')).toBe('WINSTON HILLS');
    expect(suburbFromAddress('12 Old Pittwater Road Brookvale NSW 2100')).toBe('BROOKVALE');
    // Sol 2026-10-21: a comma after the unit only; the last part still holds the street
    expect(suburbFromAddress('Unit 3, 12 Smith Street Winston Hills NSW 2153')).toBe('WINSTON HILLS');
    expect(suburbFromAddress('G03/12 Smith Street Winston Hills NSW 2153')).toBe('WINSTON HILLS');
    expect(suburbFromAddress('G03, 12 Smith Street Winston Hills NSW 2153')).toBe('WINSTON HILLS');
    expect(suburbFromAddress('12 Smith Street, NSW 2153')).toBe('');
    expect(suburbFromAddress('3/12 Smith Street, Summer Hill')).toBe('SUMMER HILL');
    expect(suburbFromAddress('')).toBe('');
    expect(suburbFromAddress(undefined)).toBe('');
  });
});
