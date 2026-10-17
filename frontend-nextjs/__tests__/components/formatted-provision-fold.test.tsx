/**
 * DQ-145 step 4: a whole long clause is served folded, never cut. Every word is in the page; one click opens it.
 */
import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import { FOLD_WORDS, FormattedProvisionText, wordCount } from '@/components/compliance/FormattedProvisionText';

const LONG = Array.from({ length: FOLD_WORDS + 50 }, (_, i) => `word${i}`).join(' ') + ' LASTWORD';

describe('long clause fold', () => {
  it('folds a clause over FOLD_WORDS but keeps every word in the page', () => {
    const { container } = render(<FormattedProvisionText text={LONG} theme="purple" />);
    expect(screen.getByTestId('clause-fold')).toBeInTheDocument();
    expect(container.querySelector('[data-folded="true"]')).not.toBeNull();
    expect(container.textContent).toContain('LASTWORD');
    const btn = screen.getByRole('button', { name: `Show full clause (${wordCount(LONG)} words)` });
    fireEvent.click(btn);
    expect(container.querySelector('[data-folded="false"]')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Show less' })).toHaveAttribute('aria-expanded', 'true');
  });

  it('a clause at or under FOLD_WORDS is not folded', () => {
    const short = Array.from({ length: FOLD_WORDS }, (_, i) => `w${i}`).join(' ');
    render(<FormattedProvisionText text={short} theme="purple" />);
    expect(screen.queryByTestId('clause-fold')).toBeNull();
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('counts words, not characters', () => {
    expect(wordCount('a  b\nc')).toBe(3);
    expect(wordCount(null)).toBe(0);
  });
});
