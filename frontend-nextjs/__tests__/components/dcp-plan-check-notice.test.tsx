import { render, screen } from '@testing-library/react';
import { DcpPlanCheckNotice } from '@/components/compliance/DcpPlanCheckNotice';

const NOW = new Date('2026-11-10T00:00:00Z');

describe('DcpPlanCheckNotice (DQ-153)', () => {
  it('shows the date when the last check is over 30 days old', () => {
    render(<DcpPlanCheckNotice checkedOn="2026-06-29T02:03:55Z" now={NOW} />);
    const el = screen.getByTestId('plan-check-notice');
    expect(el.textContent).toContain('29 June 2026');
    expect(el.textContent).toMatch(/last checked against the council/);
  });
  it('shows nothing when the plan was checked recently', () => {
    render(<DcpPlanCheckNotice checkedOn="2026-11-10T02:00:26Z" now={NOW} />);
    expect(screen.queryByTestId('plan-check-notice')).toBeNull();
  });
  it('shows nothing without a date', () => {
    const { container, rerender } = render(<DcpPlanCheckNotice checkedOn={null} now={NOW} />);
    expect(container.firstChild).toBeNull();
    rerender(<DcpPlanCheckNotice checkedOn={undefined} now={NOW} />);
    expect(container.firstChild).toBeNull();
  });
});
