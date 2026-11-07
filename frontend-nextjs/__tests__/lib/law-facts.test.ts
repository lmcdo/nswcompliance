/**
 * The website shows Chapter 5 figures only from the stored law facts.
 *
 * Until 2026-11-07 StateLevelControls.tsx typed "22m", "24m" and "2.5:1" into a paragraph. A change to section 155 would
 * not have changed the page, and no test would have failed. These tests pin the other direction: the rendered code of the
 * component and the facts library contain no planning figure, and the sentence is built from the rows it is given.
 * @jest-environment node
 */
import fs from 'fs';
import path from 'path';
import {
  rowsToFacts, todStandardsSentence, TOD_STANDARDS_UNAVAILABLE, LAW_FACT_KEYS, accessibleAreaLimits, type LawFactRow,
} from '@/lib/law-facts';

const read = (rel: string) => fs.readFileSync(path.join(__dirname, '..', '..', rel), 'utf8');

/** Source with block and line comments blanked, so a comment may name what the code avoids. */
const code = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|\s)\/\/[^\n]*/g, ' ');

const ROW = (k: string, value: unknown, n: number | null, clause: string, page: number): LawFactRow => ({
  fact_key: k, value, value_number: n, unit: null, clause, pdf_page: page, quote: `quote for ${k}`, law_version_date: '2026-10-23',
});
const ROWS: LawFactRow[] = [
  ROW('tod_height_residential_flat_building_m', 22, 22, 's155(2)', 75),
  ROW('tod_height_seniors_or_shop_top_m', 24, 24, 's155(3)', 76),
  ROW('tod_fsr', '2.5:1', null, 's155(4)', 76),
];

describe('todStandardsSentence', () => {
  it('is built from the rows it is given, with clause, page and law version date', () => {
    const s = todStandardsSentence(rowsToFacts(ROWS))!;
    expect(s).toMatch(/22m for a residential flat building \(s155\(2\), page 75\)/);
    expect(s).toMatch(/24m for seniors or shop top housing \(s155\(3\), page 76\)/);
    expect(s).toMatch(/floor space ratio of 2\.5:1 .*\(s155\(4\), page 76\)/);
    expect(s).toMatch(/Law as at 2026-10-23/);
  });

  it('changes when the stored figure changes — the point of reading it from the table', () => {
    const changed = ROWS.map((r) => (r.fact_key === 'tod_fsr' ? { ...r, value: '3:1' } : r));
    expect(todStandardsSentence(rowsToFacts(changed))).toMatch(/floor space ratio of 3:1/);
    const taller = ROWS.map((r) => (r.fact_key === 'tod_height_residential_flat_building_m' ? { ...r, value: 25, value_number: 25 } : r));
    expect(todStandardsSentence(rowsToFacts(taller))).toMatch(/25m for a residential flat building/);
  });

  it('is null — so the page prints no figure — when any one of the three is missing or has no usable value', () => {
    for (const drop of ROWS.map((r) => r.fact_key)) {
      expect(todStandardsSentence(rowsToFacts(ROWS.filter((r) => r.fact_key !== drop)))).toBeNull();
    }
    expect(todStandardsSentence(null)).toBeNull();
    expect(todStandardsSentence(undefined)).toBeNull();
    expect(todStandardsSentence({})).toBeNull();
    const empty = ROWS.map((r) => (r.fact_key === 'tod_fsr' ? { ...r, value: '', value_number: null } : r));
    expect(todStandardsSentence(rowsToFacts(empty))).toBeNull();
  });
});

describe('rowsToFacts', () => {
  it('ignores a key the website does not read and a row missing its clause, page or quote', () => {
    const f = rowsToFacts([
      ROW('something_else', 1, 1, 's1', 1),
      { ...ROW('tod_fsr', '2.5:1', null, '', 76) },
      { ...ROW('lmr_outer_distance', 800, 800, 's163', 0) },
      { ...ROW('lmr_inner_distance', 400, 400, 's163', 78), quote: '' },
    ]);
    expect(Object.keys(f)).toEqual([]);
  });

  it('reads a numeric string from the database and a Date version', () => {
    const f = rowsToFacts([{ ...ROW('lmr_outer_distance', null, 800 as never, 's163', 77), value: null, value_number: '800', law_version_date: new Date('2026-10-23T00:00:00Z') }]);
    expect(f.lmr_outer_distance).toMatchObject({ value: 800, lawVersionDate: '2026-10-23' });
  });

  it('serves only the listed facts', () => {
    expect(LAW_FACT_KEYS).toContain('tod_fsr');
    expect(LAW_FACT_KEYS).not.toContain('s164' as never);
  });
});

