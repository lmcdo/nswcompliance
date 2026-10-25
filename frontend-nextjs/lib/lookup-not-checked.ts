/**
 * Property lookup checks that did not answer (everything except the hazard maps, which have
 * lib/hazard-unchecked.ts).
 *
 * A check whose source failed, timed out, was rate-limited or ran out of time tells us nothing about
 * the lot. It is named in `PlanningConstraints.notChecked` and its fact stays null — never a default,
 * never "No".
 *
 * prior-art-checked: reuse not viable because lib/hazard-unchecked.ts ALL_HAZARDS is read by the
 * hazard printers (SEE intake, findings, project summary); adding non-hazard keys there would print
 * "Bush fire"-style lines for zoning and roads.
 */
export type LookupCheck =
  | 'planning_layers' // zoning, height, FSR, lot size, heritage, local provisions (layerintersect)
  | 'lot_shape' // lot boundary: lot dimensions
  | 'tod' // TOD and accelerated TOD maps
  | 'roads' // road hierarchy near the lot
  | 'spatial_overlays' // PostGIS overlays: APU, foreshore, riparian, key sites, TOD, acid sulfate, ...
  | 'dual_occupancy' // dual occupancy prohibition map
  | 'sepp_exclusions' // low-mid-rise, complying and exempt exclusion maps
  | 'flood' // flood planning map
  | 'corner_lot' // corner lot and street frontage
  | 'classified_road' // State / classified road the lot fronts
  | 'acid_sulfate' // no class from the planning layers AND the PostGIS fallback did not answer
  | 'precinct'; // DCP precinct lookup (precinct boundaries) failed

export const LOOKUP_CHECKS: readonly LookupCheck[] = [
  'planning_layers', 'lot_shape', 'tod', 'roads', 'spatial_overlays',
  'dual_occupancy', 'sepp_exclusions', 'flood', 'corner_lot', 'classified_road', 'acid_sulfate', 'precinct',
];

/** One time limit for the whole lookup, under the 30 s function limit in vercel.json. */
export const LOOKUP_BUDGET_MS = 25_000;

/**
 * Preview-only switch to see the "Not checked" notice on a real page: LOOKUP_FAIL_CHECKS=precinct,roads
 * makes those checks fail through their own failure path. Ignored on production (VERCEL_ENV), so a stray
 * setting can never serve "Not checked" to real users. Runs only when VERCEL_ENV=preview or NODE_ENV=development. Wired for: planning_layers, lot_shape, tod, roads, precinct.
 */
export function forcedLookupFailure(check: LookupCheck): Error | null {
  // Only on a Vercel preview or a local dev server: an unset VERCEL_ENV in a production build is not a preview.
  if (process.env.VERCEL_ENV === 'production') return null;
  if (process.env.VERCEL_ENV !== 'preview' && process.env.NODE_ENV !== 'development') return null;
  const named = (process.env.LOOKUP_FAIL_CHECKS ?? '').split(',').map((s) => s.trim());
  return named.includes(check) ? new Error(`forced by LOOKUP_FAIL_CHECKS (${check})`) : null;
}
