import { floodLevels } from '@/lib/flood/flood-levels';

describe('floodLevels lists every flood level, most frequent first', () => {
  it('puts the 1% AEP before the 0.2% AEP (text order put 0.2% first)', () => {
    expect(floodLevels(['0.2%AEP', '1%AEP'])).toBe('1% AEP, 0.2% AEP');
  });
  it('puts PMF after every AEP', () => {
    expect(floodLevels(['PMF', '5.0%AEP', '20.0%AEP'])).toBe('20% AEP, 5% AEP, PMF');
  });
  it('treats 1%AEP and 1.0%AEP as one level', () => {
    expect(floodLevels(['1%AEP', '1.0%AEP'])).toBe('1% AEP');
  });
  it('keeps a value it does not know, after the known ones', () => {
    expect(floodLevels(['Flood Planning Area', 'PMF', '1%AEP'])).toBe('1% AEP, PMF, Flood Planning Area');
  });
  it('gives nothing for no values, so the badge falls back to Yes', () => {
    expect(floodLevels([])).toBeUndefined();
    expect(floodLevels([null, ' '])).toBeUndefined();
  });
});
