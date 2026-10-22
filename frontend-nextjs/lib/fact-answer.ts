/**
 * Three-state answers for property facts the lookup can leave unknown.
 *
 * /api/property sets heritage / strata / corner lot to null, and leaves acid sulfate empty, when the
 * source did not answer (lib/lookup-not-checked.ts). Every reader goes through these, so an unknown
 * is shown as "Not checked" and never decides a pass. __tests__/unknown-never-no.test.ts blocks the
 * old `x ? 'Yes' : 'No'` / `x || false` readings.
 *
 * prior-art-checked: reuse not viable because lib/hazard-unchecked.ts covers the hazard maps only
 * (bush fire, mine subsidence, ...); these facts come from the planning layers and the lot.
 */
import { HAZARD_NOT_CHECKED_SHORT } from './hazard-unchecked';

export const NOT_CHECKED = HAZARD_NOT_CHECKED_SHORT;

/** true / false as given; anything else (null, undefined) is unknown. */
export function answer(v: unknown): boolean | null {
  return typeof v === 'boolean' ? v : null;
}

/** "Yes" / "No" / "Not checked". */
export function yesNo(v: unknown, yes = 'Yes', no = 'No'): string {
  const a = answer(v);
  return a === true ? yes : a === false ? no : NOT_CHECKED;
}

/** Heritage from a payload's `heritage` object ({ isHeritage }) or a bare boolean. Missing = unknown. */
export function heritageAnswer(heritage: unknown): boolean | null {
  if (heritage && typeof heritage === 'object') return answer((heritage as { isHeritage?: unknown }).isHeritage);
  return answer(heritage);
}

/**
 * Did any of these lookup checks (lib/lookup-not-checked.ts) fail to answer? A payload with NO list
 * (an older saved report, or a caller that never ran the lookup) cannot show any check answered, so it
 * counts as not checked. The ONLY reader of `notChecked` (__tests__/unknown-never-no.test.ts enforces it).
 */
export function wasNotChecked(constraints: { notChecked?: readonly string[] | null } | null | undefined, ...keys: string[]): boolean {
  const list = constraints?.notChecked;
  return !Array.isArray(list) || keys.some((k) => list.includes(k));
}

/**
 * Acid sulfate: the class string when mapped, false when the map answered and the lot is not on it,
 * null when neither the planning layers nor the PostGIS fallback answered.
 */
export function acidSulfateAnswer(
  constraints: { acidSulfateSoils?: string | null; notChecked?: readonly string[] | null } | null | undefined,
): string | false | null {
  if (constraints?.acidSulfateSoils) return constraints.acidSulfateSoils;
  // No not-checked list (an older saved payload) cannot show the map answered: unknown.
  if (!constraints || wasNotChecked(constraints, 'planning_layers', 'acid_sulfate')) return null;
  return false;
}
