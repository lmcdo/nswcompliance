/**
 * Housing Code stored standards: strict band parser, selector, and the
 * route-level "no stored rows => every check Not checked" guarantee.
 * Fixture rows are copied verbatim from cdc_eligibility_standards
 * (code_name = 'housing_code', is_active) by a read-only query.
 */

/** @jest-environment node */

import fixture from '../../fixtures/cdc-housing-code-standards.json';
import {
  parseBand,
  parseRow,
  parseRows,
  select,
  citationOf,
  publicRow,
  type StandardRow,
} from '@/lib/cdc/housing-code-standards';
import { evaluateCdcChecks, shortfallText } from '@/lib/cdc/housing-code-checks';

const rows = fixture as unknown as StandardRow[];
const parsed = parseRows(rows);
const byId = (id: number) => parsed.find((p) => p.row.id === id)!;

function mk(over: Partial<StandardRow>): StandardRow {
  return {
    id: 9000, standard_type: 'min_front_setback_m', numeric_value: 1, conditionality: null,
    ref_number: '3.10(3)', source_quote: 'q', ...over,
  };
}

describe('fixture', () => {
  it('holds the 79 stored rows', () => {
    expect(rows).toHaveLength(79);
  });
});

describe('parseBand accepts clean band forms', () => {
  it.each([
    ['lot area >300-450 m2', 'lot_area', 300, true, 450],
    ['lot size 200-600 m2', 'lot_area', 200, false, 600],
    ['lot area >1,500 m2', 'lot_area', 1500, true, null],
    ['lot width at building line 6m-18m', 'lot_width', 6, false, 18],
    ['lot width at building line >24m', 'lot_width', 24, true, null],
    ['building height 0-4.5 m', 'building_height', 0, false, 4.5],
  ])('%s', (text, dimension, lower, exclusive, upper) => {
    const r = parseBand(text);
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.ranges).toEqual([{ dimension, lower, lowerExclusive: exclusive, upper }]);
    }
  });

  it('parses ";"-joined clauses', () => {
    const r = parseBand('lot width at building line >10m-18m; building height 0m-4.5m');
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.ranges.map((x) => x.dimension)).toEqual(['lot_width', 'building_height']);
  });
});

describe('parseBand rejects', () => {
  it.each([
    'bands in row 37063, values here',
    'values only; bands in other rows, not paired',
    'bands row 37044, values row 37045; not paired in storage',
    'detached garage/carport from primary road (value-only row; header in 37206)',
    'corner lot dwelling; lot size >600-1,500 m2',
    'battle-axe lot: rear boundary of lot in front',
    'parallel road lots',
    'classified road; if no setback specified by other EPI',
    'detached studio within 900 mm of a lane and above a garage',
    'detached development, parallel road lot',
    'lot area 200-300 m2; building height >4.5-8.5 m (upper level)',
    'lot size 200-300 m2 (if fewer than 2 dwelling houses within 40 m)',
    'lot width at building line 18 m or less',
    'lot width 6m-10m / >10-12.5m',
    'lot area 200-300 m2; lot area 300-400 m2',
    'lot area 200-300 m',
    'lot area 300-200 m2',
    'average of 2 nearest dwelling houses on same side of primary road',
    'something else entirely',
  ])('%s', (text) => {
    expect(parseBand(text).ok).toBe(false);
  });
});

