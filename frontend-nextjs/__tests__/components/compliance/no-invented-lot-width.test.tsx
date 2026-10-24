/**
 * An unknown lot width must not be replaced by a plausible one.
 *
 * Until 2026-10-06 `regulatory-constants.ts` held `DEFAULT_LOT_WIDTH_M: 15`, which cleared every
 * Housing SEPP lot width minimum, so an unknown width read as "width is fine". The card now takes
 * `lotWidthRange: {min,max} | null` (measured from the street edge, lib/geometry/street-frontage.ts);
 * null means "not measured" and the card must ask for the width, skip the eligibility fetch, and
 * print no width. StateLevelControls must not reintroduce a numeric fallback.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import { HousingSEPPEligibilityCard } from '@/components/compliance/HousingSEPPEligibilityCard';
import { NSW_PLANNING_CONSTANTS } from '@/lib/regulatory-constants';

describe('the constant is gone from the shipped object, not just from the source', () => {
  it('HOUSING_SEPP carries no default lot width', () => {
    const housingSepp = NSW_PLANNING_CONSTANTS.HOUSING_SEPP as Record<string, unknown>;
    expect(housingSepp).toBeDefined();
    expect('DEFAULT_LOT_WIDTH_M' in housingSepp).toBe(false);
  });

  it('carries no other key holding a bare default width either', () => {
    // A rename would walk straight past the assertion above.
    const housingSepp = NSW_PLANNING_CONSTANTS.HOUSING_SEPP as Record<string, unknown>;
    const widthish = Object.keys(housingSepp).filter(
      (k) => /DEFAULT/i.test(k) && /WIDTH|FRONTAGE/i.test(k),
    );
    expect(widthish).toEqual([]);
  });

  it('still carries the real minimums, so the fix deleted the default and nothing else', () => {
    const housingSepp = NSW_PLANNING_CONSTANTS.HOUSING_SEPP as Record<string, unknown>;
    expect(Object.keys(housingSepp).length).toBeGreaterThan(0);
  });
});

describe('HousingSEPPEligibilityCard with no lot width', () => {
  beforeEach(() => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
    ) as unknown as jest.Mock;
  });
  afterEach(() => jest.resetAllMocks());

  it('asks for the frontage instead of assessing eligibility', async () => {
    render(
      <HousingSEPPEligibilityCard zoneCode="R2" lotSize={620} lotWidthRange={null} isLMRArea />,
    );
    expect(await screen.findByText(/lot width at the front building line are needed/i)).toBeInTheDocument();
  });

  it('never runs the eligibility check on a frontage it does not have', async () => {
    render(
      <HousingSEPPEligibilityCard zoneCode="R2" lotSize={620} lotWidthRange={null} isLMRArea />,
    );
    await screen.findByText(/lot width at the front building line are needed/i);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('does not print 15m, or any number, as the frontage', async () => {
    const { container } = render(
      <HousingSEPPEligibilityCard zoneCode="R2" lotSize={620} lotWidthRange={null} isLMRArea />,
    );
    await screen.findByText(/lot width at the front building line are needed/i);
    expect(container.textContent).not.toMatch(/Lot width measured from the street:\s*\d/);
    expect(container.textContent).not.toContain('15m');
  });

  it('shows no property-summary frontage line at all on this branch', async () => {
    /**
     * This pins WHY the `lotWidth != null ? ... : 'Not available'` ternary at the
     * frontage line is unreachable today, and the mutation harness proved it:
     * reverting that line to a bare `{lotWidth}m` fails no test, because a null
     * width skips the fetch, `data` stays null, and the component early-returns
     * the ask-for-a-frontage card before the summary ever renders.
     *
     * The ternary is kept as a guard against a future change to that early
     * return, and the harness carries the reason rather than a silently dropped
     * row. What IS observable is asserted here: no frontage line, not an empty one.
     */
    const { container } = render(
      <HousingSEPPEligibilityCard zoneCode="R2" lotSize={620} lotWidthRange={null} isLMRArea />,
    );
    await screen.findByText(/lot width at the front building line are needed/i);
    expect(container.textContent).not.toContain('Lot width measured from the street:');
  });
});

