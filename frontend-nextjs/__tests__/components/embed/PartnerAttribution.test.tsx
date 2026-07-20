/**
 * PartnerAttribution drives the co-branding line on every non-duplex tool
 * embed. The trust boundary is that an UNBRANDED embed (no resolved partner)
 * must render nothing extra — a stray attribution on the public/direct embed
 * would falsely imply a partner. And a branded embed must show the exact
 * registered name, never a raw slug.
 */
import { render, screen } from '@testing-library/react';
import { PartnerAttribution } from '@/components/embed/PartnerAttribution';

describe('PartnerAttribution', () => {
  it('renders nothing when there is no partner (unbranded embed)', () => {
    const { container: nullContainer } = render(
      <PartnerAttribution partnerName={null} checkLabel="flood risk check" />,
    );
    expect(nullContainer).toBeEmptyDOMElement();

    const { container: undefContainer } = render(
      <PartnerAttribution partnerName={undefined} checkLabel="flood risk check" />,
    );
    expect(undefContainer).toBeEmptyDOMElement();
  });

  it('renders the partner name and the check label when branded', () => {
    render(<PartnerAttribution partnerName="Buildana" checkLabel="flood risk check" />);
    expect(screen.getByText('Buildana')).toBeInTheDocument();
    expect(screen.getByText(/A free flood risk check from/)).toBeInTheDocument();
  });
});
