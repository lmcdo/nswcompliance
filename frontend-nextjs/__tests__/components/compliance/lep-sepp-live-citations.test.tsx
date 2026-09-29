/**
 * LEP / SEPP tab citations point at the live, in-force instrument — never a static
 * page image of one council's LEP.
 *
 * Before: HeritageProvisionsCard's clause 5.10 panel and LocalProvisionsCard's Key
 * Site panel rendered an Inner West LEP 2022 page image (and, for 5.10, an Inner
 * West legislation URL) for EVERY council, and both fetched /api/lep/provisions —
 * which answers from Inner West LEP 2022 by clause number alone — so a Waverley
 * lot was shown Inner West's clause text as its own.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { HeritageProvisionsCard } from '@/components/compliance/HeritageProvisionsCard';
import { LocalProvisionsCard } from '@/components/compliance/LocalProvisionsCard';
import { SeppCitationLink, seppHousingProvisionUrl } from '@/components/compliance/SeppCitationLink';
import type { LocalProvision } from '@/lib/nsw-planning-portal';

const IW_LEP = 'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457';
// Waverley LEP 2012 (epi-2012-0540, per lib/lep-local-provisions-mapping.ts)
const WAVERLEY_LEP = 'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2012-0540';

const IW_TEXT = {
  clauseNumber: '5.10',
  clauseTitle: 'Heritage conservation',
  provisionText: 'x'.repeat(200),
  pageNumber: 50,
};

beforeEach(() => {
  global.fetch = jest.fn(() =>
    Promise.resolve({ ok: true, json: () => Promise.resolve(IW_TEXT) })
  ) as jest.Mock;
});
afterEach(() => jest.resetAllMocks());

describe('HeritageProvisionsCard — clause 5.10', () => {
  it("links a non-Inner-West lot to its OWN LEP's live clause 5.10, with no static image or IW text", async () => {
    const { container } = render(
      <HeritageProvisionsCard
        heritage
        heritageType="Conservation Area - General"
        heritageLegislativeClause="Clause 5.10"
        heritageLegislationUrl={WAVERLEY_LEP}
        lga="Waverley"
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /expand provision/i }));

    const link = await screen.findByRole('link', { name: /view clause 5\.10/i });
    expect(link).toHaveAttribute('href', `${WAVERLEY_LEP}#sec.5.10`);
    expect(container.querySelector('img')).toBeNull();
    expect(container.textContent).not.toMatch(/Inner West/);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('still fetches stored clause text for an Inner West LEP 2022 lot', async () => {
    render(
      <HeritageProvisionsCard
        heritage
        heritageLegislativeClause="Clause 5.10"
        heritageLegislationUrl={IW_LEP}
        lga="Inner West"
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /expand provision/i }));
    await waitFor(() =>
      expect(global.fetch).toHaveBeenCalledWith('/api/lep/provisions?clause=5.10&epi=epi-2022-0457')
    );
  });

  it('shows no link at all when the Portal returned no legislation URL', async () => {
    render(<HeritageProvisionsCard heritage heritageLegislativeClause="Clause 5.10" />);
    fireEvent.click(screen.getByRole('button', { name: /expand provision/i }));
    expect(await screen.findByText(/did not return a legislation link/i)).toBeInTheDocument();
    expect(screen.queryByRole('link')).toBeNull();
  });
});

describe('LocalProvisionsCard — Key Site clause', () => {
  const waverleyKeySite = {
    title: 'Key site',
    epiName: 'Waverley Local Environmental Plan 2012',
    legislationUrl: WAVERLEY_LEP,
    mapType: 'KSM',
    clauseNumber: '6.9',
    pageNumber: 80,
  } as LocalProvision;

  it('never fetches Inner West text or renders a page image for another council', async () => {
    const { container } = render(<LocalProvisionsCard localProvisions={[waverleyKeySite]} />);
    fireEvent.click(screen.getByRole('button', { name: /expand provision/i }));

    const inline = await screen.findByRole('link', { name: /view clause 6\.9 in lep/i });
    expect(inline).toHaveAttribute('href', `${WAVERLEY_LEP}#sec.6.9`);
    expect(container.querySelector('img')).toBeNull();
    expect(container.textContent).not.toMatch(/Inner West/);
    expect(global.fetch).not.toHaveBeenCalled();
  });
});

describe('SEPP tab citation links', () => {
  it('deep-links SEPP (Housing) 2021 provisions on the in-force legislation view', () => {
    expect(seppHousingProvisionUrl('sec.24')).toBe(
      'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sec.24'
    );
    expect(seppHousingProvisionUrl('sch.11')).toBe(
      'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sch.11'
    );
  });

  it('renders an external link (new tab), not an image-modal button', () => {
    render(<SeppCitationLink href={seppHousingProvisionUrl('sec.68')} label="View clause 68" />);
    const link = screen.getByRole('link', { name: 'View clause 68' });
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });
});
