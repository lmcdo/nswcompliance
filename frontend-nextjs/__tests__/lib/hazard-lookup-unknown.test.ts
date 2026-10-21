/**
 * A hazard map that fails or never answers must read as unknown — never "No".
 *
 * Measured 2026-10-21: one stalled NSW map call (bush fire stalled 40 s) held /api/property past
 * the 30 s gateway limit, and every stage-2 call ended `.catch(() => null)` with bushfireProne
 * defaulting to false, so a FAILED lookup was printed as "No". Fixtures only, no network.
 */
jest.mock('@/lib/road-classification-service', () => ({ getRoadClassifications: jest.fn().mockResolvedValue([]) }));
jest.mock('@/lib/flood/flood-map', () => ({
  floodMapStatus: jest.fn().mockResolvedValue({ floodProne: null, note: 'flood not known' }),
}));

import { NSWPlanningPortalService } from '@/lib/nsw-planning-portal';
import { MAP_LOOKUP_TIMEOUT_MS } from '@/lib/fetch-timeout';
import { autoPopulateFromConstraints } from '@/lib/see/intake';
import { ReportGenerator } from '@/lib/assessment/reports';
import { buildSiteFlags } from '@/lib/project-summary';
import { HAZARD_NOT_CHECKED } from '@/lib/hazard-unchecked';
import { describeBushfireWithoutCategory } from '@/app/reports/intelligence-brief/unavailable';

const BFPL = '/Fire/BFPL/';
const MINE = 'NSW_Administrative_Boundaries_Theme/FeatureServer/7';
const empty = () => Promise.resolve({ ok: true, json: async () => ({ features: [] }) } as Response);

function stubStage1() {
  jest.spyOn(NSWPlanningPortalService, 'searchProperty').mockResolvedValue({ propId: 1, address: '1 TEST ST TESTVILLE 2000', GURASID: 1 });
  jest.spyOn(NSWPlanningPortalService, 'getPlanningLayers').mockResolvedValue([]);
  jest.spyOn(NSWPlanningPortalService, 'getPropertyValuation').mockResolvedValue({
    address: '1 TEST ST', geometry: { x: 16830000, y: -4010000 },
  } as any);
  jest.spyOn(NSWPlanningPortalService, 'getLotGeometry').mockResolvedValue(null);
  jest.spyOn(NSWPlanningPortalService, 'getTODLayers').mockResolvedValue([]);
}

