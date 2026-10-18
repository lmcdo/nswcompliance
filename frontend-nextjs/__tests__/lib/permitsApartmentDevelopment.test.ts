import { permitsApartmentDevelopment } from '@/lib/regulatory-constants';

// Gate behind the Apartment Design Guide panel. Apartments (residential flat
// buildings) are permissible in R4 + business/mixed-use zones under the Standard
// Instrument anywhere, but in R1-R3 only inside a Low and Mid-Rise housing area as
// answered by the planning map (true / false / null when the map did not answer).

describe('permitsApartmentDevelopment', () => {
  it('qualifies R1-R3 only when the map says the lot is in a Low and Mid-Rise housing area', () => {
    expect(permitsApartmentDevelopment('R3: Medium Density Residential', true)).toBe(true);
    expect(permitsApartmentDevelopment('R2', true)).toBe(true);
    expect(permitsApartmentDevelopment('R1', true)).toBe(true);
  });

  it('does not qualify R1-R3 outside a Low and Mid-Rise housing area', () => {
    expect(permitsApartmentDevelopment('R3: Medium Density Residential', false)).toBe(false);
    expect(permitsApartmentDevelopment('R2: Low Density Residential', false)).toBe(false);
  });

  it('does not qualify R1-R3 when the map did not answer (null)', () => {
    expect(permitsApartmentDevelopment('R3', null)).toBe(false);
    expect(permitsApartmentDevelopment('R2', null)).toBe(false);
  });

  it('qualifies R4 regardless of the area answer', () => {
    expect(permitsApartmentDevelopment('R4: High Density Residential', false)).toBe(true);
    expect(permitsApartmentDevelopment('R4', null)).toBe(true);
  });

  it('qualifies business and mixed-use zones regardless of the area answer', () => {
    expect(permitsApartmentDevelopment('MU1', null)).toBe(true);
    expect(permitsApartmentDevelopment('B4: Mixed Use', false)).toBe(true);
  });

  it('does not qualify rural or large-lot residential zones, even inside an area', () => {
    expect(permitsApartmentDevelopment('RU1: Primary Production', true)).toBe(false);
    expect(permitsApartmentDevelopment('R5: Large Lot Residential', true)).toBe(false);
  });

  it('does not qualify an empty zone', () => {
    expect(permitsApartmentDevelopment('', true)).toBe(false);
  });
});