describe('row usability against the real stored rows', () => {
  it('uses the four unbanded rows (numeric ones)', () => {
    expect(byId(2).usable).toBe(true);
    expect(byId(7).usable).toBe(true);
    expect(byId(3).usable).toBe(true);
    expect(select(parsed, 'min_lot_size').ok && (select(parsed, 'min_lot_size') as any).value).toBe(200);
    expect((select(parsed, 'min_lot_width') as any).value).toBe(6);
  });

  it('never uses value-only or unpaired rows', () => {
    for (const id of [17, 21, 55, 56, 57, 62, 73, 81, 82]) {
      expect(byId(id).usable).toBe(false);
    }
  });

  it('never uses rows whose clause label names a structure', () => {
    for (const id of [39, 42, 43, 48, 51, 63]) expect(byId(id).usable).toBe(false);
  });

  it('never uses upper-level rear rows', () => {
    for (const id of [25, 27, 29, 31]) expect(byId(id).usable).toBe(false);
  });

  it('uses the clean banded front, side and rear rows', () => {
    for (const id of [14, 15, 16, 18, 19, 20, 24, 26, 28, 30]) expect(byId(id).usable).toBe(true);
  });

  it('rejects a row with a stored number but zone-limited', () => {
    expect(parseRow(mk({ applicable_zones: ['R2'] })).usable).toBe(false);
  });

  it('accepts numeric values that arrive as strings (pg numeric)', () => {
    const p = parseRow(mk({ numeric_value: '4.5', conditionality: 'lot area >300-900 m2' }));
    expect(p.usable).toBe(true);
    expect(p.numericValue).toBe(4.5);
  });
});

describe('select boundaries', () => {
  const rear = (lotAreaM2: number, buildingHeightM = 3) =>
    select(parsed, 'min_rear_setback_m', { lotAreaM2, buildingHeightM });

  it('exactly the band edge belongs to the lower, inclusive band; just above goes to the ">" band', () => {
    const synthetic = parseRows([
      mk({ id: 1, numeric_value: 10, conditionality: 'lot area 200-300 m2', ref_number: '9.1' }),
      mk({ id: 2, numeric_value: 20, conditionality: 'lot area >300-450 m2', ref_number: '9.2' }),
    ]);
    const at = (a: number) => select(synthetic, 'min_front_setback_m', { lotAreaM2: a });
    expect((at(300) as any).value).toBe(10);
    expect((at(300.01) as any).value).toBe(20);
    expect((at(200) as any).value).toBe(10);
    expect(at(199.99).ok).toBe(false);
    expect((at(450) as any).value).toBe(20);
    expect(at(450.01).ok).toBe(false);
  });

  it('real rows: 900 m2 is in the >300-900 band, 900.5 in the >900-1,500 band', () => {
    const a = select(parsed, 'min_front_setback_m', { lotAreaM2: 900 });
    const b = select(parsed, 'min_front_setback_m', { lotAreaM2: 900.5 });
    expect(a.ok && a.clause).toBe('3.10(3)');
    expect(a.ok && a.value).toBe(Number(byId(14).numericValue));
    expect(b.ok && b.value).toBe(Number(byId(15).numericValue));
  });

  it('returns clause and verbatim quote of the selected row', () => {
    const r = select(parsed, 'min_front_setback_m', { lotAreaM2: 500 });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.quote).toBe(byId(14).row.source_quote);
      expect(r.quote.length).toBeGreaterThan(0);
    }
  });

  it('rear setback needs both lot area and height', () => {
    const noHeight = select(parsed, 'min_rear_setback_m', { lotAreaM2: 500 });
    expect(noHeight.ok).toBe(false);
    expect(rear(500).ok).toBe(true);
  });

  it('a lot of 250 m2 has no usable front band: null with a reason', () => {
    const r = select(parsed, 'min_front_setback_m', { lotAreaM2: 250 });
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.reason).toMatch(/no stored band/);
      expect(r.storedClauses).toContain('3.10(1)');
    }
  });

  it('missing input => null naming what to enter', () => {
    const r = select(parsed, 'min_front_setback_m', {});
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.reason).toMatch(/lot area/);
  });

  it('conflicting matches => null', () => {
    const conflict = parseRows([
      mk({ id: 1, numeric_value: 3, conditionality: 'lot area 200-500 m2', ref_number: '9.1' }),
      mk({ id: 2, numeric_value: 4, conditionality: 'lot area >300-900 m2', ref_number: '9.2' }),
    ]);
    const r = select(conflict, 'min_front_setback_m', { lotAreaM2: 400 });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.reason).toMatch(/conflict/);
  });

  it('two matches with the SAME value are not a conflict', () => {
    const same = parseRows([
      mk({ id: 1, numeric_value: 3, conditionality: 'lot area 200-500 m2', ref_number: '9.1' }),
      mk({ id: 2, numeric_value: 3, conditionality: 'lot area >300-900 m2', ref_number: '9.2' }),
    ]);
    const r = select(same, 'min_front_setback_m', { lotAreaM2: 400 });
    expect(r.ok && r.value).toBe(3);
  });

  it('unknown standard type => null', () => {
    expect(select(parsed, 'max_site_coverage_pct', { lotAreaM2: 500 }).ok).toBe(false);
  });

  it('structure rows only match when the proposal carries that structure', () => {
    expect(select(parsed, 'max_height_m', {}).ok).toBe(false);
    const r = select(parsed, 'max_height_m', { structures: ['dwelling_house_and_attached'] });
    expect(r.ok && r.value).toBe(Number(byId(10).numericValue));
  });
});

