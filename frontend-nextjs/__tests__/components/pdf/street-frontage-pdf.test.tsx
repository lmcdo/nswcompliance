import React from 'react';

jest.mock('@react-pdf/renderer', () => {
  const R = require('react');
  const el = (n: string) => ({ children }: { children?: React.ReactNode }) => R.createElement(n, null, children);
  return { Page: el('div'), Text: el('span'), View: el('div'), StyleSheet: { create: (s: unknown) => s },
    Font: { register: jest.fn() }, Image: el('div'), Link: el('a') };
});

import { renderToStaticMarkup } from 'react-dom/server';
import { ContextSection } from '@/components/pdf/ContextSection';

const prop = (ld: Record<string, unknown>) => ({
  property: { address: 'a', zone: 'R2', former_council: 'x', heritage_status: { in_hca: false }, lot_dimensions: ld },
});

describe('SEE PDF context section frontage', () => {
  const render = (ld: Record<string, unknown>) =>
    renderToStaticMarkup(React.createElement(ContextSection as never, prop(ld) as never));

  it('measured: prints street frontage text; short side only as lot width', () => {
    const html = render({ area: 600, frontage: 22.4, street_frontage_text: '13.3 m along Berrigan St' });
    expect(html).toContain('13.3 m along Berrigan St');
    expect(html).toContain('Lot width (shorter side):');
    expect(html).not.toMatch(/Frontage:<\/span><span[^>]*>22\.4/i);
  });
  it('null: prints not measured', () => {
    const html = render({ area: 600, frontage: 22.4, street_frontage_text: null });
    expect(html).toContain('not measured');
    expect(html).not.toContain('nullm');
  });
});

import { Page2SiteContext } from '@/components/pdf/see-pages/Page2SiteContext';

describe('SEE page 2 frontage rows', () => {
  const render = (ld: Record<string, unknown>) =>
    renderToStaticMarkup(React.createElement(Page2SiteContext as never, {
      computed: {
        property: { address: 'a', zone: 'R2', former_council: 'x' },
        heritage_status: { in_hca: false },
        lot_dimensions: ld,
        zoneCode: 'R2', pathway: 'DA', reason: '', housingSeppApplies: false,
        siteSuitabilityText: '', footerRef: '',
      },
    } as never));

  it('measured: street frontage text in both tables, short side only as lot width', () => {
    const html = render({ area: 600, frontage: 22.4, depth: 30, street_frontage_text: '13.3 m along Berrigan St' });
    expect(html.split('13.3 m along Berrigan St').length - 1).toBe(2);
    expect(html).toContain('Lot Width (shorter side):');
    expect(html).not.toMatch(/Frontage:<[^>]*>[^<]*<[^>]*>22\.4/);
  });
  it('null: not measured, and never "nullm"', () => {
    const html = render({ area: 600, frontage: null, depth: 30, street_frontage_text: null });
    expect(html).toContain('not measured');
    expect(html).not.toContain('nullm');
  });
});
