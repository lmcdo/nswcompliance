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

export function battleaxeAwareLotWidth(
  lotDimensions: LotDimensionsLike | null | undefined,
): number | null {
  if (!lotDimensions) return null;

  const ba = lotDimensions.battleaxe;
  const headWidth = ba?.mainLotWidth;
  if (
    lotDimensions.lotType === 'battleaxe' &&
    typeof headWidth === 'number' &&
    headWidth > 0
  ) {
    // The handle frontage would understate a battleaxe — use the head width.
    return headWidth;
  }

  return typeof lotDimensions.frontage === 'number' ? lotDimensions.frontage : null;
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
    typeof headArea === 'number' &&
    headArea > 0 &&
    typeof headWidth === 'number' &&
    headWidth > 0
  ) {
    return headArea / headWidth;
  }

  return typeof lotDimensions.depth === 'number' ? lotDimensions.depth : null;
}