describe('evaluateCdcChecks with real rows', () => {
  const input = {
    developmentType: 'new_dwelling' as const,
    lotAreaM2: 500,
    lotWidthM: 12,
    neighbourDwellings: 'no' as const,
    setbacks: { front: 3, sideLeft: 1, sideRight: 0.5, rear: 3 },
    hasUpperFloorHabitableRooms: false,
    siteCoveragePercent: 40,
    landscapedAreaPercent: 20,
    buildingHeightMeters: 4,
    storeys: 3,
    parkingSpaces: 1,
  };
  const checks = evaluateCdcChecks(input, parsed);
  const get = (k: string) => checks.find((c) => c.key === k)!;

  it('front fails against the stored >300-900 value, showing its clause', () => {
    const c = get('front');
    expect(c.status).toBe('fail');
    expect(c.required).toBe(Number(byId(14).numericValue));
    expect(c.clause).toBe('3.10(3)');
    expect(c.quote).toBe(byId(14).row.source_quote);
  });

  it('side: width 12 and height 4 selects the 0.9 band (clause 3.10(4))', () => {
    expect(get('sideLeft').status).toBe('pass');
    expect(get('sideRight').status).toBe('fail');
    expect(get('sideLeft').clause).toBe('3.10(4)');
  });

  it('site coverage and parking have no stored standard to apply: Not checked, no number', () => {
    for (const k of ['siteCoverage', 'parking', 'landscapedArea']) {
      const c = get(k);
      expect(c.status).toBe('not_checked');
      expect(c.required).toBeNull();
      expect(c.margin).toBeNull();
      expect(c.clause).toBeNull();
    }
  });

  it('storeys 3 fails against the stored maximum for a new dwelling house', () => {
    expect(get('storeys').status).toBe('fail');
  });

  it('upper floor => rear not checked', () => {
    const r = evaluateCdcChecks({ ...input, hasUpperFloorHabitableRooms: true }, parsed).find((c) => c.key === 'rear')!;
    expect(r.status).toBe('not_checked');
    expect(r.required).toBeNull();
  });

  it('secondary dwelling => height and storeys not checked (structure not modelled)', () => {
    const cs = evaluateCdcChecks({ ...input, developmentType: 'secondary_dwelling' }, parsed);
    expect(cs.find((c) => c.key === 'buildingHeight')!.status).toBe('not_checked');
    expect(cs.find((c) => c.key === 'storeys')!.status).toBe('not_checked');
  });

  it('blank input is never a pass or fail', () => {
    const cs = evaluateCdcChecks({}, parsed);
    expect(cs.every((c) => c.status === 'not_checked' && c.proposed === null)).toBe(true);
  });
});

