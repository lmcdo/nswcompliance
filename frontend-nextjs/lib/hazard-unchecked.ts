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

/** Every map-backed hazard the property lookup can report. */
export const ALL_HAZARDS: readonly HazardKey[] = [
  'bushfire', 'mine_subsidence', 'contaminated_land', 'drinking_water', 'coastal', 'anef',
];

/** Hazards a caller did NOT look up: everything except `answered`. Unqueried = unknown, never "No". */
export function hazardsNotQueried(answered: readonly HazardKey[] = []): HazardKey[] {
  return ALL_HAZARDS.filter((k) => !answered.includes(k));
}

/**
 * Bush fire answer from a property payload. `constraints` is the fresh lookup: when it carries
 * the field, its value wins even when null (map did not answer) — `??` would replace that null
 * with an older `environmental` boolean. Fall back to `environmental` only when the field is absent.
 */
export function bushfireFromPayload(
  constraints: Record<string, unknown> | null | undefined,
  environmental: Record<string, unknown> | null | undefined,
): boolean | null {
  const pick = (v: unknown): boolean | null => (typeof v === 'boolean' ? v : null);
  if (constraints && 'bushfireProne' in constraints) return pick(constraints.bushfireProne);
  return pick(environmental?.bushfireProne);
}
