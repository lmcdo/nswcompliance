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

// The unavailable-label classifier was extracted out of page.tsx into its own
// module so its wording could be unit-tested directly. These source-scan guards
// pin the copy, so they must follow it: scan both files, or a future extraction
// silently turns every "not.toContain" assertion below into a pass over a file
// that no longer holds the string.
const UNAVAILABLE_SRC = fs.readFileSync(
  path.join(__dirname, '..', '..', 'app', 'reports', 'intelligence-brief', 'unavailable.ts'),
  'utf8',
);

const CLASSIFIER_SRC = `${PAGE_SRC}\n${UNAVAILABLE_SRC}`;

describe('intelligence-brief page — unavailable-label classifier copy', () => {
  it('the catch-all no longer claims a promised field is "Not part of this report"', () => {
    // The phrase may survive ONLY in the not-requested (optional add-on) branch —
    // count code lines, not comments.
    const codeLines = CLASSIFIER_SRC.split('\n').filter((l) => !l.trim().startsWith('//'));
    const occurrences = codeLines.filter((l) => /not part of this report/i.test(l));
    expect(occurrences.length).toBeLessThanOrEqual(1);
    expect(occurrences.join('\n')).toContain('An optional add-on');
    expect(CLASSIFIER_SRC).not.toContain("detail: 'Not part of this report.'");
  });

  it('retrieval misses route to a retry, not a shrug', () => {
    expect(CLASSIFIER_SRC).toContain(
      'This field could not be retrieved on this run — run the report again to retry.',
    );
  });

  it('the "None here" branch no longer editorialises about good news', () => {
    expect(CLASSIFIER_SRC).not.toContain("For a constrained site that's good news");
  });

  it('the field-level renderer shows the explanation, not just the short label', () => {
    // A bare "None here" cannot distinguish a checked-clear result from an
    // unchecked one. The per-field branch must render u.detail alongside u.label.
    const fieldBranch = PAGE_SRC.slice(
      PAGE_SRC.indexOf('const u = describeUnavailable(df.reason, section'),
      PAGE_SRC.indexOf('lot dimensions rendered readably'),
    );
    expect(fieldBranch).toContain('{u.label}');
    expect(fieldBranch).toContain('{u.detail}');
  });

  it('the confidence legend no longer instructs readers to treat values as fact', () => {
    expect(PAGE_SRC).not.toContain('treat as fact');
    expect(PAGE_SRC).toContain(
      'Taken directly from an official government source (the LEP, the cadastre, the Valuer General).',
    );
  });

  it('the Data Gaps verify link is separated from the sentence by a space', () => {
    // The rendered text previously concatenated "…report.Verify".
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
