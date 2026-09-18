/**
 * The DQ-78 notice as a reader actually meets it, not as a helper function returns it.
 *
 * `__tests__/lib/map-scrambled-provision-text.test.ts` pins the detector. This pins the
 * component contract the detector exists for: an affected provision says where its
 * characters came from, an ordinary one says nothing, and — the rule that matters — the
 * binding controls living inside a scrambled row are still rendered at full strength.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import { FormattedProvisionText } from '@/components/compliance/FormattedProvisionText';

/** A City of Sydney locality provision: a real control, then the map's street labels. */
const CONTROL_LINE = 'This locality is bounded by Ashmore Street to the north.';
const SCRAMBLED_LINE =
  'Zen B H i i t a n h S n d S in fi t g e r e S ld y e tr s t ee S t t d ree E t n l A e ' +
  'li y s o h t P t m A a v r o enu k e r e R S oa t M r F o d i x e t B c A u e h v r e r ' +
  't e o ll w n R s u o R e a o d ad W a l k e r S t r e e t B o u n d a r y S t r e e t';
const MIXED = `${CONTROL_LINE}\n${SCRAMBLED_LINE}`;

const PLAIN =
  'Buildings are to be no more than 9.5 metres in height above existing ground level and ' +
  'are to be set back at least 3 metres from the primary street boundary in accordance ' +
  'with the setback diagram for this locality. Development is to provide active frontages ' +
  'at ground level and to maintain the existing pattern of subdivision along the street.';

describe('FormattedProvisionText with map-scrambled text', () => {
  it('tells the reader the characters came off a map image', () => {
    render(<FormattedProvisionText text={MIXED} />);
    expect(screen.getByTestId('map-text-notice')).toBeInTheDocument();
    expect(screen.getByRole('note')).toHaveTextContent(/came off a map image/i);
  });

  it('says nothing on an ordinary provision', () => {
    render(<FormattedProvisionText text={PLAIN} />);
    expect(screen.queryByTestId('map-text-notice')).not.toBeInTheDocument();
  });

  it('still shows the binding control inside the scrambled row', () => {
    // The harmful direction the DQ-78 note names: never let the warning cost a control.
    render(<FormattedProvisionText text={MIXED} />);
    expect(screen.getByText(/bounded by Ashmore Street to the north/)).toBeInTheDocument();
  });

  it('does not dim the control line, only the figure text', () => {
    const { container } = render(<FormattedProvisionText text={MIXED} />);
    const dimmed = container.querySelectorAll('[data-testid="map-scrambled-line"]');
    expect(dimmed.length).toBeGreaterThan(0);
    dimmed.forEach((el) => {
      expect(el.textContent).not.toContain('bounded by Ashmore Street');
    });
  });

  it('keeps the scrambled characters in the document rather than deleting them', () => {
    // A planner checking the council's PDF needs to find what we read.
    const { container } = render(<FormattedProvisionText text={MIXED} />);
    expect(container.textContent).toContain('W a l k e r');
  });

  it('links to the source page when the caller knows it', () => {
    render(<FormattedProvisionText text={MIXED} sourceUrl="https://example.gov.au/dcp.pdf" sourcePage={14} />);
    const link = screen.getByRole('link', { name: /open the source PDF \(page 14\)/i });
    expect(link).toHaveAttribute('href', 'https://example.gov.au/dcp.pdf');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });

  it('still renders the notice when no source link is available', () => {
    render(<FormattedProvisionText text={MIXED} />);
    expect(screen.getByTestId('map-text-notice')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });
});
