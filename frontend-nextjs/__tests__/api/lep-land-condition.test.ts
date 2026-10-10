/**
 * DQ-140: Inner West LEP site-specific rules are served only on the land they name.
 *
 * Calls the real filter (applyLandConditions) on every served Inner West LEP 2022 row with the condition
 * enrichment/config/inner_west_lep_land.py gives it, against the live layerintersect answers of two real
 * lots, recorded 2026-10-11 in __tests__/fixtures/iw_lep_land_conditions.json.
 */
import fixture from '../fixtures/iw_lep_land_conditions.json';
import {
  applyLandConditions,
  decideLandCondition,
  decodeLandFacts,
  encodeLandFacts,
  landFactsFromLayers,
  type LandCondition,
  type LandFacts,
} from '@/lib/lep-land-condition';

type Row = { id: number; clause: string | null; v2_land_condition: LandCondition | null };
const rows = fixture.rows as Row[];
const lots = fixture.lots as Record<string, { layers: Array<{ layerName: string; results: Array<Record<string, string>> }> }>;

function factsFor(address: string): LandFacts {
  const layers = lots[address].layers;
  const zone = layers.find((l) => l.layerName === 'Land Zoning Map')?.results[0]?.Zone ?? null;
  const facts = landFactsFromLayers(layers, zone);
  if (!facts) throw new Error('fixture lot has no layers');
  return facts;
}

/** Served clause keys (and Schedule 1 items) for a lot, through the real filter. */
function served(facts: LandFacts | null) {
  const { kept } = applyLandConditions(rows, facts);
  const clauses = new Set(kept.map((r) => r.clause));
  const items = new Set(
    kept
      // By condition, not heading: item 46's only served row (23689) is headed clause 7.4.
      .filter((r) => r.v2_land_condition?.source?.startsWith('Schedule 1 item'))
      .flatMap((r) => r.v2_land_condition?.labels ?? [])
  );
  return { kept, clauses, items };
}

describe('10 Norton Street, Leichhardt (E1, Key Sites Area 1, APU 46)', () => {
  const s = served(factsFor('10 Norton Street, Leichhardt'));

  it('shows Schedule 1 item 46 and clauses 6.14, 6.15', () => {
    expect(s.items.has('46')).toBe(true);
    expect(s.clauses.has('6.14')).toBe(true);
    expect(s.clauses.has('6.15')).toBe(true);
  });

  it('shows 6.26 (Trafalgar St lots, APU 46) only as "could not confirm" -- the label is shared', () => {
    const rows626 = s.kept.filter((r) => r.clause === '6.26');
    expect(rows626.length).toBeGreaterThan(0);
    expect(rows626.every((r) => r.land_status === 'unconfirmed')).toBe(true);
  });

  it('does not show 6.17 (Area 5, 168 Norton St) or Schedule 1 item 45', () => {
    expect(s.clauses.has('6.17')).toBe(false);
    expect(s.items.has('45')).toBe(false);
  });

  it('serves item 46 row 23689 even though it carries clause 7.4 (Dulwich Grove) as its heading', () => {
    expect(s.kept.some((r) => r.id === 23689)).toBe(true);
    expect(s.clauses.has('7.2')).toBe(false); // Dulwich Grove = Key Sites Area 14
  });

  it('keeps every rule that is not land-limited', () => {
    const free = rows.filter((r) => !r.v2_land_condition).length;
    expect(s.kept.filter((r) => !r.v2_land_condition).length).toBe(free);
  });
});

describe('45 Victoria Road, Rozelle (E4, Key Sites Area 1 + Area 19, no APU)', () => {
  const s = served(factsFor('45 Victoria Road, Rozelle'));

  it('shows 6.21 (Zone E3/E4 and Area 19)', () => {  // noqa: zone-codes -- the zones cl 6.21's own words name, a test expectation
    expect(s.clauses.has('6.21')).toBe(true);
  });

  it('does not show Schedule 1 item 46, 6.26, or 6.22 (Area 20)', () => {
    expect(s.items.has('46')).toBe(false);
    expect(s.clauses.has('6.26')).toBe(false);
    expect(s.clauses.has('6.22')).toBe(false);
  });
});

describe('no portal answer', () => {
  it('withholds nothing and marks every land-limited rule unconfirmed', () => {
    const { kept, withheld, unconfirmed } = applyLandConditions(rows, null);
    expect(withheld).toBe(0);
    expect(kept.length).toBe(rows.length);
    expect(unconfirmed).toBe(rows.filter((r) => r.v2_land_condition).length);
    expect(kept.filter((r) => r.land_status === 'unconfirmed').every((r) => r.land_note?.startsWith('Could not confirm this land'))).toBe(true);
  });
});

describe('decideLandCondition', () => {
  const facts: LandFacts = { zone: 'E1', layers: { 'Key Sites Map': ['Area 19'] } };
  it('a zone the clause also requires must match', () => {
    expect(decideLandCondition({ layer: 'Key Sites Map', labels: ['Area 19'], zones: ['E3', 'E4'], verified: true }, facts)).toBe('no_match');  // noqa: zone-codes -- cl 6.21's own zones, a test expectation
  });
  it('an unverified layer absent from the answer is unconfirmed, not withheld', () => {
    expect(decideLandCondition({ layer: 'Foreshore Building Line Map', labels: null, zones: null, verified: false }, facts)).toBe('unconfirmed');
  });
  it('a verified layer absent from the answer is no_match', () => {
    expect(decideLandCondition({ layer: 'Heritage Map', labels: null, zones: null, verified: true }, facts)).toBe('no_match');
  });
  it('land no layer holds is always unconfirmed', () => {
    expect(decideLandCondition({ layer: null, labels: null, zones: null, verified: false }, facts)).toBe('unconfirmed');
  });
  it('labels compare without quotes, case or spacing', () => {
    expect(decideLandCondition({ layer: 'Key Sites Map', labels: ['area  19'], zones: null, verified: true }, facts)).toBe('match');
  });
});

describe('encode / decode', () => {
  it('round-trips', () => {
    const f = factsFor('45 Victoria Road, Rozelle');
    expect(decodeLandFacts(encodeLandFacts(f))).toEqual(f);
  });
  it('malformed input is null (read as unconfirmed, never as a match)', () => {
    expect(decodeLandFacts('{not json')).toBeNull();
    expect(decodeLandFacts('{"zone":"E1","layers":[]}')).toBeNull();
    expect(decodeLandFacts('{"zone":"E1","layers":{}}')).toBeNull();
  });
});
