// prior-art-checked: 2026-11-23. No helper in frontend-nextjs/lib builds a walk-against-limit scale or the at-a-glance sentences for the evidence page (grep lib/ for "walk_low_m", "limit_m", "buildScale": only
// lib/evidence-statement.ts, which holds the payload types). Every figure here is read from the payload (limit, range, margins, distances): nothing regulatory is typed in this file.
import type { Evidence, EvidenceExclusion } from '@/lib/evidence-statement';

const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);

/** A whole number with thousands separators ('1,103'). */
export const fmtNum = (n: number): string => Math.round(n).toLocaleString('en-AU', { maximumFractionDigits: 0 });

/** A distance for a sentence: metres to one decimal under a kilometre, otherwise kilometres to one decimal ('9.9 km'). Matches the server's wording. */
export function distanceWords(metres: number): string {
  if (!finite(metres) || metres < 0) return 'a distance that could not be read';
  const m = Number(metres.toFixed(1));   // round first, so 999.96 m reads '1.0 km' and never '1000 m'
  if (m >= 1000) return `${(m / 1000).toFixed(1)} km`;
  return `${m.toFixed(1).replace(/\.0$/, '')} m`;
}

export type WalkKind = 'over' | 'within' | 'straddles' | 'unknown';
export interface WalkVerdict { kind: WalkKind; limit: number | null; low: number | null; high: number | null; best: number | null; gapM: number | null }

/** Where the walking range sits against the limit. 'over' = even the shortest case is over; 'within' = even the longest case is inside; 'straddles' = the range crosses the limit. */
export function walkVerdict(w: Evidence['walk']): WalkVerdict {
  const limit = finite(w.limit_m) ? w.limit_m : null, low = finite(w.walk_low_m) ? w.walk_low_m : null, high = finite(w.walk_high_m) ? w.walk_high_m : null;
  let best: number | null = finite(w.walk_best_m) ? w.walk_best_m : null;
  if (best === null && low !== null && finite(w.margin_low_m)) best = low + w.margin_low_m;   // the measured walk is the low end plus its margin
  if (best !== null && best < 0) best = null;   // a negative distance is not a measured walk
  if (best === null) return { kind: 'unknown', limit, low, high, best, gapM: null };   // no measured walk, no verdict: the range alone is never turned into 'within' or 'over'
  if (limit === null || low === null || high === null || low > high || limit <= 0 || low < 0 || best < low || best > high) return { kind: 'unknown', limit, low, high, best, gapM: null };   // a measured walk outside its own range is an inconsistent answer: no verdict
  if (low > limit) return { kind: 'over', limit, low, high, best, gapM: low - limit };
  if (high <= limit) return { kind: 'within', limit, low, high, best, gapM: limit - high };
  return { kind: 'straddles', limit, low, high, best, gapM: null };
}

/** The words for the first tile and the bottom line. The measured walk against the limit, in metres; no colour verdict and no 'complies': it says where the walk sits and that a person decides. */
export function verdictWords(v: WalkVerdict, detail: string | null): { pill: string; sentence: string; margin: string | null; bottom: string } {
  const lim = v.limit !== null ? fmtNum(v.limit) : '';
  const has = v.best !== null && v.limit !== null;
  const diff = has && v.best !== null && v.limit !== null ? Math.abs(v.best - v.limit) : v.gapM ?? 0;
  if (v.kind === 'over') {
    return {
      pill: `Over the ${lim} m limit`,
      sentence: `${has ? `The shortest walk is ${fmtNum(v.best as number)} m, which is ${fmtNum(diff)} m over the ${lim} m limit` : `The walk is longer than the ${lim} m limit`} the Low and Mid Rise housing rules use. On this measure the lot does not meet the walking test.`,
      margin: has ? `Shortest walk ${fmtNum(v.best as number)} m: ${fmtNum(diff)} m over.` : null,
      bottom: 'On this measure the lot does not meet the walking test.',
    };
  }
  if (v.kind === 'within') {
    return {
      pill: `Within the ${lim} m limit`,
      sentence: `${has ? `The shortest walk is ${fmtNum(v.best as number)} m, which is ${fmtNum(diff)} m under the ${lim} m limit` : `The walk is shorter than the ${lim} m limit`} the Low and Mid Rise housing rules use. On this measure the lot meets the walking test.`,
      margin: has ? `Shortest walk ${fmtNum(v.best as number)} m: ${fmtNum(diff)} m under.` : null,
      bottom: 'On this measure the lot meets the walking test.',
    };
  }
  if (v.kind === 'straddles') {
    return {
      pill: `Too close to the ${lim} m limit to call`,
      sentence: `${has ? `The shortest walk is ${fmtNum(v.best as number)} m against the ${lim} m limit.` : `The walk is close to the ${lim} m limit.`} That is close enough that a small difference in the route could put the lot on the other side, so this tool cannot say whether the lot meets the walking test. Check the route on the ground.`,
      margin: has ? `Shortest walk ${fmtNum(v.best as number)} m.` : null,
      bottom: 'The walk is too close to the limit for this tool to say whether the lot meets the walking test.',
    };
  }
  if (v.best !== null) {   // a measured walk with no usable verdict: show the walk, say the test could not be applied
    return { pill: 'Walking-test result unavailable', sentence: `The shortest walk is ${fmtNum(v.best)} m. This tool could not apply the walking limit to it.${detail ? ` ${detail}` : ''}`, margin: `Shortest walk ${fmtNum(v.best)} m.`, bottom: 'The walking test could not be applied to the measured walk.' };
  }
  return { pill: 'No walk measured', sentence: detail ?? 'No walk was measured.', margin: null, bottom: 'No walk was measured, so the walking test could not be applied.' };
}

