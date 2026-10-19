import { councilDisplayName } from '@/lib/council-display-name';

describe('councilDisplayName', () => {
  it.each([
    ['THE HILLS SHIRE', 'The Hills Shire'],
    ['CITY OF PARRAMATTA', 'City of Parramatta'],
    ['CANTERBURY-BANKSTOWN', 'Canterbury-Bankstown'],
    ['KU-RING-GAI', 'Ku-Ring-Gai'],
    ['INNER WEST', 'Inner West'],
  ])('%s -> %s', (raw, shown) => {
    expect(councilDisplayName(raw)).toBe(shown);
  });
  it('blank is null, never an empty name in a sentence', () => {
    expect(councilDisplayName('')).toBeNull();
    expect(councilDisplayName(null)).toBeNull();
  });
});
