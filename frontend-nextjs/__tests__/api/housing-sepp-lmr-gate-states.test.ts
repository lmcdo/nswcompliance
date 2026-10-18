/**
 * @jest-environment node
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
  row('dual_occupancy', 'min_lot_size', '400'),
  row('residential_flat_r1r2', 'min_lot_size', '500', RESIDENTIAL, true),
  row('residential_flat_r1r2', 'max_height', '9.5', RESIDENTIAL, true),
];

async function formFor(body: Record<string, unknown>, type: string) {
  mockQuery.mockResolvedValue({ rows: ROWS });
  const res = await POST(new NextRequest('http://localhost/api/housing-sepp/eligibility', {
    method: 'POST',
    body: JSON.stringify(body),
  }));
  expect(res.status).toBe(200);
  const json = await res.json();
  return json.data.eligibleTypes.find((r: { developmentType: string }) => r.developmentType === type);
}

const LOT = { zoneCode: 'R2', lotSize: 800, lotWidth: 20 };

describe('housing-sepp eligibility - Low and Mid-Rise area answer', () => {
  beforeEach(() => mockQuery.mockReset());

  it('false: a form that requires the area is ineligible, with the map-based reason', async () => {
    const f = await formFor({ ...LOT, isLMRArea: false }, 'residential_flat_r1r2');
    expect(f.isEligible).toBe(false);
    expect(f.assessmentStatus).toBe('ineligible');
    expect(f.eligibilityReason).toBe(
      'Not in a Low and Mid-Rise housing area (no Town Centres Map catchment or TOD catchment at this lot)',
    );
  });

  it('null: a form that requires the area is not assessed, never ineligible', async () => {
    const f = await formFor({ ...LOT, isLMRArea: null }, 'residential_flat_r1r2');
    expect(f.isEligible).toBe(false);
    expect(f.assessmentStatus).toBe('not_assessed');
    expect(f.eligibilityReason).toBe('Whether this lot is in a Low and Mid-Rise housing area could not be checked');
  });

  it('absent: treated the same as null', async () => {
    const f = await formFor(LOT, 'residential_flat_r1r2');
    expect(f.assessmentStatus).toBe('not_assessed');
  });

  it('true: the form passes the area gate and is decided on its own standards', async () => {
    const f = await formFor({ ...LOT, isLMRArea: true }, 'residential_flat_r1r2');
    expect(f.assessmentStatus).not.toBe('not_assessed');
    expect(f.eligibilityReason).not.toMatch(/Low and Mid-Rise housing area/);
  });

  it('a form that does not require the area is decided the same for false and null', async () => {
    const f = await formFor({ ...LOT, isLMRArea: null }, 'dual_occupancy');
    expect(f.isEligible).toBe(true);
  });
});
