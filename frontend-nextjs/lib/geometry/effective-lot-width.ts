/**
 * Eligibility-safe lot width.
 *
 * prior-art-checked: no existing lot-width helper — StateLevelControls.tsx
 * inlines `lotDimensions.frontage ?? geometry.frontageWidth ?? ...`; the
 * prior-art-guard match (ProvisionsByTocStructure.tsx) is an unrelated TOC
 * component sharing only the words aware/effective/width. Reuse not viable.
 *
 * Width-based SEPP / LMR tests (dual occupancy, manor house, minimum lot width)
 * must use the *developable* width of the lot. For a battleaxe (flag) lot the
 * cadastral "frontage" is the access HANDLE (e.g. 18.6 m) — feeding that into a
 * minimum-lot-width test understates the lot and can wrongly fail or pass
 * eligibility. The developable width is the head (mainLotWidth).
 *
 * Returns the head width for a battleaxe, otherwise the frontage; null when
 * nothing usable is present so callers keep their own fallback chain.
 */

interface BattleaxeLike {
  isBattleaxe?: boolean;
  mainLotWidth?: number | null;
  mainLotArea?: number | null;
}

interface LotDimensionsLike {
  lotType?: 'rectangular' | 'battleaxe' | 'irregular';
  frontage?: number | null;
  depth?: number | null;
  battleaxe?: BattleaxeLike | null;
}

/**
 * A measurement, or null. Nothing else counts as one.
 *
 * 0, NaN, Infinity and negatives all reach the width chain from upstream
 * sentinels and failed parseFloats, and each would otherwise be treated as a
 * frontage by one check and as missing by another. `typeof` alone does not
 * separate NaN from a number, and `> 0` alone does not separate Infinity.
 */
export function positiveFiniteOrNull(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : null;
}

export function battleaxeAwareLotWidth(
  lotDimensions: LotDimensionsLike | null | undefined,
): number | null {
  if (!lotDimensions) return null;

  const ba = lotDimensions.battleaxe;
  if (lotDimensions.lotType === 'battleaxe') {
    // The handle frontage would understate a battleaxe — use the head width.
    const headWidth = positiveFiniteOrNull(ba?.mainLotWidth);
    if (headWidth !== null) return headWidth;
  }

  // Normalised here rather than at the call site: a NaN or 0 frontage used to
  // escape this function, win a caller's `??` chain, and only then be rejected —
  // which discarded a valid later candidate. Cross-review, 2026-10-06.
  return positiveFiniteOrNull(lotDimensions.frontage);
}

/**
 * The first candidate that is an actual measurement, or null.
 *
 * Each candidate is normalised BEFORE the comparison, which is the whole point.
 * `a ?? b` falls through only on null and undefined, so an upstream 0 or NaN in
 * `a` wins and `b` is never consulted; wrapping the finished chain in a
 * normaliser then turns that into null and loses `b` entirely.
 */
export function firstMeasuredWidth(
  ...candidates: Array<number | null | undefined>
): number | null {
  for (const candidate of candidates) {
    const measured = positiveFiniteOrNull(candidate);
    if (measured !== null) return measured;
  }
  return null;
}

/**
 * Eligibility-safe lot depth, for buildable-footprint estimation.
 *
 * For a battleaxe the rectangular "depth" is the heuristic L-shape value (it
 * spans the handle), which understates the head. The head depth is approximated
 * as head area / head width. Returns the raw depth for non-battleaxe lots, or
 * null when nothing usable is present so callers keep their fallback.
 */
export function battleaxeAwareLotDepth(
  lotDimensions: LotDimensionsLike | null | undefined,
): number | null {
  if (!lotDimensions) return null;

  const ba = lotDimensions.battleaxe;
  const headArea = ba?.mainLotArea;
  const headWidth = ba?.mainLotWidth;
  if (
    lotDimensions.lotType === 'battleaxe' &&
    positiveFiniteOrNull(headArea) !== null &&
    positiveFiniteOrNull(headWidth) !== null
  ) {
    return positiveFiniteOrNull((headArea as number) / (headWidth as number));
  }

  return positiveFiniteOrNull(lotDimensions.depth);
}
