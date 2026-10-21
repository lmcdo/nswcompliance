/**
 * The notice is the only thing that tells a reader why setback numbers are
 * missing or out of date. Three states: absent (older backend) says nothing,
 * null (check failed) says it could not check, and anything held back says why.
 * Only a change at the council's source is called an amendment: measured
 * 2026-10-22, 114 of 192 withheld rows are held for a number that did not match
 * the council's document, and calling those an amendment would be false.
 */
import { render, screen } from '@testing-library/react';
import { ReviewNotice } from '@/components/compliance/DcpStructuredControls';

const text = () => screen.getByTestId('dcp-review-pending').textContent;

describe('ReviewNotice', () => {
  test('rows withheld for a source change say the plan changed', () => {
    render(<ReviewNotice status={{ amendment_pending: true, withheld_source_changed: 42, withheld_other: 0 }} />);
    expect(text()).toBe(
      "The council's plan has changed — 42 controls are held back until reviewed. Check the council website for the latest version.",
    );
  });

  test('a single row reads in the singular', () => {
    render(<ReviewNotice status={{ amendment_pending: false, withheld_source_changed: 1, withheld_other: 0 }} />);
    expect(text()).toContain('1 control is held back until reviewed');
  });

  test('a pending chapter with nothing withheld still warns', () => {
    render(<ReviewNotice status={{ amendment_pending: true, withheld_source_changed: 0, withheld_other: 0 }} />);
    expect(text()).toContain('updated controls are pending review');
  });

  test('rows held for another reason NEVER say the plan changed', () => {
    render(<ReviewNotice status={{ amendment_pending: false, withheld_source_changed: 0, withheld_other: 13 }} />);
    expect(text()).toBe("13 controls are held back until checked against the council's plan.");
    expect(text()).not.toContain('changed');
  });

  test('both reasons are given, each with its own count', () => {
    render(<ReviewNotice status={{ amendment_pending: true, withheld_source_changed: 2, withheld_other: 3 }} />);
    expect(text()).toBe(
      "The council's plan has changed — 2 controls are held back until reviewed. Check the council website for the latest version. 3 more are held back until checked against the council's plan.",
    );
  });

  test('nothing pending shows nothing', () => {
    const { container } = render(<ReviewNotice status={{ amendment_pending: false, withheld_source_changed: 0, withheld_other: 0 }} />);
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
