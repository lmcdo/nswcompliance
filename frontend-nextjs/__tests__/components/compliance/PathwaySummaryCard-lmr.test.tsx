import React from 'react';
import { render, screen } from '@testing-library/react';
import { PathwaySummaryCard } from '@/components/compliance/PathwaySummaryCard';

const base = { propertyData: {}, zoneCode: 'R2' };

describe('PathwaySummaryCard Low and Mid-Rise line', () => {
  it('true renders Applicable', () => {
    render(<PathwaySummaryCard {...base} housingLmrApplicable={true} />);
    expect(screen.getByText('Applicable')).toBeInTheDocument();
  });

  it('false renders the not-in-area wording', () => {
    render(<PathwaySummaryCard {...base} housingLmrApplicable={false} />);
    expect(screen.getByText('Not in a Low and Mid-Rise housing area')).toBeInTheDocument();
    expect(screen.queryByText('Applicable')).not.toBeInTheDocument();
  });

  it('null renders Not checked, never Applicable or Not applicable', () => {
    render(<PathwaySummaryCard {...base} housingLmrApplicable={null} />);
    expect(screen.getByText('Not checked: the planning map did not answer')).toBeInTheDocument();
    expect(screen.queryByText('Applicable')).not.toBeInTheDocument();
    // The Exempt & Complying line has its own "Not applicable"; scope to the Housing SEPP line.
    const line = screen.getByText(/Housing SEPP \(LMR\):/).closest('span') as HTMLElement;
    expect(line).not.toHaveTextContent(/Not applicable/);
    expect(line).not.toHaveTextContent(/: Applicable/);
  });

  it('omitted behaves as null', () => {
    render(<PathwaySummaryCard {...base} />);
    expect(screen.getByText('Not checked: the planning map did not answer')).toBeInTheDocument();
  });
});
