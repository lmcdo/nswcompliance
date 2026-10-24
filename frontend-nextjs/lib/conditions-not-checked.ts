/**
 * Site conditions the rules lookup could not confirm, in plain words: what, why, where to check.
 *
 * The rules page serves condition rules (flood, bush fire, riparian, ...) only for a Yes. When the
 * property lookup could not answer, no rules show — which read exactly like "none apply". This lists
 * those conditions so the page can say so.
 *
 * prior-art-checked: lib/fact-answer.ts answers single facts and lib/hazard-unchecked.ts prints
 * hazard tiles; neither says which DCP rule groups are missing because a check failed.
 */
import { wasNotChecked } from './fact-answer';
import type { LookupCheck } from './lookup-not-checked';

export interface ConditionNotChecked {
  /** e.g. "Flood" */
  what: string;
  /** e.g. "the NSW flood map did not reply in time" */
  why: string;
  /** Where to check it yourself. */
  whereLabel: string;
  whereUrl: string;
}

const PORTAL = { whereLabel: 'NSW Planning Portal spatial viewer', whereUrl: 'https://www.planningportal.nsw.gov.au/spatialviewer' };
const RFS = { whereLabel: 'NSW RFS bush fire prone land check', whereUrl: 'https://www.rfs.nsw.gov.au/plan-and-prepare/building-in-a-bush-fire-area/planning-for-bush-fire-protection/bush-fire-prone-land/check-bfpl' };

type Why = 'no_reply' | 'busy' | 'error';
const WHY_WORDS: Record<Why, string> = {
  no_reply: 'did not reply in time',
  busy: 'was busy and turned the request away',
  error: 'returned an error',
};

interface Constraints {
  notChecked?: readonly string[] | null;
  notCheckedWhy?: Partial<Record<LookupCheck, Why>> | null;
  bushfireProne?: boolean | null;
  dcpFloodMap?: unknown;
  riparianLand?: unknown;
  greenwebUnchecked?: string;
  railOrBusyRoadUnchecked?: string;
  classifiedRoadUnchecked?: string;
}

function why(c: Constraints, source: string, check: LookupCheck): string {
  const w = c.notCheckedWhy?.[check];
  return `${source} ${w ? WHY_WORDS[w] : 'did not answer'}`;
}

/**
 * Conditions whose rules may be missing from the list because their check did not answer.
 * An empty list means every condition check answered (Yes or No).
 */
export function conditionsNotChecked(c: Constraints | null | undefined): ConditionNotChecked[] {
  if (!c) return [];
  const out: ConditionNotChecked[] = [];
  if (wasNotChecked(c, 'flood')) out.push({ what: 'Flood', why: why(c, 'the flood planning map', 'flood'), ...PORTAL });
  if (c.bushfireProne === null) out.push({ what: 'Bush fire', why: 'the bush fire prone land map did not answer', ...RFS });
  if (wasNotChecked(c, 'spatial_overlays')) {
    out.push({ what: 'Riparian land and waterways', why: why(c, 'our map database', 'spatial_overlays'), ...PORTAL });
  }
  if (wasNotChecked(c, 'precinct')) {
    out.push({ what: 'Precinct (area-specific council rules)', why: why(c, 'our precinct map', 'precinct'), whereLabel: 'council DCP precinct maps', whereUrl: 'https://www.planningportal.nsw.gov.au/spatialviewer' });
  }
  const plain = (note: string) => note.replace(/\.\s*$/, '');
  if (c.greenwebUnchecked) out.push({ what: 'Greenweb (Ku-ring-gai)', why: plain(c.greenwebUnchecked), ...PORTAL });
  if (c.railOrBusyRoadUnchecked) out.push({ what: 'Rail or busy road', why: plain(c.railOrBusyRoadUnchecked), ...PORTAL });
  if (c.classifiedRoadUnchecked) out.push({ what: 'State or classified road', why: plain(c.classifiedRoadUnchecked), ...PORTAL });
  return out;
}

/** Map a thrown error to why a check failed. */
export function whyFromError(error: unknown): Why {
  const msg = error instanceof Error ? `${error.name} ${error.message}` : String(error);
  if (/\b429\b|rate limit/i.test(msg)) return 'busy';
  if (/abort|timeout|timed out/i.test(msg)) return 'no_reply';
  return 'error';
}
