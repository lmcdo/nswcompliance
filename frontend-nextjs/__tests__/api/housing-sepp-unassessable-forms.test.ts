/**
 * @jest-environment node
 */
/**
 * A housing form whose lot standard is not in the dataset is never reported eligible.
 *
 * The route marked every form "eligible" once its zone matched and no lot-size or
 * lot-width row stopped it. A form with no lot rows at all therefore passed by
 * default: until 2026-09-15 that was `manor_house`, whose four rows were section 108
 * standards for independent living units, so a user was told a Manor House was
 * eligible, with numbers that were never manor house rules, plus a "SEPP allows
 * 9.5m vs LEP" override. The rows now carry their real label and the route treats
 * such a form as not assessed. No form is exempt (cross-review: exempting dual
 * occupancy let a missing lot row pass silently); only the station-distance apartment
 * forms, which have no lot row, keep their own check. Overrides are shown only for
 * forms found eligible, as the brief does.
 *
 * Fixture values are test inputs, not the stored standards.
 */
import { NextRequest } from 'next/server';
import { HOUSING_SEPP_LMR } from '@/lib/regulatory-constants';

const mockQuery = jest.fn();
jest.mock('@/lib/db', () => ({
  getPool: () => ({ query: (...args: unknown[]) => mockQuery(...args) }),
}));

import { POST } from '@/app/api/housing-sepp/eligibility/route';

// The route's own residential zone set, not a new literal list.
const RESIDENTIAL = [...HOUSING_SEPP_LMR.ELIGIBLE_ZONES] as string[];
const MEDIUM_HIGH = RESIDENTIAL.filter(z => /^R[34]$/.test(z));

function row(developmentType: string, standardType: string, value: string, zones = RESIDENTIAL, lmr = false) {
  return {
    development_type: developmentType,
    standard_type: standardType,
    numeric_value: value,
    unit: 'm',
    applicable_zones: zones,
    requires_lmr_area: lmr,
    source_clause: 'test',
    source_provision_id: null,
    source_document: 'test',
    legislation_url: null,
    effective_date: null,
    pdf_page: null,
    r2_pdf_url: null,
  };
}

const ROWS = [
  row('independent_living_unit', 'max_height', '9.5'),
  row('secondary_dwelling', 'min_lot_size', '450'),
  row('secondary_dwelling', 'max_floor_area', '60'),
  row('dual_occupancy', 'min_lot_size', '400'),
  row('dual_occupancy', 'max_height', '9.5'),
  row('residential_flat_r1r2', 'min_lot_size', '500', RESIDENTIAL, true),
  row('residential_flat_r1r2', 'max_height', '9.5', RESIDENTIAL, true),
  row('residential_flat_r3r4_inner', 'max_fsr', '2.2', MEDIUM_HIGH, true),
];

type Result = { developmentType: string; isEligible: boolean; assessmentStatus: string; eligibilityReason: string };

async function check(body: Record<string, unknown>, rows = ROWS) {
  mockQuery.mockResolvedValue({ rows });
  const res = await POST(new NextRequest('http://localhost/api/housing-sepp/eligibility', {
    method: 'POST',
    body: JSON.stringify(body),
  }));
  const json = await res.json();
  const results: Result[] = json.data.eligibleTypes;
  return { json, form: (t: string) => results.find(r => r.developmentType === t) };
}

const R2_LOT = { zoneCode: 'R2', lotSize: 600, lotWidth: 15, isLMRArea: true };

describe('housing-sepp eligibility — a form with no lot standard in the dataset', () => {
  beforeEach(() => mockQuery.mockReset());

  it('fixture sanity: the route treats R2 and R3 as residential', () => {
    expect(RESIDENTIAL).toEqual(expect.arrayContaining(['R2', 'R3']));
    expect(MEDIUM_HIGH.length).toBe(2);
  });

  it('is not reported eligible, and says it was not assessed', async () => {
    const ilu = (await check(R2_LOT)).form('independent_living_unit');
    expect(ilu).toBeDefined();
    expect(ilu!.isEligible).toBe(false);
    expect(ilu!.assessmentStatus).toBe('not_assessed');
    expect(ilu!.eligibilityReason).toMatch(/not in the dataset/);
  });

  it('exempts no form: dual occupancy whose lot row is missing is not assessed', async () => {
    const withoutDualLot = ROWS.filter(r => !(r.development_type === 'dual_occupancy' && r.standard_type === 'min_lot_size'));
    const dual = (await check(R2_LOT, withoutDualLot)).form('dual_occupancy')!;
    expect(dual.isEligible).toBe(false);
    expect(dual.assessmentStatus).toBe('not_assessed');
  });

  it('still decides a form whose lot standard is in the dataset', async () => {
    const { form } = await check(R2_LOT);
    expect(form('dual_occupancy')!.isEligible).toBe(true);
    // secondary_dwelling is not decided by a lot row at all -- see the
    // "tested per approval path" block below.
    const small = (await check({ ...R2_LOT, lotSize: 300 })).form('dual_occupancy')!;
    expect(small.isEligible).toBe(false);
    expect(small.eligibilityReason).toMatch(/below minimum/);
  });

  it('leaves the station-distance apartment forms to their own check', async () => {
    const { form } = await check({ zoneCode: 'R3', lotSize: 600, lotWidth: 15, isLMRArea: true, stationDistance: 300 });
    expect(form('residential_flat_r3r4_inner')!.isEligible).toBe(true);
  });
});

describe('housing-sepp eligibility — SEPP-over-LEP overrides', () => {
  beforeEach(() => mockQuery.mockReset());

  it('are listed only for forms found eligible', async () => {
    const { json } = await check({ ...R2_LOT, isLMRArea: false, lepHeight: 8.5 });
    const types = (json.data.overrides ?? []).map((o: { developmentType: string }) => o.developmentType);
    expect(types).toContain('dual_occupancy');
    expect(types).not.toContain('independent_living_unit');
    // Outside a reform area the low-rise apartment form is ineligible, so its height is no override.
    expect(types).not.toContain('residential_flat_r1r2');
  });
});

describe('housing-sepp eligibility — granny flats are tested per approval path', () => {
  beforeEach(() => mockQuery.mockReset());

  // The fixture still carries a 450 m2 secondary_dwelling min_lot_size row, as the
  // table does until migration 089 retires ids 34/44.
  it('a small lot is not declared below a 450 m2 minimum', async () => {
    const { form } = await check({ zoneCode: 'R2', lotSize: 300, lotWidth: 8, isLMRArea: true });
    const sd = form('secondary_dwelling')!;
    expect(sd.assessmentStatus).toBe('not_assessed');
    expect(sd.eligibilityReason).not.toMatch(/below minimum/);
    expect(sd.eligibilityReason).toMatch(/No single minimum lot size applies to a granny flat/);
  });

  it('the old 450 m2 / 12 m rows are not shown as its standards', async () => {
    const rows = [...ROWS, row('secondary_dwelling', 'min_lot_width', '12')];
    const { json } = await check(R2_LOT, rows);
    const sd = json.data.eligibleTypes.find((r: { developmentType: string }) => r.developmentType === 'secondary_dwelling');
    const types = sd.standards.map((s: { standardType: string }) => s.standardType);
    expect(types).not.toContain('min_lot_size');
    expect(types).not.toContain('min_lot_width');
    expect(types).toContain('max_floor_area');
  });

  it('other forms keep their lot-size gate', async () => {
    const { form } = await check({ zoneCode: 'R2', lotSize: 300, lotWidth: 15, isLMRArea: true });
    expect(form('dual_occupancy')!.assessmentStatus).toBe('ineligible');
  });
});
