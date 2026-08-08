import { readFileSync } from 'fs';
import { join } from 'path';

/**
 * DQ-31 — an absent LMR-area input must never mean "yes".
 *
 * `/api/housing-sepp/eligibility` computed `const inLMRArea = isLMRArea !== false`,
 * so a caller that simply omitted the field got the property treated as inside an
 * LMR reform area. That is the single input the whole endpoint turns on, resolved
 * in the claimant's favour whenever nobody supplied it.
 *
 * services/housing_sepp_eligibility.py was written to replace this logic and names
 * it in its own docstring as "a silent over-eligibility bug". That service derives
 * the gate from the live 776 exclusion layer and fails CONSERVATIVE — any query
 * failure yields ineligible, never false eligibility. This endpoint now matches
 * that contract.
 *
 * Source-level guards: the route needs a live DB to execute, so these assert on the
 * source the same way __tests__/api/capacity-repoint.test.ts does. Comments are
 * stripped first so documenting the old expression does not trip the guard.
 */
// NOTE for anyone adding assertions here: these match against SOURCE TEXT, so a
// phrase that spans a TypeScript `+` concatenation will never be found. Three
// assertions in this PR failed that way. Keep each pattern inside one literal.
function strip(src: string): string {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/(^|\s)\/\/[^\n]*/g, ' ');
}

const ROUTE = strip(
  readFileSync(join(process.cwd(), 'app/api/housing-sepp/eligibility/route.ts'), 'utf8'),
);
const ROUTER = strip(readFileSync(join(process.cwd(), 'lib/ai/router.ts'), 'utf8'));

describe('housing-sepp eligibility — absent LMR input (DQ-31)', () => {
  it('no longer treats an omitted isLMRArea as true', () => {
    // The exact shipped expression. Its return reinstates the over-eligibility.
    expect(ROUTE).not.toMatch(/inLMRArea\s*=\s*isLMRArea\s*!==\s*false/);
  });

  it('requires an explicit boolean before claiming the property is in an LMR area', () => {
    expect(ROUTE).toMatch(/typeof isLMRArea === 'boolean'/);
    expect(ROUTE).toMatch(/const inLMRArea = isLMRArea === true/);
  });

  it('distinguishes "not assessed" from "confirmed outside an LMR area"', () => {
    // Both are ineligible, but they are different statements and a user acts on
    // them differently.
    expect(ROUTE).toMatch(/lmrAreaKnown/);
    expect(ROUTE).toMatch(/not assessed for this property/);
    // Matched within a SINGLE string literal: the sentence is built by TS
    // concatenation, so a phrase spanning the `+` never appears in the source.
    expect(ROUTE).toMatch(/finding that the property is outside/);
  });
});

describe('AI router — no fabricated site measurements (DQ-31)', () => {
  it('does not hardcode the LMR gate to true', () => {
    expect(ROUTER).not.toMatch(/isLMRArea:\s*true/);
  });

  it('does not invent a zone, lot size or lot width for a real property', () => {
    // `|| 'R2'` appeared TWICE — the Housing SEPP handler and the DCP topic
    // lookup, which answered with R2's provisions whenever the zone was unknown.
    expect(ROUTER).not.toMatch(/context\.zone\s*\|\|\s*'R2'/);
    expect(ROUTER).not.toMatch(/context\.lotSize\s*\|\|\s*450/);
    expect(ROUTER).not.toMatch(/context\.lotWidth\s*\|\|\s*12/);
  });

  it('stops the check when an input is missing, and says so is not a finding', () => {
    expect(ROUTER).toMatch(/Housing SEPP eligibility needs/);
    expect(ROUTER).toMatch(/not a finding that the property is ineligible/);
  });
});

describe('three-state reaches the RESPONSE, not just the input (DQ-31, cross-review)', () => {
  it('exposes a machine-readable status so consumers need not parse prose', () => {
    // The first pass fixed the input and left `isEligible: false` covering both
    // "confirmed outside" and "never assessed" — a consumer rendering the boolean
    // would say "not eligible" about a check that never ran.
    expect(ROUTE).toMatch(/assessmentStatus/);
    expect(ROUTE).toMatch(/'eligible' \| 'ineligible' \| 'not_assessed'/);
    expect(ROUTE).toMatch(/lmrAreaKnown \? 'ineligible' : 'not_assessed'/);
  });

  it('keeps isEligible so existing consumers do not break', () => {
    expect(ROUTE).toMatch(/isEligible: boolean/);
  });

  it('refuses a zone-dependent DCP lookup when the zone is unknown', () => {
    // Omitting the zone param drops the filter entirely, so OTHER zones'
    // provisions come back and read as applicable to this property.
    expect(ROUTER).toMatch(/for this property is not known/);
    // Matched within one literal — the sentence is built by TS concatenation.
    expect(ROUTER).toMatch(/provisions are scoped by both/);
    expect(ROUTER).toMatch(/is not a finding/);
  });
});

