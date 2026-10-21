// Reading a Site Report start from the link — pure helper extracted so the
// rules are unit-testable, the same way unavailable.ts and provenance.ts were.
//
// The plotdetect.com.au hero form submits to brief.plotdetect.com.au with
// ?address=<typed text>&plan=<intent>. The page starts the report from the
// address (lat/lng resolve server-side, exactly as the landing-search event
// does) and preselects the plan chip.
//
// Anything the link carries is untrusted: an address is trimmed and capped,
// and a plan that is not one of the intent chips is dropped rather than shown.

import { INTENT_CHIPS } from '@/components/reports/BriefIntentOverlay';

/** Longer than any real NSW street address; a cap, not a validator. */
export const MAX_URL_ADDRESS_LENGTH = 200;

const INTENT_VALUES = new Set(INTENT_CHIPS.map((c) => c.value));

export interface BriefUrlStart {
  address: string | null;
  intent: string | null;
}

export function readBriefStartParams(
  params: { get(name: string): string | null } | null | undefined,
): BriefUrlStart {
  if (!params) return { address: null, intent: null };

  const rawAddress = params.get('address');
  const address =
    typeof rawAddress === 'string' &&
    rawAddress.trim().length > 0 &&
    rawAddress.trim().length <= MAX_URL_ADDRESS_LENGTH
      ? rawAddress.trim()
      : null;

  const rawPlan = params.get('plan');
  const intent = typeof rawPlan === 'string' && INTENT_VALUES.has(rawPlan.trim()) ? rawPlan.trim() : null;

  return { address, intent };
}