describe('route level: database returns no rows', () => {
  beforeEach(() => {
    jest.resetModules();
  });

  async function callRoute(queryImpl: () => Promise<unknown>, body: unknown) {
    jest.doMock('@/lib/db', () => ({ query: queryImpl }));
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { POST } = require('@/app/api/cdc/compliance-check/route');
    const req = { json: async () => body } as any;
    const res = await POST(req);
    return res.json();
  }

  const body = {
    developmentType: 'new_dwelling',
    lotAreaM2: 500,
    lotWidthM: 12,
    neighbourDwellings: 'no',
    setbacks: { front: 6, sideLeft: 1, sideRight: 1, rear: 3 },
    hasUpperFloorHabitableRooms: false,
    siteCoveragePercent: 40,
    landscapedAreaPercent: 30,
    buildingHeightMeters: 4,
    storeys: 2,
    parkingSpaces: 2,
  };

  function expectAllNotChecked(out: any) {
    expect(out.results.length).toBeGreaterThan(0);
    for (const r of out.results) {
      expect(r.status).toBe('not_checked');
      expect(r.required).toBeNull();
      expect(r.margin).toBeNull();
      expect(r.clause).toBeNull();
      expect(r.quote).toBeNull();
    }
    expect(out.passCount).toBe(0);
    expect(out.failCount).toBe(0);
    expect(out.overallCompliant).toBeNull();
    expect(JSON.stringify(out.recommendations)).toBe('[]');
  }

  it('empty table => every check Not checked', async () => {
    expectAllNotChecked(await callRoute(async () => ({ rows: [] }), body));
  });

  it('database error => every check Not checked, error surfaced', async () => {
    const out = await callRoute(async () => { throw new Error('connection refused'); }, body);
    expectAllNotChecked(out);
    expect(out.meta.standardsError).toMatch(/connection refused/);
    for (const r of out.results) expect(r.reason).toMatch(/connection refused/);
  });

  it('with the real rows the same request does produce decided checks', async () => {
    const out = await callRoute(async () => ({ rows }), body);
    expect(out.passCount + out.failCount).toBeGreaterThan(0);
    const front = out.results.find((r: any) => r.key === 'front');
    expect(front.clause).toBe('3.10(3)');
  });
});

describe('citations', () => {
  const FORBIDDEN = /not stored|not in stored|value-only|row |table_in_/i;

  it('clause rows cite the clause part only; others cite the stored PDF page', () => {
    expect(byId(2).citation).toBe('cl 3.1(3)(b)');
    expect(byId(14).citation).toBe('3.10(3)');
    expect(byId(39).citation).toBe('3.21(2)'); // label after the clause is dropped
    expect(byId(10).citation).toBe(`Codes SEPP 2008, page ${rows.find((r) => r.id === 10)!.pdf_page}`);
    expect(byId(10).citation).toMatch(/^Codes SEPP 2008, page \d+$/);
    expect(byId(67).citation).toMatch(/^Codes SEPP 2008, page \d+$/);
  });

  it('a row with neither clause nor page is not usable and says so', () => {
    const p = parseRow(mk({ ref_number: 'heading row not stored', pdf_page: null, conditionality: 'lot area >300-900 m2' }));
    expect(p.citation).toBeNull();
    expect(p.usable).toBe(false);
    expect(p.unusableReason).toBe('no clause or page stored');
    const r = select([p], 'min_front_setback_m', { lotAreaM2: 500 });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.reason).toBe('no clause or page stored');
  });

  it('a page-cited row is usable for a verdict', () => {
    const p = parseRow(mk({ ref_number: 'dwelling house height (heading row not stored)', pdf_page: 118 }));
    expect(p.usable).toBe(true);
    expect(p.citation).toBe('Codes SEPP 2008, page 118');
  });

  it('no citation string anywhere carries an internal label (all 79 rows, checks and API rows)', () => {
    const strings: string[] = [];
    for (const p of parsed) {
      if (p.citation) strings.push(p.citation);
      const pub = publicRow(p.row);
      if (pub.ref_number) strings.push(pub.ref_number);
      const c = citationOf(p.row);
      if (c) strings.push(c);
    }
    const inputs = [];
    for (const a of [150, 250, 300, 500, 1000, 2000]) {
      for (const w of [7, 12, 20, 26]) {
        for (const h of [3, 5, 7]) {
          for (const dt of ['new_dwelling', 'addition', 'secondary_dwelling'] as const) {
            inputs.push({
              developmentType: dt, lotAreaM2: a, lotWidthM: w, buildingHeightMeters: h,
              neighbourDwellings: (['yes', 'no', 'unknown', null] as const)[(a + w + h) % 4],
              neighbourAverageFrontM: 7,
              setbacks: { front: 5, sideLeft: 1, sideRight: 1, rear: 4 },
              hasUpperFloorHabitableRooms: false, siteCoveragePercent: 40,
              landscapedAreaPercent: 20, storeys: 2, parkingSpaces: 1,
            });
          }
        }
      }
    }
    for (const input of inputs) {
      for (const c of evaluateCdcChecks(input, parsed)) {
        for (const v of [c.clause, c.reason, ...c.storedClauses, ...c.unmodelledClauses]) {
          if (v) strings.push(v);
        }
      }
    }
    expect(strings.length).toBeGreaterThan(100);
    for (const t of strings) expect(t).not.toMatch(FORBIDDEN);
  });

  it('the standards and check routes do not return internal labels as citations', async () => {
    jest.resetModules();
    // Mocked DB: the page lookup by id (is_current deliberately not filtered, see the loader).
    jest.doMock('@/lib/db', () => ({
      query: async (sql: string) => (/regulatory_provisions/.test(sql)
        ? { rows: Array.from(new Set(rows.map((r) => (r as any).source_provision_ids[0])))
            .map((id) => ({ id, pdf_page: (rows.find((r) => (r as any).source_provision_ids[0] === id) as any).pdf_page })) }
        : { rows: rows.map((r) => ({ ...r })) }),
    }));
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const std = await require('@/app/api/cdc/standards/route').GET();
    const sj = await std.json();
    const refs = sj.rows.map((r: any) => r.ref_number).filter(Boolean);
    expect(refs.length).toBeGreaterThan(40);
    for (const t of refs) expect(t).not.toMatch(FORBIDDEN);
    // pages came through the loader
    expect(sj.rows.find((r: any) => r.id === 10).pdf_page).toBe((rows.find((r) => r.id === 10) as any).pdf_page);
    // parsing the public rows gives the same usable set as parsing the raw rows
    expect(parseRows(sj.rows).map((p) => p.usable)).toEqual(parsed.map((p) => p.usable));
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const cc = await require('@/app/api/cdc/compliance-check/route').GET();
    const cj = await cc.json();
    for (const s of cj.storedStandards) expect(s.clause).not.toMatch(FORBIDDEN);
  });
});

