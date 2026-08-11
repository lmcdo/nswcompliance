/**
 * plainReason — the display translation over engine reason strings.
 * The load-bearing case: the engine formats with :.0f, so a lot width of
 * 11.6 m renders "Lot width 12 m is below the minimum 12 m" — a visible
 * self-contradiction. The translation must never show equal numbers in a
 * below-minimum sentence.
 */

import { plainReason, type FormResult } from '@/lib/upzoning';

function form(reason: string, overrides: Partial<FormResult> = {}): FormResult {
  return {
    development_type: 'dual_occupancy',
    eligible: false,
    reason,
    unconfirmed: false,
    requires_lmr_area: false,
    min_lot_size_m2: null,
    min_lot_width_m: null,
    source_clause: null,
    legislation_url: null,
    effective_date: null,
    ...overrides,
  };
}

describe('plainReason — rounding collision (rule 4)', () => {
  it('equal displayed width numbers become "just under", never a contradiction', () => {
    const out = plainReason(form('Lot width 12 m is below the minimum 12 m'));
    expect(out).toBe('The street frontage is just under the 12 m minimum for this.');
    expect(out).not.toMatch(/12 m.*below.*12 m/);
  });

  it('equal displayed area numbers become "just under"', () => {
    const out = plainReason(form('Lot area 450 m² is below the minimum 450 m²'));
    expect(out).toContain('just under the 450 m² minimum');
  });

  it('distinct numbers state both plainly', () => {
    expect(plainReason(form('Lot area 302 m² is below the minimum 450 m²'))).toBe(
      'The block is 302 m² — this type needs at least 450 m².',
    );
    expect(plainReason(form('Lot width 10 m is below the minimum 12 m'))).toBe(
      'The frontage is 10 m — this type needs at least 12 m.',
    );
  });
});

describe('plainReason — hedge phrases never reach the user (rule 3)', () => {
  it.each([
    ['Not in a Low and Mid-Rise reform area (or area unconfirmed)'],
    ['Lot standard for this form is not in the dataset (treated conservatively)'],
    ['Some future reason (or area unconfirmed)'],
  ])('"%s" renders without internal hedges', (reason) => {
    const out = plainReason(form(reason));
    expect(out).not.toContain('or area unconfirmed');
    expect(out).not.toContain('treated conservatively');
  });
});

describe('plainReason — known reasons translate to plain sentences', () => {
  it('eligible always wins regardless of reason text', () => {
    const out = plainReason(
      form('Meets the applicable Housing SEPP standards (subject to a development application)', {
        eligible: true,
      }),
    );
    expect(out).toBe('Meets the standards — you can apply to build this here.');
  });

  it('heritage exclusion', () => {
    expect(
      plainReason(form('Excluded on heritage land — the Low and Mid-Rise reforms do not apply')),
    ).toBe('Heritage rules on this block switch off the 2025 pathways.');
  });

  it('TOD catchment', () => {
    expect(plainReason(form('Not in a Transport Oriented Development catchment'))).toContain(
      'station precinct',
    );
  });

  it('dual-occ prohibition', () => {
    expect(
      plainReason(form('Dual occupancy is prohibited on this lot (LEP local provision)')),
    ).toContain('specifically prohibits dual occupancies');
  });

  it('unknown reasons pass through verbatim (audit-trail fallback)', () => {
    expect(plainReason(form('Some brand new engine reason'))).toBe('Some brand new engine reason');
  });
});
