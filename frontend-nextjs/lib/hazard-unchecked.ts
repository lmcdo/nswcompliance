/**
 * Hazard map lookups that did not answer.
 *
 * Each NSW hazard map (bush fire, mine subsidence, contaminated land, ...) is one network call. A
 * call that fails or times out tells us nothing about the lot, so it must never read as "No".
 * `PlanningConstraints.uncheckedHazards` lists the maps that did not answer; every place that
 * prints a hazard checks it first and prints HAZARD_NOT_CHECKED instead of "No".
 *
 * prior-art-checked: reuse not viable because the only existing three-state wording
 * (lib/flood/flood-map.ts UNREACHABLE) is flood-specific; the conveyancing report's
 * "Not assessed" is Python (scripts/generate_conveyancing_report.py).
 */
export type HazardKey =
  | 'bushfire'
  | 'mine_subsidence'
  | 'contaminated_land'
  | 'drinking_water'
  | 'coastal'
  | 'anef';

export const HAZARD_NOT_CHECKED = 'Not checked — the government map did not answer';

/** Short form for tight table cells. */
export const HAZARD_NOT_CHECKED_SHORT = 'Not checked';

export function hazardUnchecked(
  c: { uncheckedHazards?: readonly string[] | null } | null | undefined,
  key: HazardKey,
): boolean {
  return Array.isArray(c?.uncheckedHazards) && c!.uncheckedHazards!.includes(key);
}