export interface ScaleModel {
  min: number; max: number; ticks: number[]; limitPct: number; bandLeftPct: number; bandWidthPct: number; bestPct: number | null;
}

/** The axis and positions for the range-against-limit graphic. Null when the numbers cannot be drawn (missing, not finite, or a range that is back to front). Positions are percentages of the axis. */
export function buildScale(limit: number | null, low: number | null, high: number | null, best: number | null): ScaleModel | null {
  if (!finite(limit) || !finite(low) || !finite(high) || limit <= 0 || low > high || low < 0) return null;
  const vals = [limit, low, high, ...(finite(best) ? [best] : [])];
  const span = Math.max(...vals) - Math.min(...vals);
  const step = span <= 600 ? 100 : span <= 1500 ? 200 : 500;   // a round tick spacing; a display choice, not a planning figure
  const min = Math.max(0, Math.floor((Math.min(...vals) - step) / step) * step);
  const max = Math.ceil((Math.max(...vals) + step) / step) * step;
  const ticks: number[] = [];
  for (let t = min; t <= max; t += step) ticks.push(t);
  const pct = (v: number) => ((v - min) / (max - min)) * 100;
  return { min, max, ticks, limitPct: pct(limit), bandLeftPct: pct(low), bandWidthPct: pct(high) - pct(low), bestPct: finite(best) ? pct(best) : null };
}

export interface ExclusionTally { total: number; clear: number; excludes: number; other: EvidenceExclusion[]; clearRows: EvidenceExclusion[] }

/** Counts for the summary box, from the rows themselves so they cannot drift from the table. 'other' = every row that is not clear (excluded, possible, could not be determined, not checked). */
export function tally(rows: EvidenceExclusion[]): ExclusionTally {
  const clearRows = rows.filter((r) => r.result === 'clear');
  const other = rows.filter((r) => r.result !== 'clear');
  return { total: rows.length, clear: clearRows.length, excludes: rows.filter((r) => r.result === 'excludes').length, other, clearRows };
}

/** The rows shown as cards in section 2: every row that is not clear, and any clear row that carries distances (flood, pipelines) so the reader sees the number behind the answer. */
export function cardRows(rows: EvidenceExclusion[]): EvidenceExclusion[] {
  return rows.filter((r) => r.result !== 'clear' || (!!r.facts && Object.keys(r.facts).length > 0));
}

/** A council name for display: 'KU-RING-GAI' becomes 'Ku-ring-gai', 'CITY OF SYDNEY' becomes 'City of Sydney'. Only the case changes; the letters are the payload's. */
export function lgaName(lga: string | null | undefined): string | null {
  if (typeof lga !== 'string' || !lga.trim()) return null;
  const small = new Set(['of', 'and', 'the']);
  return lga.trim().toLowerCase().split(' ').map((w, i) => (i > 0 && small.has(w) ? w : w.charAt(0).toUpperCase() + w.slice(1))).join(' ');
}

/** The first letter of a sentence in capitals ('the lot is ...' becomes 'The lot is ...'); the rest is untouched. */
export const sentence = (s: string): string => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

export const rowTitle = (r: { title?: string | null; clause?: string | null }): string => r.title ?? r.clause ?? 'Paragraph not named';

/** The status of a row as a symbol and words (never colour alone). */
export function statusOf(result: string): { symbol: string; words: string } {
  switch (result) {
    case 'clear': return { symbol: '✓', words: 'None found' };
    case 'excludes': return { symbol: '■', words: 'Excluded' };
    case 'warn': return { symbol: '◐', words: 'Check needed' };
    case 'not_checked': return { symbol: '○', words: 'Not checked' };
    default: return { symbol: '○', words: 'Could not be determined' };
  }
}
