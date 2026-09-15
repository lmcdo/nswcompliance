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
 * such a form as not assessed, the same guard services/housing_sepp_eligibility.py
 * applies. Overrides are shown only for forms found eligible, as the brief does.
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
  row('secondary_dwelling', 'max_floor_area', '60'),
  row('dual_occupancy', 'min_lot_size', '400'),
  row('dual_occupancy', 'max_height', '9.5'),
  row('residential_flat_r1r2', 'min_lot_size', '500', RESIDENTIAL, true),
  row('residential_flat_r1r2', 'max_height', '9.5', RESIDENTIAL, true),
  row('residential_flat_r3r4_inner', 'max_fsr', '2.2', MEDIUM_HIGH, true),
];

type Result = { developmentType: string; isEligible: boolean; assessmentStatus: string; eligibilityReason: string };

async function check(body: Record<string, unknown>) {
  mockQuery.mockResolvedValue({ rows: ROWS });
  const res = await POST(new NextRequest('http://localhost/api/housing-sepp/eligibility', {
    method: 'POST',
    body: JSON.stringify(body),
  }));
  const json = await res.json();
  const results: Result[] = json.data.eligibleTypes;
  return { json, form: (t: string) => results.find(r => r.developmentType === t) };
}

describe('housing-sepp eligibility — a form with no lot standard in the dataset', () => {
  beforeEach(() => mockQuery.mockReset());

  it('fixture sanity: the route treats R2 and R3 as residential', () => {
    expect(RESIDENTIAL).toEqual(expect.arrayContaining(['R2', 'R3']));
    expect(MEDIUM_HIGH.length).toBe(2);
  });

  it('is not reported eligible, and says it was not assessed', async () => {
    const { form } = await check({ zoneCode: 'R2', lotSize: 600, lotWidth: 15, isLMRArea: true });
    const ilu = form('independent_living_unit');
    expect(ilu).toBeDefined();
    expect(ilu!.isEligible).toBe(false);
    expect(ilu!.assessmentStatus).toBe('not_assessed');
    expect(ilu!.eligibilityReason).toMatch(/not in the dataset/);
  });

  it('does not catch the base forms, which are assessed without a lot standard', async () => {
    const { form } = await check({ zoneCode: 'R2', lotSize: 600, lotWidth: 15, isLMRArea: true });
    expect(form('secondary_dwelling')!.isEligible).toBe(true);
  });

  it('still decides a form whose lot standard is in the dataset', async () => {
    expect((await check({ zoneCode: 'R2', lotSize: 600, lotWidth: 15, isLMRArea: true })).form('dual_occupancy')!.isEligible).toBe(true);
    const small = (await check({ zoneCode: 'R2', lotSize: 300, lotWidth: 15, isLMRArea: true })).form('dual_occupancy')!;
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
    const { json } = await check({ zoneCode: 'R2', lotSize: 600, lotWidth: 15, isLMRArea: false, lepHeight: 8.5 });
    const types = (json.data.overrides ?? []).map((o: { developmentType: string }) => o.developmentType);
    expect(types).toContain('dual_occupancy');
    expect(types).not.toContain('independent_living_unit');
    // Outside a reform area the low-rise apartment form is ineligible, so its height is no override.
    expect(types).not.toContain('residential_flat_r1r2');
  });
});
