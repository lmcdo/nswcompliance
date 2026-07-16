/**
 * Source-scan guards for the intelligence-brief page + granny-flat route copy
 * (#751 batch). These pin wording fixes that live inside non-exported page
 * internals, following the static-claims pattern in tests/test_conveyancing_truth.py.
 */

import fs from 'fs';
import path from 'path';

const PAGE_SRC = fs.readFileSync(
  path.join(__dirname, '..', '..', 'app', 'reports', 'intelligence-brief', 'page.tsx'),
  'utf8',
);

const GRANNY_ROUTE_SRC = fs.readFileSync(
  path.join(__dirname, '..', '..', 'app', 'api', 'satellite', 'granny-flat', 'route.ts'),
  'utf8',
);

describe('intelligence-brief page — unavailable-label classifier copy', () => {
  it('the catch-all no longer claims a promised field is "Not part of this brief"', () => {
    // The phrase may survive ONLY in the not-requested (optional add-on) branch —
    // count code lines, not comments.
    const codeLines = PAGE_SRC.split('\n').filter((l) => !l.trim().startsWith('//'));
    const occurrences = codeLines.filter((l) => /not part of this brief/i.test(l));
    expect(occurrences.length).toBeLessThanOrEqual(1);
    expect(occurrences.join('\n')).toContain('An optional add-on');
    expect(PAGE_SRC).not.toContain("detail: 'Not part of this brief.'");
  });

  it('retrieval misses route to a retry, not a shrug', () => {
    expect(PAGE_SRC).toContain(
      'This field could not be retrieved on this run — run the brief again to retry.',
    );
  });

  it('the "None here" branch no longer editorialises about good news', () => {
    expect(PAGE_SRC).not.toContain("For a constrained site that's good news");
  });

  it('the confidence legend no longer instructs readers to treat values as fact', () => {
    expect(PAGE_SRC).not.toContain('treat as fact');
    expect(PAGE_SRC).toContain('sourced directly from the official register');
  });

  it('the Data Gaps verify link is separated from the sentence by a space', () => {
    // The rendered text previously concatenated "…brief.Verify".
    expect(PAGE_SRC).toContain("{g.verify_url && ' '}");
  });
});

describe('intelligence-brief page — SEPP context copy lives in the shared card', () => {
  it('page no longer carries the blanket shop-top sentence', () => {
    expect(PAGE_SRC).not.toContain('shop-top housing');
    expect(PAGE_SRC).toContain("from '@/components/reports/SeppContextCard'");
  });
});

describe('granny-flat route — zone ineligibility message', () => {
  it('quotes the instrument scope instead of asserting an RU5 entitlement', () => {
    expect(GRANNY_ROUTE_SRC).not.toContain('only permitted in R1, R2, R3, R4, R5, and RU5');
    expect(GRANNY_ROUTE_SRC).toContain('R1–R5 or an equivalent zone');
    expect(GRANNY_ROUTE_SRC).toContain('A council LEP can separately permit secondary dwellings');
  });
});
