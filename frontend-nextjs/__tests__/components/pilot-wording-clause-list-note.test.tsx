/**
 * Owner ruling 2026-11-17: (1) when a project type other than a new house is picked in a pilot council, the
 * clause list is not shown and the page says why instead of the block vanishing; (2) the registration prompt no
 * longer promises "DCP coverage across NSW" (an all-councils style claim) and says the pilot covers ten councils.
 * prior-art-checked: extends your-project-summary.test.tsx (same fixtures and renderView idea); no test covered
 * VerifyRegistrationPrompt wording.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { buildLepRows, buildSiteFlags } from '@/lib/project-summary';
import { YourProjectSummaryView, CLAUSE_LIST_HOUSE_ONLY_TEXT } from '@/components/compliance/YourProjectSummary';
import { VerifyRegistrationPrompt } from '@/components/compliance/VerifyRegistrationPrompt';
import { PILOT_COUNCILS } from '@/lib/pilot-focus';

const LEP = { maxHeight: 9.5, maxFsr: 0.65, minLotSize: 480.5, lepName: 'Fixture Local Environmental Plan 2000', legislationUrl: 'https://example.test/lep' };

function view(over: Partial<React.ComponentProps<typeof YourProjectSummaryView>> = {}) {
  return render(
    <YourProjectSummaryView
      projectType="dual_occupancy"
      onProjectTypeChange={() => {}}
      lepRows={buildLepRows(LEP)}
      dcpRows={[]}
      unmapped={false}
      flags={buildSiteFlags(null)}
      {...over}
    />,
  );
}

describe('clause list note', () => {
  it('explains why the clause list is absent for another project type in a pilot council', () => {
    view({ clauseListNote: true });
    expect(screen.getByTestId('clause-list-note').textContent).toBe(CLAUSE_LIST_HOUSE_ONLY_TEXT);
    expect(CLAUSE_LIST_HOUSE_ONLY_TEXT).toMatch(/new house/);
  });
  it('is not shown when the clause list itself is shown', () => {
    view({ clauseListNote: true, planBrief: <div data-testid="brief">brief</div> });
    expect(screen.queryByTestId('clause-list-note')).toBeNull();
    expect(screen.getByTestId('brief')).toBeInTheDocument();
  });
  it('is not shown by default', () => {
    view();
    expect(screen.queryByTestId('clause-list-note')).toBeNull();
  });
});

describe('registration prompt wording', () => {
  it('names the private pilot and makes no across-NSW or date promise', () => {
    render(<VerifyRegistrationPrompt councilName="Sydney" address="1 Test Street" />);
    const t = document.body.textContent ?? '';
    expect(t).toContain(`private pilot for ${PILOT_COUNCILS.length} councils`);
    expect(t).toMatch(/No promise of dates/);
    expect(t).not.toMatch(/across NSW/i);
    expect(t).not.toMatch(/expanding/i);
  });
});
