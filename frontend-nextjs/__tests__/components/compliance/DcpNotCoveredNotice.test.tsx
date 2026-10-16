import React from 'react';
import { render, screen } from '@testing-library/react';
import { DcpNotCoveredNotice } from '@/components/compliance/DcpNotCoveredNotice';
import { getNotCovered, chapterLabel } from '@/lib/not-covered';

describe('DcpNotCoveredNotice', () => {
  it('renders nothing for null or empty', () => {
    expect(render(<DcpNotCoveredNotice notCovered={null} />).container).toBeEmptyDOMElement();
    expect(render(<DcpNotCoveredNotice notCovered={{ council: 'x', chapters: [] }} />).container).toBeEmptyDOMElement();
  });

  it('names the chapters in plain wording without assurance words', () => {
    render(<DcpNotCoveredNotice notCovered={getNotCovered('Marrickville')} />);
    const text = screen.getByTestId('dcp-not-covered-notice').textContent ?? '';
    expect(text).toContain('Those rules are not shown here');
    expect(text).toContain('Part2 s14 unique env features');
    expect(text).not.toMatch(/\b(safe|compliant|verified|complete|comprehensive|accurate)\b/i);
  });

  it('getNotCovered is null for an unlisted council', () => {
    expect(getNotCovered('Parramatta')).toBeNull();
    expect(getNotCovered(undefined)).toBeNull();
  });

  it('chapterLabel makes a readable name', () => {
    expect(chapterLabel('chapter-e1-parking-access')).toBe('Chapter e1 parking access');
  });
});
