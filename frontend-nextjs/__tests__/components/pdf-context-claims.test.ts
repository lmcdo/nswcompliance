import { readFileSync } from 'fs';
import { join } from 'path';

/**
 * The exported PDF must not contradict itself, and must not assert site facts it
 * never checked.
 *
 * Two defects, both in the same SEPP table of the provisions PDF (reachable from
 * the live assessment page via ProvisionsByTocStructure):
 *
 *  DQ-34  "Housing SEPP 2021: ✓ Applies - R2 zone eligible for complying
 *         development (CDC) pathway" was decided on ZONE ALONE, while
 *         determineDevelopmentPathway() in the same file correctly returns
 *         "Development Application (DA) - Heritage item: CDC and exempt
 *         development not permitted". On a heritage property the one PDF gave
 *         both answers.
 *
 *  (new) "Transport Oriented Development: ✗ Not applicable - Property not within
 *         400m of metro station or 800m of strategic centre" was HARDCODED. The
 *         component is passed no TOD data, so no code path could ever produce a
 *         different answer — for any property inside a catchment the PDF stated a
 *         falsehood about that site.
 *
 * Source-level guards: the component needs @react-pdf/renderer and a full
 * PropertyContext to render, so these assert on the source the same way
 * __tests__/api/capacity-repoint.test.ts does. Comments are stripped first, so
 * documenting the old wording doesn't trip the guard.
 */
const raw = readFileSync(
  join(process.cwd(), 'components/pdf/ContextSection.tsx'),
  'utf8',
);
const src = raw
  .replace(/\/\*[\s\S]*?\*\//g, ' ')
  .replace(/\{\/\*[\s\S]*?\*\/\}/g, ' ')
  .replace(/(^|\s)\/\/[^\n]*/g, ' ');

describe('PDF SEPP table — no self-contradiction (DQ-34)', () => {
  it('does not decide Housing SEPP eligibility from the zone alone', () => {
    // The exact shipped string. Its return would mean the heritage gate is gone.
    expect(src).not.toMatch(/✓ Applies - \$\{[^}]*\} zone eligible for complying development/);
  });

  it('gates the Housing SEPP line on heritage, like determineDevelopmentPathway does', () => {
    expect(src).toMatch(/heritage_status\?\.in_hca/);
    expect(src).toMatch(/housingSeppStatus/);
  });

  it('reports a zone match as a zone test, not as an eligibility verdict', () => {
    expect(src).toMatch(/Zone test met/);
  });

  it('does not turn a missing zone into a "does not apply" verdict', () => {
    // zoneDisplay falls back to 'Unknown', which is not in HOUSING_SEPP_ZONES, so
    // an absent zone would otherwise print a definitive negative from no data.
    expect(src).toMatch(/Not assessed - zoning data unavailable/);
    expect(src).toMatch(/const hasZone/);
  });

  it('still says plainly when the zone is outside the Housing SEPP', () => {
    expect(src).toMatch(/Does not apply/);
  });
});

describe('PDF SEPP table — no unchecked site claims', () => {
  it('does not assert the property is outside a TOD catchment', () => {
    expect(src).not.toMatch(/Property not within 400m of metro station/);
  });

  it('says TOD was not assessed instead', () => {
    expect(src).toMatch(/Not assessed in this report/);
  });

  it('does not present proposal-dependent SEPPs as settled for this property', () => {
    // "✗ Not applicable" is a determination; these depend on a proposal the
    // report has never seen. Four of them shipped that way.
    const verdicts = src.match(/✗ Not applicable/g) || [];
    expect(verdicts).toHaveLength(0);
  });

  it('states those SEPPs as scope, which is the part that is actually known', () => {
    const scoped = src.match(/Depends on the proposal - Applies to/g) || [];
    expect(scoped.length).toBeGreaterThanOrEqual(4);
  });
});
