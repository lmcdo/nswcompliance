/**
 * SeppContextCard — zone-family copy switch.
 * The live Kincumber brief (C4 Environmental Living) described a conservation
 * zone as shop-top housing territory; these tests pin the per-family copy.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { SeppContextCard } from '@/components/reports/SeppContextCard';

const C4_CTX = {
  zone: 'C4',
  zoneFull: 'Environmental Living',
  zoneEpi: 'Central Coast Local Environmental Plan 2022',
  legislationUrl: 'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0084',
};

describe('SeppContextCard — conservation zone (C4)', () => {
  it('renders the conservation copy, keyed to the land-use table', () => {
    render(<SeppContextCard ctx={C4_CTX} />);
    expect(screen.getByText(/a conservation zone/)).toBeInTheDocument();
    expect(
      screen.getByText(/Whether a dwelling house or other housing is permitted on this land/),
    ).toBeInTheDocument();
    expect(screen.getByText(/land-use table in the LEP/)).toBeInTheDocument();
  });

  it('never mentions shop-top housing on a conservation zone', () => {
    const { container } = render(<SeppContextCard ctx={C4_CTX} />);
    expect(container.textContent).not.toMatch(/shop-top/i);
  });

  it('states the reforms reach only R1–R4', () => {
    const { container } = render(<SeppContextCard ctx={C4_CTX} />);
    expect(container.textContent).toContain('R1–R4');
  });
});

describe('SeppContextCard — rural zone (RU1)', () => {
  it('renders the rural copy without shop-top language', () => {
    const { container } = render(
      <SeppContextCard ctx={{ zone: 'RU1', zoneFull: 'Primary Production' }} />,
    );
    expect(screen.getByText(/a rural zone/)).toBeInTheDocument();
    expect(
      screen.getByText(/What housing is permitted on rural land is set by the zone/),
    ).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/shop-top/i);
  });
});

describe('SeppContextCard — centres zone (E1)', () => {
  it('keeps the shop-top sentence on a centres/business zone', () => {
    const { container } = render(
      <SeppContextCard ctx={{ zone: 'E1', zoneFull: 'Local Centre' }} />,
    );
    expect(container.textContent).toMatch(/shop-top housing/);
    expect(container.textContent).toMatch(/centre\/business zone/);
  });
});

describe('SeppContextCard — other zone (SP2)', () => {
  it('renders the generic land-use-table copy without shop-top language', () => {
    const { container } = render(
      <SeppContextCard ctx={{ zone: 'SP2', zoneFull: 'Infrastructure' }} />,
    );
    expect(container.textContent).toMatch(/reach only the residential zones/);
    expect(container.textContent).not.toMatch(/shop-top/i);
    expect(container.textContent).not.toMatch(/conservation zone/);
    expect(container.textContent).not.toMatch(/rural zone/);
  });
});

describe('SeppContextCard — residential zone (R2)', () => {
  it('renders the standards-missing residential copy', () => {
    const { container } = render(
      <SeppContextCard ctx={{ zone: 'R2', zoneFull: 'Low Density Residential' }} />,
    );
    expect(container.textContent).toMatch(/It.s a residential zone/);
    expect(container.textContent).not.toMatch(/shop-top/i);
  });
});