describe('row 24 (rear, lot area 200-300 m2, height 0-4.5 m)', () => {
  const at = (a: number) => select(parsed, 'min_rear_setback_m', { lotAreaM2: a, buildingHeightM: 3 });
  it.each([200, 250, 300])('%s m2 selects row 24 only', (a) => {
    const r = at(a);
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.rowIds).toEqual([24]);
      expect(r.value).toBe(Number(byId(24).numericValue));
      expect(r.clause).toBe('3.10(10)');
    }
  });
  it('300.01 m2 moves to row 26; 199.99 m2 matches nothing', () => {
    const a = at(300.01);
    expect(a.ok && a.rowIds).toEqual([26]);
    expect(at(199.99).ok).toBe(false);
  });
});

describe('front setback: neighbours average rule vs lot-area band', () => {
  const base = {
    developmentType: 'new_dwelling' as const,
    lotAreaM2: 500,
    setbacks: { front: 5 },
  };
  const front = (extra: object) =>
    evaluateCdcChecks({ ...base, ...extra }, parsed).find((c) => c.key === 'front')!;
  const bandValue = Number(byId(14).numericValue);

  it('yes + average: compared with the average, citing the average rule (not the band)', () => {
    const c = front({ neighbourDwellings: 'yes', neighbourAverageFrontM: 7 });
    expect(c.status).toBe('fail');
    expect(c.required).toBe(7);
    expect(c.clause).toBe(byId(17).citation);
    expect(c.quote).toBe(byId(17).row.source_quote);
    expect(c.required).not.toBe(bandValue);
  });

  it('yes + average: passes when the setback meets the average, even above/below the band figure', () => {
    expect(front({ neighbourDwellings: 'yes', neighbourAverageFrontM: 5 }).status).toBe('pass');
    expect(front({ neighbourDwellings: 'yes', neighbourAverageFrontM: 2 }).required).toBe(2);
  });

  it('yes without an average => Not checked, rule quoted', () => {
    const c = front({ neighbourDwellings: 'yes' });
    expect(c.status).toBe('not_checked');
    expect(c.required).toBeNull();
    expect(c.reason).toMatch(/average front setback/);
    expect(c.quote).toBe(byId(17).row.source_quote);
  });

  it('no => the stored lot-area band applies', () => {
    const c = front({ neighbourDwellings: 'no', neighbourAverageFrontM: 99 });
    expect(c.status).toBe(5 >= bandValue ? 'pass' : 'fail');
    expect(c.required).toBe(bandValue);
    expect(c.clause).toBe('3.10(3)');
  });

  it.each([['unknown'], [null], [undefined]])('state %s => Not checked, no number, rule quoted', (st) => {
    const c = front({ neighbourDwellings: st, neighbourAverageFrontM: 7 });
    expect(c.status).toBe('not_checked');
    expect(c.required).toBeNull();
    expect(c.margin).toBeNull();
    expect(c.reason).toMatch(/at least 2 dwelling houses/);
    expect(c.quote).toBe(byId(17).row.source_quote);
  });

  it('absent in the API body => front Not checked', async () => {
    jest.resetModules();
    jest.doMock('@/lib/db', () => ({ query: async (sql: string) => (/regulatory_provisions/.test(sql)
      ? { rows: rows.map((r: any) => ({ id: r.source_provision_ids[0], pdf_page: r.pdf_page })) }
      : { rows: rows.map((r) => ({ ...r })) }) }));
    const { POST } = require('@/app/api/cdc/compliance-check/route');
    const res = await POST({ json: async () => ({ ...base, setbacks: { front: 5 } }) } as any);
    const out = await res.json();
    expect(out.results.find((r: any) => r.key === 'front').status).toBe('not_checked');
  });
});

