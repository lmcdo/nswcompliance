/** OC-20: the rule card shows "Citation not yet checked" unless the server said citation_checked === true. */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { CITATION_UNCHECKED_TOOLTIP } from '@/lib/citation-display';
import { PageGroupedProvisions, type Provision } from '@/components/compliance/PageGroupedProvisions';

const base: Provision = {
  id: 1, provision_text: 'Front setback is 6m.', v2_dcp_layer: 'generic', pdf_page: 4,
  source_council: 'woollahra',
};
const show = (p: Partial<Provision>) =>
  render(<PageGroupedProvisions provisions={[{ ...base, ...p }]} />);

describe('citation unchecked mark', () => {
  it('shows for citation_checked false', () => {
    show({ citation_checked: false });
    expect(screen.getAllByText(/Citation not yet checked/).length).toBeGreaterThan(0);
    expect(screen.getByTestId('citation-unchecked').getAttribute('title'))
      .toBe(CITATION_UNCHECKED_TOOLTIP);
  });
  it('shows when the field is missing (fail closed)', () => {
    show({});
    expect(screen.getByTestId('citation-unchecked')).toBeTruthy();
  });
  it('is absent for citation_checked true', () => {
    show({ citation_checked: true });
    expect(screen.queryByTestId('citation-unchecked')).toBeNull();
  });
});
