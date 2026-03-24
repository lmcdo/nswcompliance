/**
 * Classify a Planning Portal heritageType string into boolean flags.
 *
 * Observed values from NSW Planning Portal Heritage Map layer (surveyed 2026-03-21):
 *   "Conservation Area - General"  → isConservationArea: true
 *   "Item - General"               → isItem: true
 *   "Item - Archaeological"        → isItem: true
 *
 * A property can carry multiple Heritage Map entries (e.g. item within a CA),
 * but heritageType is a single string from the first matching entry.
 * The patterns are intentionally broad to cover future Portal variants.
 */

export function classifyHeritageType(heritageType: string | undefined | null): {
  isConservationArea: boolean;
  isItem: boolean;
} {
  const t = (heritageType ?? '').toLowerCase();
  return {
    isConservationArea: t.includes('conservation area'),
    isItem: t.includes('item'),
  };
}
