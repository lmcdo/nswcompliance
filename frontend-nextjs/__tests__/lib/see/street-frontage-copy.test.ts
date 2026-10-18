import { buildPropertyContext } from '@/lib/see/propertyContext';
import { buildSEEData } from '@/lib/see/section-aggregation';

const measured = {
  status: 'measured' as const,
  unnamedRoadEdge_m: 0,
  roads: [{ road: 'BERRIGAN ST', frontage_m: 13.34, minFrontHalf_m: 13, maxAll_m: 22, depth_m: 40 }],
};
const base = { lotDimensions: { area: 600, frontage: 22.4, depth: 30 } };
const heritage = { in_hca: false } as never;
const ctx = (cornerLot?: unknown) =>
  buildPropertyContext({ ...base, cornerLot }, null, '6 Berrigan St', 'R2', 'x', heritage);

describe('SEE property context street frontage', () => {
  it('carries the measured street frontage text and keeps the rectangle side separate', () => {
    const c = ctx({ streetFrontage: measured });
    expect(c.lot_dimensions?.street_frontage_text).toBe('13.3 m along Berrigan St');
    expect(c.lot_dimensions?.frontage).toBe(22.4);
  });
  it('is null when not measured', () => {
    expect(ctx().lot_dimensions?.street_frontage_text).toBeNull();
  });
});

describe('SEE site suitability sentence', () => {
  const text = (c: ReturnType<typeof ctx>) =>
    buildSEEData({ property: c, annotated_provisions: [], all_provisions: [], generated_date: '2026-01-01' } as never)
      .siteSuitabilityText;

  it('prints measured frontage and never labels the rectangle side as frontage', () => {
    const t = text(ctx({ streetFrontage: measured }));
    expect(t).toContain('street frontage of 13.3 m along Berrigan St');
    expect(t).toContain('lot width (shorter side) of 22.4 m');
    expect(t).not.toContain('22.4 m frontage');
  });
  it('says not measured when null', () => {
    const t = text(ctx());
    expect(t).toContain('street frontage that has not been measured');
    expect(t).not.toContain('22.4 m frontage');
  });
});
