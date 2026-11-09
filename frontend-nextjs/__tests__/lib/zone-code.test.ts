import { zoneCode } from '@/lib/zone-code';

describe('zoneCode', () => {
  it('reduces portal zone labels to the bare code', () => {
    expect(zoneCode('R2')).toBe('R2');
    expect(zoneCode('R2 Low Density Residential')).toBe('R2');
    expect(zoneCode('R2: Low Density Residential')).toBe('R2');
    expect(zoneCode('  ru1 primary production ')).toBe('RU1');
    expect(zoneCode('E4 General Industrial')).toBe('E4');
    expect(zoneCode('B4')).toBe('B4');
  });

  it('returns null, meaning no filter, when no code can be read', () => {
    expect(zoneCode(undefined)).toBeNull();
    expect(zoneCode(null)).toBeNull();
    expect(zoneCode('')).toBeNull();
    expect(zoneCode('   ')).toBeNull();
    expect(zoneCode('Low Density Residential')).toBeNull();
    expect(zoneCode('Zone R2')).toBeNull(); // does not guess a code from the middle of a label
  });
});
