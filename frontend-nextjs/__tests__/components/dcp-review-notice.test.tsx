/**
 * The notice is the only thing that tells a reader why setback numbers are
 * missing or out of date. Three states: absent (older backend) says nothing,
 * null (check failed) says it could not check, and a pending change says so.
 */
import { render, screen } from '@testing-library/react';
import { ReviewNotice } from '@/components/compliance/DcpStructuredControls';

describe('ReviewNotice', () => {
  test('withheld rows are counted in the warning', () => {
    render(<ReviewNotice status={{ amendment_pending: true, withheld_controls: 42 }} />);
    expect(screen.getByTestId('dcp-review-pending').textContent).toBe(
      'Amendment detected — 42 controls are held back until reviewed. Check the council website for the latest version.',
    );
  });

  test('a single withheld row reads in the singular', () => {
    render(<ReviewNotice status={{ amendment_pending: false, withheld_controls: 1 }} />);
    expect(screen.getByTestId('dcp-review-pending').textContent).toContain('1 control is held back');
  });

  test('a pending chapter with nothing withheld still warns', () => {
    render(<ReviewNotice status={{ amendment_pending: true, withheld_controls: 0 }} />);
    expect(screen.getByTestId('dcp-review-pending').textContent).toContain('updated controls pending review');
  });

  test('nothing pending shows nothing', () => {
    const { container } = render(<ReviewNotice status={{ amendment_pending: false, withheld_controls: 0 }} />);
    expect(container.textContent).toBe('');
  });

  test('a failed check says it could not check - never silent', () => {
    render(<ReviewNotice status={null} />);
    expect(screen.getByTestId('dcp-review-status-unknown')).toBeTruthy();
    expect(screen.queryByTestId('dcp-review-pending')).toBeNull();
  });

  test('an older backend without the field shows nothing', () => {
    const { container } = render(<ReviewNotice status={undefined} />);
    expect(container.textContent).toBe('');
  });
});
