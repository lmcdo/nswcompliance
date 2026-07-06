/**
 * Golden + static-claims tests for the DA-outcome displays.
 *
 * The NSW DA tracking layer is a point-in-time extract frozen at 2023-04
 * (verified live 2026-07-06). These tests pin the honesty contract:
 * every temporal claim must come from the payload's data-derived window
 * (window_start/window_end/data_currency), never "last N years" arithmetic —
 * and when the window is absent the claim is suppressed, not defaulted.
 *
 * Payloads come from the same recorded golden fixtures the Python tests use
 * (tests/fixtures/brief_golden/) — real Concord / Canada Bay captures, no
 * hand-written values.
 */

import React from 'react';
import fs from 'fs';
import path from 'path';
import { render, screen } from '@testing-library/react';
import {
  DAOutcomesDisplay,
  RefusalStatsSentence,
  formatMonthYear,
  type DAOutcomesPayload,
  type RefusalStatsRow,
} from '@/components/reports/DAOutcomes';

/* eslint-disable @typescript-eslint/no-var-requires */
const STALE_PAYLOAD: DAOutcomesPayload =
  require('../../../../tests/fixtures/brief_golden/da_outcomes.json').output;
const STALE_STATS: RefusalStatsRow =
  require('../../../../tests/fixtures/brief_golden/da_refusal_stats.json').output;

const asIs = (s: string) => s;
const rowCount = STALE_PAYLOAD.outcomes?.length ?? 0;
const determinedCount = (STALE_PAYLOAD.outcomes ?? []).filter((r) => r.outcome != null).length;

// ---------------------------------------------------------------------------
// formatMonthYear
// ---------------------------------------------------------------------------