describe('failure wording', () => {
  it('maximum says over, minimum says short', () => {
    const cs = evaluateCdcChecks({
      developmentType: 'new_dwelling', buildingHeightMeters: 9.5, storeys: 3,
      lotAreaM2: 500, neighbourDwellings: 'no', setbacks: { front: 1 },
    }, parsed);
    const h = cs.find((c) => c.key === 'buildingHeight')!;
    const f = cs.find((c) => c.key === 'front')!;
    expect(h.status).toBe('fail');
    expect(shortfallText(h)).toBe(`${Math.abs(h.margin!).toFixed(1)} m over the stored maximum`);
    expect(shortfallText(h)).not.toMatch(/short/);
    expect(f.status).toBe('fail');
    expect(shortfallText(f)).toBe(`${Math.abs(f.margin!).toFixed(1)} m short of the stored minimum`);
    expect(shortfallText(f)).not.toMatch(/over/);
  });

  it('route recommendations use the same wording', async () => {
    jest.resetModules();
    jest.doMock('@/lib/db', () => ({ query: async (sql: string) => (/regulatory_provisions/.test(sql)
      ? { rows: rows.map((r: any) => ({ id: r.source_provision_ids[0], pdf_page: r.pdf_page })) }
      : { rows: rows.map((r) => ({ ...r })) }) }));
    const { POST } = require('@/app/api/cdc/compliance-check/route');
    const res = await POST({ json: async () => ({
      developmentType: 'new_dwelling', buildingHeightMeters: 9.5, lotAreaM2: 500,
      neighbourDwellings: 'no', setbacks: { front: 1 },
    }) } as any);
    const out = await res.json();
    const recs: string[] = out.recommendations;
    expect(recs.some((r) => /over the stored maximum/.test(r))).toBe(true);
    expect(recs.some((r) => /short of the stored minimum/.test(r))).toBe(true);
    expect(recs.join(' ')).not.toMatch(/short of the stored maximum/);
  });
});


describe('negative inputs never pass', () => {
  it('a negative height or storey count is Not checked, not a pass against the maximum', () => {
    const input = {
      developmentType: 'new_dwelling' as const, lotAreaM2: 500, lotWidthM: 12, neighbourDwellings: 'no' as const,
      setbacks: { front: 3, sideLeft: 1, sideRight: 1, rear: 3 }, hasUpperFloorHabitableRooms: false,
      buildingHeightMeters: -1, storeys: -1,
    };
    const checks = evaluateCdcChecks(input, parsed);
    for (const key of ['buildingHeight', 'storeys']) {
      expect(checks.find((c) => c.key === key)?.status).toBe('not_checked');
    }
  });
});
