/**
 * Strata plan from the Planning Portal lot records for one property.
 *
 * The Portal's /lot endpoint returns every lot on the parcel. A strata scheme is the common
 * property ("CP/-/SP9807") plus one lot per unit ("1/-/SP9807", "2/-/SP9807", ...). The page
 * used to decide "strata" only from a missing valuation or a "5/" in the address, and so showed
 * 14 Gale St Concord as not strata while its lot records name strata plan SP9807 (2026-10-19).
 *
 * Pure function: no fetch. Returns null unless EVERY lot belongs to the same strata plan, so a
 * mixed parcel is never called strata on one stray record.
 */
export interface StrataPlan {
  /** e.g. "SP9807" (SS = strata subdivision plan also accepted). */
  plan: string;
  /** Unit lots on the plan, not counting the common property. */
  units: number;
}

const STRATA_LOT = /^(CP|\d+)\/[^/]*\/((?:SP|SS)\d+)$/i;

export function strataPlanFromLots(descriptions: Array<string | null | undefined>): StrataPlan | null {
  const parsed = descriptions
    .map((d) => (d ?? '').trim().match(STRATA_LOT))
    .filter((m): m is RegExpMatchArray => m !== null);
  if (parsed.length === 0 || parsed.length !== descriptions.length) return null;
  const plans = new Set(parsed.map((m) => m[2].toUpperCase()));
  if (plans.size !== 1) return null;
  const units = parsed.filter((m) => m[1].toUpperCase() !== 'CP').length;
  return { plan: [...plans][0], units };
}
