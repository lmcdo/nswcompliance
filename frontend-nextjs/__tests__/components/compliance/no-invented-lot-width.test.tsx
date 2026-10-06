/**
 * prior-art-checked: `__tests__/components/compliance/DcpRequestCta.test.tsx` (the
 * render + mocked-fetch convention followed here), `__tests__/lib/lot-area-not-invented.test.ts`
 * (the same defect class on the setbacks path, #1230), `lib/see/propertyUtils.ts`
 * (`lmrFrontageStatus`, the function the invented width was fed to), and
 * `__tests__/components/compliance/lep-sepp-live-citations.test.tsx`. No parallel surface.
 *
 * An unknown lot frontage must not be replaced by a plausible one.
 *
 * Until 2026-10-06 `regulatory-constants.ts` held `DEFAULT_LOT_WIDTH_M: 15`, and
 * `StateLevelControls` put it at the end of the lotWidth chain. 15 is the single most
 * permissive value that still reads as a real suburban frontage, because the LMR
 * minimums are 12m (dual occupancy), 12m (manor house) and 15m (multi dwelling
 * housing) — so an invented 15 cleared ALL THREE. `lmrFrontageStatus(15).excluded`
 * is asserted empty below, which is the whole reason the default was dangerous
 * rather than merely wrong.
 *
 * Two measured consequences, and they pull in opposite directions, which is why
 * both are tested:
 *
 *   1. The amber panel in StateLevelControls renders only when something is
 *      EXCLUDED. A 15 emptied that list, so the panel vanished and the reader saw
 *      no frontage caveat at all — which reads as "frontage is fine".
 *   2. HousingSEPPEligibilityCard printed "Frontage: 15m" as this property's
 *      frontage and ran its eligibility fetch on it — even though that card
 *      ALREADY skips the fetch and asks for a frontage when it has none. The
 *      constant was defeating a guard that was already in place, which is the part
 *      worth remembering: the fix is mostly deletion.
 *
 * This is a mounted, live surface, unlike the setbacks path in #1230:
 * `app/assessment/page.tsx:563` renders StateLevelControls, which renders this card.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import { HousingSEPPEligibilityCard } from '@/components/compliance/HousingSEPPEligibilityCard';
import { NSW_PLANNING_CONSTANTS } from '@/lib/regulatory-constants';
import { LMR_FRONTAGE_MINIMUMS, lmrFrontageStatus } from '@/lib/see/propertyUtils';

describe('why 15 was the worst possible default', () => {
  it('clears every LMR frontage minimum, so it excluded nothing', () => {
    const status = lmrFrontageStatus(15);
    expect(status.excluded).toEqual([]);
    expect(status.eligible).toHaveLength(Object.keys(LMR_FRONTAGE_MINIMUMS).length);
  });

  it('sits exactly on the highest of the three minimums', () => {
    const minimums = Object.values(LMR_FRONTAGE_MINIMUMS).map((m) => m.minM);
    expect(Math.max(...minimums)).toBe(15);
  });

  it('a real narrow frontage is excluded, so the check itself works', () => {
    // Guards against the above passing because lmrFrontageStatus returns nothing.
    const narrow = lmrFrontageStatus(11);
    expect(narrow.excluded.map((e) => e.devType).sort()).toEqual([
      'dual_occupancy',
      'manor_house',
      'multi_dwelling',
    ]);
    const mid = lmrFrontageStatus(13);
    expect(mid.excluded.map((e) => e.devType)).toEqual(['multi_dwelling']);
    expect(mid.eligible.map((e) => e.devType).sort()).toEqual(['dual_occupancy', 'manor_house']);
  });
});

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
    expect('MIN_LOT_WIDTH_DUAL_OCC_M' in housingSepp).toBe(true);
  });
});

describe('HousingSEPPEligibilityCard with no frontage', () => {
  beforeEach(() => {
    global.fetch = jest.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({}) }),
    ) as unknown as jest.Mock;
  });
  afterEach(() => jest.resetAllMocks());

  it('asks for the frontage instead of assessing eligibility', async () => {
    render(
      <HousingSEPPEligibilityCard zoneCode="R2" lotSize={620} lotWidth={null} isLMRArea />,
    );
    expect(await screen.findByText(/frontage width are needed/i)).toBeInTheDocument();
  });

  it('never runs the eligibility check on a frontage it does not have', async () => {
    render(
      <HousingSEPPEligibilityCard zoneCode="R2" lotSize={620} lotWidth={null} isLMRArea />,
    );
    await screen.findByText(/frontage width are needed/i);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('does not print 15m, or any number, as the frontage', async () => {
    const { container } = render(
      <HousingSEPPEligibilityCard zoneCode="R2" lotSize={620} lotWidth={null} isLMRArea />,
    );
    await screen.findByText(/frontage width are needed/i);
    expect(container.textContent).not.toMatch(/Frontage:\s*\d/);
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
      <HousingSEPPEligibilityCard zoneCode="R2" lotSize={620} lotWidth={null} isLMRArea />,
    );
    await screen.findByText(/frontage width are needed/i);
    expect(container.textContent).not.toContain('Frontage:');
    expect(container.textContent).not.toMatch(/Frontage:\s*m/);
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

  it('prints the measured frontage and sends it to the check', async () => {
    render(<HousingSEPPEligibilityCard zoneCode="R2" lotSize={620} lotWidth={11.4} isLMRArea />);

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    const body = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    expect(body.lotWidth).toBe(11.4);
    // The measured value, not a default.
    expect(body.lotWidth).not.toBe(15);

    expect(await screen.findByText(/11.4m/)).toBeInTheDocument();
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

describe('StateLevelControls resolves a frontage without inventing one', () => {
  const src = readStripped('components', 'compliance', 'StateLevelControls.tsx');

  it('is read, so the assertions below are not vacuous', () => {
    expect(src.length).toBeGreaterThan(2000);
    expect(src).toContain('battleaxeAwareLotWidth');
  });

  it('ends the lotWidth chain in null, not a constant', () => {
    expect(src).toMatch(/const lotWidth: number \| null =/);
    expect(src).toMatch(/\?\?\s*propertyData\?\.constraints\?\.lotWidth\s*\?\?\s*null;/);
    expect(src).not.toMatch(/DEFAULT_LOT_WIDTH_M/);
  });

  it('does not hide the whole LMR section when the frontage is unknown', () => {
    // Gating the section on lotWidth would trade a false answer for a silent one.
    expect(src).toMatch(/showHousingSEPPSection = isLMRArea && lotSize;/);
    expect(src).not.toMatch(/showHousingSEPPSection = isLMRArea && lotSize && lotWidth/);
  });

  it('says the frontage minimums were not checked, rather than rendering nothing', () => {
    // The amber panel only fires on an exclusion, so a missing frontage would
    // otherwise produce no frontage text at all.
    expect(src).toMatch(/lotWidth == null &&/);
    expect(src).toMatch(/Frontage width not available for this property/);
    expect(src).toMatch(/have not been checked/);
  });
});
