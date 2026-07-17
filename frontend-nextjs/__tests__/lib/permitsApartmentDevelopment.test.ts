import { permitsApartmentDevelopment } from '@/lib/regulatory-constants';

// Gate behind the Apartment Design Guide panel. Apartments (residential flat
// buildings) are permissible in R4 + business/mixed-use zones under the Standard
// Instrument anywhere, but in R1–R3 only where the Stage-2 LMR mid-rise reforms
// reach the LGA (a designated region). Regional R2/R3 lots must NOT qualify.

describe('permitsApartmentDevelopment', () => {
  it('does NOT qualify a regional R3 lot outside a Stage-2 region (the 38 Park Rd Bowral bug)', () => {
    expect(permitsApartmentDevelopment('R3: Medium Density Residential', 'WINGECARRIBEE')).toBe(false);
  });

  it('qualifies a metro R3 lot inside a Stage-2 designated region', () => {
    expect(permitsApartmentDevelopment('R3: Medium Density Residential', 'Inner West')).toBe(true);
  });

  it('does NOT qualify R2 outside a Stage-2 region — Stage-1 is dual-occ only, not apartments', () => {
    expect(permitsApartmentDevelopment('R2: Low Density Residential', 'Wingecarribee')).toBe(false);
  });

  it('qualifies R2 inside a Stage-2 region where mid-rise reforms reach it', () => {
    expect(permitsApartmentDevelopment('R2', 'City of Sydney')).toBe(true);
  });

  it('qualifies R4 anywhere — high density permits RFBs under the Standard Instrument', () => {
    expect(permitsApartmentDevelopment('R4: High Density Residential', 'Wingecarribee')).toBe(true);
  });

  it('qualifies mixed-use / business zones anywhere (shop-top housing under the SI)', () => {
    expect(permitsApartmentDevelopment('MU1', 'Wingecarribee')).toBe(true);
    expect(permitsApartmentDevelopment('B4: Mixed Use', 'Dubbo Regional')).toBe(true);
  });

  it('does NOT qualify non-apartment zones regardless of region', () => {
    expect(permitsApartmentDevelopment('RU1: Primary Production', 'City of Sydney')).toBe(false);
    expect(permitsApartmentDevelopment('R5: Large Lot Residential', 'City of Sydney')).toBe(false);
  });

  it('returns false for empty or missing zone/lga input', () => {
    expect(permitsApartmentDevelopment('', '')).toBe(false);
    expect(permitsApartmentDevelopment('R3', '')).toBe(false);
  });
});
