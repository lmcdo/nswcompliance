import React from 'react';
import { render, screen } from '@testing-library/react';
import { DcpNotCoveredNotice } from '@/components/compliance/DcpNotCoveredNotice';
import { getNotCovered, chapterLabel } from '@/lib/not-covered';
import notCoveredData from '@/shared/not-covered-councils.json';
import { MAY_APPLY_REASONS } from '@/lib/may-apply-reasons';

describe('DcpNotCoveredNotice', () => {
  it('renders nothing for null or empty', () => {
    expect(render(<DcpNotCoveredNotice notCovered={null} />).container).toBeEmptyDOMElement();
    expect(render(<DcpNotCoveredNotice notCovered={{ council: 'x', chapters: [] }} />).container).toBeEmptyDOMElement();
  });

  it('names the part, the reason and the plan page in plain wording without assurance words', () => {
    render(<DcpNotCoveredNotice notCovered={getNotCovered('Marrickville')} chapterPdfUrls={{ 'part2-s14-unique-env-features': 'https://x.test/m.pdf' }} />);
    const text = screen.getByTestId('dcp-not-covered-notice').textContent ?? '';
    expect(text).toContain('Rules for particular areas we could not place on the map');
    expect(text).toContain('their rules are not listed below');
    // the plan's own title from the not-covered list, not the internal chapter key
    expect(text).toContain('Part 2.14 Unique Environmental Features');
    expect(text).not.toContain('part2-s14');
    expect(text).toContain('The plan describes this area in words only, with no map.');
    expect(text).not.toMatch(/\b(safe|compliant|verified|complete|comprehensive|accurate|approved|confirmed|ensure)\b/i);
  });

  it('links to the plan at the page for a PDF, and shows no link without a URL', () => {
    const nc = getNotCovered('Marrickville');
    const flood = 'part2-s22-flood-management';
    const { rerender } = render(<DcpNotCoveredNotice notCovered={nc} chapterPdfUrls={{ [flood]: 'https://x.test/flood.pdf' }} />);
    expect(screen.getByRole('link', { name: 'Read it in the plan (page 6)' })).toHaveAttribute('href', 'https://x.test/flood.pdf#page=6');
    expect(screen.getAllByRole('link')).toHaveLength(1);
    expect(screen.getByText(MAY_APPLY_REASONS.PART_MAPPED)).toBeInTheDocument();
    rerender(<DcpNotCoveredNotice notCovered={nc} chapterPdfUrls={{}} />);
    expect(screen.queryByRole('link')).toBeNull();
    // a web page address cannot take a page anchor: link without it, never a broken one
    rerender(<DcpNotCoveredNotice notCovered={nc} chapterPdfUrls={{ [flood]: 'https://x.test/plan' }} />);
    expect(screen.getByRole('link')).toHaveAttribute('href', 'https://x.test/plan');
  });

  it('collapses the list when there are more than three parts, and not otherwise', () => {
    const many = render(<DcpNotCoveredNotice notCovered={getNotCovered('Canterbury-Bankstown')} />);
    expect(many.container.querySelector('details')).not.toBeNull();
    expect(screen.getAllByTestId('dcp-not-covered-chapter').length).toBeGreaterThan(3);
    many.unmount();
    const few = render(<DcpNotCoveredNotice notCovered={getNotCovered('Ashfield')} />);
    expect(few.container.querySelector('details')).toBeNull();
  });

  it('every listed part has a known reason sentence', () => {
    for (const council of Object.keys(notCoveredData)) {
      for (const ch of getNotCovered(council)?.chapters ?? []) {
        expect([council, ch.chapter_key, Boolean(ch.reason_text)]).toEqual([council, ch.chapter_key, true]);
      }
    }
  });

  it('getNotCovered is null for an unlisted council', () => {
    expect(getNotCovered('Hornsby')).toBeNull();
    expect(getNotCovered(undefined)).toBeNull();
  });

  it('chapterLabel makes a readable name', () => {
    expect(chapterLabel('chapter-e1-parking-access')).toBe('Chapter e1 parking access');
  });
});
