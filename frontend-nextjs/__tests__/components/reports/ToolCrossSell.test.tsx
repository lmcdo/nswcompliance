/**
 * ToolCrossSell — shared cross-sell component for satellite tool result pages.
 *
 * Key invariants:
 *  - Never cross-sells itself
 *  - Granny flat is always first in the card order (income angle)
 *  - maxCards default is 2
 *  - Address is URL-encoded in hrefs
 *  - Returns null when address is empty
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';

const ADDRESS = '42 Test Rd Leichhardt NSW 2040';

// ---------------------------------------------------------------------------
// Never cross-sells itself
// ---------------------------------------------------------------------------

describe('ToolCrossSell — never shows current tool', () => {
  it('solar-yield result does not show solar-yield card', () => {
    render(<ToolCrossSell currentTool="solar-yield" address={ADDRESS} />);
    expect(screen.queryByText('Rooftop Solar Yield Underwriter')).not.toBeInTheDocument();
  });

  it('shadow-detector result does not show shadow-detector card', () => {
    render(<ToolCrossSell currentTool="shadow-detector" address={ADDRESS} />);
    expect(screen.queryByText('Construction Shadow Detector')).not.toBeInTheDocument();
  });

  it('flood-truth result does not show flood-truth card', () => {
    render(<ToolCrossSell currentTool="flood-truth" address={ADDRESS} />);
    expect(screen.queryByText('Wet Season Flood Truth')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Granny flat is first for solar, shadow, flood
// ---------------------------------------------------------------------------

describe('ToolCrossSell — planning controls is first card for satellite tools', () => {
  it('solar-yield shows planning controls as first card', () => {
    render(<ToolCrossSell currentTool="solar-yield" address={ADDRESS} />);
    const links = screen.getAllByRole('link');
    expect(links[0]).toHaveTextContent('Planning Controls Assessment');
  });

  it('shadow-detector shows planning controls as first card', () => {
    render(<ToolCrossSell currentTool="shadow-detector" address={ADDRESS} />);
    const links = screen.getAllByRole('link');
    expect(links[0]).toHaveTextContent('Planning Controls Assessment');
  });

  it('flood-truth shows planning controls as first card', () => {
    render(<ToolCrossSell currentTool="flood-truth" address={ADDRESS} />);
    const links = screen.getAllByRole('link');
    expect(links[0]).toHaveTextContent('Planning Controls Assessment');
  });
});

// ---------------------------------------------------------------------------
// maxCards default = 2
// ---------------------------------------------------------------------------

describe('ToolCrossSell — card count', () => {
  it('renders 2 cards by default', () => {
    render(<ToolCrossSell currentTool="solar-yield" address={ADDRESS} />);
    expect(screen.getAllByRole('link')).toHaveLength(2);
  });

  it('renders 1 card when maxCards=1', () => {
    render(<ToolCrossSell currentTool="solar-yield" address={ADDRESS} maxCards={1} />);
    expect(screen.getAllByRole('link')).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// Address encoding in hrefs
// ---------------------------------------------------------------------------

describe('ToolCrossSell — address encoding', () => {
  it('encodes address in granny flat link href', () => {
    render(<ToolCrossSell currentTool="solar-yield" address={ADDRESS} />);
    const link = screen.getByRole('link', { name: /Check granny flat eligibility/i });
    expect(link).toHaveAttribute('href', expect.stringContaining('/granny-flat'));
    expect(link).toHaveAttribute('href', expect.stringContaining(encodeURIComponent(ADDRESS)));
  });

  it('encodes spaces in address as %20', () => {
    render(<ToolCrossSell currentTool="flood-truth" address={ADDRESS} />);
    const links = screen.getAllByRole('link');
    links.forEach((link) => {
      const href = link.getAttribute('href') ?? '';
      if (href.includes('address=')) {
        expect(href).toContain('%20');
        expect(href).not.toMatch(/address=[^&]*\s/);
      }
    });
  });
});

// ---------------------------------------------------------------------------
// Empty address — renders nothing
// ---------------------------------------------------------------------------

describe('ToolCrossSell — empty address', () => {
  it('renders nothing when address is empty string', () => {
    const { container } = render(<ToolCrossSell currentTool="solar-yield" address="" />);
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when address is whitespace only', () => {
    const { container } = render(<ToolCrossSell currentTool="solar-yield" address="   " />);
    expect(container.firstChild).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// "Also check" label
// ---------------------------------------------------------------------------

describe('ToolCrossSell — section label', () => {
  it('renders "Also check" label', () => {
    render(<ToolCrossSell currentTool="shadow-detector" address={ADDRESS} />);
    expect(screen.getByText('Also check')).toBeInTheDocument();
  });
});
