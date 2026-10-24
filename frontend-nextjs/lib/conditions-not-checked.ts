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

/** Every lookup check, in words. A Record so a new LookupCheck cannot be left out (TypeScript fails). */
const CHECK_WORDS: Record<LookupCheck, { what: string; source: string; where: typeof PORTAL }> = {
  planning_layers: { what: 'Zoning, height, floor space and heritage', source: 'the NSW planning layers', where: PORTAL },
  lot_shape: { what: 'Lot size and shape', source: 'the NSW lot boundary map', where: PORTAL },
  tod: { what: 'Transport Oriented Development area', source: 'the TOD map', where: PORTAL },
  roads: { what: 'Nearby road types', source: 'the road map', where: PORTAL },
  spatial_overlays: { what: 'Riparian land, foreshore and other overlays', source: 'our map database', where: PORTAL },
  dual_occupancy: { what: 'Dual occupancy prohibition area', source: 'the dual occupancy map', where: PORTAL },
  sepp_exclusions: { what: 'Complying and exempt development exclusions', source: 'the state policy exclusion maps', where: PORTAL },
  flood: { what: 'Flood', source: 'the flood planning map', where: PORTAL },
  corner_lot: { what: 'Corner lot and street frontage', source: 'the road and lot maps', where: PORTAL },
  classified_road: { what: 'State or classified road', source: 'the classified road map', where: PORTAL },
  acid_sulfate: { what: 'Acid sulfate soils', source: 'the acid sulfate soils map', where: PORTAL },
  precinct: { what: 'Precinct (area-specific council rules)', source: 'our precinct map', where: PORTAL },
};

/**
 * Checks that did not answer, so rules or facts that depend on them may be missing.
 * An empty list means every lookup check answered (Yes or No).
 */
export function conditionsNotChecked(c: Constraints | null | undefined): ConditionNotChecked[] {
  if (!c) return [];
  const out: ConditionNotChecked[] = [];
  const plain = (note: string) => note.replace(/\.\s*$/, '');
  const failed = new Set(Array.isArray(c.notChecked) ? c.notChecked : (Object.keys(CHECK_WORDS) as LookupCheck[]));
  for (const [check, w] of Object.entries(CHECK_WORDS) as Array<[LookupCheck, (typeof CHECK_WORDS)[LookupCheck]]>) {
    if (!failed.has(check)) continue;
    // A check with its own plain-words note says it that way.
    const own = check === 'classified_road' ? c.classifiedRoadUnchecked : undefined;
    out.push({ what: w.what, why: own ? plain(own) : why(c, w.source, check), ...w.where });
  }
  if (c.bushfireProne == null) out.push({ what: 'Bush fire', why: 'the bush fire prone land map did not answer', ...RFS });
  if (c.greenwebUnchecked) out.push({ what: 'Greenweb (Ku-ring-gai)', why: plain(c.greenwebUnchecked), ...PORTAL });
  if (c.railOrBusyRoadUnchecked) out.push({ what: 'Rail or busy road', why: plain(c.railOrBusyRoadUnchecked), ...PORTAL });
  if (c.classifiedRoadUnchecked && !failed.has('classified_road')) {
    out.push({ what: 'State or classified road', why: plain(c.classifiedRoadUnchecked), ...PORTAL });
  }
  return out;
}

/** Map a thrown error to why a check failed. */
export function whyFromError(error: unknown): Why {
  const msg = error instanceof Error ? `${error.name} ${error.message}` : String(error);
  if (/\b429\b|rate limit/i.test(msg)) return 'busy';
  if (/abort|timeout|timed out/i.test(msg)) return 'no_reply';
  return 'error';
}