describe('no planning figure is typed where the page shows Chapter 5 standards', () => {
  const FIGURES = /\b22\s?m\b|\b24\s?m\b|2\.5\s?:\s?1|\b800\b|\b600\b|\b400\b/;

  it('the unavailable sentence carries no figure', () => {
    expect(TOD_STANDARDS_UNAVAILABLE).not.toMatch(FIGURES);
    expect(TOD_STANDARDS_UNAVAILABLE).toMatch(/Section 155 identifies/);
  });

  it('lib/law-facts.ts and the route type no planning figure in their code', () => {
    for (const f of ['lib/law-facts.ts', 'app/api/law-facts/route.ts', 'hooks/useLawFacts.ts']) {
      expect(code(read(f))).not.toMatch(/\b22\b|\b24\b|2\.5|\b800\b|\b400\b/);
    }
  });

  it('StateLevelControls renders the Chapter 5 sentence from the facts, not from text in the file', () => {
    const c = code(read('components/compliance/StateLevelControls.tsx'));
    expect(c).toMatch(/todStandardsSentence\(lawFacts\)/);
    expect(c).not.toMatch(/\b22m\b|\b24m\b|2\.5:1/);
  });
});

describe('accessibleAreaLimits (the law distances behind the parking-reduction card)', () => {
  const R = (k: string, n: number) => ({ ...ROW(k, null, n, 'Schedule 10 dictionary, accessible area (a)', 125), value: null });
  const rows: LawFactRow[] = [R('accessible_area_rail_distance', 800), R('accessible_area_bus_distance', 400)];

  it('reads both distances with clause, page and law version date', () => {
    const l = accessibleAreaLimits(rowsToFacts(rows))!;
    expect(l).toMatchObject({ railM: 800, busM: 400, pdfPage: 125, lawVersionDate: '2026-10-23' });
    expect(l.clause).toMatch(/accessible area/);
  });

  it('follows the stored figures — nothing is typed', () => {
    expect(accessibleAreaLimits(rowsToFacts([R('accessible_area_rail_distance', 900), R('accessible_area_bus_distance', 450)]))).toMatchObject({ railM: 900, busM: 450 });
  });

  it('is null unless BOTH are present and positive, so the page makes no distance claim', () => {
    expect(accessibleAreaLimits(rowsToFacts([rows[0]]))).toBeNull();
    expect(accessibleAreaLimits(rowsToFacts([rows[1]]))).toBeNull();
    expect(accessibleAreaLimits(rowsToFacts([R('accessible_area_rail_distance', 0), rows[1]]))).toBeNull();
    expect(accessibleAreaLimits(null)).toBeNull();
    expect(accessibleAreaLimits(undefined)).toBeNull();
  });
});

describe('the page no longer types transport distances', () => {
  it('the component and constants file carry no 600 m light rail figure, 1000 m search radius or TOD_THRESHOLDS', () => {
    const comp = code(read('components/compliance/StateLevelControls.tsx'));
    const consts = code(read('lib/regulatory-constants.ts'));
    for (const src of [comp, consts]) {
      expect(src).not.toMatch(/WALKABLE_M|TRANSPORT_PROXIMITY|TOD_THRESHOLDS|isInTODAccessibleArea/);
      // A distance-shaped number: a figure followed by m / metres, or a *_M constant assigned one. Colour classes such as text-purple-600 are not distances.
      expect(src).not.toMatch(/\b(600|1000)\s?(m\b|metres)|_M:\s*(600|1000)\b/);
    }
    expect(comp).toMatch(/accessibleAreaLimits\(lawFacts\)/);
  });
});
