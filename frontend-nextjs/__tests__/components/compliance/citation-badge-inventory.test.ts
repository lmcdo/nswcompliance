/**
 * OC-20 inventory: every component that renders a rule's citation uses the shared
 * CitationUncheckedBadge. Grep-based, so a NEW citation-rendering component fails here until it
 * uses the badge (or is listed in EXEMPT with a reason).
 * @jest-environment node
 */
import { readdirSync, readFileSync, statSync } from 'fs';
import { join, relative } from 'path';

const ROOT = join(__dirname, '../../..');
// JSX that prints a citation: a clause/ref label, a Planning Portal clause, or a SEPP clause link.
const CITATION_MARKERS = [
  /\{[^}]*\bclause_reference\b[^}]*\}/,
  /\{[^}]*\bref_number\b[^}]*\}/,
  /\{[^}]*\brefNumber\b[^}]*\}/,
  /\{[^}]*\bclause_label\b[^}]*\}/,
  /\{[^}]*\blegislativeClause\b[^}]*\}/,
  /\{[^}]*\bclauseNumber\b[^}]*\}/,
  /\{[^}]*\bheritageClause\b[^}]*\}/,
  /\{[^}]*\b(citation|legislativeControlLabel)\b[^}]*\}/,
  /<SeppCitationLink\b/,
  /LEP Clause \d/,
];
// JSX element, not an import or a comment: an unused import must not satisfy the inventory.
const USES_BADGE = /<CitationUncheckedBadge\b|<SeppCitationLink\b/;

/** Files that match a marker but render no citation to the reader, or are not mounted. */
const EXEMPT: Record<string, string> = {
  'components/compliance/CitationUncheckedBadge.tsx': 'the badge itself',
  'components/compliance/SeppCitationLink.tsx': 'renders the badge itself (its callers pass <SeppCitationLink>)',
  'components/compliance/ComplianceDashboard.tsx': 'not mounted (no <ComplianceDashboard> anywhere); see no-fabricated-citations.test.tsx',
  'components/compliance/BASIXProvisions.tsx': 'not mounted anywhere',
  // Data plumbing: passes ref_number into an object that a badged component then renders.
  'components/compliance/ComplianceDashboardV2.tsx': 'passes ref_number to ConstraintCard, which renders the badge',
  'components/compliance/DCPProvisionsBrowser.tsx': 'passes ref_number to a badged card; prints none itself',
  'components/compliance/GeneralDCPSection.tsx': 'type declarations only; prints no citation',
  'app/assessment/search/page.tsx': 'passes ref_number to a badged card; prints none itself',
  'components/property-card.tsx': 'no citation text; matched on a variable name',
  // Prose or comments, not a rule citation.
  'components/compliance/CDCPathway.tsx': 'prose sentence naming a clause inside a calculation hint',
  'components/compliance/ConstraintArithmeticCard.tsx': 'matches a code comment only',
  'components/compliance/HeritageProvisionsCard.tsx': 'clause appears only in a fetch URL',
  'components/compliance/LocalProvisionsCard.tsx': 'clause appears only in a fetch URL and logs',
  'components/compliance/ProvisionsByTocStructure.tsx': 'clause_label only prefixes exported text; cards render via PageGroupedProvisions',
  // Not address-page rule cards.
  'app/for/students/page.tsx': 'marketing copy',
  'app/glossary/GlossaryClient.tsx': 'glossary copy',
  'app/quick-guide/page.tsx': 'help copy',
  'app/internal/dcp-review/DcpReviewQueue.tsx': 'internal reviewer tool showing raw rows',
  'app/internal/setback-review/SetbackReviewQueue.tsx': 'internal reviewer tool showing raw rows',
  // Separate renderer (@react-pdf); follow-up, not covered by this badge.
  'components/pdf/ContextSection.tsx': 'PDF export renderer',
  'components/pdf/ProvisionTable.tsx': 'PDF export renderer',
  'components/pdf/see-pages/Page2SiteContext.tsx': 'PDF export renderer',
};

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name === '.next' || name === '__tests__') continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (p.endsWith('.tsx')) out.push(p);
  }
  return out;
}

const files = [...walk(join(ROOT, 'components')), ...walk(join(ROOT, 'app'))]
  .map((p) => ({ rel: relative(ROOT, p).replace(/\\/g, '/'), src: readFileSync(p, 'utf8') }));
const citing = files.filter((f) => CITATION_MARKERS.some((m) => m.test(f.src)));

describe('citation badge inventory', () => {
  it('finds the known citation surfaces (the grep is not vacuous)', () => {
    const names = citing.map((f) => f.rel);
    for (const must of [
      'components/compliance/PageGroupedProvisions.tsx',
      'components/compliance/LandUseZoningCard.tsx',
      'components/compliance/StateLevelControls.tsx',
      'components/browse/ProvisionDisplay.tsx',
    ]) expect(names).toContain(must);
  });

  it('every citing component uses the shared badge', () => {
    const missing = citing
      .filter((f) => !(f.rel in EXEMPT) && !USES_BADGE.test(f.src))
      .map((f) => f.rel);
    expect(missing).toEqual([]);
  });

  it('every exemption still matches a real file with a reason', () => {
    for (const [rel, why] of Object.entries(EXEMPT)) {
      expect(why.length).toBeGreaterThan(5);
      expect(files.some((f) => f.rel === rel)).toBe(true);
    }
  });
});