describe('HousingSEPPEligibilityCard with a real frontage', () => {
  /** Shape taken from the component's own reads, so the happy path still renders. */
  const eligibilityPayload = {
    eligibleTypes: [
      {
        developmentType: 'dual_occupancy',
        displayName: 'Dual Occupancy',
        description: 'Two dwellings on one lot',
        isEligible: true,
        assessmentStatus: 'eligible',
        eligibilityReason: 'Meets the minimum lot width',
        standards: [],
      },
    ],
    eligibleCount: 1,
    totalChecked: 1,
  };

  beforeEach(() => {
    // The route's envelope is { success, data }; the component throws
    // result.error otherwise, which is how the first draft of this test rendered
    // "Unknown error" instead of the card.
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true, data: eligibilityPayload }),
      }),
    ) as unknown as jest.Mock;
  });
  afterEach(() => jest.resetAllMocks());

  it('prints the measured width range and sends it to the check', async () => {
    render(
      <HousingSEPPEligibilityCard
        zoneCode="R2"
        lotSize={620}
        lotWidthRange={{ min: 11.4, max: 13.2 }}
        isLMRArea
      />,
    );

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(body.lotWidthMin).toBe(11.4);
    expect(body.lotWidthMax).toBe(13.2);
    // The measured values, not a default.
    expect(body.lotWidth).toBeUndefined();

    expect(await screen.findByText(/11\.4m narrowest in the front half, 13\.2m widest/)).toBeInTheDocument();
    expect(screen.getByText(/Lot width measured from the street:/)).toBeInTheDocument();
  });
});

/**
 * StateLevelControls is ~1,600 lines and mounts a tree of fetching children, so its
 * two changed decisions are asserted on source with comments stripped rather than by
 * rendering it. The behavioural assertions above cover the card, which is where the
 * figure was actually printed.
 *
 * Comments are stripped because THIS FILE'S OWN HEADER names the forbidden constant
 * and the number 15, and so does the provenance comment left at the fix site.
 */
import { readFileSync } from 'fs';
import { join } from 'path';

const readStripped = (...parts: string[]) =>
  readFileSync(join(__dirname, '..', '..', '..', ...parts), 'utf8')
    .replace(/\{\s*\/\*[\s\S]*?\*\/\s*\}/g, ' ') // {/* JSX comment */}
    .replace(/\/\*[\s\S]*?\*\//g, ' ') //           /* block */
    .replace(/(^|[^:])\/\/.*$/gm, '$1 ') //         // line, and trailing
    .replace(/\s+/g, ' ');

describe('StateLevelControls resolves a lot width without inventing one', () => {
  const src = readStripped('components', 'compliance', 'StateLevelControls.tsx');

  it('is read, so the assertions below are not vacuous', () => {
    expect(src.length).toBeGreaterThan(2000);
    expect(src).toContain('lotWidthRange');
  });

  it('takes the width range from the measured street edge only, with no constant', () => {
    expect(src).toMatch(/const lotWidthRange = widthRange\(propertyData\?\.cornerLot\?\.streetFrontage\);/);
    expect(src).not.toMatch(/DEFAULT_LOT_WIDTH_M/);
    expect(src).not.toMatch(/lotWidthRange = [^;]*(\?\?|\|\|)\s*[\d.]/);
  });

  it('holds no hardcoded lot width table', () => {
    expect(src).not.toMatch(/LMR_FRONTAGE_MINIMUMS|lmrFrontageStatus/);
  });

  it('does not hide the whole LMR section when the width is unknown', () => {
    expect(src).toMatch(/showHousingSEPPSection = zone && isLMREligibleZone\(zone\) && lotSize;/);
    expect(src).not.toMatch(/showHousingSEPPSection = [^;]*lotWidth/);
  });

  it('says the width minimums were not checked, rather than rendering nothing', () => {
    expect(src).toMatch(/lotWidthRange == null &&/);
    expect(src).toMatch(/have not been checked/);
  });
});