describe('formatMonthYear', () => {
  it('formats an ISO date to month-year', () => {
    expect(formatMonthYear('2023-04-29')).toBe('April 2023');
    expect(formatMonthYear('2018-01-01')).toBe('January 2018');
  });

  it('returns null for missing or non-ISO values — never a fabricated date', () => {
    expect(formatMonthYear(null)).toBeNull();
    expect(formatMonthYear(undefined)).toBeNull();
    expect(formatMonthYear('20230429151817.89')).toBeNull();
    expect(formatMonthYear('2023-13-01')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// DAOutcomesDisplay — golden stale-window rendering (Concord capture)
// ---------------------------------------------------------------------------

describe('DAOutcomesDisplay with the recorded stale-window capture', () => {
  it('fixture sanity: the capture is the stale-extract shape this PR fixes', () => {
    expect(STALE_PAYLOAD.data_currency).toBe('2023-04-29');
    expect(STALE_PAYLOAD.window_start).toBe('2020-08-20');
    expect(rowCount).toBeGreaterThan(0);
    expect(determinedCount).toBeGreaterThan(0);
  });

  it('states the data-derived lodgement window, not "last N years"', () => {
    const { container } = render(<DAOutcomesDisplay data={STALE_PAYLOAD} formatLabel={asIs} />);
    expect(container.textContent).toContain('lodged between August 2020 and February 2023');
    expect(container.textContent).not.toMatch(/last\s+\d+\s+years/i);
  });

  it('names the extent of the published tracking data', () => {
    const { container } = render(<DAOutcomesDisplay data={STALE_PAYLOAD} formatLabel={asIs} />);
    expect(container.textContent).toContain(
      'The published tracking data extends to applications lodged up to April 2023.'
    );
  });

  it('keeps the counts of recorded results', () => {
    const { container } = render(<DAOutcomesDisplay data={STALE_PAYLOAD} formatLabel={asIs} />);
    expect(container.textContent).toContain(`${rowCount} applications within 200 m`);
    expect(container.textContent).toContain(`${determinedCount} with a recorded result (0 refused)`);
  });

  it('renders outcome values verbatim from the data', () => {
    render(<DAOutcomesDisplay data={STALE_PAYLOAD} formatLabel={asIs} />);
    expect(screen.getAllByText('Approved').length).toBeGreaterThan(0);
  });
});

describe('DAOutcomesDisplay empty result', () => {
  it('states the layer extent instead of an undated "none in the last N years"', () => {
    const { container } = render(
      <DAOutcomesDisplay
        data={{ ...STALE_PAYLOAD, outcomes: [], window_start: null, window_end: null }}
        formatLabel={asIs}
      />
    );
    expect(container.textContent).toContain('No applications with a determination within 200 m');
    expect(container.textContent).toContain('extends to applications lodged up to April 2023');
    expect(container.textContent).not.toMatch(/last\s+\d+\s+years/i);
  });
});

describe('DAOutcomesDisplay without window fields (defensive)', () => {
  it('suppresses the temporal claim rather than defaulting it', () => {
    const { data_currency, window_start, window_end, ...bare } = STALE_PAYLOAD;
    const { container } = render(<DAOutcomesDisplay data={bare} formatLabel={asIs} />);
    expect(container.textContent).not.toMatch(/last\s+\d+\s+years/i);
    expect(container.textContent).not.toContain('lodged between');
    // the factual counts still render
    expect(container.textContent).toContain(`${rowCount} applications within 200 m`);
  });
});

// ---------------------------------------------------------------------------
// RefusalStatsSentence — golden stale-window rendering (Canada Bay capture)
// ---------------------------------------------------------------------------

describe('RefusalStatsSentence with the recorded stale-window capture', () => {
  it('states the window and the extent of the tracking data', () => {
    const { container } = render(
      <dd><RefusalStatsSentence stats={STALE_STATS} formatLabel={asIs} /></dd>
    );
    expect(container.textContent).toContain('lodged between January 2018 and April 2023');
    expect(container.textContent).toContain('the extent of the published tracking data');
    expect(container.textContent).not.toMatch(/last\s+\d+\s+years/i);
    expect(container.textContent).not.toMatch(/over the last/i);
  });

  it('keeps counts and rate from the data values', () => {
    const { container } = render(
      <dd><RefusalStatsSentence stats={STALE_STATS} formatLabel={asIs} /></dd>
    );
    expect(container.textContent).toContain('Of 992 applications determined');
    expect(container.textContent).toContain('918 granted development consent');
    expect(container.textContent).toContain('45 refused');
    expect(container.textContent).toContain('29 deferred commencement');
    expect(container.textContent).toContain('(4.5% refused)');
  });
});

describe('RefusalStatsSentence without a data window', () => {
  it('suppresses the counts instead of serving them with implied currency', () => {
    const { window_start, data_currency, ...noWindow } = STALE_STATS;
    const { container } = render(
      <dd><RefusalStatsSentence stats={noWindow} formatLabel={asIs} /></dd>
    );
    expect(container.textContent).toContain('Determination counts are not shown');
    expect(container.textContent).not.toContain('992');
    expect(container.textContent).not.toMatch(/last\s+\d+\s+years/i);
  });
});

// ---------------------------------------------------------------------------
// Static-claims guard — forbid undated recency phrasing at the source level,
// the way tests/test_conveyancing_truth.py forbids its phrases.
// ---------------------------------------------------------------------------

describe('static claims guard', () => {
  const componentSrc = fs.readFileSync(
    path.join(__dirname, '../../../components/reports/DAOutcomes.tsx'), 'utf-8'
  );
  const pageSrc = fs.readFileSync(
    path.join(__dirname, '../../../app/reports/intelligence-brief/page.tsx'), 'utf-8'
  );

  it('DAOutcomes.tsx contains no "last N years" phrasing', () => {
    expect(componentSrc).not.toMatch(/in the last/i);
    expect(componentSrc).not.toMatch(/over the last/i);
    expect(componentSrc).not.toMatch(/last\s*\{[^}]*years/i);
  });

  it('DAOutcomes.tsx never renders years_back/period_years', () => {
    // The fields stay on the payload types for compatibility, but no JSX
    // expression may interpolate them.
    expect(componentSrc).not.toMatch(/\{[^}]*years_back[^}]*\}[^;]*</);
    expect(componentSrc).not.toMatch(/period_years\s*\}/);
  });

  it('page.tsx delegates DA-outcome rendering to the guarded component', () => {
    expect(pageSrc).toContain('<DAOutcomesDisplay');
    expect(pageSrc).toContain('<RefusalStatsSentence');
    // the old inline undated sentence must not come back
    expect(pageSrc).not.toMatch(/over the last \{r\.period_years\}/);
    expect(pageSrc).not.toMatch(/in the last \{years\} years/);
  });
});
