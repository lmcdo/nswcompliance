/**
 * Owner ruling 2026-11-16: the Pattern Book CDC check is hidden for the pilot. It required three different
 * lot-size minimums (900, 600 and 1500 m2) at once, so any lot under 1,500 m2 showed "Ineligible", and it
 * was built from the Exempt and Complying Codes Schedule 1 extraction, not the Pattern Book Development
 * Code (Part 3BA). Audit: ce-tabs-audit-sepp-lep-2026-11-16.md.
 * prior-art-checked: no test covered the Pattern Book surfaces; this lists every place that calls the route.
 */
import fs from 'fs';
import path from 'path';
import React from 'react';
import { render } from '@testing-library/react';
import { PATTERN_BOOK_CHECK_SHOWN } from '@/lib/pilot-focus';
import { PathwaySummaryCard } from '@/components/compliance/PathwaySummaryCard';

const ROOT = path.resolve(__dirname, '..', '..', '..');

describe('Pattern Book check is hidden for the pilot', () => {
  it('the switch is off', () => {
    expect(PATTERN_BOOK_CHECK_SHOWN).toBe(false);
  });

  it('the pathway summary shows no Pattern Book line, whatever the status', () => {
    for (const status of [undefined, 'INELIGIBLE', 'ELIGIBLE', 'CONDITIONAL'] as const) {
      const { container, unmount } = render(<PathwaySummaryCard patternBookStatus={status} exemptComplyingCount={4} />);
      expect(container.textContent).not.toMatch(/Pattern Book/);
      expect(container.textContent).toMatch(/Exempt & Complying/);
      unmount();
    }
  });

  it('every caller of the Pattern Book route is behind the switch', () => {
    for (const rel of ['components/compliance/StateLevelControls.tsx', 'components/compliance/ProvisionsByTocStructure.tsx']) {
      const src = fs.readFileSync(path.join(ROOT, rel), 'utf8');
      expect(src).toMatch(/import \{ PATTERN_BOOK_CHECK_SHOWN \} from '@\/lib\/pilot-focus'/);
      const at = src.indexOf("fetch('/api/pathway/pattern-book-eligibility'");
      expect(at).toBeGreaterThan(-1);
      expect(src.slice(Math.max(0, at - 400), at)).toMatch(/PATTERN_BOOK_CHECK_SHOWN/);
    }
    const state = fs.readFileSync(path.join(ROOT, 'components/compliance/StateLevelControls.tsx'), 'utf8');
    expect(state).toMatch(/\{PATTERN_BOOK_CHECK_SHOWN && \(\s*<PatternBookEligibilityCard/);
  });
});