describe('stage-2 hazard lookups (lib/nsw-planning-portal.ts)', () => {
  const realFetch = global.fetch;
  beforeEach(() => {
    stubStage1();
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterEach(() => {
    global.fetch = realFetch;
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it('(1) a map call that never answers is cut off at the deadline and that hazard is null', async () => {
    jest.useFakeTimers();
    global.fetch = jest.fn((url: any) => (String(url).includes(BFPL) ? new Promise(() => {}) : empty())) as any;
    let settled = false;
    const pending = NSWPlanningPortalService.getPropertyComplianceData('1 Test St').then((r) => { settled = true; return r; });
    await jest.advanceTimersByTimeAsync(MAP_LOOKUP_TIMEOUT_MS + 50);
    expect(settled).toBe(true);
    const r = await pending;
    expect(r!.constraints.bushfireProne).toBeNull();
    expect(r!.constraints.uncheckedHazards).toContain('bushfire');
    // the maps that answered "no features" are a real No
    expect(r!.constraints.uncheckedHazards).not.toContain('mine_subsidence');
  });

  it('(2) a bush fire call that rejects gives bushfireProne null, never false; a real empty answer gives false', async () => {
    global.fetch = jest.fn((url: any) => {
      const u = String(url);
      if (u.includes(BFPL) || u.includes(MINE)) return Promise.reject(new Error('ECONNRESET'));
      return empty();
    }) as any;
    const failed = await NSWPlanningPortalService.getPropertyComplianceData('1 Test St');
    expect(failed!.constraints.bushfireProne).toBeNull();
    expect(failed!.constraints.uncheckedHazards).toEqual(expect.arrayContaining(['bushfire', 'mine_subsidence']));

    global.fetch = jest.fn(empty) as any;
    const clear = await NSWPlanningPortalService.getPropertyComplianceData('1 Test St');
    expect(clear!.constraints.bushfireProne).toBe(false);
    expect(clear!.constraints.uncheckedHazards).toEqual([]);
  });

  it('an ArcGIS error body (HTTP 200 with {error}) is unknown, not "no features"', async () => {
    global.fetch = jest.fn((url: any) => (String(url).includes(BFPL)
      ? Promise.resolve({ ok: true, json: async () => ({ error: { code: 500 } }) } as Response)
      : empty())) as any;
    const r = await NSWPlanningPortalService.getPropertyComplianceData('1 Test St');
    expect(r!.constraints.bushfireProne).toBeNull();
  });
});

describe('(4) SEE intake (lib/see/intake.ts)', () => {
  it('leaves bush fire, mine subsidence and contaminated land unanswered when the map did not answer', () => {
    const a = autoPopulateFromConstraints({
      bushfireProne: null,
      uncheckedHazards: ['bushfire', 'mine_subsidence', 'contaminated_land'],
    });
    expect(a.bushfire_prone).toBeUndefined();
    expect(a.mine_subsidence).toBeUndefined();
    expect(a.contaminated_land).toBeUndefined();
  });
  it('still answers no when the maps answered with nothing', () => {
    const a = autoPopulateFromConstraints({ bushfireProne: false, uncheckedHazards: [] });
    expect(a.bushfire_prone).toBe('no');
    expect(a.mine_subsidence).toBe('no');
  });
});

describe('(5) assessment findings (lib/assessment/reports.ts)', () => {
  const findings = (constraints: any) =>
    ReportGenerator.generateFindings({ property_data: { constraints } } as any, 's');
  it('writes "Not checked" for an unknown bush fire answer, not "No"', async () => {
    const f = await findings({ bushfireProne: null, uncheckedHazards: ['bushfire', 'mine_subsidence'] });
    expect(f.environmental_constraints.bushfire).toBe(HAZARD_NOT_CHECKED);
    expect(f.environmental_constraints.mineSubsidence).toBe(HAZARD_NOT_CHECKED);
  });
  it('writes "No" only when the map answered', async () => {
    const f = await findings({ bushfireProne: false, uncheckedHazards: [] });
    expect(f.environmental_constraints.bushfire).toBe('No');
  });
  it('reads the mine subsidence district the portal client actually sets', async () => {
    const f = await findings({ bushfireProne: false, mineSubsidence: { inDistrict: true, districtName: 'Swansea' } });
    expect(f.environmental_constraints.mineSubsidence).toBe('Yes - Swansea');
  });
});

describe('(6) project summary (lib/project-summary.ts)', () => {
  it('adds an unchecked note for an unknown bush fire answer', () => {
    const r = buildSiteFlags({ floodProne: false, bushfireProne: null });
    expect(r.unchecked.some((u) => /Bush fire: not checked/.test(u))).toBe(true);
    expect(r.flags.some((f) => f.key === 'bushfire')).toBe(false);
  });
  it('adds no note when the map answered No', () => {
    const r = buildSiteFlags({ floodProne: false, bushfireProne: false });
    expect(r.unchecked.some((u) => /Bush fire/.test(u))).toBe(false);
  });
});

describe('Site Report bushfire label (app/reports/intelligence-brief/unavailable.ts)', () => {
  it('a pre-screen whose RFS query failed is "Not checked", not "Not bushfire-prone"', () => {
    expect(describeBushfireWithoutCategory({ is_bushfire_prone: null, category: null })!.label).toBe('Not checked');
  });
  it('a prone lot without a category is not called "Not bushfire-prone"', () => {
    expect(describeBushfireWithoutCategory({ is_bushfire_prone: true, category: null })!.label).toBe('Bushfire-prone');
  });
  it('only an RFS No is "Not bushfire-prone"', () => {
    expect(describeBushfireWithoutCategory({ is_bushfire_prone: false, category: null })!.label).toBe('Not bushfire-prone');
  });
});
