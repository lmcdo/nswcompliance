import { render, screen } from '@testing-library/react';
import { DcpPlanCheckNotice } from '@/components/compliance/DcpPlanCheckNotice';

const NOW = new Date('2026-11-10T00:00:00Z');
const base = { checked_on: '2026-11-10T02:00:26Z', never_checked: false, blocked: false };

describe('DcpPlanCheckNotice (DQ-153)', () => {
  it('shows the date when the last check is over 14 days old', () => {
    render(<DcpPlanCheckNotice check={{ ...base, checked_on: '2026-06-29T02:03:55Z' }} now={NOW} />);
    const el = screen.getByTestId('plan-check-notice');
    expect(el.textContent).toContain('29 June 2026');
    expect(el.textContent).toMatch(/last checked against the council/);
  });
  it('says so when the council website blocks our check, with the date', () => {
    render(<DcpPlanCheckNotice check={{ ...base, checked_on: '2026-09-24T05:01:43Z', blocked: true }} now={NOW} />);
    const el = screen.getByTestId('plan-check-notice');
    expect(el.textContent).toMatch(/not letting our check reach/);
    expect(el.textContent).toContain('24 September 2026');
  });
  it('shows a blocked chapter even when its date is fresh', () => {
    render(<DcpPlanCheckNotice check={{ ...base, blocked: true }} now={NOW} />);
    expect(screen.getByTestId('plan-check-notice').textContent).toMatch(/not letting our check reach/);
  });
  it('shows a chapter that was never checked', () => {
    render(<DcpPlanCheckNotice check={{ checked_on: null, never_checked: true, blocked: false }} now={NOW} />);
    expect(screen.getByTestId('plan-check-notice').textContent).toMatch(/not yet checked/);
  });
  it('shows nothing when checked recently', () => {
    render(<DcpPlanCheckNotice check={base} now={NOW} />);
    expect(screen.queryByTestId('plan-check-notice')).toBeNull();
  });
  it('shows nothing without data', () => {
    const { container, rerender } = render(<DcpPlanCheckNotice check={null} now={NOW} />);
    expect(container.firstChild).toBeNull();
    rerender(<DcpPlanCheckNotice check={undefined} now={NOW} />);
    expect(container.firstChild).toBeNull();
  });
});
