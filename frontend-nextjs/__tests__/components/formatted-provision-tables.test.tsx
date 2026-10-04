/**
 * DQ-125 as the reader meets it: a served rule's table renders as a table, and no tag is printed.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import { FormattedProvisionText, FormattedProvisionTextInline } from '@/components/compliance/FormattedProvisionText';

const TEXT = 'Side setbacks are to comply with the table below.\n\n<table><thead><tr><th>Floor</th>' +
  '<th>Side setback (min.)</th></tr></thead><tbody><tr><td>Ground Floor</td><td>0.9m</td></tr>' +
  '<tr><td>Second Floor</td><td>1.5m</td></tr></tbody></table>\n\nSee also Part B.';

describe('FormattedProvisionText with a table', () => {
  it('renders a real table holding every cell, and prints no markup', () => {
    const { container } = render(<FormattedProvisionText text={TEXT} theme="green" />);
    expect(screen.getByTestId('provision-table')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Side setback (min.)' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '1.5m' })).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/<\/?(table|thead|tbody|tr|th|td)\b/i);
    expect(container.textContent).toContain('Side setbacks are to comply');
    expect(container.textContent).toContain('See also Part B.');
  });

  it('text without a table renders no table', () => {
    render(<FormattedProvisionText text="C1 Buildings are not to exceed 9.5m." theme="green" />);
    expect(screen.queryByTestId('provision-table')).toBeNull();
  });

  it('the inline preview prints rows as text, not tags', () => {
    const { container } = render(<FormattedProvisionTextInline text={TEXT} />);
    expect(container.textContent).not.toMatch(/<\/?(table|tr|td)\b/i);
  });
});
