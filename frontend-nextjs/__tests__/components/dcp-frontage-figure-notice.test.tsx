import { render, screen } from '@testing-library/react';
import { DcpFrontageFigureNotice } from '@/components/compliance/DcpFrontageFigureNotice';

describe('DcpFrontageFigureNotice', () => {
  it('renders a link to the figure page', () => {
    render(
      <DcpFrontageFigureNotice
        items={[{ chapter_key: 'a', page: 28, figure: '14E.9-6', pdf_url: 'https://x/a.pdf#page=28' }]}
      />,
    );
    expect(screen.getByTestId('dcp-frontage-figure-notice')).toHaveTextContent(
      'Upper-level setbacks apply to some street frontages in this centre: see Figure 14E.9-6, page 28',
    );
    const a = screen.getByRole('link', { name: 'see Figure 14E.9-6, page 28' });
    expect(a).toHaveAttribute('href', 'https://x/a.pdf#page=28');
    expect(a).toHaveAttribute('target', '_blank');
    expect(a).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('renders nothing when empty or undefined', () => {
    const { container, rerender } = render(<DcpFrontageFigureNotice items={[]} />);
    expect(container).toBeEmptyDOMElement();
    rerender(<DcpFrontageFigureNotice items={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('DcpFrontageFigureNotice when the lookup failed', () => {
  it('says the figures could not be loaded instead of showing nothing', () => {
    render(<DcpFrontageFigureNotice items={[]} failed />);
    expect(screen.getByTestId('dcp-frontage-figure-notice')).toHaveTextContent('could not be loaded');
  });
});
