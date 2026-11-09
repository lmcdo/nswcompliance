/**
 * The Development Capacity card combines LEP limits with DCP setbacks, so it is a council-rules figure.
 * During the private pilot it is withheld from Site Facts and shown in Council Rules only for a pilot council in zone R2.
 * Source-scan test, in the pattern of hidden-products-not-linked.test.ts: both pages are large client components.
 */
import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(__dirname, '..', '..');
const read = (rel: string) => fs.readFileSync(path.join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n');

describe('Development Capacity card is pilot-only', () => {
  const site = read('app/reports/intelligence-brief/page.tsx');
  const lep = read('components/compliance/LepControls.tsx');

  it('Site Facts drops the constraint_arithmetic section before rendering', () => {
    expect(site).toMatch(/\.filter\(\(p\) => p\.data\.section !== 'constraint_arithmetic'\)/);
  });

  it('Site Facts no longer waits for the section it drops', () => {
    const line = site.split('\n').find((l) => l.startsWith('const EXPECTED_SECTIONS_DEV')) ?? '';
    expect(line).not.toBe('');
    expect(line).not.toContain('constraint_arithmetic');
  });

  it('Council Rules shows the card only for a pilot council in the pilot zone', () => {
    const idx = lep.indexOf('<ConstraintArithmeticCard');
    expect(idx).toBeGreaterThan(0);
    const guard = lep.slice(Math.max(0, idx - 700), idx);
    expect(guard).toContain('pilotCouncilKey(formerCouncil, constraints?.lga) !== null');
    expect(guard).toContain('isPilotZone(constraints?.zone)');
  });
});
