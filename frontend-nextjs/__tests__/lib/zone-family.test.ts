/**
 * zoneFamily — Standard Instrument zone-family classifier.
 * The copy switch in SeppContextCard / ConstraintArithmeticCard hangs off this,
 * so a misclassification puts the wrong housing-pathway sentence on a lot.
 */

import { zoneFamily } from '@/lib/regulatory-constants';

describe('zoneFamily — residential', () => {
  it.each(['R1', 'R2', 'R3', 'R4', 'R5'])('classifies %s as residential', (z) => {
    expect(zoneFamily(z)).toBe('residential');
  });

  it('classifies RU5 Village as residential (dwelling-model zone)', () => {
    expect(zoneFamily('RU5')).toBe('residential');
  });

  it('accepts a labelled zone string', () => {
    expect(zoneFamily('R2 Low Density Residential')).toBe('residential');
  });
});

describe('zoneFamily — rural', () => {
  it.each(['RU1', 'RU2', 'RU3', 'RU4', 'RU6'])('classifies %s as rural', (z) => {
    expect(zoneFamily(z)).toBe('rural');
  });
});

describe('zoneFamily — conservation', () => {
  it.each(['C1', 'C2', 'C3', 'C4'])('classifies %s as conservation', (z) => {
    expect(zoneFamily(z)).toBe('conservation');
  });

  it('classifies the Kincumber zone label as conservation', () => {
    expect(zoneFamily('C4 Environmental Living')).toBe('conservation');
  });
});

describe('zoneFamily — centres/business/mixed use', () => {
  it.each(['E1', 'E2', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'MU1', 'MU'])(
    'classifies %s as centres',
    (z) => {
      expect(zoneFamily(z)).toBe('centres');
    },
  );
});

describe('zoneFamily — other (waterway, special purpose, recreation, industrial)', () => {
  it.each(['W1', 'W2', 'SP1', 'SP2', 'RE1', 'RE2', 'IN1', 'IN2', 'E3', 'E4', 'E5'])(
    'classifies %s as other',
    (z) => {
      expect(zoneFamily(z)).toBe('other');
    },
  );

  it('classifies an empty string as other', () => {
    expect(zoneFamily('')).toBe('other');
  });

  it('classifies an unknown code as other', () => {
    expect(zoneFamily('ZZ9')).toBe('other');
  });
});
